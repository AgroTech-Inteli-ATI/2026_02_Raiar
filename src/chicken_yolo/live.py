"""Captura contínua de câmeras (RTSP, USB ou arquivo) com reconexão e amostragem por intervalo."""

import hashlib
import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from .config import fingerprint, load_yaml
from .domain import Frame, utc_now

MIN_INTERVAL_SECONDS = 5.0
BACKOFF_START_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 60.0


@dataclass(frozen=True)
class CameraSpec:
    id: str
    source: str
    interval_seconds: float = MIN_INTERVAL_SECONDS
    lote_id: str | None = None
    enabled: bool = True
    zones: str | None = None


def redact_source(source: str) -> str:
    """Remove usuário e senha de URLs, para que credenciais do DVR não cheguem ao histórico."""
    parsed = urlparse(source)
    if not parsed.scheme or not (parsed.username or parsed.password):
        return source
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=host))


def parse_cameras(data: dict) -> list[CameraSpec]:
    entries = data.get("cameras")
    if not isinstance(entries, list) or not entries:
        raise ValueError("cameras.yaml deve ter a lista 'cameras' com ao menos uma câmera.")
    cameras, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry or "source" not in entry:
            raise ValueError("Cada câmera precisa de 'id' e 'source'.")
        camera = CameraSpec(
            id=str(entry["id"]),
            source=str(entry["source"]),
            interval_seconds=float(entry.get("interval_seconds", MIN_INTERVAL_SECONDS)),
            lote_id=None if entry.get("lote_id") is None else str(entry["lote_id"]),
            enabled=bool(entry.get("enabled", True)),
            zones=None if entry.get("zones") is None else str(entry["zones"]),
        )
        if camera.id in seen:
            raise ValueError(f"Câmera repetida: {camera.id}")
        if (
            not math.isfinite(camera.interval_seconds)
            or camera.interval_seconds < MIN_INTERVAL_SECONDS
        ):
            raise ValueError(
                f"Câmera {camera.id}: intervalo mínimo é {MIN_INTERVAL_SECONDS:g} s "
                "(o nó não acompanha intervalos menores)."
            )
        seen.add(camera.id)
        cameras.append(camera)
    return cameras


def load_cameras(path: Path) -> list[CameraSpec]:
    return parse_cameras(load_yaml(path))


def cameras_from_env(environ=os.environ) -> list[CameraSpec]:
    source = environ.get("RAIAR_CAMERA_SOURCE")
    if not source:
        raise ValueError("Informe --cameras ou defina RAIAR_CAMERA_SOURCE.")
    return parse_cameras(
        {
            "cameras": [
                {
                    "id": environ.get("RAIAR_CAMERA_ID", "camera-1"),
                    "source": source,
                    "lote_id": environ.get("RAIAR_LOTE_ID") or None,
                    "zones": environ.get("RAIAR_ZONES") or None,
                    "interval_seconds": environ.get("RAIAR_INTERVAL_SECONDS", MIN_INTERVAL_SECONDS),
                }
            ]
        }
    )


def open_capture(source: str):
    import cv2

    return cv2.VideoCapture(int(source) if source.isdigit() else source)


class LatestFrameReader:
    """Lê a câmera sem parar e guarda só o quadro mais recente.

    Evita atraso acumulado em RTSP enquanto a inferência ocupa a CPU, e reconecta com espera
    crescente quando o stream cai.
    """

    def __init__(
        self, source: str, opener=open_capture, backoff_start: float = BACKOFF_START_SECONDS
    ):
        self.source = source
        self._opener = opener
        self._backoff_start = backoff_start
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._image = None
        self._seq = 0
        self.reconnects = 0
        self.last_error: str | None = None
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=5)

    def latest(self):
        """Devolve (sequência, imagem) do último quadro lido, ou (0, None)."""
        with self._lock:
            return self._seq, self._image

    def _loop(self):
        backoff = self._backoff_start
        while not self._stop.is_set():
            capture = None
            try:
                capture = self._opener(self.source)
                if not capture.isOpened():
                    raise ConnectionError(f"Fonte de vídeo não abriu: {redact_source(self.source)}")
                while not self._stop.is_set():
                    ok, image = capture.read()
                    if not ok:
                        raise ConnectionError(
                            f"Leitura falhou ou o stream terminou: {redact_source(self.source)}"
                        )
                    backoff = self._backoff_start
                    with self._lock:
                        self._image, self._seq = image, self._seq + 1
            except Exception as exc:
                self.last_error = redact_source(str(exc))
            finally:
                if capture is not None:
                    capture.release()
            if self._stop.is_set():
                break
            self.reconnects += 1
            self._stop.wait(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX_SECONDS)


def make_frame(camera: CameraSpec, image) -> Frame:
    digest = hashlib.sha256(image.tobytes()).hexdigest()
    metadata = {
        "arquivo_ref": redact_source(camera.source),
        "origem_sha256": digest,
        "camera_id": camera.id,
        "lote_id": camera.lote_id,
        "sha256": digest,
        "offset_ms": None,
        "video_origem_ref": None,
        "capturado_em": utc_now(),
    }
    metadata["quadro_id"] = fingerprint(metadata)
    return Frame(image, metadata)


def run_cameras(
    cameras: list[CameraSpec],
    process,
    stop: threading.Event,
    max_frames: int | None = None,
    opener=open_capture,
    clock=time.monotonic,
    backoff_start: float = BACKOFF_START_SECONDS,
    on_error=None,
    on_status=None,
) -> int:
    """Amostra cada câmera no seu intervalo e entrega o quadro a `process(frame)`.

    `on_status(camera, evento, detalhe)` é chamado no laço principal (não na thread de leitura)
    com "queda" quando a câmera perde o stream e "recuperada" quando volta a entregar quadros.

    Um quadro só é processado uma vez: se a câmera não entregou nada novo desde a última
    amostra, o intervalo é adiado em vez de repetir a imagem.
    """
    active = [c for c in cameras if c.enabled]
    if not active:
        raise ValueError("Nenhuma câmera habilitada.")
    readers = {c.id: LatestFrameReader(c.source, opener, backoff_start).start() for c in active}
    due = dict.fromkeys(readers, clock())
    last_seq = dict.fromkeys(readers, 0)
    seen_reconnects = dict.fromkeys(readers, 0)
    down = dict.fromkeys(readers, False)
    processed = 0
    try:
        while not stop.is_set() and (max_frames is None or processed < max_frames):
            now = clock()
            for camera in active:
                reader = readers[camera.id]
                if on_status and reader.reconnects > seen_reconnects[camera.id]:
                    seen_reconnects[camera.id] = reader.reconnects
                    down[camera.id] = True
                    on_status(
                        camera, "queda", f"tentativa {reader.reconnects}: {reader.last_error}"
                    )
                if now < due[camera.id]:
                    continue
                seq, image = reader.latest()
                if image is None or seq == last_seq[camera.id]:
                    due[camera.id] = now + 1
                    continue
                last_seq[camera.id] = seq
                if on_status and down[camera.id]:
                    down[camera.id] = False
                    on_status(camera, "recuperada", "voltou a entregar quadros")
                due[camera.id] = now + camera.interval_seconds
                try:
                    process(make_frame(camera, image))
                    processed += 1
                except Exception as exc:
                    if on_error:
                        on_error(camera, exc)
                    else:
                        raise
                if max_frames is not None and processed >= max_frames:
                    break
            stop.wait(0.2)
    finally:
        for reader in readers.values():
            reader.stop()
    return processed
