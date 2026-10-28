---
title: Provisionamento do nó de borda com Arch Linux ARM no Raspberry Pi 4
sidebar_label: Nó de borda no Raspberry Pi
sidebar_position: 2
description: Preparação de um cartão SD com Arch Linux ARM aarch64 ultra-leve para o Raspberry Pi 4, com Docker e captura de câmera por DVR (RTSP) ou USB.
---

# Provisionamento do nó de borda com Arch Linux ARM no Raspberry Pi 4

Esta página registra como foi preparado o sistema operacional do **nó de borda** (*Edge Computing*), o pequeno computador que roda os modelos de visão computacional no aviário. O dispositivo é um Raspberry Pi 4 Model B de 4 GB de RAM, como definido nos [requisitos](../sprint-1/requisitos.md). Os termos técnicos estão no [glossário](../sprint-1/glossario.md). A proposta para executar os containers dos modelos neste nó está em [Containers no nó de borda](./integracao-containers-no-no-de-borda.md).

## Em linguagem simples

O Raspberry Pi é um computador do tamanho de um cartão de crédito. Como qualquer computador, ele precisa de um sistema operacional, o programa que controla o equipamento, como o Windows num notebook. Aqui foi escolhido o **Arch Linux ARM**, uma versão do Linux feita para esse tipo de processador, instalada num **cartão SD**, o mesmo tipo de cartão usado em câmeras fotográficas.

O foco do trabalho foi deixar o sistema o mais enxuto possível. Um sistema comum gasta muita memória com coisas que o nó não usa, como tela, áudio e Bluetooth, e essa memória faria falta aos modelos que contam as aves. Por isso, o sistema instalado só liga à rede, aceita acesso remoto, executa Docker (a ferramenta que roda os modelos em containers) e lê as imagens das câmeras.

## Motivação

Os modelos da Sprint 2 identificam e contam as aves nos níveis N0, N1 e N2, como descrevem [Níveis e regra de contagem](../sprint-2/visao-computacional/niveis-e-regra-de-contagem.md) e [Detecção de aves com YOLO](../sprint-2/deteccao-de-aves.md). Eles rodam em containers e disputam a memória do equipamento com o próprio sistema operacional. O requisito RNF12 exige que a memória disponível fique em pelo menos 20% da RAM reconhecida durante 24 horas de teste. Por isso, tudo o que o sistema consome sem necessidade é memória que falta para o modelo.

Um sistema com interface gráfica, Bluetooth, áudio e registros (*logs*) em disco gasta centenas de megabytes e escreve o tempo todo no armazenamento. A escolha foi o oposto: o menor sistema que ainda sobe a rede, aceita acesso remoto, executa Docker e lê as imagens das câmeras.

## Escolhas

| Decisão | O que foi escolhido | Por quê |
| --- | --- | --- |
| Sistema | Arch Linux ARM `aarch64` (ARM de 64 bits), sem interface gráfica (*headless*, sem tela) | Instalação mínima, 64 bits, pacotes atuais e nenhum serviço que não seja habilitado de propósito |
| Armazenamento | Cartão SD, com sistema, Docker, imagens e dados no mesmo cartão | É o boot padrão do Raspberry Pi 4, dispensa outro dispositivo no case e simplifica a instalação em campo [1][2] |
| Bootloader | U-Boot, que já vem no pacote oficial | É o programa que liga o equipamento e carrega o sistema; não foi preciso trocá-lo, e ele lê o `boot.scr` da partição de boot [1] |
| Rede | `wpa_supplicant` com `systemd-networkd` | São os componentes que o pacote já inclui e que conectam ao Wi-Fi sem instalar nada extra [1] |
| Contêineres | Docker e Docker Compose, instalados no primeiro boot | Mantêm o sistema base pequeno e deixam a pilha dos modelos isolada [3] |

## Layout do armazenamento

O script cria no cartão SD uma tabela de partições `msdos`, o formato clássico de divisão de um disco, com duas partições.

| Partição | Tipo | Tamanho | Rótulo | Uso |
| --- | --- | --- | --- | --- |
| 1 | FAT32, com a flag `boot` | 512 MiB | `BOOT` | U-Boot, kernel (o núcleo do sistema), `initramfs`, dtbs e `config.txt` |
| 2 | ext4 | restante do dispositivo | `ROOT` | Sistema de arquivos raiz, onde ficam o sistema, o Docker e os dados |

