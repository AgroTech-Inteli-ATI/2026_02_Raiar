"""Treinamento transferido com origem, parâmetros e dataset preservados."""

import json
import shutil
import uuid
from pathlib import Path

from .config import artifact_hash, load_yaml, project_root, resolve_path
from .dataset import validate_dataset
from .detector import resolve_weights
from .domain import utc_now


def train_model(config_path: Path) -> dict:
    config = load_yaml(config_path)
    root = project_root(config_path)
    data = resolve_path(root, config.pop("dataset"))
    _, _, dataset_metadata = validate_dataset(data)
    weights, original_metadata = resolve_weights(
        root, config.pop("model"), config.pop("weights", None)
    )
    allowed = {"epochs", "patience", "imgsz", "batch", "device", "workers", "seed", "deterministic"}
    if set(config) - allowed or config.get("epochs", 0) < 1:
        raise ValueError("Configuração de treinamento contém parâmetros inválidos.")
    from ultralytics import YOLO

    name = f"galinhas-{uuid.uuid4().hex[:12]}"
    model = YOLO(str(weights), task="detect")
    model.train(
        data=str(data), project=str(root / "runs/train"), name=name, exist_ok=False, **config
    )
    best = Path(model.trainer.save_dir) / "weights/best.pt"
    if not best.is_file():
        raise RuntimeError("Treinamento não produziu weights/best.pt.")
    destination = root / "src/chicken_yolo/models/trained" / name
    destination.mkdir(parents=True, exist_ok=False)
    target = destination / "best.pt"
    shutil.copy2(best, target)
    metadata = {
        "id": name,
        "weights": target.relative_to(root).as_posix(),
        "sha256": artifact_hash(target),
        "source_model": original_metadata,
        "dataset": dataset_metadata,
        "parameters": config,
        "trained_at": utc_now(),
        "status": "aguardando_avaliacao",
        "classes": ["galinha"],
    }
    (destination / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def export_model(weights: Path, format_name: str, imgsz: int = 640) -> str:
    if not weights.exists():
        raise FileNotFoundError(f"Pesos não encontrados: {weights}")
    if format_name not in {"onnx", "ncnn"}:
        raise ValueError("Formatos suportados: onnx e ncnn.")
    from ultralytics import YOLO

    source_hash = artifact_hash(weights)
    artifact = Path(
        YOLO(str(weights), task="detect").export(format=format_name, imgsz=imgsz)
    ).resolve()
    metadata = {
        "id": "exported",
        "weights": str(artifact),
        "sha256": artifact_hash(artifact),
        "source_model": {"weights": str(weights.resolve()), "sha256": source_hash},
        "format": format_name,
        "imgsz": imgsz,
        "exported_at": utc_now(),
    }
    Path(f"{artifact}.raiar.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return str(artifact)
