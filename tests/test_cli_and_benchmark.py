import json
import sqlite3

import numpy as np
import pytest
from conftest import FakeDetector

from raiar_vision.benchmark import benchmark
from raiar_vision.capture import write_image
from raiar_vision.cli import main
from raiar_vision.config import InferenceConfig
from raiar_vision.pipeline import Pipeline


def test_cli_end_to_end_creates_history_and_exports(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (root / "config.yaml").write_text("model: coco\nsave_annotated: true\n", encoding="utf-8")
    source = root / "input.png"
    write_image(source, np.full((100, 100, 3), 120, dtype=np.uint8))
    monkeypatch.setattr("raiar_vision.cli.YOLODetector", lambda *args: FakeDetector())
    code = main(
        [
            "--root",
            str(root),
            "predict",
            "--config",
            "config.yaml",
            "--source",
            str(source),
            "--output",
            "results",
        ]
    )
    assert code == 0
    result = json.loads((root / "results/results.jsonl").read_text(encoding="utf-8"))
    assert result["quantidade_aves_visiveis"] == 0
    assert (root / "outputs/results.sqlite3").is_file()
    assert list((root / "results/annotated").glob("*.jpg"))
    assert (
        main(
            [
                "--root",
                str(root),
                "predict",
                "--config",
                "config.yaml",
                "--source",
                str(source),
                "--output",
                "results",
            ]
        )
        == 1
    )


def test_benchmark_collects_resource_samples_and_reports_budget(tmp_path):
    source = tmp_path / "input.png"
    write_image(source, np.full((100, 100, 3), 120, dtype=np.uint8))
    pipeline = Pipeline(InferenceConfig(), FakeDetector())
    report = benchmark(pipeline, source, tmp_path / "benchmark", 1.1, 0.2)
    assert report["statuses"]["valido"] >= 1
    assert report["resource_samples"]
    assert report["inference_within_80_percent_interval"] == 1
    assert 0 < report["min_available_memory_percent"] <= 100
    assert (tmp_path / "benchmark/report.json").is_file()


@pytest.mark.parametrize("duration,interval", [(0, 1), (1, 0), (float("nan"), 1)])
def test_benchmark_rejects_invalid_schedule_before_processing(tmp_path, duration, interval):
    with pytest.raises(ValueError):
        benchmark(
            Pipeline(InferenceConfig(), FakeDetector()),
            tmp_path / "unused.png",
            tmp_path / "benchmark",
            duration,
            interval,
        )


def test_video_capture_failure_is_recorded_in_local_history(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (root / "config.yaml").write_text("model: coco\n", encoding="utf-8")
    (root / "invalid.avi").write_bytes(b"broken-video")
    monkeypatch.setattr("raiar_vision.cli.YOLODetector", lambda *args: FakeDetector())
    assert (
        main(
            [
                "--root",
                str(root),
                "predict",
                "--config",
                "config.yaml",
                "--source",
                "invalid.avi",
                "--output",
                "failed-run",
            ]
        )
        == 1
    )
    with sqlite3.connect(root / "outputs/results.sqlite3") as connection:
        assert connection.execute("SELECT type FROM events").fetchone()[0] == "falha_captura"
