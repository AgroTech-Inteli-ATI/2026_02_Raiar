FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    YOLO_CONFIG_DIR=/app/.cache/ultralytics \
    MPLCONFIGDIR=/app/.cache/matplotlib \
    TORCH_HOME=/app/.cache/torch

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src/chicken_yolo ./src/chicken_yolo

RUN uv sync --frozen --no-dev \
    && uv pip install --python /opt/venv/bin/python \
        --index-url https://download.pytorch.org/whl/cpu torch==2.10.0

ENV PATH="/opt/venv/bin:${PATH}"

ENTRYPOINT ["chicken-yolo", "--root", "/app"]
CMD ["--help"]
