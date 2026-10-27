---
title: Exemplos de código dos containers
sidebar_label: Exemplos de código
sidebar_position: 2
description: Arquivos dos exemplos 01-contador e 02-raiar-vision, com a função de cada um.
---

# Exemplos de código dos containers

Os arquivos abaixo estão em `src/edge/exemplos-docker/`. O primeiro exemplo ensina os conceitos do Docker; o segundo containeriza o detector da Raiar. O [guia](./guia-docker-para-iniciantes.md) explica cada linha.

## Exemplo 01: contador

Programa mínimo que conta quantas vezes o container rodou e guarda o número em um volume. Serve para treinar imagem, volume, permissões e Compose.

### `01-contador/app/contador.py`

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

### `01-contador/Dockerfile`

```dockerfile
FROM python:3.12-slim
# Cria a pasta de dados já com o dono certo. Um volume novo herda esse dono.
RUN mkdir /dados && chown 1000:1000 /dados
WORKDIR /app
COPY app/contador.py .
USER 1000:1000
CMD ["python", "contador.py"]
```

### `01-contador/compose.yaml`

```yaml
name: contador

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
    command:
      - python
      - -c
      - |
        import os, time, pathlib
        p = pathlib.Path("/dados/saida.txt")
        i = 0
        while True:
            i += 1
            p.open("a").write(f"linha {i}\n")
            print(f"escrevi a linha {i}", flush=True)
            time.sleep(int(os.environ["INTERVALO"]))

  leitor:
    image: contador:2
    user: "1000:1000"
    restart: unless-stopped
    read_only: true
    mem_limit: 64m
    depends_on: [escritor]
    volumes:
      - dados:/dados:ro
    command: ["sh", "-c", "while true; do sleep 5; echo \"total de linhas: $(wc -l < /dados/saida.txt)\"; done"]

volumes:
  dados:
```

## Exemplo 02: imagem do nó de borda (`raiar-vision`)

Containeriza o módulo `chicken_yolo`, descrito em [Detecção de aves com YOLO](../../sprint-2/deteccao-de-aves.md). A imagem usa PyTorch só para CPU, embute os pesos e roda sem privilégios. O Compose separa a captura e a sincronização em dois serviços.

### `02-raiar-vision/Dockerfile`

```dockerfile
# Imagem do nó de borda Raiar. Construa a partir da RAIZ do repositório:
#   docker build -f src/edge/exemplos-docker/02-raiar-vision/Dockerfile \
#     --build-arg MODELO=coco -t raiar-vision:dev .
FROM python:3.12-slim

# Bibliotecas de sistema exigidas pelo opencv-python.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# PyTorch só para CPU. O uv.lock traria ~2,7 GB de bibliotecas NVIDIA que o Pi não usa.
RUN pip install --no-cache-dir torch==2.14.1 torchvision==0.29.1 \
      --index-url https://download.pytorch.org/whl/cpu

# Dependências e código mudam pouco e raramente juntos: cada COPY é uma camada de cache.
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/chicken_yolo ./src/chicken_yolo
RUN pip install --no-cache-dir .

# Embute os pesos na imagem: o nó não depende da internet para iniciar.
ARG MODELO=coco
RUN raiar-vision prepare-model ${MODELO}

# Usuário sem privilégios (uid 1000, o mesmo do usuário "raiar" do nó).
RUN useradd --uid 1000 --create-home raiar \
 && mkdir -p /app/outputs && chown raiar:raiar /app/outputs
USER raiar
ENV YOLO_CONFIG_DIR=/tmp/ultralytics

# IMPORTANTE: use "raiar-vision" e não "chicken-yolo". Com o nome terminado em "yolo",
# o Ultralytics se acha na linha de comando dele e o "predict" devolve None.
ENTRYPOINT ["raiar-vision"]
CMD ["--help"]
```

### `02-raiar-vision/compose.yaml`

```yaml
# Ponto de partida para o nó de borda. Suba com:  RAIAR_TAG=dev docker compose up -d
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
    # Hoje, "raiar-vision predict --source ARQUIVO" processa imagens e vídeos locais.
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

### `02-raiar-vision/.dockerignore`

```text
.git
.venv
**/__pycache__
data
outputs
docs
src/raiarnet
src/modelos_PIO
**/*.ipynb
```

### `02-raiar-vision/backend_falso.py`

Backend simulado que recebe os lotes do `raiar-vision sync`, usado para validar a sincronização sem o servidor real.

```python
"""Backend de mentira para testar o sync: aceita tudo e confirma os IDs recebidos."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ids = [a["analise_id"] for a in corpo["analyses"]]
        print(f"[backend] recebi {len(ids)} análise(s); token={self.headers.get('Authorization')}", flush=True)
        resp = json.dumps({"accepted_analysis_ids": ids}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp))); self.end_headers(); self.wfile.write(resp)
    def log_message(self, *a): pass

HTTPServer(("127.0.0.1", 8081), H).serve_forever()
```
