---
title: Provisionamento do nó de borda com Arch Linux ARM no Raspberry Pi 4
sidebar_label: Nó de borda no Raspberry Pi
sidebar_position: 2
description: Preparação de um Pen Drive USB com Arch Linux ARM aarch64 ultra-leve para o Raspberry Pi 4, com Docker e captura de câmera por DVR (RTSP) ou USB.
---

# Provisionamento do nó de borda com Arch Linux ARM no Raspberry Pi 4

Esta página registra como eu preparei o sistema operacional do **nó de borda** (*Edge Computing*) que roda os modelos de visão computacional no aviário. O dispositivo é um Raspberry Pi 4 Model B de 4 GB de RAM, como definido nos [requisitos](../sprint-1/requisitos.md). Os termos técnicos estão no [glossário](../sprint-1/glossario.md). A proposta para executar os containers dos modelos neste nó está em [Containers no nó de borda](./integracao-containers-no-no-de-borda.md).

## Motivação

Os modelos da Sprint 2 identificam e contam as aves nos níveis N0, N1 e N2, como descrevem [Níveis e regra de contagem](../sprint-2/visao-computacional/niveis-e-regra-de-contagem.md) e [Detecção de aves com YOLO](../sprint-2/deteccao-de-aves.md). Eles rodam em containers e disputam a memória do equipamento com o próprio sistema operacional. O requisito RNF12 exige que a memória disponível fique em pelo menos 20% da RAM reconhecida durante 24 horas de teste. Por isso, tudo o que o sistema consome sem necessidade é memória que falta para o modelo.

Um sistema com interface gráfica, Bluetooth, áudio e logs em disco gasta centenas de megabytes e escreve o tempo todo no armazenamento. Eu quis o oposto: o menor sistema que ainda sobe a rede, aceita acesso remoto, executa Docker e lê as imagens das câmeras.

## Escolhas

| Decisão | O que escolhi | Por quê |
| --- | --- | --- |
| Sistema | Arch Linux ARM `aarch64`, sem interface gráfica (*headless*) | Instalação mínima, 64 bits, pacotes atuais e nenhum serviço que eu não habilite |
| Armazenamento | Pen Drive USB com boot direto (`USB-MSD`) | O Raspberry Pi 4 consegue iniciar por USB, e dispensa o cartão SD como único ponto de falha [1][2] |
| Bootloader | U-Boot, que já vem no tarball oficial | Não precisei trocar o bootloader; ele lê o `boot.scr` da partição de boot [1] |
| Rede | `wpa_supplicant` com `systemd-networkd` | São os componentes que o tarball já inclui; não precisei de pacotes extras para o Wi-Fi subir sozinho [1] |
| Contêineres | Docker e Docker Compose, instalados no primeiro boot | Mantém o sistema base pequeno e deixa a pilha dos modelos isolada [3] |

## Layout do armazenamento

O script cria uma tabela de partições `msdos` com duas partições.

| Partição | Tipo | Tamanho | Rótulo | Uso |
| --- | --- | --- | --- | --- |
| 1 | FAT32, com a flag `boot` | 512 MiB | `BOOT` | U-Boot, kernel, `initramfs`, dtbs e `config.txt` |
| 2 | ext4 | restante do dispositivo | `ROOT` | Sistema de arquivos raiz |

Baixo o tarball `ArchLinuxARM-rpi-aarch64-latest.tar.gz` de `os.archlinuxarm.org` e confiro o md5 publicado junto com ele antes de gravar [1]. Depois extraio o arquivo com `bsdtar -xpf`, que preserva permissões, e movo o conteúdo de `/boot` para a partição `BOOT`.

### Boot sem cartão SD

Esperava encontrar um `cmdline.txt` apontando para `/dev/mmcblk0p2`, mas o tarball atual não o tem. O arquivo `kernel8.img` é o U-Boot, e os argumentos do kernel vêm do `boot.scr`, compilado a partir do `boot.txt`. Nesse arquivo, a raiz já é definida como `root=PARTUUID=<partição 2 do dispositivo de boot> rw rootwait`. Assim, o sistema monta a raiz no mesmo dispositivo de onde o U-Boot carregou o kernel, seja USB ou SD, e o `rootwait` dá tempo para a controladora USB 3.0 responder.

