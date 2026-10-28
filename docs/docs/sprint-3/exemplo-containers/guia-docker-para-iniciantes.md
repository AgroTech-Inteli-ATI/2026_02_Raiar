---
title: Guia de Docker para quem nunca usou
sidebar_label: Guia de Docker
sidebar_position: 1
description: Guia prático, com exercícios executados, para containerizar os modelos da Raiar e rodá-los no Raspberry Pi 4.
---

# Guia de Docker para quem nunca usou: containerizando os modelos da Raiar

Este guia leva você de "nunca abri um container" até "a imagem dos modelos da Raiar roda no Raspberry Pi 4 e envia os resultados ao backend". Ele foi escrito para a tarefa **Conteinerização dos modelos** e para a tarefa **Aplicação dos modelos na Raspberry + setup da Raspberry**.

Quase tudo aqui foi **executado de verdade** antes de eu escrever. Onde eu não consegui testar (principalmente no Raspberry Pi e com a câmera), o texto avisa com a marca **[não testado]**. Quando você vir uma saída de terminal, ela é a saída real que eu obtive.

## Como usar este guia

| Parte | Assunto | Tempo aproximado |
| --- | --- | --- |
| 1 a 2 | A ideia e o vocabulário | 20 minutos |
| 3 a 7 | Docker na prática, com exercícios | 2 horas |
| 8 | Arquiteturas de processador (`amd64` e `arm64`) | 20 minutos |
| 9 a 11 | O projeto Raiar e a containerização dele | 2 horas |
| 12 em diante | Raspberry Pi, problemas comuns, consulta rápida | consulta |

Faça os **exercícios** digitando os comandos, não só lendo. As pastas `src/edge/exemplos-docker/01-contador` e `src/edge/exemplos-docker/02-raiar-vision`, têm os arquivos prontos.

Você vai ver três tipos de aviso:

> **Armadilha:** erro comum, que eu mesmo encontrei nos testes.

> **No projeto:** como o assunto se liga à Raiar.

> **[não testado]:** algo que depende de hardware que eu não tinha à mão.

## Parte 1: a ideia em cinco minutos

### O problema

Você escreve um programa no seu notebook e ele funciona. Seu colega o roda no notebook dele e dá erro: a versão do Python é outra, falta uma biblioteca do sistema, o caminho de uma pasta é diferente. É o famoso "na minha máquina funciona".

Agora imagine que o programa vai rodar em **vários Raspberry Pi** espalhados por aviários, que ninguém vai abrir toda semana para instalar coisas à mão. Você precisa que o programa chegue **pronto, igual em todos**, e que dê para **atualizar e voltar atrás** se algo der errado.

### A solução: o container

Pense num **contêiner de navio**. Não importa o que há dentro (bananas, peças de carro), ele tem o mesmo tamanho e encaixa em qualquer navio, caminhão ou guindaste. O porto não precisa saber o conteúdo.

Um **container de software** funciona igual: você empacota o programa **com tudo de que ele precisa** (a versão do Python, as bibliotecas, os arquivos de configuração) numa caixa padronizada. Qualquer computador com Docker consegue abrir essa caixa e rodar o programa do mesmo jeito.

### Container não é máquina virtual

| | Máquina virtual | Container |
| --- | --- | --- |
| O que carrega | Um sistema operacional **inteiro** | Só o programa e suas bibliotecas |
| Kernel | Cada VM tem o seu | **Compartilha** o kernel do computador |
| Tamanho típico | Gigabytes | Dezenas a centenas de megabytes |
| Tempo para iniciar | Minutos | Segundos |
| Memória fixa | Reserva uma fatia grande | Usa só o que o programa usa |

Isso importa para nós: o Raspberry Pi 4 tem **4 GB de RAM**. Uma máquina virtual ocuparia memória demais; um container custa pouco.

> **No projeto:** o nó de borda (o Raspberry Pi do aviário) só roda containers: leem a câmera, contam as aves por nível e enviam o resultado ao backend. O sistema do Pi foi deixado o mais enxuto possível justamente para sobrar memória para eles.

## Parte 2: o vocabulário

Decore estas sete palavras. Todo o resto do guia usa elas.

| Palavra | O que é | Analogia |
| --- | --- | --- |
| **Imagem** | Pacote imutável com o programa e tudo de que ele precisa | A **receita pronta e congelada** de um bolo |
| **Container** | Uma imagem **em execução** | O **bolo assado** a partir da receita |
| **Dockerfile** | Arquivo de texto com os passos para construir uma imagem | A **receita escrita** |
| **Registro** (*registry*) | Biblioteca online de imagens (Docker Hub, GitHub) | Um **livro de receitas** compartilhado |
| **Volume** | Pasta que **sobrevive** quando o container é apagado | A **geladeira** onde você guarda o bolo que sobrou |
| **Compose** | Arquivo que descreve **vários containers** juntos | O **cardápio** do jantar inteiro |
| **Camada** (*layer*) | Cada passo do Dockerfile vira uma camada reaproveitável | Cada **etapa** da receita, já feita e guardada |

O ciclo de vida:

```text
 Dockerfile ──(docker build)──▶ Imagem ──(docker run)──▶ Container
                                  │
                       (docker push / pull)
                                  ▼
                              Registro
```

Duas ideias que evitam muita confusão:

1. **Você pode criar vários containers da mesma imagem.** A imagem não muda; cada container é uma execução independente.
2. **Tudo o que um container grava em seu próprio interior some quando ele é apagado.** Por isso existem volumes (Parte 5).

## Parte 3: instalação e os primeiros comandos

### Instalar

- **Windows ou macOS:** instale o Docker Desktop (veja a documentação oficial [1]).
- **Linux:** instale o Docker Engine pelo gerenciador de pacotes da sua distribuição [1].

No Linux, o comando `docker` exige permissão. Adicione seu usuário ao grupo `docker` e reinicie a sessão:

```bash
sudo usermod -aG docker $USER
```

> **Armadilha de segurança:** quem está no grupo `docker` consegue virar `root` na máquina. Não coloque usuários desconhecidos nesse grupo.

Confira:

```bash
docker --version
docker compose version
```

### Exercício 1: o primeiro container

```bash
docker run --rm hello-world
```

O que acontece, em ordem: o Docker procura a imagem `hello-world` no seu computador, não acha, **baixa** do Docker Hub, cria um container, executa, mostra uma mensagem e termina. O `--rm` apaga o container no fim.

### Exercício 2: olhar o que existe

```bash
docker images        # as imagens baixadas
docker ps            # os containers rodando agora
docker ps -a         # todos, inclusive os parados
```

### Exercício 3: entrar num container

