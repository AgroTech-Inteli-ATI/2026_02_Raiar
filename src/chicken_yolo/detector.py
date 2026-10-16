"""Adapter YOLO com filtro por nome e pesos locais rastreáveis."""

import json
import math
import shutil
import time
from pathlib import Path

from .config import InferenceConfig, artifact_hash, load_yaml, resolve_path
from .domain import Detection, InferenceOutput, utc_now


def roi_pixels(image, roi) -> tuple[int, int, int, int]:
    height, width = image.shape[:2]
    if roi is None:
        return 0, 0, width, height
    box = (
        int(roi[0] * width),
        int(roi[1] * height),
        min(width, math.ceil(roi[2] * width)),
        min(height, math.ceil(roi[3] * height)),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("ROI não contém pixels nesta resolução.")
    return box


class _SAHIModelProxy:
    """Aplicar os mesmos filtros e parâmetros YOLO em cada recorte do SAHI."""

    def __init__(self, detector):
        self.detector = detector

    def __getattr__(self, name):
        return getattr(self.detector.model, name)

    def __call__(self, images, **kwargs):
        config = self.detector.config
        return self.detector.model.predict(
            images,
            iou=config.iou,
            max_det=config.max_det,
            classes=self.detector.class_ids,
            rect=False,
            **kwargs,
        )


def prepare_model(root: Path, name: str) -> dict:
    registry = load_yaml(root / "src/chicken_yolo/models/registry.yaml")["models"]
    if name not in registry:
        raise ValueError(f"Modelo desconhecido: {name}. Opções: {', '.join(registry)}")
    entry = registry[name]
    destination = root / "src/chicken_yolo/models/pretrained" / name
    destination.mkdir(parents=True, exist_ok=True)
    metadata_file = destination / "metadata.json"
    if metadata_file.is_file():
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        weights = resolve_path(root, metadata["weights"])
        if weights.exists() and artifact_hash(weights) == metadata["sha256"]:
            return metadata
        raise ValueError("Modelo local foi alterado; use outra pasta para baixar uma nova versão.")
    if entry["provider"] == "huggingface":
        from huggingface_hub import HfApi, hf_hub_download

        revision = HfApi().model_info(entry["repo_id"], revision=entry.get("revision")).sha
        snapshot = Path(
            hf_hub_download(
                entry["repo_id"],
                entry["filename"],
                revision=revision,
                cache_dir=root / ".cache/huggingface",
            )
        )
        weights = destination / revision / entry["filename"]
        weights.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot, weights)
    elif entry["provider"] == "ultralytics":
        from ultralytics import YOLO

        revision = None
        weights = destination / entry["filename"]
        YOLO(str(weights))  # Ultralytics baixa o asset oficial neste caminho.
    else:
        raise ValueError("Provedor de modelo não suportado.")
    metadata = {
        **entry,
        "id": name,
        "revision": revision,
        "weights": weights.relative_to(root).as_posix(),
        "sha256": artifact_hash(weights),
        "prepared_at": utc_now(),
    }
    metadata_file.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def resolve_weights(root: Path, model: str, weights: str | None = None) -> tuple[Path, dict]:
    if weights:
        path = resolve_path(root, weights)
        checksum = artifact_hash(path)
        for metadata_path in (Path(f"{path}.raiar.json"), path.parent / "metadata.json"):
            if not metadata_path.is_file():
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if resolve_path(root, metadata.get("weights", "")) != path:
                continue
            if metadata.get("sha256") != checksum:
                raise ValueError("Hash do checkpoint próprio não corresponde aos metadados.")
            return path, metadata
        return path, {"id": "custom", "weights": str(path), "sha256": checksum}
    metadata_path = root / "src/chicken_yolo/models/pretrained" / model / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"Modelo não preparado. Execute: chicken-yolo prepare-model {model}"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    path = resolve_path(root, metadata["weights"])
    if artifact_hash(path) != metadata["sha256"]:
        raise ValueError("Hash do modelo não corresponde ao registro local.")
    return path, metadata