Por isso mantive essa linha e não a troquei por `root=LABEL=ROOT`, o que exigiria recompilar o `boot.scr` com `mkimage`. O que mudei foi o `/etc/fstab`, que originalmente apontava para `/dev/mmcblk0p1`:

```text
LABEL=BOOT  /boot  vfat  defaults,noatime  0  0
```

Esse ajuste importa também depois: uma atualização de kernel com `pacman -Syu` grava os arquivos em `/boot`, e eles precisam ir para a partição certa.

## Otimização de memória

| Ajuste | Onde | Efeito esperado |
| --- | --- | --- |
| `gpu_mem=16` | `config.txt` | Reserva só 16 MB de RAM para a GPU, que não uso sem monitor |
| `dtoverlay=disable-bt` | `config.txt` | Desliga o Bluetooth |
| `dtparam=audio=off` | `config.txt` | Desliga o áudio |
| Módulos de Bluetooth e áudio na lista de bloqueio | `/etc/modprobe.d/raiar-lowram.conf` | Impede que o kernel carregue esses módulos |
| `Storage=volatile` e `SystemMaxUse=30M` | `/etc/systemd/journald.conf` | Mantém o log na memória, limitado a 30 MB, e poupa escrita no pen drive [4] |
| `vm.swappiness=10` | `/etc/sysctl.d/99-raiar-performance.conf` | Faz o kernel evitar o swap, se houver [5] |

Há duas ressalvas. Primeiro, como o U-Boot carrega o dtb da pasta `dtbs` por conta própria, o kernel provavelmente ignora os overlays do `config.txt`. Mantive as linhas pedidas e adicionei o bloqueio dos módulos, que age no próprio kernel. Segundo, a imagem não define swap, então o `vm.swappiness` só passa a valer quando eu habilitar um.

## Wi-Fi e acesso remoto

O script lê a conexão Wi-Fi ativa do notebook pelo `nmcli`. Com `wpa_passphrase`, ele grava em `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf` o PSK já derivado, e não a senha em texto, com permissão `600`. Também cria o arquivo `wlan.network` do `systemd-networkd`, com DHCP, e habilita o serviço `wpa_supplicant@wlan0` [6]. O `sshd`, o `systemd-networkd`, o `systemd-resolved` e o `systemd-timesyncd` já vêm habilitados. O nome do nó é `raiar-edge-01`.

Para usar o nó em outras redes, `src/edge/add_wifi.sh` acrescenta uma rede ao mesmo arquivo, sem apagar as anteriores, e aceita uma prioridade. O Raspberry Pi entra na rede conhecida de maior prioridade que estiver ao alcance. O exemplo é `/root/add_wifi.sh "NOME_DA_REDE" "SENHA" 5`, e `--list` mostra as redes gravadas. O firmware do Wi-Fi do Raspberry Pi (`linux-firmware-broadcom`) é preservado no enxugamento justamente para isso.

O pen drive guarda a credencial do Wi-Fi. Quem o tiver nas mãos pode lê-la como root, então trato o dispositivo como sensível. As senhas padrão do Arch Linux ARM (`root` e `alarm`) devem ser trocadas com `passwd` no primeiro acesso.

## Primeiro boot: Docker e câmera

Dentro do pen drive deixo `/root/setup_raiar_node.sh`, que executa, como root:

1. confere se `/boot` está montado, para o kernel novo não cair no lugar errado;
2. liga a sincronização de horário e espera por ela, porque o Raspberry Pi não tem relógio de hardware e um horário errado quebra a verificação do `pacman`;
3. executa `pacman-key --init` e `pacman-key --populate archlinuxarm`;
4. instala só `docker`, `docker-compose`, `v4l-utils` e `htop` com `pacman -Syu`; `git` e `ffmpeg` ficam de fora, e a variável `EXTRA_PKGS` os acrescenta quando necessários;
5. limita o log dos containers a 3 arquivos de 10 MB, em `/etc/docker/daemon.json`;
6. habilita o Docker com `systemctl enable --now docker`;
7. inclui o usuário `alarm` nos grupos `docker` e `video` e cria `/opt/raiar`;
8. com `ZRAM=1`, habilita o swap comprimido na RAM (`zram`), que absorve picos de memória dos modelos sem desgastar o cartão SD [8].