```bash
docker run --rm -it python:3.12-slim python
```

Isso abre um Python **dentro** de um container, com a versão exata da imagem (`3.12`), não importa a versão do seu computador. Digite `print("oi")` e saia com `exit()`.

Os dois sinalizadores: `-i` mantém a entrada aberta e `-t` simula um terminal. Juntos, `-it` deixam você interagir.

### Exercício 4: o ciclo de vida

```bash
docker run -d --name teste --rm python:3.12-slim sleep 300   # roda em segundo plano
docker ps                                                    # veja "teste" na lista
docker logs teste                                            # a saída do programa
docker exec -it teste sh                                     # entra nele (saia com exit)
docker stop teste                                            # para (e --rm apaga)
```

| Comando | Para que serve |
| --- | --- |
| `docker run` | Cria e inicia um container |
| `docker ps` | Lista os que estão rodando |
| `docker logs NOME` | Mostra o que o programa imprimiu |
| `docker exec -it NOME sh` | Abre um terminal dentro dele |
| `docker stop NOME` | Pede para parar |
| `docker rm NOME` | Apaga um container parado |

## Parte 4: construindo a sua própria imagem

### O Dockerfile, linha por linha

Vamos empacotar um programinha que conta quantas vezes foi executado. O código está em `src/edge/exemplos-docker/01-contador/app/contador.py`:

```python
"""Conta quantas vezes o container rodou e guarda o número em /dados."""
import os
from pathlib import Path

arquivo = Path("/dados/contagem.txt")
arquivo.parent.mkdir(parents=True, exist_ok=True)
n = int(arquivo.read_text()) + 1 if arquivo.exists() else 1
arquivo.write_text(str(n))
print(f"Olá! Esta é a execução número {n}. Sou o usuário {os.getuid()}.")
```

