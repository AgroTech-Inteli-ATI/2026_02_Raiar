import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import requests
import yaml
from conftest import FakeDetector

from raiar_vision.config import InferenceConfig, file_hash
from raiar_vision.detector import YOLODetector, resolve_weights
from raiar_vision.pipeline import Pipeline
from raiar_vision.storage import ResultStore
from raiar_vision.sync import sync_pending
from raiar_vision.training import export_model, train_model


def store_frames(tmp_path, frame):
    database = tmp_path / "results.sqlite3"
    with ResultStore(database, tmp_path / "exports") as store:
        rows = [Pipeline(InferenceConfig(), FakeDetector()).process(frame) for _ in range(2)]
        for row in rows:
            store.save(row)
    return database, rows


def test_only_server_acknowledged_records_leave_pending_queue(tmp_path, frame):
    database, rows = store_frames(tmp_path, frame)

    def post(url, **kwargs):
        assert len(kwargs["json"]["analyses"]) == 2
        return SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"accepted_analysis_ids": [rows[0]["analise_id"]]},
        )

    assert sync_pending(database, "http://127.0.0.1/results", post=post) == {
        "sent": 2,
        "accepted": 1,
        "pending": 1,
    }

    def confirm_remaining(url, **kwargs):
        assert len(kwargs["json"]["analyses"]) == 1
        return SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"accepted_analysis_ids": [rows[1]["analise_id"]]},
        )

    assert (
        sync_pending(database, "http://127.0.0.1/results", post=confirm_remaining)["pending"] == 0
    )


def test_offline_failure_preserves_pending_records(tmp_path, frame):
    database, _ = store_frames(tmp_path, frame)

    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline")

    with pytest.raises(requests.ConnectionError):
        sync_pending(database, "https://example.test/results", post=offline)

    def no_ack(*args, **kwargs):
        return SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"accepted_analysis_ids": []},
        )

    assert sync_pending(database, "https://example.test/results", post=no_ack)["pending"] == 2


def test_invalid_ack_and_external_plain_http_are_rejected(tmp_path, frame):
    database, _ = store_frames(tmp_path, frame)
    with pytest.raises(ValueError, match="HTTPS"):
        sync_pending(database, "http://example.test/results")

    def post(*args, **kwargs):
        return SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"accepted_analysis_ids": ["unrelated-id"]},
        )

    with pytest.raises(ValueError, match="confirmar"):
        sync_pending(database, "https://example.test/results", post=post)


def test_training_preserves_pretrained_origin_and_reserved_dataset(prepared_dataset, monkeypatch):
    root, dataset, _ = prepared_dataset
    pretrained = root / "models/pretrained/coco"
    pretrained.mkdir(parents=True)
    weights = pretrained / "base.pt"
    weights.write_bytes(b"fake-checkpoint-only-for-tests")
    (pretrained / "metadata.json").write_text(
        json.dumps(
            {
                "weights": str(weights),
                "sha256": file_hash(weights),
                "id": "coco",
            }
        ),
        encoding="utf-8",
    )
    calls = []

    class FakeYOLO:
        def __init__(self, path, task):
            assert path == str(weights)

        def train(self, **kwargs):
            calls.append(kwargs)
            save = root / "runs/fake-training"
            (save / "weights").mkdir(parents=True)
            (save / "weights/best.pt").write_bytes(b"fake-trained-checkpoint")
            self.trainer = SimpleNamespace(save_dir=save)

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    config = root / "training.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "model": "coco",
                "weights": None,
                "dataset": str(dataset / "dataset.yaml"),
                "epochs": 1,
            }
        ),
        encoding="utf-8",
    )
    metadata = train_model(config)
    assert calls[0]["data"] == str(dataset / "dataset.yaml")
    assert metadata["source_model"]["sha256"] == file_hash(weights)
    assert metadata["status"] == "aguardando_avaliacao"
    assert metadata["dataset"]["counts"]["test"] == 2
    assert (root / metadata["weights"]).is_file()


def test_detector_filters_chickens_by_name_and_excludes_eggs(tmp_path, monkeypatch):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"fake-only-for-tests")
    calls = []

    class FakeYOLO:
        names = {0: "chicken", 1: "egg"}
        task = "detect"

        def __init__(self, *args, **kwargs):
            pass

        def predict(self, *args, **kwargs):
            calls.append(kwargs)
            data = SimpleNamespace(
                cpu=lambda: SimpleNamespace(tolist=lambda: [[1, 2, 3, 4, 0.9, 0]])
            )
            return [SimpleNamespace(boxes=SimpleNamespace(data=data))]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    detector = YOLODetector(InferenceConfig(weights=str(weights)), tmp_path)
    result = detector.predict(np.zeros((10, 10, 3), dtype=np.uint8))
    assert calls[0]["classes"] == [0]
    assert result.detections[0].class_name == "chicken"


def test_exported_model_loads_with_its_own_hash_beside_checkpoint_metadata(tmp_path, monkeypatch):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"checkpoint")
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "weights": str(weights),
                "sha256": file_hash(weights),
                "id": "trained",
            }
        ),
        encoding="utf-8",
    )
    artifact = tmp_path / "best.onnx"

    class FakeYOLO:
        def __init__(self, *args, **kwargs):
            pass

        def export(self, **kwargs):
            artifact.write_bytes(b"exported-model")
            return str(artifact)

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    assert export_model(weights, "onnx") == str(artifact)
    path, metadata = resolve_weights(tmp_path, "unused", str(artifact))
    assert path == artifact
    assert metadata["sha256"] == file_hash(artifact)
    assert metadata["source_model"]["sha256"] == file_hash(weights)
