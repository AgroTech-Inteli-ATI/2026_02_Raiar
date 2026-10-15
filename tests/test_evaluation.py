import json

import pytest
from conftest import FakeDetector

from raiar_vision.config import InferenceConfig
from raiar_vision.domain import Detection
from raiar_vision.evaluation import average_precision, count_metrics, evaluate_dataset, matching


def test_duplicate_detections_cannot_match_the_same_bird_twice():
    boxes = [Detection((0, 0, 10, 10), 0.9, 14, "bird"), Detection((0, 0, 10, 10), 0.8, 14, "bird")]
    assert matching(boxes, [(0, 0, 10, 10)], 0.5) == [(0.9, 1), (0.8, 0)]
    assert average_precision([], 1) == 0
    assert average_precision([], 0) is None


def test_false_positive_before_true_positive_reduces_ap():
    assert average_precision([(0.9, 0), (0.8, 1)], 1) == pytest.approx(0.5)


def test_count_error_includes_empty_predictions_and_zero_references():
    metrics = count_metrics([0, 2], [3, 0])
    assert metrics["mae_aves"] == 2.5
    assert metrics["erro_percentual_agregado"] == pytest.approx(100 * 5 / 3)
    assert count_metrics([2], [0])["erro_percentual_agregado"] is None


def test_missed_birds_penalize_counts_even_if_distribution_cannot_be_calculated(
    prepared_dataset, tmp_path, zones
):
    _, dataset, _ = prepared_dataset
    detector = FakeDetector()
    report = evaluate_dataset(
        InferenceConfig(), detector, dataset / "dataset.yaml", tmp_path / "evaluation", zones
    )
    assert report["count_total"]["mae_aves"] == 1
    assert report["count_by_level"]["mae_aves"] == 0.5
    assert report["detection"]["recall_at_operating_threshold"] == 0
    assert report["detection"]["ap50"] == 0
    assert report["distribution_zero_total_exclusions"] == 2
    assert report["distribution_mae_pp"] == {"superior": None, "inferior": None}


def test_ap_uses_low_confidence_predictions_without_changing_operating_counts(
    prepared_dataset, tmp_path
):
    _, dataset, _ = prepared_dataset
    detector = FakeDetector([Detection((10, 10, 30, 30), 0.01, 14, "bird")])
    report = evaluate_dataset(
        InferenceConfig(), detector, dataset / "dataset.yaml", tmp_path / "evaluation"
    )
    assert report["detection"]["ap50"] == 1
    assert report["count_total"]["mae_aves"] == 1
    assert detector.calls == [0.001, 0.001]


def test_failures_are_reported_and_do_not_retry_model(prepared_dataset, tmp_path):
    _, dataset, _ = prepared_dataset
    detector = FakeDetector(error="failure")
    report = evaluate_dataset(
        InferenceConfig(), detector, dataset / "dataset.yaml", tmp_path / "evaluation"
    )
    assert report["coverage"]["falha_processamento"] == 2
    assert report["coverage"]["avaliaveis_percentual"] == 0
    assert report["detection"]["ap50"] is None
    assert len(detector.calls) == 2
    results = [
        json.loads(line) for line in (tmp_path / "evaluation/frames.jsonl").read_text().splitlines()
    ]
    assert all(row["quantidade_aves_visiveis"] is None for row in results)