class YOLODetector:
    def __init__(self, config: InferenceConfig, root: Path):
        from ultralytics import YOLO

        path, self.metadata = resolve_weights(root, config.model, config.weights)
        self.model = YOLO(str(path), task="detect")
        if self.model.task != "detect":
            raise ValueError("Este pipeline aceita somente modelos de detecção.")
        self.config = config
        accepted = {name.strip().lower() for name in config.allowed_classes}
        self.class_ids = [
            int(i) for i, name in self.model.names.items() if name.strip().lower() in accepted
        ]
        if not self.class_ids:
            raise ValueError(f"Nenhuma classe aceita no modelo: {self.model.names}")

    def predict(self, image, confidence: float | None = None) -> InferenceOutput:
        start = time.perf_counter()
        threshold = confidence if confidence is not None else self.config.confidence
        x1, y1, x2, y2 = roi_pixels(image, self.config.roi)
        region = image[y1:y2, x1:x2]
        if self.config.slicing.enabled:
            return self._predict_sliced(region, (x1, y1, x2, y2), threshold, start)
        result = self.model.predict(
            region,
            conf=threshold,
            iou=self.config.iou,
            imgsz=self.config.imgsz,
            max_det=self.config.max_det,
            device=self.config.device,
            classes=self.class_ids,
            rect=False,
            verbose=False,
        )[0]
        detections = [
            Detection(
                (float(box[0]) + x1, float(box[1]) + y1, float(box[2]) + x1, float(box[3]) + y1),
                float(box[4]),
                int(box[5]),
                self.model.names[int(box[5])],
            )
            for box in result.boxes.data.cpu().tolist()
        ]
        return InferenceOutput(
            detections,
            (time.perf_counter() - start) * 1000,
            {"mode": "standard", "roi_px": [x1, y1, x2, y2]},
        )

    def _predict_sliced(self, region, roi, threshold: float, start: float) -> InferenceOutput:
        from sahi.models.ultralytics import UltralyticsDetectionModel
        from sahi.predict import get_sliced_prediction
        from sahi.slicing import get_slice_bboxes

        slicing = self.config.slicing
        model = UltralyticsDetectionModel(
            model=_SAHIModelProxy(self),
            device=self.config.device,
            confidence_threshold=threshold,
            image_size=self.config.imgsz,
        )
        # O pipeline usa BGR; o SAHI recebe RGB e devolve caixas no sistema da região.
        result = get_sliced_prediction(
            region[:, :, ::-1],
            detection_model=model,
            slice_height=slicing.height,
            slice_width=slicing.width,
            overlap_height_ratio=slicing.overlap,
            overlap_width_ratio=slicing.overlap,
            perform_standard_pred=slicing.standard_prediction,
            postprocess_type="NMS",
            postprocess_match_metric="IOU",
            postprocess_match_threshold=slicing.merge_iou,
            postprocess_class_agnostic=False,
            force_postprocess_type=True,
            auto_slice_resolution=False,
            verbose=0,
            progress_bar=False,
        )
        detections = []
        for prediction in result.object_prediction_list:
            cls = int(prediction.category.id)
            if cls not in self.class_ids:
                continue
            box = prediction.bbox.to_xyxy()
            detections.append(
                Detection(
                    (
                        float(box[0]) + roi[0],
                        float(box[1]) + roi[1],
                        float(box[2]) + roi[0],
                        float(box[3]) + roi[1],
                    ),
                    float(prediction.score.value),
                    cls,
                    self.model.names[cls],
                )
            )
        detections.sort(key=lambda detection: detection.confidence, reverse=True)
        tile_count = len(
            get_slice_bboxes(
                region.shape[0],
                region.shape[1],
                slicing.height,
                slicing.width,
                False,
                slicing.overlap,
                slicing.overlap,
            )
        )
        return InferenceOutput(
            detections[: self.config.max_det],
            (time.perf_counter() - start) * 1000,
            {
                "mode": "sliced",
                "roi_px": list(roi),
                "tile_count": tile_count,
                "merged_detections": len(detections),
                "truncated": len(detections) > self.config.max_det,
            },
        )