O script baixa o pacote `ArchLinuxARM-rpi-aarch64-latest.tar.gz` (um *tarball*, que é um arquivo compactado) de `os.archlinuxarm.org` e confere o md5 publicado junto com ele, uma assinatura que prova que o arquivo não veio corrompido, antes de gravar [1]. Depois extrai o arquivo com `bsdtar -xpf`, que preserva permissões, e move o conteúdo de `/boot` para a partição `BOOT`.

### Boot pelo cartão SD

Esperava-se encontrar um `cmdline.txt` apontando para `/dev/mmcblk0p2`, mas o pacote atual não o tem. O arquivo `kernel8.img` é o U-Boot, e os argumentos do kernel vêm do `boot.scr`, compilado a partir do `boot.txt`. Nesse arquivo, a raiz já é definida como `root=PARTUUID=<partição 2 do dispositivo de boot> rw rootwait`. O `PARTUUID` é um identificador único da partição. Assim, o sistema monta a raiz no mesmo dispositivo de onde o U-Boot carregou o kernel, que aqui é o cartão SD, e o `rootwait` espera o dispositivo responder.

Por isso essa linha foi mantida, em vez de trocada por `root=LABEL=ROOT`, o que exigiria recompilar o `boot.scr` com `mkimage`. O que foi alterado é o `/etc/fstab`, o arquivo que diz ao sistema o que montar e onde, e que originalmente apontava para `/dev/mmcblk0p1`. Ele passa a usar rótulos e a montar a raiz com `noatime`, para que a leitura de um arquivo não gere uma escrita no cartão:

```text
LABEL=ROOT  /      ext4  defaults,noatime  0  1
LABEL=BOOT  /boot  vfat  defaults,noatime  0  0
```

Esse ajuste importa também depois: uma atualização de kernel com `pacman -Syu` grava os arquivos em `/boot`, e eles precisam ir para a partição certa.

## Otimização de memória

| Ajuste | Onde | Efeito esperado |
| --- | --- | --- |
| `gpu_mem=16` | `config.txt` | Reserva só 16 MB de RAM para a GPU (o chip de imagem), que não é usada sem monitor |
| `dtoverlay=disable-bt` | `config.txt` | Desliga o Bluetooth |
| `dtparam=audio=off` | `config.txt` | Desliga o áudio |
| Módulos de Bluetooth e áudio na lista de bloqueio | `/etc/modprobe.d/raiar-lowram.conf` | Impede que o kernel carregue esses módulos |
| `Storage=volatile` e `SystemMaxUse=30M` | `/etc/systemd/journald.conf` | Mantém o registro do sistema na memória, limitado a 30 MB, e poupa escrita no cartão SD [4] |
| `vm.swappiness=10` | `/etc/sysctl.d/99-raiar-performance.conf` | Faz o kernel evitar o swap, a área de apoio que estende a memória, se houver [5] |

Há duas ressalvas. Primeiro, como o U-Boot carrega o arquivo de descrição do hardware (dtb) da pasta `dtbs` por conta própria, o kernel provavelmente ignora os overlays do `config.txt`. As linhas foram mantidas e acrescentou-se o bloqueio dos módulos, que age no próprio kernel. Segundo, a imagem não define swap, então o `vm.swappiness` só passa a valer quando um swap for habilitado.

## Desgaste do cartão SD

Com todo o armazenamento no cartão, o desgaste causado pelas escritas passa a ser o principal risco de longo prazo, porque cada cartão suporta um número limitado de gravações. Por isso o nó foi configurado para escrever o mínimo possível.

| Medida | Efeito |
| --- | --- |
| `Storage=volatile` no `journald` | Os registros do sistema ficam na memória e não gastam o cartão |
| `noatime` na raiz e em `/boot` | Ler um arquivo não gera escrita |
| `zram` no lugar de swap em disco | Os picos de memória não escrevem no cartão |
| Registro dos containers limitado a 3 arquivos de 10 MB | O registro dos containers não cresce sem limite |
| `/tmp` e `/frames` em `tmpfs` nos containers | Os quadros capturados ficam na memória e não passam pelo cartão |
| Apenas o SQLite em `/opt/raiar/data` | A única escrita contínua são os resultados, que são pequenos |

