FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    YOLO_CONFIG_DIR=/cache/ultralytics \
    MPLCONFIGDIR=/cache/matplotlib \
    TORCH_HOME=/cache/torch

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src/chicken_yolo ./src/chicken_yolo

ENV PATH="/opt/venv/bin:${PATH}"

RUN uv sync --frozen --no-dev \
        --no-install-package torch \
        --no-install-package torchvision \
        --no-install-package opencv-python \
        --no-install-package cuda-bindings \
        --no-install-package cuda-pathfinder \
        --no-install-package cuda-toolkit \
        --no-install-package nvidia-cublas \
        --no-install-package nvidia-cuda-cupti \
        --no-install-package nvidia-cuda-nvrtc \
        --no-install-package nvidia-cuda-runtime \
        --no-install-package nvidia-cudnn-cu13 \
        --no-install-package nvidia-cufft \
        --no-install-package nvidia-cufile \
        --no-install-package nvidia-curand \
        --no-install-package nvidia-cusolver \
        --no-install-package nvidia-cusparse \
        --no-install-package nvidia-cusparselt-cu13 \
        --no-install-package nvidia-nccl-cu13 \
        --no-install-package nvidia-nvjitlink \
        --no-install-package nvidia-nvshmem-cu13 \
        --no-install-package nvidia-nvtx \
        --no-install-package triton \
    && uv pip install --python /opt/venv/bin/python \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.14.1 torchvision==0.29.1 \
    && uv pip install --python /opt/venv/bin/python \
        --index-url https://pypi.org/simple opencv-python-headless==4.14.0.94

ARG MODELO=coco
RUN useradd --uid 1000 --create-home raiar \
    && mkdir -p /app/outputs /cache \
    && chown -R raiar:raiar /app/outputs /cache \
    && raiar-vision --root /app prepare-model "${MODELO}" \
    && rm -rf /app/.cache /cache/*

USER raiar

ENTRYPOINT ["raiar-vision", "--root", "/app"]
CMD ["--help"]
