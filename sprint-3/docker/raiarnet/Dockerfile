FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OMP_NUM_THREADS=4 \
    RAIARNET_NUM_THREADS=4

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY sprint-3/docker/raiarnet/requirements.txt /tmp/requirements.txt
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.14.1 \
    && pip install -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt \
    && useradd --uid 1000 --create-home raiar \
    && mkdir -p /app/outputs /cache \
    && chown -R raiar:raiar /app/outputs /cache

COPY --chown=raiar:raiar src/raiarnet/models ./src/raiarnet/models
COPY --chown=raiar:raiar src/raiarnet/preprocessing ./src/raiarnet/preprocessing
COPY --chown=raiar:raiar src/raiarnet/configs/cameras ./src/raiarnet/configs/cameras

WORKDIR /app/src/raiarnet
USER raiar

ENTRYPOINT ["python", "-m", "models.predict"]
CMD ["--help"]
