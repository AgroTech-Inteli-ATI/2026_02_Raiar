---
title: Integração dos containers de visão computacional no nó de borda
sidebar_label: Containers no nó de borda
sidebar_position: 3
description: Proposta de arquitetura, recursos, entrega e validação para executar os modelos em containers no Raspberry Pi 4.
---

# Integração dos containers de visão computacional no nó de borda

Esta página propõe como os containers dos modelos devem rodar no nó de borda que descrevi em [Nó de borda no Raspberry Pi](./provisionamento-raspberry-pi.md). Ela serve de combinado entre quem prepara o sistema e quem containeriza os modelos. Testei a imagem, a detecção e a sincronização no notebook (`x86_64`), com um backend simulado. **Não testei em `arm64`, no Raspberry Pi nem com a câmera**, e o texto marca cada ponto que ainda depende disso. Quem nunca usou Docker encontra a explicação dos conceitos e os exercícios em [Guia de Docker para iniciantes](./exemplo-containers/guia-docker-para-iniciantes.md). Os termos técnicos estão no [glossário](../sprint-1/glossario.md).

## Papel do nó e fluxo de dados

O Raspberry Pi só executa containers que leem a câmera, contam as aves em cada nível e enviam o resultado ao backend. Ele não guarda interface, treino nem dados históricos de longo prazo. O fluxo tem quatro etapas, e cada uma atende a um requisito já definido.

| Etapa | O que acontece | Requisito |
| --- | --- | --- |
| Captura | A câmera USB entrega quadros periódicos pela interface V4L2 | RF04 |
| Inferência | O modelo conta as aves em N0, N1 e N2 em cada quadro | RF05, RF06 |
| Fila local | O resultado é gravado em SQLite no próprio nó, mesmo sem rede | RNF01, RNF10 |
| Sincronização | Lotes de resultados vão ao backend por HTTPS, sem duplicar registros | RNF04 |

A fila local é a peça que torna o nó tolerante a falhas. O detector já grava cada análise em `outputs/results.sqlite3` com a chave `analise_id`, e o comando `raiar-vision sync` só retira da fila os identificadores que o servidor confirma, como descrevo em [Detecção de aves com YOLO](../sprint-2/deteccao-de-aves.md). Por isso o nó pode ficar 24 horas sem rede e enviar tudo depois, uma única vez.

## Orçamento de recursos

Medi o nó reiniciado, com o Docker ativo e nenhum container de modelo.

| Recurso | Total | Em uso no nó | Disponível |
| --- | --- | --- | --- |
| RAM | 3.815 MB | 244 MB, dos quais cerca de 124 MB são `dockerd` e `containerd` | 3.571 MB |
| Armazenamento da raiz | 29 GB | 1,1 GB | 27 GB |
| Swap comprimido (`zram`) | 1,9 GB | 0 | 1,9 GB |

Medi também o pico de memória do detector ao processar um quadro de 640 x 480 pixels, em `x86_64`.

| Modelo | Pico de memória | Observação |
| --- | --- | --- |
| YOLO11n (`coco`) | cerca de 309 MB | Roda com limite de 384 MB; é encerrado com 256 MB |
| YOLO11m (`poultryvision`) | cerca de 509 MB | Roda com limite de 512 MB, sem folga |

Esses valores não incluem a captura ao vivo e podem ser diferentes em `arm64`, então servem só de ordem de grandeza. O RNF12 exige que a memória disponível fique em pelo menos 20% da RAM reconhecida, o que equivale a cerca de 763 MB. Descontada essa reserva, os containers podem somar aproximadamente **2,8 GB de RAM**. O mesmo requisito limita a CPU a 80% da capacidade, em média, em janelas de cinco minutos.

## Arquitetura proposta

Proponho uma única imagem do projeto, usada por dois serviços do Docker Compose [1].

| Serviço | Função | Limite de memória inicial |
| --- | --- | --- |
| `vision` | Lê a câmera, executa o modelo e grava no SQLite | 2 GB |
| `sync` | Executa `raiar-vision sync` em laço, a cada poucos minutos | 128 MB |

Os dois serviços compartilham o volume `/opt/raiar/data`, onde fica o SQLite. Escolhi esta divisão pelos motivos abaixo.

