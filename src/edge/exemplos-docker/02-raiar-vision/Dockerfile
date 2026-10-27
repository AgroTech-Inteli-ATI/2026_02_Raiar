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