A recomendação é usar um cartão de **alta resistência** (*high endurance*), de marca conhecida, e não um cartão comum, e guardar uma cópia do cartão pronto (uma imagem criada com `dd`), de modo que trocar um cartão defeituoso seja regravar essa imagem, e não reinstalar tudo. O volume de escrita real do nó será acompanhado nos testes de 24 horas, olhando, por exemplo, o total de bytes escritos no dispositivo.

## Wi-Fi e acesso remoto

O script lê a conexão Wi-Fi ativa do notebook pelo `nmcli`. Com `wpa_passphrase`, ele grava em `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf` o PSK já derivado, uma versão embaralhada da senha, e não a senha em texto, com permissão `600`. Também cria o arquivo `wlan.network` do `systemd-networkd`, com DHCP (a atribuição automática de endereço de rede), e habilita o serviço `wpa_supplicant@wlan0` [6]. O `sshd` (que permite o acesso remoto seguro por SSH), o `systemd-networkd`, o `systemd-resolved` e o `systemd-timesyncd` (que acerta o relógio pela internet) já vêm habilitados. O nome do nó é `raiar-edge-01`.

Para usar o nó em outras redes, `src/edge/add_wifi.sh` acrescenta uma rede ao mesmo arquivo, sem apagar as anteriores, e aceita uma prioridade. O Raspberry Pi entra na rede conhecida de maior prioridade que estiver ao alcance. O exemplo é `/root/add_wifi.sh "NOME_DA_REDE" "SENHA" 5`, e `--list` mostra as redes gravadas. O firmware do Wi-Fi do Raspberry Pi (`linux-firmware-broadcom`) é preservado no enxugamento justamente para isso.

O cartão SD guarda a credencial do Wi-Fi. Quem o tiver nas mãos pode lê-la como root (administrador), então o cartão deve ser tratado como sensível. As senhas padrão do Arch Linux ARM (`root` e `alarm`) devem ser trocadas com `passwd` no primeiro acesso.

## Primeiro boot: Docker e câmera

No cartão fica o script `/root/setup_raiar_node.sh`, que executa, como root:

1. confere se `/boot` está montado, para o kernel novo não cair no lugar errado;
2. liga a sincronização de horário e espera por ela, porque o Raspberry Pi não tem relógio de hardware e um horário errado quebra a verificação do `pacman`, o instalador de pacotes;
3. executa `pacman-key --init` e `pacman-key --populate archlinuxarm`, que preparam as chaves de verificação dos pacotes;
4. instala só `docker`, `docker-compose`, `v4l-utils` e `htop` com `pacman -Syu`; `git` e `ffmpeg` ficam de fora, e a variável `EXTRA_PKGS` os acrescenta quando necessários;
5. limita o registro dos containers a 3 arquivos de 10 MB, em `/etc/docker/daemon.json`;
6. habilita o Docker com `systemctl enable --now docker`;
7. inclui o usuário `alarm` nos grupos `docker` e `video` e cria `/opt/raiar`;
8. com `ZRAM=1`, habilita o swap comprimido na RAM (`zram`), que absorve picos de memória dos modelos sem desgastar o cartão SD [8].

A fonte preferida das imagens é o **servidor de câmeras (DVR)** do aviário, que o nó lê pela rede por **RTSP**, um protocolo que entrega o vídeo de uma câmera pela rede, sem ligar cada câmera ao Raspberry Pi. Isso segue a [arquitetura preliminar](../sprint-2/arquitetura-preliminar.md), que registra que as câmeras da Raiar não têm entrada USB e deixa em aberto o acesso por rede ou pela porta USB do servidor. O nó só precisa de um caminho de rede até o DVR, de preferência por cabo Ethernet, com endereço fixo ou reservado no roteador. Nenhuma configuração extra do sistema é necessária: o container abre a URL `rtsp://usuario:senha@IP_DO_DVR:554/...` com o OpenCV e o FFmpeg embutido. Para conferir o acesso a partir do nó, usa-se `nc -zv IP_DO_DVR 554`. O modelo do DVR, o RTSP habilitado, o codec e o número de canais ainda serão confirmados com a Raiar.