A fonte preferida das imagens é o **servidor de câmeras (DVR)** do aviário, que o nó lê pela rede por **RTSP**, sem ligar cada câmera ao Raspberry Pi. Isso segue a [arquitetura preliminar](../sprint-2/arquitetura-preliminar.md), que registra que as câmeras da Raiar não têm entrada USB e deixa em aberto o acesso por rede ou pela porta USB do servidor. O nó só precisa de um caminho de rede até o DVR, de preferência por cabo Ethernet, com endereço fixo ou reservado no roteador. Nenhuma configuração extra do sistema é necessária: o container abre a URL `rtsp://usuario:senha@IP_DO_DVR:554/...` com o OpenCV e o FFmpeg embutido. Para conferir o acesso a partir do nó, uso `nc -zv IP_DO_DVR 554`. O modelo do DVR, o RTSP habilitado, o codec e o número de canais ainda serão confirmados com a Raiar.

Mantive uma alternativa técnica no nó: uma câmera USB própria, que seria instalada ao lado das existentes, já que as da Raiar não têm USB. Ela aparece como `/dev/video0` e é acessada pela interface **V4L2**, que o kernel expõe por arquivos de dispositivo [7]. Para conferir, uso `v4l2-ctl --list-devices`. Para passá-la a um container, uso:

```bash
docker run --rm --device /dev/video0 --group-add "$(getent group video | cut -d: -f3)" <imagem>
```

Uso o número do grupo `video` do sistema do nó, e não o nome. Dentro de uma imagem baseada em Debian o grupo `video` tem outro número, e o nome não corresponderia ao grupo dono do dispositivo, o que impediria um usuário sem privilégios de abrir a câmera. No nó, o grupo `video` é o 983. O `v4l-utils` e o grupo `video` continuam no nó para que essa alternativa funcione sem reconfigurar o sistema.

## Enxugamento do sistema

Como armazenamento e RAM são escassos, medi o que a imagem instala antes de usá-la. Ela ocupa cerca de 2,1 GB, dos quais aproximadamente 1 GB é firmware de placas de vídeo e de Wi-Fi de computadores comuns, que o Raspberry Pi nunca usa. O script `src/edge/slim_arch_rpi4.sh` remove o que não pertence ao escopo do nó, sem precisar de internet.

| Item | Tamanho aproximado | Decisão |
| --- | --- | --- |
| Firmware Intel, NVIDIA, Atheros, AMD, MediaTek, TI e outros | 1.010 MB | Removido; ficam só o da Broadcom (Wi-Fi do Pi) e o do Raspberry Pi |
| Firmware Realtek | 39 MB | Removido, a menos que haja adaptador USB Realtek (`KEEP_REALTEK=1`) |
| `vim` e `vim-runtime` | 46 MB | Removidos; o `nano` permanece |
| Manuais, documentação e traduções | cerca de 140 MB | Apagados, mantendo `pt_BR`; `NoExtract` no `pacman.conf` impede que voltem |
| `netctl`, `dialog`, `dhcpcd` e `wireless_tools` | poucos MB | Removidos, pois a rede usa `systemd-networkd` e `wpa_supplicant` |
| `ffmpeg` e `git` | variável | Não instalados; cada container leva o que precisa |

Também desabilito o `systemd-networkd-wait-online`, que pode atrasar o boot em até dois minutos quando só há Wi-Fi. O kernel (cerca de 365 MB) permanece, porque reduzi-lo exigiria escolher módulos um a um. O maior consumo futuro de armazenamento serão as imagens dos containers. Por isso os modelos deverão sair de bibliotecas pesadas, como o PyTorch completo, para um *runtime* de inferência menor, em imagens base enxutas.

O Docker mantém dois processos residentes (`dockerd` e `containerd`) e consome memória mesmo sem containers. Mantive o Docker porque a equipe containeriza com ele, mas medirei esse custo no nó antes de decidir por uma alternativa sem *daemon*, como o Podman.

## Reprodução com o script do repositório

O procedimento está em `src/edge/provision_arch_rpi4.sh`, que também grava em `/root` os scripts `setup_raiar_node.sh`, `slim_arch_rpi4.sh` e `clone_to_sd.sh`. Ele roda como root no notebook de desenvolvimento e recebe o dispositivo de destino:

