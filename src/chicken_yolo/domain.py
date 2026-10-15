"""Tipos compartilhados pelo detector, captura e avaliação."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Horário de captura deve incluir fuso, por exemplo -03:00 ou Z.")
    return timestamp.astimezone(timezone.utc)


@dataclass(frozen=True)
class Detection:
    bbox_px: tuple[float, float, float, float]
    confidence: float
    class_id: int
    class_name: str


@dataclass
class InferenceOutput:
    detections: list[Detection]
    duration_ms: float
    details: dict = field(default_factory=dict)


@dataclass
class Frame:
    image: Any
    metadata: dict
    error: str | None = None
    manual_quality: str | None = None
    extra: dict = field(default_factory=dict)