- Apenas um processo pode abrir a câmera por vez, e o modelo só deve existir uma vez na memória. Por isso captura e inferência ficam juntas no `vision`.
- O `sync` usa apenas `json`, `sqlite3` e `requests`, e o `ultralytics` e o OpenCV são importados só dentro das funções que os usam. Assim, o `sync` roda da mesma imagem sem carregar o PyTorch na memória.
- Falhas de rede não podem derrubar a inferência. Em serviços separados, o `sync` pode falhar e reiniciar sem tocar na captura.
- O detector já abre o SQLite no modo WAL, que permite ler enquanto outro processo escreve, o que cobre este uso [2].

## Decisões e alternativas

| Decisão | Alternativa que descartei | Motivo |
| --- | --- | --- |
| Docker com Compose | Podman sem *daemon* | A equipe já containeriza com Docker, e o custo fixo de cerca de 124 MB cabe no orçamento |
| Containers | Rodar direto no sistema, com ambiente virtual Python | Containers dão imagens versionadas, reversíveis e iguais em todos os nós |
| Uma imagem, dois serviços | Duas imagens | Um único *build* e um único conjunto de dependências a manter |
| Build no notebook, para `arm64` | Build no Raspberry Pi | O nó tem pouca RAM e disco, e compilar nele competiria com os modelos |
| Quadros em memória (`tmpfs`) | Quadros no cartão SD | Gravar uma imagem a cada intervalo desgasta o cartão; só resultados e imagens representativas vão para o disco |
| Resultado local primeiro | Envio direto ao backend | Sem uma fila durável, um corte de rede perderia resultados |
| Sem Kubernetes | k3s ou similares | O custo de memória do orquestrador seria alto para três nós de 4 GB |

## Imagem do container

O ponto de partida é uma imagem Python enxuta. O Dockerfile abaixo, que está em `src/edge/exemplos-docker/02-raiar-vision/`, **foi construído e executado no notebook**, com o modelo `coco`.

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

Três escolhas desse arquivo vieram de problemas que encontrei nos testes.

| Escolha | Problema que evita |
| --- | --- |
| PyTorch só para CPU, instalado antes do projeto [3] | O `uv.lock` marca as bibliotecas CUDA apenas como `linux`, sem restringir a `x86_64`. Um `uv sync --frozen` em `arm64` baixaria cerca de 2,7 GB de bibliotecas NVIDIA que o Raspberry Pi não usa |
| Programa chamado `raiar-vision` | Com o nome `chicken-yolo`, que termina em `yolo`, o Ultralytics se supõe na própria linha de comando e o `predict` devolve `None`. A falha é registrada como `falha_processamento` com o motivo `'NoneType' object is not subscriptable` |
| Pesos baixados na construção | O nó não depende da internet para iniciar, e o `prepare-model` grava em `src/chicken_yolo/models/pretrained`, que o usuário comum não consegue escrever |

A imagem ficou com cerca de 2,5 GB em `x86_64`, dos quais 1 GB é o PyTorch para CPU. Ainda não medi o tamanho em `arm64`. O tamanho continua sendo o maior risco de armazenamento, e proponho reduzi-lo em fases, sempre medindo antes de avançar.

| Fase | O que fazer | Como decidir |
| --- | --- | --- |
| 1 | Containerizar o código atual, com pesos pré-treinados e PyTorch para CPU | Medir tamanho da imagem em `arm64`, RAM em `docker stats` e tempo por quadro |
| 2 | Exportar o modelo para ONNX ou NCNN com `raiar-vision export` e repetir o `benchmark` no nó | Escolher o formato que cumpre o RNF11, com a inferência em até 80% do intervalo entre quadros [4] |
| 3 | Trocar o PyTorch por um *runtime* de inferência menor, como o ONNX Runtime [5] | Só se a fase 1 não couber no orçamento; exige mudar o código do detector |

O `opencv-python` precisa das bibliotecas `libgl1` e `libglib2.0-0`, que arrastam componentes gráficos inúteis num nó sem tela. A troca por `opencv-python-headless` as dispensaria, mas altera o `pyproject.toml`, e por isso deixo a decisão com quem containeriza.

## Composição dos serviços

