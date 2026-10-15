import json

import numpy as np
import pytest
from conftest import FakeDetector

from chicken_yolo.config import InferenceConfig
from chicken_yolo.domain import Detection, Frame
from chicken_yolo.pipeline import Pipeline
from chicken_yolo.storage import ResultStore


def test_levels_and_indeterminate_have_correct_denominator(frame, zones):
    detector = FakeDetector(
        [
            Detection((10, 10, 30, 30), 0.9, 0, "chicken"),
            Detection((10, 60, 30, 80), 0.9, 0, "chicken"),
            Detection((10, 30, 30, 50), 0.9, 0, "chicken"),
        ]
    )
    result = Pipeline(InferenceConfig(), detector, zones).process(frame)
    assert result["status"] == "valido"
    assert result["contagens_por_nivel"] == {"superior": 1, "inferior": 1}
    assert result["percentuais_por_nivel"] == {"superior": 50, "inferior": 50}
    assert result["quantidade_aves_visiveis"] == 3
    assert result["quantidade_sem_nivel"] == 1
    assert result["detections"][2]["motivo_indeterminado"] == "fronteira"


def test_empty_valid_frame_has_zero_counts_and_null_percentages(frame, zones):
    result = Pipeline(InferenceConfig(), FakeDetector(), zones).process(frame)
    assert result["contagens_por_nivel"] == {"superior": 0, "inferior": 0}
    assert result["percentuais_por_nivel"] == {"superior": None, "inferior": None}
    assert result["status"] == "valido"


def test_failed_inference_is_not_a_zero_count(frame, zones):
    result = Pipeline(InferenceConfig(), FakeDetector(error="CPU failure"), zones).process(frame)
    assert result["status"] == "falha_processamento"
    assert result["quantidade_aves_visiveis"] is None
    assert result["contagens_por_nivel"] == {"superior": None, "inferior": None}
    assert result["detections"] == []


@pytest.mark.parametrize("kind", ["dark", "camera", "aspect", "decode", "manual"])
def test_inadequate_frames_never_call_detector(frame, zones, kind):
    if kind == "dark":
        frame.image[:] = 0
    elif kind == "camera":
        frame.metadata["camera_id"] = "different-camera"
    elif kind == "aspect":
        frame.image = np.full((100, 200, 3), 120, dtype=np.uint8)
    elif kind == "decode":
        frame = Frame(None, frame.metadata, "decode error")
    else:
        frame.manual_quality = "nao_avaliavel"
    detector = FakeDetector()
    result = Pipeline(InferenceConfig(), detector, zones).process(frame)
    assert result["status"] == "imagem_inadequada"
    assert result["quantidade_aves_visiveis"] is None
    assert detector.calls == []


def test_no_zones_preserves_raw_class_and_unknown_capture_time(frame, detection):
    result = Pipeline(InferenceConfig(), FakeDetector([detection])).process(frame)
    assert result["detections"][0]["class_name"] == "bird"
    assert result["quantidade_sem_nivel"] == 1
    assert result["contagens_por_nivel"] == {}
    assert result["capturado_em"] is None


def test_storage_idempotence_and_reprocessing_history(tmp_path, frame, zones):
    pipeline = Pipeline(InferenceConfig(), FakeDetector(), zones)
    first, second = pipeline.process(frame), pipeline.process(frame)
    assert first["analise_id"] != second["analise_id"]
    with ResultStore(tmp_path / "results.sqlite3", tmp_path / "export") as store:
        assert store.save(first)
        assert not store.save(first)
        assert store.save(second)
        assert store.connection.execute("SELECT count(*) FROM analyses").fetchone()[0] == 2
    exported = [
        json.loads(line) for line in (tmp_path / "export/results.jsonl").read_text().splitlines()
    ]
    assert len(exported) == 2
    assert len((tmp_path / "export/counts.csv").read_text().splitlines()) == 5
