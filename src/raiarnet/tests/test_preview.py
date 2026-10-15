import sqlite3
from dataclasses import replace

import matplotlib
import numpy as np
import pytest
from conftest import FakeDetector

from chicken_yolo.capture import read_image, write_image
from chicken_yolo.config import InferenceConfig
from chicken_yolo.domain import Detection
from chicken_yolo.preview import preview_figure, preview_rows, run_preview

matplotlib.use("Agg")


def test_preview_limits_frames_preserves_pixels_and_viewing_does_not_rerun_model(
    tmp_path, monkeypatch
):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    source = tmp_path / "imagens"
    source.mkdir()
    for index in range(4):
        write_image(source / f"image-{index}.png", np.full((100, 100, 3), 80 + index, np.uint8))
    detector = FakeDetector([Detection((10, 10, 30, 30), 0.9, 0, "chicken")])
    monkeypatch.setattr("chicken_yolo.preview.prepare_model", lambda *args: None)
    monkeypatch.setattr("chicken_yolo.preview.YOLODetector", lambda *args: detector)
    run = run_preview(tmp_path, source, InferenceConfig(), max_frames=2)
    assert len(run.frames) == 2
    assert len(detector.calls) == 4
    assert not run.configs["standard"].slicing.enabled
    assert run.configs["sliced"].slicing.enabled
    assert np.array_equal(read_image(run.output / "frames/frame-00.png"), run.frames[0].image)
    assert np.array_equal(run.frames[0].image, read_image(source / "image-0.png"))
    with sqlite3.connect(tmp_path / "outputs/results.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 4
    figure = preview_figure(run, 1)
    assert len(figure.axes) == 3
    assert len(detector.calls) == 4
    import matplotlib.pyplot as plt

    plt.close(figure)
    assert len(preview_rows(run)) == 4
    assert (run.output / "comparison.csv").is_file()
    assert (run.output / "run.json").is_file()


def test_failed_preview_keeps_null_count_instead_of_reporting_empty_scene(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    source = tmp_path / "image.png"
    write_image(source, np.full((100, 100, 3), 120, np.uint8))
    monkeypatch.setattr("chicken_yolo.preview.prepare_model", lambda *args: None)
    monkeypatch.setattr(
        "chicken_yolo.preview.YOLODetector", lambda *args: FakeDetector(error="falha simulada")
    )
    run = run_preview(tmp_path, source, InferenceConfig(), modes=("standard",))
    row = preview_rows(run)[0]
    assert row["status"] == "falha_processamento"
    assert row["caixas_previstas"] is None
    assert row["confianca_maxima"] is None


@pytest.mark.parametrize("maximum", [0, True, 61])
def test_preview_rejects_invalid_frame_limit_before_loading_model(tmp_path, maximum):
    with pytest.raises(ValueError, match="quadros"):
        run_preview(tmp_path, "missing.mp4", InferenceConfig(), max_frames=maximum)


def test_preview_rejects_duplicate_modes_before_processing(tmp_path):
    with pytest.raises(ValueError, match="repetições"):
        run_preview(tmp_path, "missing.mp4", replace(InferenceConfig()), modes=("sliced", "sliced"))