O arquivo abaixo está em `src/edge/exemplos-docker/02-raiar-vision/compose.yaml`. O serviço `sync` foi executado no notebook contra um backend simulado, enviou a análise e usou cerca de 1 MB de memória enquanto esperava. O serviço `vision` ainda depende da captura ao vivo. Os valores de memória e CPU precisam ser confirmados no nó com o modelo carregado [6].

```yaml
name: raiar-edge

x-comum: &comum
  image: raiar-vision:${RAIAR_TAG:-dev}
  restart: unless-stopped
  user: "1000:1000"
  read_only: true
  cap_drop: [ALL]
  security_opt: ["no-new-privileges:true"]
  environment:
    YOLO_CONFIG_DIR: /tmp/ultralytics
    RAIAR_SYNC_TOKEN: ${RAIAR_SYNC_TOKEN:-}
  volumes:
    - ${RAIAR_DATA:-/opt/raiar/data}:/app/outputs
  tmpfs:
    - /tmp:size=64m

services:
  vision:
    <<: *comum
    # Laço de captura e inferência ao vivo: ainda não existe no código (a implementar).
    devices: ["/dev/video0:/dev/video0"]
    group_add: ["${VIDEO_GID:-983}"]
    mem_limit: 2g
    cpus: 3.2
    tmpfs:
      - /tmp:size=64m
      - /frames:size=128m

  sync:
    <<: *comum
    entrypoint:
      - sh
      - -c
      - |
        while true; do
          raiar-vision sync --database /app/outputs/results.sqlite3 \
            --url "$$RAIAR_SYNC_URL" --token-env RAIAR_SYNC_TOKEN --batch-size 100 || true
          sleep 300
        done
    environment:
      YOLO_CONFIG_DIR: /tmp/ultralytics
      RAIAR_SYNC_TOKEN: ${RAIAR_SYNC_TOKEN:-}
      RAIAR_SYNC_URL: ${RAIAR_SYNC_URL:?defina RAIAR_SYNC_URL}
    mem_limit: 128m
    cpus: 0.5
```

Quatro pontos desse arquivo merecem explicação.

- O container roda com o usuário `1000:1000`, que é o `raiar` do nó, sem capacidades extras e sem novos privilégios [7]. A câmera é liberada por `devices`, e não por `privileged`, e o grupo é passado pelo número em `VIDEO_GID`. Para gravá-lo, uso `echo "VIDEO_GID=$(getent group video | cut -d: -f3)" >> /opt/raiar/.env` no nó. A pasta de dados precisa pertencer ao uid 1000, ou o container sem privilégios recebe `Permission denied`.
- O sistema de arquivos é somente leitura, com `/tmp` e `/frames` em memória, o que protege o cartão SD. A variável `YOLO_CONFIG_DIR` leva a configuração do `ultralytics` para `/tmp`, porque ele tenta gravar no diretório pessoal.
- A URL e o token do backend ficam em um arquivo `.env` com permissão `600`, nas variáveis `RAIAR_SYNC_URL` e `RAIAR_SYNC_TOKEN`. Nenhuma credencial entra na imagem nem no repositório. O `sync` aceita apenas HTTPS, ou HTTP em `localhost` para testes.
- `cpus: 3.2` é 80% dos quatro núcleos e funciona como teto. O RNF12 trata da média em janelas de cinco minutos, então o teto não substitui a medição.

## Entrega e atualização

Cada versão é uma imagem com *tag* única, como o hash curto do commit. Com isso, voltar atrás é trocar a *tag*.

1. No notebook, uma única vez, instalo `qemu-user-static` e `qemu-user-static-binfmt` para emular `arm64`.
2. Construo a imagem com `docker buildx build --platform linux/arm64 -t raiar-vision:TAG --load .` [8].
3. Envio ao nó por `docker save raiar-vision:TAG | gzip | ssh raiar@IP_DO_NO 'gunzip | docker load'`. Se a equipe adotar um registro de imagens, troco este passo por `docker pull`.
4. No nó, atualizo com `RAIAR_TAG=TAG docker compose up -d` e observo `docker compose logs`.
5. Se algo falhar, repito o passo 4 com a *tag* anterior.

O envio por SSH exige uma senha ou chave para o usuário `raiar`, que ainda deve ser definida com `passwd raiar` e `ssh-copy-id`.