```bash
sudo src/edge/provision_arch_rpi4.sh /dev/sdX
```

Antes de apagar, o script recusa qualquer dispositivo que não seja um disco inteiro, removível e em barramento USB, ou que contenha `/`, `/home` ou `/boot` do notebook. Em seguida mostra o dispositivo e pede duas confirmações. As variáveis de ambiente opcionais são:

| Variável | Função |
| --- | --- |
| `WIFI_SSID` e `WIFI_PSK` | Rede do nó; se ausentes, usa a conexão Wi-Fi ativa do notebook |
| `NODE_HOSTNAME` | Nome do nó, com `raiar-edge-01` como padrão |
| `SSH_PUBKEY_FILE` | Chave pública instalada para o usuário `alarm`; por padrão procura `~/.ssh/id_ed25519.pub` ou `id_rsa.pub` |
| `TARBALL` | Caminho de um tarball já baixado |

### Clonagem para um cartão SD

Meu notebook não tem leitor de cartão. Por isso criei `src/edge/clone_to_sd.sh`, que o script principal grava em `/root` do pen drive. Com o Raspberry Pi ligado pelo pen drive, e sem SD, encaixo o cartão e o script o particiona com o mesmo layout e copia `/boot` e a raiz. Isso funciona sem reescrever nada porque a raiz é identificada pelo `PARTUUID` do dispositivo de boot e o `fstab` usa rótulos. Depois só preciso tirar o pen drive. A imagem base não traz `parted` nem `dosfstools`, então antes da clonagem instalo os dois com `pacman -Syu` e reinicio o Raspberry Pi, para o kernel atualizado e seus módulos coincidirem.

## Roteiro completo

Este é o caminho que segui, na ordem em que deve ser repetido. As etapas 1 a 3 acontecem no notebook, e as demais, no próprio nó.

1. Identifico o pen drive com `lsblk` e confirmo que é removível e USB. Se algum gerenciador de arquivos mantiver a pasta aberta, fecho a janela antes de gravar.
2. Rodo `provision_arch_rpi4.sh` com o dispositivo e a confirmação `--yes-erase`. A gravação de 2 GB num pen drive lento é demorada, e a maior parte do tempo fica no `sync` final.
3. Espeto o pen drive numa porta USB 3.0 do Raspberry Pi 4, sem cartão SD, e ligo. O Raspberry Pi não tem botão de ligar: ele liga quando recebe energia, e `poweroff` seguido da luz verde parada é o desligamento seguro.
4. Se o cartão SD tiver outro sistema, o Raspberry Pi inicia por ele. Nesse caso, mudo a ordem de boot para USB primeiro, em `raspi-config`, na opção de ordem de boot, e reinicio com os dois conectados.
5. Entro como `root` e ajusto o teclado com `loadkeys br-abnt2`. Esse ajuste se perde a cada reinício.
6. Instalo `parted` e `dosfstools` com `pacman -Syu`, depois de `timedatectl set-ntp true` e `pacman-key --init`, e reinicio.
7. Rodo `clone_to_sd.sh` para copiar o sistema para o cartão SD, e depois desligo e tiro o pen drive.
8. Rodo `slim_arch_rpi4.sh`, que mostra a lista de remoção e pede confirmação.
9. Rodo `RAIAR_USER=raiar ZRAM=1 setup_raiar_node.sh`, reinicio e confiro Wi-Fi, Docker e `zram`.
10. Troco as senhas padrão com `passwd`.

As etapas 6 e 7 só existem porque meu notebook não tem leitor de cartão. Quem tiver um leitor pode gravar direto no SD com `provision_arch_rpi4.sh`, por exemplo `/dev/sdX`, sem passar pelo pen drive.

### Acesso ao nó

O `root` não entra por SSH com senha, que é o padrão do OpenSSH atual. Para operar sem teclado e monitor, defino a senha do usuário `raiar` e envio minha chave com `ssh-copy-id`. Desta forma, o `root` só é usado localmente. Para copiar arquivos antes de ter SSH, subo no notebook um servidor temporário com `python3 -m http.server 8000 --directory src/edge` e baixo os scripts no nó com `curl`.