Primeira versão do Dockerfile (a que **tem um defeito**, que vamos descobrir). Salve-a como `Dockerfile.v1`; a pasta já traz, em `Dockerfile`, a versão corrigida, que usaremos na Parte 6. A referência completa das instruções está na documentação oficial [2].

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY app/contador.py .
CMD ["python", "contador.py"]
```

| Linha | O que faz |
| --- | --- |
| `FROM python:3.12-slim` | Ponto de partida: uma imagem pronta com Python 3.12. O `slim` é a versão pequena |
| `WORKDIR /app` | Define a pasta de trabalho dentro da imagem |
| `COPY app/contador.py .` | Copia o arquivo do seu computador para dentro da imagem |
| `CMD [...]` | O comando que roda quando o container inicia |

### Exercício 5: construir e rodar

Dentro de `src/edge/exemplos-docker/01-contador`, depois de salvar o `Dockerfile.v1`, construa:

```bash
docker build -f Dockerfile.v1 -t contador:1 .
docker run --rm contador:1
```

O `-t contador:1` dá o nome e a *tag* (versão) da imagem. O ponto final é o **contexto**: a pasta cujos arquivos o `build` pode enxergar.

Saída que obtive:

```text
Olá! Esta é a execução número 1. Sou o usuário 0.
```

"Usuário 0" é o `root`. Guarde isso, vai importar daqui a pouco. O tamanho da imagem ficou em **179 MB** (`docker images`).

### As camadas e o cache

Cada linha do Dockerfile vira uma **camada**, e o Docker **guarda cada camada pronta**. Se você reconstruir sem mudar nada, ele reaproveita tudo:

```bash
docker build -f Dockerfile.v1 -t contador:1 .
```

Procure a palavra `CACHED` na saída: é o Docker dizendo "essa etapa eu já fiz". Isso torna o segundo `build` quase instantâneo.

A regra de ouro: **coloque no topo o que muda pouco e embaixo o que muda muito.** Se você mudar uma linha do Dockerfile, essa camada e **todas as de baixo** são refeitas. Por isso, no projeto da Raiar, instalamos as bibliotecas (que raramente mudam) **antes** de copiar o código (que muda toda hora).

### O `.dockerignore`

O `docker build` envia o contexto inteiro (a pasta) ao Docker. Se a pasta tiver dados pesados, `build` fica lento. O arquivo `.dockerignore` lista o que **não** deve entrar:

```text
.git
.venv
data
outputs
**/*.ipynb
```

## Parte 5: dados que sobrevivem

### O que acontece sem volume

```bash
docker run --rm contador:1
docker run --rm contador:1
```

Saída:

```text
Olá! Esta é a execução número 1. Sou o usuário 0.
Olá! Esta é a execução número 1. Sou o usuário 0.
```

Os dois dizem "número 1". Cada container começou do zero, e o arquivo gravado dentro dele sumiu junto.

### Exercício 6: volume nomeado

```bash
docker volume create dados
docker run --rm -v dados:/dados contador:1
docker run --rm -v dados:/dados contador:1
docker run --rm -v dados:/dados contador:1
```

Saída:

```text
Olá! Esta é a execução número 1. Sou o usuário 0.
Olá! Esta é a execução número 2. Sou o usuário 0.
Olá! Esta é a execução número 3. Sou o usuário 0.
```

Agora a contagem sobrevive. O `-v dados:/dados` significa "ligue o volume `dados` à pasta `/dados` do container".

### Três formas de ligar pastas

| Tipo | Exemplo | Quando usar |
| --- | --- | --- |
| **Volume** | `-v dados:/dados` | Dados do programa; o Docker cuida de onde ficam |
| **Bind mount** | `-v /opt/raiar/data:/app/outputs` | Você quer ver e controlar a pasta no computador |
| **tmpfs** | `--tmpfs /tmp` | Arquivos temporários que ficam **só na memória** e somem ao parar |

> **No projeto:** o banco `results.sqlite3` (a fila de resultados) fica num bind mount, `/opt/raiar/data`, para sobreviver a reinícios. Os quadros da câmera ficam em `tmpfs`: gravar uma imagem a cada intervalo no cartão SD o desgastaria, então eles vivem só na memória [3][4].

## Parte 6: a armadilha das permissões

Esta é a causa mais comum de erro de quem começa, e vai aparecer no projeto.

Boa prática de segurança: **não rode o programa como `root`** dentro do container. Vamos pedir um usuário comum (`--user 1000:1000`) e também um sistema de arquivos **somente leitura** (`--read-only`):

```bash
docker run --rm --user 1000:1000 --read-only --tmpfs /tmp -v dados:/dados contador:1
```

Saída que obtive:

```text
PermissionError: [Errno 13] Permission denied: '/dados/contagem.txt'
```

**Por quê?** O volume `dados` foi criado antes, por um container que rodava como `root`, então os arquivos pertencem ao `root`. Agora o container roda como o usuário 1000, que não tem permissão para escrever ali.

### A correção

Crie a pasta **já com o dono certo** dentro da imagem. Um volume novo herda esse dono. O Dockerfile corrigido (é o que está em `src/edge/exemplos-docker/01-contador/Dockerfile`):

```dockerfile
FROM python:3.12-slim
# Cria a pasta de dados já com o dono certo. Um volume novo herda esse dono.
RUN mkdir /dados && chown 1000:1000 /dados
WORKDIR /app
COPY app/contador.py .
USER 1000:1000
CMD ["python", "contador.py"]
```

Teste com um volume **novo**:

```bash
docker build -t contador:2 .
docker volume create dados2
docker run --rm -v dados2:/dados contador:2
docker run --rm --read-only -v dados2:/dados contador:2
```

Saída:

```text
Olá! Esta é a execução número 1. Sou o usuário 1000.
Olá! Esta é a execução número 2. Sou o usuário 1000.
```

Funciona, mesmo com `--read-only`, porque `/dados` é um volume (gravável) e o resto da imagem é só leitura.

### Com bind mount de uma pasta do computador

Aqui o dono vem do **computador**, não da imagem:

```bash
mkdir dados-host
docker run --rm -v "$PWD/dados-host:/dados" contador:2
ls -ln dados-host
```

O arquivo aparece em `dados-host/contagem.txt`, com dono `1000`. Isso funciona porque o seu usuário no computador também é `1000` (confira com `id -u`). Se o seu fosse outro número, daria `Permission denied`: resolva com `sudo chown 1000:1000 dados-host`.

> **No projeto:** no Raspberry Pi, a pasta `/opt/raiar/data` pertence ao usuário `raiar` (uid 1000). Por isso o container roda como `1000:1000`.

## Parte 7: o Docker Compose

Rodar `docker run` com dez sinalizadores é cansativo e fácil de errar. O **Compose** descreve tudo num arquivo `compose.yaml` e sobe com um comando [5].

### Exercício 7: dois containers conversando por um volume

O arquivo `src/edge/exemplos-docker/01-contador/compose.yaml` define dois serviços: o `escritor` grava uma linha a cada 2 segundos e o `leitor` conta as linhas. Trecho do `escritor`:

```yaml
services:
  escritor:
    image: contador:2
    user: "1000:1000"
    restart: unless-stopped
    read_only: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    mem_limit: 64m
    cpus: 0.5
    environment:
      INTERVALO: "2"
    tmpfs:
      - /tmp:size=8m
    volumes:
      - dados:/dados
```

Cada campo importa:

| Campo | O que faz |
| --- | --- |
| `image` | Qual imagem usar |
| `user` | Usuário sem privilégios (não `root`) |
| `restart: unless-stopped` | Reinicia sozinho se cair ou se o computador reiniciar |
| `read_only` | O interior do container vira somente leitura |
| `cap_drop: [ALL]` | Remove poderes especiais do Linux que o programa não usa |
| `no-new-privileges` | Impede o programa de ganhar mais privilégios |
| `mem_limit`, `cpus` | **Teto** de memória e de CPU [6] |
| `environment` | Variáveis de ambiente (configuração sem mudar a imagem) |
| `volumes` | Liga a pasta de dados |

Os comandos do dia a dia:

```bash
docker compose config -q    # valida o arquivo (silencioso = ok)
docker compose up -d        # sobe tudo em segundo plano
docker compose ps           # vê o estado
docker compose logs -f      # acompanha os logs (Ctrl+C sai)
docker compose down         # para e apaga os containers (mantém os volumes)
docker compose down -v      # idem e também apaga os volumes
```

Resultado que obtive depois do `up -d`:

```text
SERVICE    STATE     STATUS
escritor   running   Up 8 seconds
leitor     running   Up 8 seconds
```

E o consumo real:

```text
contador-escritor-1  mem=9.121MiB / 64MiB  cpu=0.00%
contador-leitor-1    mem=1.191MiB / 64MiB  cpu=0.46%
```

Isso mostra por que containers são leves: o programa inteiro usa 9 MB.

O `leitor` monta o volume com `:ro` (somente leitura). Se ele tentar escrever, falha, **como deve**:

```text
sh: 1: cannot create /dados/saida.txt: Read-only file system
```

### Os dados sobrevivem a recriar os containers

```bash
docker compose down
docker compose up -d
```

Contei as linhas antes e depois: o arquivo continuou crescendo (6 linhas antes, 19 depois), porque o volume não foi apagado.

> **Armadilha:** se você usar uma imagem que **não tem** a pasta `/dados` (por exemplo, a `python:3.12-slim` pura), o Docker cria o volume com dono `root` e o container sem privilégios falha com `Permission denied`, ficando num ciclo de reinício (`Restarting (1)`). Foi exatamente o que aconteceu no meu primeiro teste. A correção é a da Parte 6.

## Parte 8: limites de recurso e o que acontece ao estourar

O Raspberry Pi tem pouca memória. Se um container tentar usar mais do que o limite, o Linux o **mata**. É o chamado OOM (*out of memory*), e o código de saída é **137**.

### Exercício 8: ver o OOM acontecer

```bash
docker run --rm --memory 32m --memory-swap 32m python:3.12-slim \
  python -c "x = bytearray(200*1024*1024); print('não deveria chegar aqui')"
echo "código de saída: $?"
```

Saída:

```text
código de saída: 137
```

### Reinício automático

Com `--restart=on-failure:3`, o Docker tenta de novo, no máximo 3 vezes, quando o programa sai com erro:

```bash
docker run -d --name falha --restart=on-failure:3 python:3.12-slim \
  python -c "import sys; print('vou falhar'); sys.exit(1)"
sleep 12
docker inspect -f 'estado={{.State.Status}} saída={{.State.ExitCode}} reinícios={{.RestartCount}}' falha
docker rm -f falha
```

Saída:

```text
estado=exited saída=1 reinícios=3
```

> **No projeto:** o RNF12 pede que a memória disponível do nó fique em pelo menos 20% durante 24 horas, e o RNF10 pede que toda falha gere registro. Os limites de memória protegem o nó: se o modelo "vazar" memória, só o container dele morre e reinicia, em vez de derrubar o Pi inteiro.

## Parte 9: arquiteturas de processador

Este é o ponto mais importante e mais surpreendente para quem vem de Windows ou macOS.

| | Seu notebook | Raspberry Pi 4 |
| --- | --- | --- |
| Arquitetura | `x86_64` (também chamada `amd64`) | `aarch64` (também chamada `arm64`) |
| Quem fabrica o processador | Intel ou AMD | ARM (Broadcom) |

**Uma imagem construída para `amd64` não roda em `arm64`, e vice-versa.** Se você tentar, o Docker dá um erro com a frase `exec format error`.

Quando você usa `FROM python:3.12-slim`, o Docker escolhe sozinho a variante da sua arquitetura (essa imagem oficial existe para as duas). O problema aparece quando **você constrói no notebook para rodar no Pi**.

### Construir para o Pi no seu notebook [não testado]

Eu não consegui testar esta parte, porque meu notebook não tinha a emulação de `arm64` instalada. O caminho que a documentação oficial descreve é o *build* multiplataforma com o `buildx` [7]:

```bash
# uma única vez, para o notebook emular arm64 (Arch Linux; em Ubuntu, veja a documentação):
sudo pacman -S qemu-user-static qemu-user-static-binfmt

docker buildx build --platform linux/arm64 -t raiar-vision:TAG --load .
```

A emulação é mais lenta que um `build` normal. Para conferir a arquitetura da imagem:

```bash
docker image inspect raiar-vision:TAG --format '{{.Architecture}}'
```

Deve mostrar `arm64`.

### Levar a imagem até o Pi

Sem um registro de imagens, o jeito mais simples é "empacotar" a imagem em um arquivo e abri-la no Pi, pelo SSH:

```bash
docker save raiar-vision:TAG | gzip | ssh raiar@IP_DO_PI 'gunzip | docker load'
```

Com um registro (Docker Hub, GitHub Container Registry), o caminho é `docker push` no notebook e `docker pull` no Pi.

## Parte 10: conhecendo o projeto

### O que a Raiar precisa

A Raiar Orgânicos cria galinhas em um **aviário** com uma estrutura chamada **Jump Start**, que tem três níveis para as aves: **N0** (o piso), **N1** (o meio) e **N2** (a plataforma superior). Uma câmera filma a estrutura, e o sistema precisa dizer **quantas aves há em cada nível**, ao longo do tempo. O resultado vai para um backend e aparece num dashboard.

O Raspberry Pi 4 (4 GB de RAM) é o **nó de borda**: fica no aviário, perto da câmera, e processa as imagens ali mesmo.

### O fluxo de dados

```text
 Câmera USB ─▶ [ captura ] ─▶ [ modelo conta aves por nível ] ─▶ fila local (SQLite)
                                                                       │
                                                  [ sync: envia por HTTPS ao backend ]
```

| Etapa | O que faz | Requisito |
| --- | --- | --- |
| Captura | Lê um quadro da câmera a cada intervalo | RF04 |
| Inferência | O modelo detecta e conta as aves | RF05, RF06 |
| Fila local | Guarda o resultado em SQLite, mesmo sem rede | RNF01, RNF10 |
| Sincronização | Envia os resultados em lotes; o servidor confirma | RNF04 |

A **fila local** é o que torna o nó robusto: se a internet cair por 24 horas, nada se perde, e tudo é enviado depois, uma única vez.

### Quem faz o quê

| Quem | Responsabilidade |
| --- | --- |
| **Containerização** (você, com o Gui) | A imagem, o `compose.yaml` e o teste dos containers |
| **Gui** | O sistema do Raspberry Pi, o Docker instalado, o Wi-Fi, a câmera e a entrega dos containers no nó |

### O código

O código fica na pasta `src/chicken_yolo`. O programa tem um conjunto de comandos:

| Comando | Para que serve |
| --- | --- |
| `prepare-model` | Baixa os pesos do modelo |
| `predict` | Processa uma imagem, um vídeo ou uma pasta |
| `sync` | Envia ao backend os resultados pendentes |
| `benchmark` | Mede tempo e recursos |
| `export` | Converte o modelo para ONNX ou NCNN (mais leves) |
| `train`, `evaluate`, `extract`, `crop`, `prepare-dataset` | Treino e preparo de dados |

Dois modelos estão disponíveis: `poultryvision` (maior, padrão) e `coco` (menor, mais rápido).

> **Armadilha importante:** o programa tem dois nomes de comando, `chicken-yolo` e `raiar-vision`. **Use sempre `raiar-vision` em Linux.** Veja a Parte 11, Passo 2.

## Parte 11: containerizando o projeto, passo a passo

Tudo desta parte eu construí e executei no meu notebook (`x86_64`). A parte `arm64` e a câmera são **[não testadas]**.

### Passo 1: preparar a pasta

```bash
git clone URL_DO_REPOSITORIO
cd 2026_02_Raiar
git switch -c feat/containerizacao
```

Os arquivos de apoio estão em `src/edge/exemplos-docker/02-raiar-vision/`: `Dockerfile`, `.dockerignore`, `compose.yaml` e `backend_falso.py`.

### Passo 2: as três descobertas que mudam o Dockerfile

Antes de olhar o Dockerfile, conheça os três problemas que eu encontrei. Cada linha dele existe por causa de um deles.

**Descoberta 1: o PyTorch puxaria 2,7 GB de bibliotecas inúteis.** O arquivo `uv.lock` marca as bibliotecas de GPU NVIDIA (`cuda-toolkit`, `nvidia-cudnn`, `nccl`, `triton`) apenas como "linux", sem limitar a `x86_64`. Fazer `uv sync --frozen` num `arm64` baixaria cerca de **2,7 GB** de arquivos que o Raspberry Pi nunca usa, pois ele não tem GPU NVIDIA. A solução é instalar a versão do PyTorch **só para CPU**, que existe para `arm64` na mesma versão do lock (`2.14.1`) [8].

**Descoberta 2: o nome `chicken-yolo` quebra o detector.** Quando rodei `chicken-yolo predict`, o resultado foi `falha_processamento` com o motivo `'NoneType' object is not subscriptable`. A causa: o Ultralytics (a biblioteca do YOLO) olha o nome do programa e, se ele **termina em `yolo`** e há a palavra `predict` nos argumentos, ele acha que está sendo usado pela linha de comando dele mesmo e devolve `None` em vez dos resultados. O programa tem um segundo nome, **`raiar-vision`**, que não tem esse problema:

```text
chicken-yolo predict ...  →  "falha_processamento": 1   (NoneType not subscriptable)
raiar-vision predict ...  →  "valido": 1                (funciona)
```

> Provavelmente a equipe não percebeu antes porque no Windows o programa se chama `chicken-yolo.exe` (termina em `.exe`, não em `yolo`). Vale avisar quem mantém o código.

**Descoberta 3: o usuário sem privilégios não consegue baixar os pesos.** O `prepare-model` grava em `src/chicken_yolo/models/pretrained`. Se o container roda como usuário comum, não consegue escrever ali. A solução é baixar os pesos **durante o `build`**, como `root`, antes de trocar de usuário. Como bônus, o nó não depende da internet para iniciar.

### Passo 3: o Dockerfile, linha por linha

```dockerfile
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch==2.14.1 torchvision==0.29.1 \
      --index-url https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/chicken_yolo ./src/chicken_yolo
RUN pip install --no-cache-dir .

ARG MODELO=coco
RUN raiar-vision prepare-model ${MODELO}

RUN useradd --uid 1000 --create-home raiar \
 && mkdir -p /app/outputs && chown raiar:raiar /app/outputs
USER raiar
ENV YOLO_CONFIG_DIR=/tmp/ultralytics

ENTRYPOINT ["raiar-vision"]
CMD ["--help"]
```

| Trecho | Por que está aí |
| --- | --- |
| `libgl1`, `libglib2.0-0` | Bibliotecas do sistema que o `opencv-python` exige. `--no-install-recommends` e `rm -rf` mantêm a imagem pequena |
| `pip install torch ... --index-url .../cpu` | Descoberta 1. Vem **antes** do projeto, para o `pip` considerar o requisito do `torch` já satisfeito e não baixar o pacote com CUDA |
| `COPY pyproject.toml ... ` e depois `COPY src/...` | Ordem das camadas: o que muda pouco vem primeiro (Parte 4) |
| `ARG MODELO=coco` e `prepare-model` | Descoberta 3. O argumento `MODELO` escolhe qual modelo embutir (`coco` ou `poultryvision`) |
| `useradd --uid 1000` e `chown` | Cria o usuário comum e a pasta de saída com o dono certo (Parte 6) |
| `USER raiar` | Tudo daqui em diante roda sem privilégios |
| `ENV YOLO_CONFIG_DIR` | O Ultralytics grava um arquivo de configuração; mandamos para `/tmp` |
| `ENTRYPOINT ["raiar-vision"]` | Descoberta 2. Fixa o nome certo do programa |

> **Atenção à reprodutibilidade:** o `pip install .` resolve as versões pelas faixas do `pyproject.toml`, **não** pelo `uv.lock`. No meu teste, o lock fixa `ultralytics 8.4.177` e a imagem instalou `8.4.190`. Funcionou, mas versões podem mudar entre builds. Uma melhoria futura é gerar uma lista de requisitos com `uv export` e filtrar as bibliotecas NVIDIA.

### Passo 4: construir

Da **raiz do repositório** (o contexto precisa enxergar `pyproject.toml` e `src/`):

```bash
docker build -f src/edge/exemplos-docker/02-raiar-vision/Dockerfile \
  --build-arg MODELO=coco -t raiar-vision:dev .
```

Para o `.dockerignore` valer, copie o arquivo de `src/edge/exemplos-docker/02-raiar-vision/.dockerignore` para a raiz do repositório. Na primeira vez, o build levou cerca de 2 minutos; com cache, 8 segundos.

Resultado: uma imagem de cerca de **2,5 GB** em `x86_64`, dos quais cerca de **1 GB** é o PyTorch para CPU. Eu **não medi o tamanho em `arm64`**. Esse é o maior risco de armazenamento do nó, e a Parte 13 mostra como reduzir.

### Passo 5: rodar a detecção

Crie uma imagem de teste. O código abaixo gera uma imagem cinza com três manchas escuras (**não tem aves de verdade**, então o resultado esperado é "válido, 0 aves"). Para ver detecções, use uma foto ou um vídeo real que a equipe tenha.

```bash
mkdir -p entrada saida
chmod 777 entrada saida   # o container roda como usuário 1000; em teste local, libere a escrita
docker run --rm --entrypoint python -v "$PWD/entrada:/entrada" raiar-vision:dev -c "
import cv2, numpy as np
img = np.full((480,640,3), 160, np.uint8)
for x,y in [(150,200),(320,260),(480,330)]: cv2.ellipse(img,(x,y),(40,28),0,0,360,(40,60,90),-1)
cv2.imwrite('/entrada/teste.jpg', img)"
```

Agora a detecção, com todas as proteções ligadas:

```bash
docker run --rm \
  --read-only --tmpfs /tmp:size=64m \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 2g \
  -v "$PWD/saida:/app/outputs" -v "$PWD/entrada:/entrada:ro" \
  raiar-vision:dev predict --source /entrada/teste.jpg \
  --camera-id camera-01 --lote-id lote-01 --model coco
```

Saída:

```json
{
  "output": "/app/outputs/predict-97910a197463",
  "frames": 1,
  "valido": 1,
  "imagem_inadequada": 0,
  "falha_processamento": 0
}
```

### Passo 6: entender o que foi gravado

Na pasta `saida/` apareceu:

| Arquivo | O que é |
| --- | --- |
| `results.sqlite3` | A **fila** durável (a tabela `analyses`), com a chave `analise_id` |
| `predict-.../results.jsonl` | O resultado completo de cada quadro |
| `predict-.../counts.csv` | As contagens |
| `predict-.../annotated/` | A imagem com as caixas desenhadas |

Cada quadro recebe um dos três estados, e é importante não confundir:

| Estado | Significa |
| --- | --- |
| `valido` | Imagem processada; a contagem vale (pode ser zero) |
| `imagem_inadequada` | A imagem foi reprovada na triagem (muito escura, borrada, pequena) |
| `falha_processamento` | Algo deu errado; o motivo fica em `motivo_status` |

Uma falha **não é escondida**: ela vira registro. É assim que o RNF10 é cumprido.

### Passo 7: enviar ao backend (com um backend de mentira)

Como ainda não há backend real, uso o `backend_falso.py`, que aceita tudo e confirma os IDs recebidos. O contrato do `sync` é: `POST` com `{"schema_version":1,"analyses":[...]}`, e o servidor responde `{"accepted_analysis_ids":[...]}`. Só os IDs confirmados saem da fila.

```bash
python3 -I src/edge/exemplos-docker/02-raiar-vision/backend_falso.py &
```

Quando terminar, encerre com `kill %1`.

Em seguida, o envio. O `--network host` deixa o container enxergar o `127.0.0.1` do seu computador. O `sync` **só aceita HTTPS**, com uma exceção: HTTP em `localhost`, para testes.

```bash
docker run --rm --network host --read-only --tmpfs /tmp \
  -e RAIAR_SYNC_TOKEN=segredo-de-teste \
  -v "$PWD/saida:/app/outputs" \
  raiar-vision:dev sync --database /app/outputs/results.sqlite3 \
  --url http://127.0.0.1:8081/api/analyses --token-env RAIAR_SYNC_TOKEN
```

Primeiro envio:

```json
{ "sent": 1, "accepted": 1, "pending": 0 }
```

Rode o mesmo comando de novo: a fila está vazia, então nada é reenviado.

```json
{ "sent": 0, "accepted": 0, "pending": 0 }
```

E o backend de mentira imprimiu: `[backend] recebi 1 análise(s); token=Bearer segredo-de-teste`.

**E se a rede cair?** Pare o `backend_falso` e rode o `sync` de novo. Ele reporta o erro (`Max retries exceeded ... Failed to establish a new connection`) e **a fila continua intacta**, pronta para o próximo envio.

> **Armadilha de segurança:** o token vai por variável de ambiente, nunca dentro da imagem nem no repositório.

### Passo 8: o Compose do projeto

O arquivo `src/edge/exemplos-docker/02-raiar-vision/compose.yaml` define dois serviços a partir de **uma única imagem**:

| Serviço | Função | Memória |
| --- | --- | --- |
| `vision` | Lê a câmera, roda o modelo e grava no SQLite | 2 GB |
| `sync` | Roda `raiar-vision sync` a cada 5 minutos | 128 MB |

Por que dois serviços e uma imagem:

- **Um processo só pode abrir a câmera por vez**, e o modelo só deve ficar na memória uma vez. Captura e inferência ficam juntas.
- O `sync` usa só `json`, `sqlite3` e `requests`; o `ultralytics` é carregado apenas dentro das funções que o usam. Por isso o `sync`, mesmo estando na imagem grande, **não carrega o PyTorch na memória**. Medi o serviço `sync` em espera usando cerca de **1 MB**.
- Se a rede cair, só o `sync` falha e reinicia; a captura nem percebe.
- O banco usa o modo WAL, que permite um processo ler enquanto outro escreve [9].

Testei o serviço `sync` assim, contra o backend de mentira:

```bash
export RAIAR_TAG=dev RAIAR_DATA=$PWD/saida
export RAIAR_SYNC_URL=http://127.0.0.1:8081/api/analyses RAIAR_SYNC_TOKEN=token-de-teste
docker compose -f src/edge/exemplos-docker/02-raiar-vision/compose.yaml up -d sync
docker compose -f src/edge/exemplos-docker/02-raiar-vision/compose.yaml logs sync
```

(No meu teste precisei de um arquivo `override` com `network_mode: host`, só para o container enxergar o `127.0.0.1` do notebook. No Pi, o URL será o do backend real, em HTTPS, e isso não é necessário.)

Resposta nos logs: `{"sent":1,"accepted":1,"pending":0}`.

O serviço `vision` está pronto como esqueleto, mas **falta o laço de captura ao vivo**, que ainda não existe no código. Veja a Parte 12.

### Passo 9: medir

Dois comandos que respondem "quanto custa?":

```bash
docker stats --no-stream           # memória e CPU de cada container agora
docker images                      # tamanho das imagens
```

E o pico de memória real de uma execução:

```bash
docker run --rm -v "$PWD/saida:/app/outputs" -v "$PWD/entrada:/entrada:ro" \
  --entrypoint sh raiar-vision:dev -c \
  'raiar-vision predict --source /entrada/teste.jpg --model coco >/dev/null 2>&1; echo "pico: $(( $(cat /sys/fs/cgroup/memory.peak) / 1048576 )) MB"'
```

Resultados que obtive, processando um quadro de 640 x 480, em `x86_64`:

| Modelo | Pico de memória | Limite |
| --- | --- | --- |
| YOLO11n (`coco`) | cerca de **309 MB** | roda com 384 MB, morre (OOM) com 256 MB |
| YOLO11m (`poultryvision`) | cerca de **509 MB** | roda com 512 MB, sem folga |

> **Atenção:** em `arm64` os números podem ser diferentes, e eu não medi o **tempo por quadro** no Pi. O RNF11 exige que a inferência termine em até 80% do intervalo entre quadros, e isso só se confirma no equipamento.

## Parte 12: indo para o Raspberry Pi

### O que o Gui entrega no nó

O nó já está pronto: Arch Linux ARM enxuto, Docker 29 e Compose instalados, swap comprimido na RAM (`zram`), Wi-Fi configurado e o usuário `raiar`. Os detalhes estão na documentação do Docusaurus, nas páginas **Nó de borda no Raspberry Pi** e **Containers no nó de borda**.

| Item | Valor |
| --- | --- |
| Sistema do nó | Arch Linux ARM `aarch64` (os containers usam Debian por dentro, e isso não é problema) |
| RAM | 3.815 MB totais; cerca de 3.570 MB disponíveis sem containers |
| Disco | 29 GB, com 27 GB livres |
| Usuário | `raiar` (uid 1000), nos grupos `docker` e `video` |
| Dados | `/opt/raiar/data` |
| Rede | Só saída; nenhuma porta aberta pelos containers |

**Orçamento de memória.** O RNF12 exige 20% de RAM livre (cerca de 763 MB). Sobram aproximadamente **2,8 GB** para os containers. Os modelos medidos (309 a 509 MB) cabem com folga, mas a captura ao vivo e o pico de uso ainda precisam ser medidos.

### O que você precisa pedir ao Gui

1. O **IP** do Pi na rede e uma **senha ou chave SSH** para o usuário `raiar`. Hoje esse usuário está **sem senha** (conta travada), então o Gui precisa defini-la e instalar a sua chave.
2. Para saber o número do grupo `video` no nó: `getent group video`. No nó, é **983**.

### Entregar e subir

```bash
# no notebook: construir para arm64 e enviar [não testado]
docker buildx build --platform linux/arm64 -f src/edge/exemplos-docker/02-raiar-vision/Dockerfile \
  --build-arg MODELO=coco -t raiar-vision:v1 --load .
docker save raiar-vision:v1 | gzip | ssh raiar@IP_DO_PI 'gunzip | docker load'

# uma única vez, no Pi: pasta de dados e arquivo de configuração (sem credenciais no Git)
ssh raiar@IP_DO_PI
mkdir -p /opt/raiar/data
cat > /opt/raiar/.env <<EOF
RAIAR_SYNC_URL=https://URL_DO_BACKEND/api/analyses
RAIAR_SYNC_TOKEN=COLE_O_TOKEN_AQUI
RAIAR_CAMERA_SOURCE=rtsp://USUARIO:SENHA@IP_DO_DVR:554/CAMINHO_DO_SUBSTREAM
RAIAR_CAMERA_ID=camera-1
EOF
chmod 600 /opt/raiar/.env
exit

# no notebook: levar o compose.yaml
scp src/edge/exemplos-docker/02-raiar-vision/compose.yaml src/edge/exemplos-docker/02-raiar-vision/compose.usb.yaml raiar@IP_DO_PI:/opt/raiar/

# no Pi: subir
ssh raiar@IP_DO_PI
cd /opt/raiar
RAIAR_TAG=v1 docker compose up -d
docker compose ps
docker compose logs -f
```

**Voltar atrás** é subir a versão anterior: `RAIAR_TAG=v0 docker compose up -d`. É por isso que cada versão tem uma *tag* diferente.

### A câmera

A fonte principal é o **DVR** do aviário, lido por RTSP pela rede. Não há dispositivo para passar ao container: a URL fica em `RAIAR_CAMERA_SOURCE` no `.env`, e o Pi precisa alcançar o DVR (`nc -zv IP_DO_DVR 554`). Peça o *substream* em H.264 e use cabo de rede. A câmera USB continua como alternativa (veja abaixo) e se escolhe só por configuração.

> **[não testado]:** nem o DVR nem a câmera USB foram exercitados com hardware.

#### Alternativa: câmera USB

Defina `RAIAR_CAMERA_SOURCE=/dev/video0` e `VIDEO_GID=$(getent group video | cut -d: -f3)` no `.env`, leve também o `compose.usb.yaml` e suba com `docker compose -f compose.yaml -f compose.usb.yaml up -d`. Conecte a câmera e confira no Pi:

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

Para dar acesso ao container, use `devices` (não `privileged`) e passe o grupo `video` pelo **número**, não pelo nome:

```bash
docker run --rm --device /dev/video0 --group-add "$(getent group video | cut -d: -f3)" ...
```

> **Armadilha:** dentro de uma imagem Debian, o grupo `video` tem outro número (44) que no sistema do Pi (983). Se você escrever `--group-add video`, o Docker resolve o nome **dentro da imagem** e o container sem privilégios não consegue abrir a câmera. Use sempre o número do grupo do **Pi**.

> **[não testado]:** nenhuma câmera estava conectada. Nada nesta seção foi exercitado com hardware.

### O que ainda falta construir

O código atual lê **arquivos** (imagem, vídeo, pasta). Falta o programa que fica **em laço**: ler um quadro da câmera a cada intervalo, guardar em `/frames` (memória), chamar a detecção e gravar no SQLite. A forma mais simples de começar é:

1. Um script que abre `RAIAR_CAMERA_SOURCE` (URL RTSP ou `/dev/video0`) com o OpenCV, salva um quadro por intervalo em `/frames` e dorme.
2. Para cada quadro salvo, chamar `raiar-vision predict --source ARQUIVO` e apagar o quadro.
3. Quando funcionar, trocar a chamada por uso direto do detector, para não recarregar o modelo a cada quadro (carregar custa tempo e memória).

Quem escreve esse laço é uma decisão do time. O que o nó oferece: câmera, 2,8 GB de RAM, o SQLite e o `sync`.

## Parte 13: reduzir o tamanho da imagem

A imagem tem cerca de 2,5 GB. Para três nós com 27 GB livres isso cabe, mas cada versão nova ocupa espaço. Proponho reduzir em fases, **sempre medindo antes de avançar**:

| Fase | Ação | Quando |
| --- | --- | --- |
| 1 | Imagem atual (PyTorch para CPU) | Já feito; medir em `arm64` |
| 2 | Exportar o modelo para ONNX ou NCNN com `raiar-vision export` e comparar com o `benchmark` no Pi [10] | Quando a Fase 1 estiver rodando no Pi |
| 3 | Trocar o PyTorch por um *runtime* de inferência menor (ONNX Runtime) [11] | Só se a Fase 1 não couber; **exige mudar o código** do detector |

Outras reduções pequenas: trocar `opencv-python` por `opencv-python-headless` (dispensa `libgl1`, que arrasta componentes gráficos), e usar *multi-stage build* [12].

## Parte 14: solução de problemas

Os erros marcados com ✔ eu reproduzi de verdade.

| Sintoma | Causa provável | O que fazer |
| --- | --- | --- |
| ✔ `Permission denied: '/dados/...'` | O volume ou a pasta pertence ao `root`, e o container roda como 1000 | `chown 1000:1000` na pasta, ou criar a pasta na imagem com o dono certo (Parte 6) |
| ✔ Container em `Restarting (1)` sem parar | O programa falha ao iniciar e a política de reinício tenta de novo | `docker compose logs NOME` para ver o erro |
| ✔ `falha_processamento` com `'NoneType' object is not subscriptable` | Você usou `chicken-yolo` em vez de `raiar-vision` | Trocar o `ENTRYPOINT` e os comandos para `raiar-vision` |
| ✔ `Read-only file system: '/app/runs'` | Mesmo problema acima, com `--read-only`: o Ultralytics tenta gravar | Usar `raiar-vision`. Se persistir, `--tmpfs /app/runs` |
| ✔ Container morto, saída 137 | Passou do limite de memória (OOM) | Aumentar `mem_limit` ou usar um modelo menor (Parte 8) |
| ✔ `Endpoint deve usar HTTPS` | O `sync` só aceita HTTPS, ou HTTP em `localhost` | Usar `https://` ou testar em `127.0.0.1` |
| `exec format error` | Imagem de outra arquitetura (`amd64` no Pi) | Construir com `--platform linux/arm64` (Parte 9) |
| `Cannot connect to the Docker daemon` | O Docker não está rodando, ou seu usuário não está no grupo `docker` | `sudo systemctl start docker` e conferir `groups` |
| `no space left on device` | Imagens e volumes antigos ocupando o disco | `docker system df`, depois `docker image prune` |
| `/dev/video0: no such file` | Câmera desconectada ou com outro número | `v4l2-ctl --list-devices` no Pi |
| Câmera "ocupada" | Outro processo (ou outro container) já a abriu | Só um processo por vez; `docker ps` para achar |

Para investigar qualquer container: `docker logs NOME`, `docker inspect NOME` e `docker exec -it NOME sh`.

## Parte 15: consulta rápida

```bash
# Imagens
docker build -t NOME:TAG .             # construir
docker images                           # listar
docker rmi NOME:TAG                     # apagar
docker image inspect NOME:TAG --format '{{.Architecture}}'

# Containers
docker run --rm -it IMAGEM COMANDO      # rodar e apagar ao sair
docker run -d --name X IMAGEM           # em segundo plano
docker ps / docker ps -a                # listar
docker logs -f X                        # logs ao vivo
docker exec -it X sh                    # entrar
docker stop X / docker rm X             # parar / apagar
docker stats --no-stream                # memória e CPU

# Opções úteis do run
--memory 512m   --cpus 2   --user 1000:1000   --read-only
--tmpfs /tmp    -v PASTA:/destino    -e VAR=valor
--device /dev/video0    --group-add NÚMERO    --restart unless-stopped

# Compose
docker compose config -q                # validar
docker compose up -d                    # subir
docker compose ps / logs -f             # ver
docker compose down                     # parar (mantém volumes)
docker compose down -v                  # parar e apagar volumes

# Espaço
docker system df                        # quanto o Docker ocupa
docker image prune                      # apaga imagens sem uso
```

> **Cuidado com `docker system prune -a`:** apaga **todas** as imagens sem container ativo, inclusive as de outros projetos seus. Prefira apagar pelo nome.

## Parte 16: boas práticas, em uma página

1. **Um processo principal por container.** Mais fácil de reiniciar, medir e depurar.
2. **Não rode como `root`.** Use `USER` e `--user`.
3. **Sistema de arquivos somente leitura**, com `tmpfs` onde precisar escrever.
4. **Segredos nunca na imagem nem no Git.** Use variáveis de ambiente ou um arquivo `.env` fora do repositório (o `.gitignore` do projeto já ignora `.env`).
5. **Tags fixas e únicas** (`v1`, `v2`, o hash do commit). Evite `latest` em produção: não dá para saber o que ela contém, nem voltar atrás.
6. **Imagens pequenas**: base `slim`, `--no-install-recommends`, `rm -rf /var/lib/apt/lists/*`, `--no-cache-dir` no pip [12].
7. **Camadas na ordem certa**: o que muda pouco primeiro.
8. **Limites de memória e CPU** sempre definidos, principalmente no Pi.
9. **Logs na saída padrão** (`print`), não em arquivos. O Docker os recolhe e o `daemon.json` do nó limita o tamanho.
10. **Meça antes de otimizar.** Os números deste guia vieram de medir, e três deles mudaram o Dockerfile.

## Parte 17: teste o que aprendeu

1. Qual a diferença entre imagem e container?
2. Por que os dados sumiram no exercício sem volume?
3. Por que o container deu `Permission denied` ao rodar como usuário 1000?
4. O que significa o código de saída 137?
5. Por que uma imagem construída no notebook pode não rodar no Raspberry Pi?
6. Por que instalamos o PyTorch antes de instalar o projeto, usando o índice de CPU?
7. Por que usar `raiar-vision` e não `chicken-yolo`?
8. Por que o `sync` e o `vision` são serviços separados, mas usam a mesma imagem?
9. Qual a vantagem de a fila de resultados ficar num SQLite local?
10. Por que passar o grupo da câmera pelo **número**?

**Respostas.** (1) A imagem é o pacote imutável; o container é uma execução dela. (2) O arquivo foi gravado dentro do container, que foi apagado; só um volume sobrevive. (3) O volume foi criado por `root`, e o usuário 1000 não tem permissão. (4) O container passou do limite de memória e foi morto. (5) Os processadores têm arquiteturas diferentes (`amd64` e `arm64`). (6) Para o `pip` não baixar a versão com CUDA, cerca de 2,7 GB inúteis no Pi. (7) O nome terminado em `yolo` faz o Ultralytics devolver `None` no `predict`. (8) Para a rede cair sem afetar a captura, e para ter um único build. (9) Nada se perde se a internet cair; tudo é enviado depois, sem duplicar. (10) No container, o nome `video` aponta para outro número que o do Pi.

## Parte 18: o que ainda está em aberto

| Ponto | Quem decide | Observação |
| --- | --- | --- |
| Laço de captura ao vivo | Time de containerização | Não existe no código |
| Tamanho da imagem e tempo por quadro em `arm64` | Medição no Pi | Não medi |
| Formato do modelo (PyTorch, ONNX, NCNN) | Resultado do `benchmark` no Pi | Fase 2 da Parte 13 |
| Backend real (URL, token) | Time do backend | Só existe o contrato do `sync` |
| Relógio do Pi | Hardware | O Pi não tem relógio próprio; sem rede após um reinício, a hora fica errada. Sugiro um módulo RTC |
| Corrigir o nome `chicken-yolo` | Quem mantém o código | Hoje só `raiar-vision` funciona em Linux |

## Referências

[1] DOCKER INC. **Get started**. Disponível em: [https://docs.docker.com/get-started/](https://docs.docker.com/get-started/). Acesso em: 27 out. 2026.

[2] DOCKER INC. **Dockerfile reference**. Disponível em: [https://docs.docker.com/reference/dockerfile/](https://docs.docker.com/reference/dockerfile/). Acesso em: 27 out. 2026.

[3] DOCKER INC. **Volumes**. Disponível em: [https://docs.docker.com/engine/storage/volumes/](https://docs.docker.com/engine/storage/volumes/). Acesso em: 27 out. 2026.

[4] DOCKER INC. **tmpfs mounts**. Disponível em: [https://docs.docker.com/engine/storage/tmpfs/](https://docs.docker.com/engine/storage/tmpfs/). Acesso em: 27 out. 2026.

[5] DOCKER INC. **Docker Compose**. Disponível em: [https://docs.docker.com/compose/](https://docs.docker.com/compose/). Acesso em: 27 out. 2026.

[6] DOCKER INC. **Resource constraints**. Disponível em: [https://docs.docker.com/engine/containers/resource_constraints/](https://docs.docker.com/engine/containers/resource_constraints/). Acesso em: 27 out. 2026.

[7] DOCKER INC. **Multi-platform builds**. Disponível em: [https://docs.docker.com/build/building/multi-platform/](https://docs.docker.com/build/building/multi-platform/). Acesso em: 27 out. 2026.

[8] PYTORCH FOUNDATION. **Get started locally**. Disponível em: [https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/). Acesso em: 27 out. 2026.

[9] SQLITE. **Write-ahead logging**. Disponível em: [https://sqlite.org/wal.html](https://sqlite.org/wal.html). Acesso em: 27 out. 2026.

[10] ULTRALYTICS. **Raspberry Pi setup and benchmarks**. Disponível em: [https://docs.ultralytics.com/guides/raspberry-pi/](https://docs.ultralytics.com/guides/raspberry-pi/). Acesso em: 27 out. 2026.

[11] ONNX RUNTIME. **ONNX Runtime documentation**. Disponível em: [https://onnxruntime.ai/docs/](https://onnxruntime.ai/docs/). Acesso em: 27 out. 2026.

[12] DOCKER INC. **Building best practices**. Disponível em: [https://docs.docker.com/build/building/best-practices/](https://docs.docker.com/build/building/best-practices/). Acesso em: 27 out. 2026.
