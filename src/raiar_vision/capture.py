"""Leitura incremental de arquivos locais; horário desconhecido permanece nulo."""

import hashlib
import math
from datetime import timedelta
from pathlib import Path

from .config import file_hash, fingerprint
from .domain import Frame, parse_timestamp

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}


def read_image(path: Path):
    # imdecode suporta caminhos com acentos no Windows.
    import cv2
    import numpy as np

    return cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)


def write_image(path: Path, image) -> None:
    import cv2

    ok, encoded = cv2.imencode(path.suffix, image)
    if not ok:
        raise OSError(f"Não foi possível codificar a imagem: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded.tobytes())


def iter_frames(
    source: Path,
    sample_seconds: float = 1,
    camera_id: str | None = None,
    lote_id: str | None = None,
    captured_at: str | None = None,
):
    if not math.isfinite(sample_seconds) or sample_seconds <= 0:
        raise ValueError("Intervalo de amostragem deve ser positivo e finito.")
    source = source.resolve()
    start = parse_timestamp(captured_at)
    if source.is_dir():
        if start is not None:
            raise ValueError("Informe horários por arquivo; captured-at não vale para uma pasta.")
        files = sorted(
            p for p in source.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES
        )
        if not files:
            raise ValueError("Pasta sem imagens ou vídeos suportados.")
        for path in files:
            yield from iter_frames(path, sample_seconds, camera_id, lote_id)
        return
    if not source.is_file():
        raise FileNotFoundError(f"Entrada não encontrada: {source}")
    source_sha = file_hash(source)
    base = {
        "arquivo_ref": str(source),
        "origem_sha256": source_sha,
        "camera_id": camera_id,
        "lote_id": lote_id,
    }
    if source.suffix.lower() in IMAGE_SUFFIXES:
        image = read_image(source)
        metadata = {
            **base,
            "sha256": source_sha,
            "offset_ms": None,
            "video_origem_ref": None,
            "capturado_em": start.isoformat() if start else None,
        }
        metadata["quadro_id"] = fingerprint(metadata)
        yield Frame(image, metadata, "Imagem não decodificada." if image is None else None)
        return
    if source.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"Formato não suportado: {source.suffix}")
    import cv2

    capture = cv2.VideoCapture(str(source))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not capture.isOpened() or not math.isfinite(fps) or fps <= 0:
            raise ValueError("Vídeo não pode ser aberto ou não possui FPS válido.")
        next_sample = 0.0
        index = 0
        yielded = False
        while True:
            ok, image = capture.read()
            if not ok:
                break
            offset = index / fps
            if offset + 1e-9 >= next_sample:
                metadata = {
                    **base,
                    "sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                    "offset_ms": round(offset * 1000),
                    "video_origem_ref": str(source),
                    "capturado_em": (start + timedelta(seconds=offset)).isoformat()
                    if start
                    else None,
                }
                metadata["quadro_id"] = fingerprint(metadata)
                yield Frame(image, metadata)
                yielded = True
                next_sample += sample_seconds
            index += 1
        if not yielded:
            raise ValueError("Vídeo sem quadros decodificáveis.")
    finally:
        capture.release()