Há uma alternativa técnica no nó: uma câmera USB própria, que seria instalada ao lado das existentes, já que as da Raiar não têm USB. Ela aparece como `/dev/video0` e é acessada pela interface **V4L2**, que o kernel expõe por arquivos de dispositivo [7]. Para conferir, usa-se `v4l2-ctl --list-devices`. Para passá-la a um container, o comando é:

```bash
docker run --rm --device /dev/video0 --group-add "$(getent group video | cut -d: -f3)" <imagem>
```

Usa-se o número do grupo `video` do sistema do nó, e não o nome. Dentro de uma imagem baseada em Debian o grupo `video` tem outro número, e o nome não corresponderia ao grupo dono do dispositivo, o que impediria um usuário sem privilégios de abrir a câmera. No nó, o grupo `video` é o 983. O `v4l-utils` e o grupo `video` continuam no nó para que essa alternativa funcione sem reconfigurar o sistema.

## Enxugamento do sistema

Como armazenamento e RAM são escassos, mediu-se o que a imagem instala antes de usá-la. Ela ocupa cerca de 2,1 GB, dos quais aproximadamente 1 GB é firmware (programas internos de componentes) de placas de vídeo e de Wi-Fi de computadores comuns, que o Raspberry Pi nunca usa. O script `src/edge/slim_arch_rpi4.sh` remove o que não pertence ao escopo do nó, sem precisar de internet.

| Item | Tamanho aproximado | Decisão |
| --- | --- | --- |
| Firmware Intel, NVIDIA, Atheros, AMD, MediaTek, TI e outros | 1.010 MB | Removido; ficam só o da Broadcom (Wi-Fi do Pi) e o do Raspberry Pi |
| Firmware Realtek | 39 MB | Removido, a menos que haja adaptador USB Realtek (`KEEP_REALTEK=1`) |
| `vim` e `vim-runtime` | 46 MB | Removidos; o `nano` permanece |
| Manuais, documentação e traduções | cerca de 140 MB | Apagados, mantendo `pt_BR`; `NoExtract` no `pacman.conf` impede que voltem |
| `netctl`, `dialog`, `dhcpcd` e `wireless_tools` | poucos MB | Removidos, pois a rede usa `systemd-networkd` e `wpa_supplicant` |
| `ffmpeg` e `git` | variável | Não instalados; cada container leva o que precisa |

O script também desabilita o `systemd-networkd-wait-online`, que pode atrasar o boot em até dois minutos quando só há Wi-Fi. O kernel (cerca de 365 MB) permanece, porque reduzi-lo exigiria escolher módulos um a um. O maior consumo futuro de armazenamento serão as imagens dos containers. Por isso os modelos deverão sair de bibliotecas pesadas, como o PyTorch completo, para um *runtime* (motor de execução) de inferência menor, em imagens base enxutas.

O Docker mantém dois processos residentes (`dockerd` e `containerd`) e consome memória mesmo sem containers. O Docker foi mantido porque a equipe containeriza com ele, mas esse custo será medido no nó antes de decidir por uma alternativa sem *daemon*, como o Podman.

## Reprodução com o script do repositório

O procedimento está em `src/edge/provision_arch_rpi4.sh`, que também grava em `/root` os scripts `setup_raiar_node.sh` e `slim_arch_rpi4.sh` (e o `clone_to_sd.sh`, usado só no caminho alternativo). Ele roda como root no notebook de desenvolvimento e recebe o cartão SD como destino:

```bash
sudo src/edge/provision_arch_rpi4.sh /dev/mmcblk0   # leitor de cartão interno
sudo src/edge/provision_arch_rpi4.sh /dev/sdX       # leitor de cartão USB
```

Antes de apagar, o script recusa qualquer dispositivo que não seja um disco inteiro, que seja o disco do sistema do notebook ou que contenha `/`, `/home` ou `/boot`. Um dispositivo `sdX` precisa ser removível e estar em barramento USB, como um leitor externo; o `mmcblk*` do leitor interno é aceito mesmo constando como não removível. Em seguida o script mostra o dispositivo e pede duas confirmações, para evitar apagar o disco errado. As variáveis de ambiente opcionais são:

| Variável | Função |
| --- | --- |
| `WIFI_SSID` e `WIFI_PSK` | Rede do nó; se ausentes, usa a conexão Wi-Fi ativa do notebook |
| `NODE_HOSTNAME` | Nome do nó, com `raiar-edge-01` como padrão |
| `SSH_PUBKEY_FILE` | Chave pública instalada para o usuário `alarm`; por padrão procura `~/.ssh/id_ed25519.pub` ou `id_rsa.pub` |
| `TARBALL` | Caminho de um pacote já baixado |

O nó em uso foi provisionado pelo caminho alternativo descrito adiante.

## Roteiro completo

Este é o caminho recomendado, na ordem em que deve ser repetido. As etapas 1 e 2 acontecem no notebook, e as demais, no próprio nó.

1. Identificar o cartão SD com `lsblk` e conferir o dispositivo (`mmcblk0` ou `sdX`). Se algum gerenciador de arquivos mantiver o cartão aberto, fechar a janela antes de gravar.
2. Rodar `provision_arch_rpi4.sh` com o dispositivo e a confirmação `--yes-erase`. A gravação de 2 GB num cartão lento é demorada, e a maior parte do tempo fica no `sync` final, que garante que tudo foi escrito.
3. Colocar o cartão no Raspberry Pi 4 e ligar. O Raspberry Pi não tem botão de ligar: ele liga quando recebe energia, e `poweroff` seguido da luz verde parada é o desligamento seguro. O cartão SD é o boot padrão, então não é preciso alterar a ordem de boot da EEPROM.
4. Entrar como `root` e ajustar o teclado com `loadkeys br-abnt2`. Esse ajuste se perde a cada reinício.
5. Instalar o que falta e rodar `slim_arch_rpi4.sh`, que mostra a lista de remoção e pede confirmação.
6. Rodar `RAIAR_USER=raiar ZRAM=1 setup_raiar_node.sh`, reiniciar e conferir Wi-Fi, Docker e `zram`.
7. Trocar as senhas padrão com `passwd`.
8. Com o nó configurado, gerar a imagem de reserva do cartão para recuperação.

### Caminho alternativo: notebook sem leitor de cartão

O notebook usado não tem leitor de cartão, então o nó atual foi preparado por este caminho. O destino final continua sendo o cartão SD; o pen drive é só um veículo de partida e não faz parte do nó.

1. Gravar um pen drive USB com o mesmo `provision_arch_rpi4.sh` (`/dev/sdX`), que também grava o `clone_to_sd.sh` em `/root`.
2. Ligar o Raspberry Pi pelo pen drive, **sem** cartão SD encaixado. Se o cartão tiver outro sistema, o Raspberry Pi inicia por ele; nesse caso, é preciso pôr o USB primeiro em `raspi-config`, na ordem de boot.
3. Instalar `parted` e `dosfstools` com `pacman -Syu`, depois de `timedatectl set-ntp true` e `pacman-key --init`, e reiniciar, para o kernel atualizado e seus módulos coincidirem.
4. Encaixar o cartão com o Raspberry Pi ligado e rodar `clone_to_sd.sh`, que particiona o cartão com o mesmo layout e copia `/boot` e a raiz. Isso funciona sem reescrever nada porque a raiz é identificada pelo `PARTUUID` do dispositivo de boot e o `fstab` usa rótulos.
5. Desligar, tirar o pen drive e ligar de novo: o nó inicia só pelo cartão. A partir daqui, o roteiro segue da etapa 4 acima.

### Acesso ao nó

O `root` não entra por SSH com senha, que é o padrão do OpenSSH atual. Para operar sem teclado e monitor, define-se a senha do usuário `raiar` e envia-se a chave pública com `ssh-copy-id`, o que dispensa digitar a senha a cada acesso. Desta forma, o `root` só é usado localmente. Para copiar arquivos antes de ter SSH, sobe-se no notebook um servidor temporário com `python3 -m http.server 8000 --directory src/edge` e baixam-se os scripts no nó com `curl`.