## O que é preciso do nó e dos containers

Este é o combinado mínimo entre as duas frentes.

| Item | Valor combinado |
| --- | --- |
| Arquitetura da imagem | `linux/arm64` |
| Usuário no nó | `raiar` (uid 1000), nos grupos `docker` e `video` |
| Câmera | `/dev/video0`, por `devices` e o grupo `video` pelo número |
| Dados persistentes | `/opt/raiar/data`, montado em `/app/outputs` |
| Segredos | `/opt/raiar/.env`, permissão `600` |
| Comandos usados | `raiar-vision predict`, `raiar-vision sync` (nunca `chicken-yolo`) |
| Rede | Só saída HTTPS; nenhuma porta publicada pelos containers |
| Reinício | `restart: unless-stopped`, com o Docker habilitado no boot |

Da minha parte, entrego o nó com Docker, Compose, `zram` e as ferramentas de câmera. Da parte da containerização, espero a imagem, o `compose.yaml` e um `.env` de exemplo, sem credenciais.

## Pontos que ainda dependem de código ou de hardware

A captura ao vivo ainda não existe: hoje o `chicken_yolo` lê arquivos locais, e a integração com a câmera está prevista na documentação do detector. O serviço `vision` depende dessa captura e do laço periódico, que também deve registrar um sinal de funcionamento para um futuro `healthcheck`.

O Raspberry Pi não tem relógio de hardware. Depois de um reinício sem rede, o horário só se corrige quando o Wi-Fi volta, e um horário errado compromete a série temporal. Sugiro um módulo de relógio externo (RTC) no case e, no software, iniciar o Docker somente depois da sincronização de horário.

## Validação antes de homologar

| Teste | Critério | Requisito |
| --- | --- | --- |
| Câmera visível no nó | `v4l2-ctl --list-devices` lista a câmera e o container abre `/dev/video0` | RF04 |
| Consumo de recursos | `docker stats` com o modelo carregado cabe nos limites propostos | RNF12 |
| Tempo por quadro | Inferência em até 80% do intervalo em pelo menos 95% dos quadros | RNF11 |
| Operação contínua | 24 horas com CPU média de até 80% e memória disponível de pelo menos 20% | RNF12 |
| Sem rede | 24 horas sem Wi-Fi e envio único dos registros ao voltar | RNF01, RNF04 |
| Queda de energia | Após desligar e ligar, o Docker e os containers voltam sozinhos | RNF01 |
| Falhas registradas | Câmera desconectada ou rede fora gera registro, sem perda silenciosa | RNF10 |

## Referências {#referencias}

[1] DOCKER INC. **Compose file reference**. Disponível em: [https://docs.docker.com/reference/compose-file/](https://docs.docker.com/reference/compose-file/). Acesso em: 26 out. 2026.

[2] SQLITE. **Write-ahead logging**. Disponível em: [https://sqlite.org/wal.html](https://sqlite.org/wal.html). Acesso em: 26 out. 2026.

[3] PYTORCH FOUNDATION. **Get started locally**. Disponível em: [https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/). Acesso em: 26 out. 2026.

[4] ULTRALYTICS. **Raspberry Pi setup and benchmarks**. Disponível em: [https://docs.ultralytics.com/guides/raspberry-pi/](https://docs.ultralytics.com/guides/raspberry-pi/). Acesso em: 26 out. 2026.

[5] ONNX RUNTIME. **ONNX Runtime documentation**. Disponível em: [https://onnxruntime.ai/docs/](https://onnxruntime.ai/docs/). Acesso em: 26 out. 2026.

[6] DOCKER INC. **Resource constraints**. Disponível em: [https://docs.docker.com/engine/containers/resource_constraints/](https://docs.docker.com/engine/containers/resource_constraints/). Acesso em: 26 out. 2026.

[7] DOCKER INC. **Docker security**. Disponível em: [https://docs.docker.com/engine/security/](https://docs.docker.com/engine/security/). Acesso em: 26 out. 2026.

[8] DOCKER INC. **Multi-platform builds**. Disponível em: [https://docs.docker.com/build/building/multi-platform/](https://docs.docker.com/build/building/multi-platform/). Acesso em: 26 out. 2026.
