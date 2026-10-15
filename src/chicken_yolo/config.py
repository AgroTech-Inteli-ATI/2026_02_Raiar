"""Configurações e caminhos independentes do diretório de execução."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Configuração deve ser um mapa: {path}")
    return value


def project_root(path: Path) -> Path:
    for parent in [path.resolve().parent, *path.resolve().parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise ValueError("Configuração deve estar dentro do projeto com pyproject.toml.")


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_hash(path: Path) -> str:
    if path.is_file():
        return file_hash(path)
    if path.is_dir():
        files = sorted(item for item in path.rglob("*") if item.is_file())
        if files:
            return fingerprint({str(item.relative_to(path)): file_hash(item) for item in files})
    raise FileNotFoundError(f"Pesos ausentes ou artefato vazio: {path}")


@dataclass(frozen=True)
class QualityConfig:
    min_width: int = 64
    min_height: int = 64
    min_brightness: float = 5.0
    max_brightness: float = 250.0
    min_blur_score: float | None = None

    def __post_init__(self):
        if self.min_width <= 0 or self.min_height <= 0:
            raise ValueError("Dimensões mínimas devem ser positivas.")
        if not 0 <= self.min_brightness < self.max_brightness <= 255:
            raise ValueError("Faixa de brilho deve estar entre 0 e 255.")
        if self.min_blur_score is not None and (
            not math.isfinite(self.min_blur_score) or self.min_blur_score < 0
        ):
            raise ValueError("Limiar de desfoque inválido.")


@dataclass(frozen=True)
class SlicingConfig:
    enabled: bool = False
    height: int = 256
    width: int = 256
    overlap: float = 0.2
    merge_iou: float = 0.5
    standard_prediction: bool = False

    def __post_init__(self):
        if (
            type(self.height) is not int
            or type(self.width) is not int
            or min(self.height, self.width) < 64
        ):
            raise ValueError(
                "Recortes devem ter largura e altura inteiras de pelo menos 64 pixels."
            )
        if not 0 <= self.overlap < 0.5 or not 0 < self.merge_iou <= 1:
            raise ValueError("Sobreposição deve estar em [0, 0.5); IoU de união em (0, 1].")


@dataclass(frozen=True)
class InferenceConfig:
    model: str = "poultryvision"
    weights: str | None = None
    allowed_classes: tuple[str, ...] = ("chicken", "bird", "galinha")
    confidence: float = 0.25
    iou: float = 0.6
    imgsz: int = 640
    max_det: int = 1000
    device: str = "cpu"
    sample_seconds: float = 1.0
    zones: str | None = None
    output_dir: str = "outputs"
    database: str = "outputs/results.sqlite3"
    save_annotated: bool = True
    quality: QualityConfig = field(default_factory=QualityConfig)
    slicing: SlicingConfig = field(default_factory=SlicingConfig)
    roi: tuple[float, float, float, float] | None = None

    def __post_init__(self):
        if not 0 < self.confidence <= 1 or not 0 < self.iou <= 1:
            raise ValueError("Confiança e IoU devem estar no intervalo (0, 1].")
        if self.imgsz < 32 or self.imgsz % 32 or self.max_det < 1:
            raise ValueError("imgsz deve ser múltiplo de 32; max_det deve ser positivo.")
        if not math.isfinite(self.sample_seconds) or self.sample_seconds <= 0:
            raise ValueError("Intervalo de amostragem deve ser positivo e finito.")
        if not self.allowed_classes or any(not isinstance(x, str) for x in self.allowed_classes):
            raise ValueError("Informe os nomes das classes aceitas.")
        if self.roi is not None and (
            len(self.roi) != 4
            or any(not math.isfinite(v) or not 0 <= v <= 1 for v in self.roi)
            or not self.roi[0] < self.roi[2]
            or not self.roi[1] < self.roi[3]
        ):
            raise ValueError(
                "ROI deve ser [x_min, y_min, x_max, y_max] normalizada e com área positiva."
            )

    def snapshot(self) -> dict:
        return asdict(self)


def load_inference(path: Path) -> tuple[InferenceConfig, Path]:
    raw = load_yaml(path)
    raw["quality"] = QualityConfig(**raw.get("quality", {}))
    raw["slicing"] = SlicingConfig(**raw.get("slicing", {}))
    if raw.get("roi") is not None:
        raw["roi"] = tuple(raw["roi"])
    raw["allowed_classes"] = tuple(raw.get("allowed_classes", ("chicken", "bird", "galinha")))
    return InferenceConfig(**raw), project_root(path)