### Problemas encontrados

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `wipefs` informa dispositivo ocupado | O gerenciador de arquivos mantinha o dispositivo aberto | Fechar a janela; o script agora falha com mensagem clara |
| O Raspberry Pi abre o Raspberry Pi OS | No caminho alternativo, o cartão tinha outro sistema e prioridade sobre o USB | Colocar USB primeiro em `raspi-config` ou usar um cartão vazio |
| `comando ausente: parted` | A imagem não traz `parted` nem `dosfstools` | Instalar os dois e reiniciar |
| Erro de leitura e escrita em `mmcblk0` | Provavelmente o cartão encaixado com o Pi ligado; com ele presente desde o boot, a cópia funcionou | Manter o SD encaixado antes de ligar |
| `command not found` para `hostname` | O sistema enxuto não instala o programa | Usar `cat /etc/hostname` |
| SSH recusa `root` e `alarm` | Usuário `alarm` removido e `root` sem senha por SSH | Criar `raiar` e usar chave |
| Download de 850 MB a 150 KB/s | O servidor de download automático era lento | Usar outro espelho (*mirror*), como `fl.us.mirror.archlinuxarm.org` |
| `pacman -Rns` recusa `--print` | As opções `-n` e `--print` são incompatíveis | A prévia usa `-Rs` |

## Situação atual e limites

O nó atual roda inteiramente num cartão SD, sem pen drive: como o notebook não tem leitor, gravou-se antes um pen drive de partida e copiou-se o sistema dele para o cartão, de onde o nó já inicia sozinho. Depois aplicaram-se o enxugamento e o primeiro boot no próprio nó, e mediram-se os valores abaixo.

| Medida | Antes | Depois |
| --- | --- | --- |
| Armazenamento usado na raiz | 2.401 MB | 791 MB após o enxugamento; 1.100 MB com Docker, Compose e `zram` |
| RAM em uso, sem containers | 177 MB de 3.815 MB | 220 MB, já com o Docker ativo |
| Swap | nenhum | `zram` de 1,9 GB, com prioridade 100 |

A capacidade total do cartão e o espaço livre devem ser conferidos no nó com `df -h /` e `lsblk`, porque uma medição anterior registrou cerca de 29 GB e o cartão em uso mostra menos. Esse dado define quanto sobra para as imagens dos containers.

O `dockerd` ocupa cerca de 84 MB e o `containerd` cerca de 40 MB de memória residente, sem nenhum container em execução. É esse o custo fixo do Docker no nó. Com `zram`, o `vm.swappiness` passa a 100, e não mais a 10 como a configuração inicial, porque o swap comprimido deve ser preferido ao descarte de cache.

O Docker executou o container `hello-world` com sucesso. A captura pelo DVR ou por câmera USB, a estabilidade do nó em 24 horas (exigida pelo RNF12), a memória disponível com o modelo carregado e a imagem do container em `arm64` serão verificadas na etapa de validação descrita em [Containers no nó de borda](./integracao-containers-no-no-de-borda.md).

## Referências {#referencias}

[1] ARCH LINUX ARM. **Raspberry Pi 4**. Disponível em: [https://archlinuxarm.org/platforms/armv8/broadcom/raspberry-pi-4](https://archlinuxarm.org/platforms/armv8/broadcom/raspberry-pi-4). Acesso em: 25 out. 2026.

[2] RASPBERRY PI LTD. **Raspberry Pi documentation: computers**. Disponível em: [https://www.raspberrypi.com/documentation/computers/raspberry-pi.html](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html). Acesso em: 25 out. 2026.

[3] DOCKER INC. **Install Docker Engine**. Disponível em: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/). Acesso em: 25 out. 2026.

[4] FREEDESKTOP.ORG. **journald.conf**. Disponível em: [https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html). Acesso em: 25 out. 2026.

[5] THE LINUX KERNEL ORGANIZATION. **Documentation for /proc/sys/vm/**. Disponível em: [https://docs.kernel.org/admin-guide/sysctl/vm.html](https://docs.kernel.org/admin-guide/sysctl/vm.html). Acesso em: 25 out. 2026.

[6] ARCH LINUX WIKI. **wpa_supplicant**. Disponível em: [https://wiki.archlinux.org/title/Wpa_supplicant](https://wiki.archlinux.org/title/Wpa_supplicant). Acesso em: 25 out. 2026.

[7] THE LINUX KERNEL ORGANIZATION. **Video for Linux API**. Disponível em: [https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html). Acesso em: 25 out. 2026.

[8] ARCH LINUX WIKI. **Zram**. Disponível em: [https://wiki.archlinux.org/title/Zram](https://wiki.archlinux.org/title/Zram). Acesso em: 26 out. 2026.
