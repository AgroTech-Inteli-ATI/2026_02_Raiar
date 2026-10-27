FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OMP_NUM_THREADS=4 \
    RAIARNET_NUM_THREADS=4

WORKDIR /app/src/raiarnet

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY docker/raiarnet/requirements.txt /tmp/requirements.txt
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.10.0 \
    && pip install -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY src/raiarnet/models ./models
COPY src/raiarnet/preprocessing ./preprocessing
COPY src/raiarnet/configs/cameras ./configs/cameras

ENTRYPOINT ["python", "-m", "models.predict"]
CMD ["--help"]
