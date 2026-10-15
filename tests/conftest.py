import json

import numpy as np
import pytest

from raiar_vision.capture import write_image
from raiar_vision.dataset import prepare_dataset
from raiar_vision.domain import Detection, Frame, InferenceOutput
from raiar_vision.zones import Zone, ZoneConfig


class FakeDetector:
    metadata = {"id": "fake-for-tests", "sha256": "a" * 64}

    def __init__(self, detections=(), error=None):
        self.detections = list(detections)
        self.error = error
        self.calls = []

    def predict(self, image, confidence=None):
        self.calls.append(confidence)
        if self.error:
            raise RuntimeError(self.error)
        return InferenceOutput(self.detections, 1.0)


@pytest.fixture
def zones():
    return ZoneConfig(
        "camera-01",
        "zones-v1",
        "borda-inferior-v1",
        (100, 100),
        (
            Zone("superior", ((0, 0), (1, 0), (1, 0.5), (0, 0.5))),
            Zone("inferior", ((0, 0.5), (1, 0.5), (1, 1), (0, 1))),
        ),
        "z" * 64,
    )


@pytest.fixture
def frame():
    return Frame(
        np.full((100, 100, 3), 120, dtype=np.uint8),
        {
            "quadro_id": "frame-01",
            "camera_id": "camera-01",
            "lote_id": "lote-01",
            "capturado_em": None,
            "arquivo_ref": "test.png",
        },
    )


@pytest.fixture
def detection():
    return Detection((10, 10, 30, 30), 0.9, 14, "bird")


@pytest.fixture
def raw_dataset(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    rows = []
    for index in range(6):
        image = root / f"image-{index}.png"
        label = image.with_suffix(".txt")
        write_image(image, np.full((100, 100, 3), 80 + index * 10, dtype=np.uint8))
        label.write_text("0 0.2 0.2 0.2 0.2\n", encoding="utf-8")
        rows.append(
            {
                "imagem": image.name,
                "rotulo": label.name,
                "quadro_id": f"frame-{index}",
                "grupo_origem": f"session-{index // 2}",
                "qualidade": "avaliavel",
                "status_revisao": "revisada",
                "camera_id": "camera-01",
                "lote_id": "lote-01",
                "contagens_por_nivel": {"superior": 1, "inferior": 0},
                "zonas_versao": "zones-v1",
            }
        )
    manifest = root / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return root, manifest, rows


@pytest.fixture
def prepared_dataset(raw_dataset):
    root, manifest, rows = raw_dataset
    output = root / "data/processed/test-v1"
    prepare_dataset(root, manifest, output)
    return root, output, rows
