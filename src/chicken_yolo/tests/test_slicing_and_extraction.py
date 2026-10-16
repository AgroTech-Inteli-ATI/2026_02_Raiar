import json
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import FakeDetector

from chicken_yolo.capture import read_image, write_image
from chicken_yolo.config import InferenceConfig, SlicingConfig
from chicken_yolo.dataset import export_crops, extract_frames, read_jsonl
from chicken_yolo.detector import YOLODetector, roi_pixels
from chicken_yolo.evaluation import evaluate_dataset
from chicken_yolo.pipeline import Pipeline


def test_lossless_extraction_preserves_native_pixels_and_unknown_metadata(tmp_path):
    image = np.random.default_rng(42).integers(0, 256, (100, 200, 3), dtype=np.uint8)
    source = tmp_path / "source.png"
    write_image(source, image)
    manifest = extract_frames(tmp_path, source, "session-01", "CAM16", None, 20)
    row = json.loads(manifest.read_text(encoding="utf-8"))
    assert row["imagem"].endswith(".png")
    assert np.array_equal(read_image(tmp_path / row["imagem"]), image)
    assert row["capturado_em"] is None and row["lote_id"] is None
    assert row["grupo_origem"] == "session-01"
    assert row["qualidade"] == "pendente" and row["status_revisao"] == "rascunho"


@pytest.mark.parametrize(
    "roi", [(0, 0, 1, 2), (0.5, 0, 0.5, 1), (0, 0, float("nan"), 1), (0, 1, 1, 0)]
)
def test_invalid_regions_are_rejected(roi):
    with pytest.raises(ValueError):
        InferenceConfig(roi=roi)


@pytest.mark.parametrize(
    "kwargs", [{"width": 63}, {"overlap": 0.5}, {"merge_iou": 0}, {"height": 128.5}]
)
def test_invalid_slicing_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        SlicingConfig(**kwargs)


def fake_yolo_detector(config):
    detector = YOLODetector.__new__(YOLODetector)
    detector.config = config
    detector.class_ids = [0]
    detector.metadata = {"sha256": "test-sha"}
    calls = []

    def predict(images, **kwargs):
        calls.append((images, kwargs))
        data = SimpleNamespace(
            cpu=lambda: SimpleNamespace(tolist=lambda: [[10, 5, 20, 15, 0.9, 0]])
        )
        return [SimpleNamespace(boxes=SimpleNamespace(data=data))]

    detector.model = SimpleNamespace(names={0: "chicken", 1: "egg"}, task="detect", predict=predict)
    return detector, calls


def test_roi_predictions_are_translated_back_to_original_image():
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    config = InferenceConfig(roi=(0.25, 0.25, 0.75, 0.75))
    detector, calls = fake_yolo_detector(config)
    assert roi_pixels(image, config.roi) == (50, 25, 150, 75)
    prediction = detector.predict(image, confidence=0.1)
    assert calls[0][0].shape == (50, 100, 3)
    assert calls[0][1]["conf"] == 0.1
    assert prediction.detections[0].bbox_px == (60, 30, 70, 40)
    assert prediction.details["roi_px"] == [50, 25, 150, 75]


def test_sahi_receives_rgb_preserves_filters_and_translates_boxes(monkeypatch):
    config = InferenceConfig(roi=(0.25, 0.25, 0.75, 0.75), slicing=SlicingConfig(enabled=True))
    detector, calls = fake_yolo_detector(config)

    class FakeSAHI:
        def __init__(self, **kwargs):
            self.model = kwargs["model"]

    def sliced(image, **kwargs):
        assert list(image[0, 0]) == [30, 20, 10]
        assert kwargs["postprocess_type"] == "NMS"
        assert kwargs["postprocess_class_agnostic"] is False
        kwargs["detection_model"].model([image], conf=0.25, device="cpu", imgsz=640, verbose=False)

        def proposal(cls):
            return SimpleNamespace(
                category=SimpleNamespace(id=cls),
                bbox=SimpleNamespace(to_xyxy=lambda: [10, 5, 20, 15]),
                score=SimpleNamespace(value=0.9),
            )

        return SimpleNamespace(object_prediction_list=[proposal(0), proposal(1)])

    monkeypatch.setattr("sahi.models.ultralytics.UltralyticsDetectionModel", FakeSAHI)
    monkeypatch.setattr("sahi.predict.get_sliced_prediction", sliced)
    image = np.full((100, 200, 3), [10, 20, 30], dtype=np.uint8)
    output = detector.predict(image)
    assert len(output.detections) == 1
    assert output.detections[0].bbox_px == (60, 30, 70, 40)
    assert output.detections[0].class_name == "chicken"
    assert calls[0][1]["classes"] == [0]
    assert calls[0][1]["max_det"] == config.max_det
    assert calls[0][1]["iou"] == config.iou
    assert output.details["mode"] == "sliced"


def test_roi_scope_is_explicit_and_cannot_be_compared_to_full_frame_reference(frame, tmp_path):
    config = InferenceConfig(roi=(0.1, 0.1, 0.9, 0.9))
    result = Pipeline(config, FakeDetector()).process(frame)
    assert result["escopo_contagem"] == "regiao_configurada"
    with pytest.raises(ValueError, match="recorte"):
        evaluate_dataset(config, FakeDetector(), tmp_path / "unused.yaml", tmp_path / "report")


def test_exported_crops_keep_pixels_parent_and_group_without_becoming_negatives(raw_dataset):
    root, manifest, rows = raw_dataset
    output = root / "crops"
    exported = read_jsonl(export_crops(root, manifest, output, (0.25, 0.25, 0.75, 0.75)))
    for parent, child in zip(rows, exported, strict=True):
        expected = read_image(root / parent["imagem"])[25:75, 25:75]
        assert np.array_equal(read_image(root / child["imagem"]), expected)
        assert child["grupo_origem"] == parent["grupo_origem"]
        assert child["parent_quadro_id"] == parent["quadro_id"]
        assert child["qualidade"] == "pendente" and child["status_revisao"] == "rascunho"
        assert not (root / child["rotulo"]).exists()