### Problemas encontrados

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `wipefs` informa dispositivo ocupado | O Nautilus mantinha o pen drive aberto | Fechar a janela; o script agora falha com mensagem clara |
| O Raspberry Pi abre o Raspberry Pi OS | O cartão SD tem prioridade sobre o USB no boot | Colocar USB primeiro em `raspi-config` |
| `comando ausente: parted` | A imagem não traz `parted` nem `dosfstools` | Instalar os dois e reiniciar |
| Erro de leitura e escrita em `mmcblk0` | Provavelmente o cartão encaixado com o Pi ligado; com ele presente desde o boot, a cópia funcionou | Manter o SD encaixado antes de ligar |
| `command not found` para `hostname` | O sistema enxuto não instala o programa | Usar `cat /etc/hostname` |
| SSH recusa `root` e `alarm` | Usuário `alarm` removido e `root` sem senha por SSH | Criar `raiar` e usar chave |
| Download de 850 MB a 150 KB/s | O mirror automático era lento | Usar outro mirror, como `fl.us.mirror.archlinuxarm.org` |
| `pacman -Rns` recusa `--print` | As opções `-n` e `--print` são incompatíveis | A prévia usa `-Rs` |

## Situação atual e limites

Gravei o pen drive, iniciei o Raspberry Pi 4 por ele e copiei o sistema para um cartão SD de 32 GB, de onde o nó já inicia sozinho. Depois apliquei o enxugamento e o primeiro boot no próprio nó, e medi os valores abaixo.

| Medida | Antes | Depois |
| --- | --- | --- |
| Armazenamento usado na raiz | 2.401 MB | 791 MB após o enxugamento; 1.100 MB com Docker, Compose e `zram` |
| RAM em uso, sem containers | 177 MB de 3.815 MB | 220 MB, já com o Docker ativo |
| Swap | nenhum | `zram` de 1,9 GB, com prioridade 100 |

O `dockerd` ocupa cerca de 84 MB e o `containerd` cerca de 40 MB de memória residente, sem nenhum container em execução. É esse o custo fixo do Docker no nó. Com `zram`, o `vm.swappiness` passa a 100, e não mais a 10 como a configuração inicial, porque o swap comprimido deve ser preferido ao descarte de cache.

O Docker executou o container `hello-world` com sucesso. **Ainda não testei** a captura pelo DVR nem por câmera USB, porque nenhum estava disponível, nem a estabilidade do nó em 24 horas, que é o que o RNF12 exige. Também falta medir a memória disponível com o modelo carregado.

## Referências {#referencias}

[1] ARCH LINUX ARM. **Raspberry Pi 4**. Disponível em: [https://archlinuxarm.org/platforms/armv8/broadcom/raspberry-pi-4](https://archlinuxarm.org/platforms/armv8/broadcom/raspberry-pi-4). Acesso em: 25 out. 2026.

[2] RASPBERRY PI LTD. **Raspberry Pi documentation: computers**. Disponível em: [https://www.raspberrypi.com/documentation/computers/raspberry-pi.html](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html). Acesso em: 25 out. 2026.

[3] DOCKER INC. **Install Docker Engine**. Disponível em: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/). Acesso em: 25 out. 2026.

[4] FREEDESKTOP.ORG. **journald.conf**. Disponível em: [https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html). Acesso em: 25 out. 2026.

[5] THE LINUX KERNEL ORGANIZATION. **Documentation for /proc/sys/vm/**. Disponível em: [https://docs.kernel.org/admin-guide/sysctl/vm.html](https://docs.kernel.org/admin-guide/sysctl/vm.html). Acesso em: 25 out. 2026.

[6] ARCH LINUX WIKI. **wpa_supplicant**. Disponível em: [https://wiki.archlinux.org/title/Wpa_supplicant](https://wiki.archlinux.org/title/Wpa_supplicant). Acesso em: 25 out. 2026.

[7] THE LINUX KERNEL ORGANIZATION. **Video for Linux API**. Disponível em: [https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html). Acesso em: 25 out. 2026.

[8] ARCH LINUX WIKI. **Zram**. Disponível em: [https://wiki.archlinux.org/title/Zram](https://wiki.archlinux.org/title/Zram). Acesso em: 26 out. 2026.
