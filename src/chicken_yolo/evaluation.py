"""Comparação de uma classe, com AP por caixas e referências manuais por nível."""

import json
import statistics
import uuid
from bisect import bisect_left
from pathlib import Path

from .capture import read_image
from .config import InferenceConfig
from .dataset import read_labels, validate_dataset
from .domain import Detection, Frame, utc_now
from .pipeline import Pipeline
from .quality import assess_quality
from .zones import ZoneConfig


def box_iou(a, b) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def matching(detections: list[Detection], references: list, threshold: float) -> list[tuple]:
    unmatched = set(range(len(references)))
    matches = []
    for detection in sorted(detections, key=lambda d: d.confidence, reverse=True):
        best = max(
            sorted(unmatched), key=lambda i: box_iou(detection.bbox_px, references[i]), default=None
        )
        hit = best is not None and box_iou(detection.bbox_px, references[best]) >= threshold
        if hit:
            unmatched.remove(best)
        matches.append((detection.confidence, int(hit)))
    return matches


def average_precision(matches: list[tuple], reference_count: int) -> float | None:
    if reference_count == 0:
        return None
    true_positives = 0
    recalls, precisions = [], []
    for rank, (_, hit) in enumerate(sorted(matches, key=lambda x: x[0], reverse=True), 1):
        true_positives += hit
        recalls.append(true_positives / reference_count)
        precisions.append(true_positives / rank)
    envelope = 0.0
    for index in range(len(precisions) - 1, -1, -1):
        envelope = max(envelope, precisions[index])
        precisions[index] = envelope
    samples = []
    for level in range(101):
        index = bisect_left(recalls, level / 100)
        samples.append(precisions[index] if index < len(precisions) else 0.0)
    return sum(samples) / 101


def count_metrics(predictions: list[int], references: list[int]) -> dict:
    if len(predictions) != len(references):
        raise ValueError("Contagens previstas e manuais devem ter o mesmo comprimento.")
    error = sum(abs(pred - ref) for pred, ref in zip(predictions, references, strict=True))
    return {
        "mae_aves": error / len(references) if references else None,
        "erro_percentual_agregado": 100 * error / sum(references) if sum(references) else None,
        "pares_avaliados": len(references),
        "total_referencia": sum(references),
    }


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[94]


def evaluate_dataset(
    config: InferenceConfig,
    detector,
    dataset_yaml: Path,
    output: Path,
    zones: ZoneConfig | None = None,
    split: str = "val",
) -> dict:
    if config.roi is not None:
        raise ValueError("Para avaliar uma ROI, use imagens e referências do recorte com roi=null.")
    dataset_root, records, metadata = validate_dataset(dataset_yaml)
    if split not in {"val", "test"}:
        raise ValueError("Avaliação usa somente val ou test.")
    selected = [row for row in records if row["split"] == split]
    levels = [zone.id for zone in zones.zones] if zones else []
    for row in selected:
        if zones and (
            set(row.get("contagens_por_nivel", {})) != set(levels)
            or row.get("zonas_versao") != zones.version
        ):
            raise ValueError(
                "Avaliação por nível exige contagens manuais revisadas e zonas_versao."
            )
    output.mkdir(parents=True, exist_ok=False)
    pipeline = Pipeline(config, detector, zones)
    thresholds = [0.5 + i * 0.05 for i in range(10)]
    ap_matches = {threshold: [] for threshold in thresholds}
    operating_matches = []
    reference_count = 0
    totals_pred, totals_ref, levels_pred, levels_ref = [], [], [], []
    distribution_errors = {level: [] for level in levels}
    zero_total_exclusions = 0
    statuses = {"valido": 0, "imagem_inadequada": 0, "falha_processamento": 0}
    timings = []
    with (output / "frames.jsonl").open("w", encoding="utf-8") as handle:
        for row in selected:
            image = read_image(dataset_root / row["imagem"])
            frame = Frame(
                image,
                {
                    key: row.get(key)
                    for key in ("quadro_id", "camera_id", "lote_id", "capturado_em")
                },
                manual_quality=row["qualidade"],
                extra=row,
            )
            raw = None
            reason, _ = assess_quality(frame, config.quality)
            if reason is None and zones:
                reason = zones.check_frame(image.shape[1], image.shape[0], row.get("camera_id"))
            if reason is None:
                try:
                    raw = detector.predict(image, confidence=0.001)
                except Exception as exc:
                    # Manter falha separada de imagem vazia e de rejeição técnica.
                    result = pipeline.process(frame, inference_error=str(exc))
                else:
                    result = pipeline.process(frame, raw)
            else:
                result = pipeline.process(frame)
            statuses[result["status"]] += 1
            handle.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
            if result["status"] != "valido":
                continue
            height, width = image.shape[:2]
            references = [
                (
                    max(0, (x - w / 2) * width),
                    max(0, (y - h / 2) * height),
                    min(width, (x + w / 2) * width),
                    min(height, (y + h / 2) * height),
                )
                for x, y, w, h in read_labels(dataset_root / row["rotulo"])
            ]
            reference_count += len(references)
            for threshold in thresholds:
                ap_matches[threshold].extend(matching(raw.detections, references, threshold))
            operating = [d for d in raw.detections if d.confidence >= config.confidence]
            operating_matches.extend(matching(operating, references, 0.5))
            totals_pred.append(result["quantidade_aves_visiveis"])
            totals_ref.append(len(references))
            timings.append(result["inference_ms"])
            if zones:
                ref_counts = row["contagens_por_nivel"]
                for level in levels:
                    levels_pred.append(result["contagens_por_nivel"][level])
                    levels_ref.append(ref_counts[level])
                ref_total = sum(ref_counts.values())
                if ref_total and result["total_atribuido_quadro"]:
                    for level in levels:
                        distribution_errors[level].append(
                            abs(
                                result["percentuais_por_nivel"][level]
                                - 100 * ref_counts[level] / ref_total
                            )
                        )
                else:
                    zero_total_exclusions += 1
    ap_values = [average_precision(ap_matches[t], reference_count) for t in thresholds]
    tp = sum(hit for _, hit in operating_matches)
    precision = tp / len(operating_matches) if operating_matches else 0.0
    recall = tp / reference_count if reference_count else None
    report = {
        "evaluation_id": str(uuid.uuid4()),
        "evaluated_at": utc_now(),
        "split": split,
        "dataset": metadata,
        "model": detector.metadata,
        "config": config.snapshot(),
        "zonas_sha256": zones.sha256 if zones else None,
        "coverage": {
            **statuses,
            "previstos": len(selected),
            "avaliaveis_percentual": 100 * statuses["valido"] / len(selected),
        },
        "detection": {
            "ap50": ap_values[0],
            "map50_95": statistics.mean(ap_values) if reference_count else None,
            "precision_at_operating_threshold": precision,
            "recall_at_operating_threshold": recall,
            "false_positives": len(operating_matches) - tp,
            "false_negatives": reference_count - tp,
            "ap_confidence_floor": 0.001,
            "method": "Uma classe; correspondência por IoU e AP interpolada em 101 pontos.",
        },
        "count_total": count_metrics(totals_pred, totals_ref),
        "count_by_level": count_metrics(levels_pred, levels_ref) if zones else None,
        "distribution_mae_pp": {
            level: statistics.mean(errors) if errors else None
            for level, errors in distribution_errors.items()
        },
        "distribution_zero_total_exclusions": zero_total_exclusions,
        "inference_p95_ms": _p95(timings),
        "limitations": [
            "AP e erros calculados apenas nos quadros válidos; consultar cobertura.",
            "Este relatório não comprova generalização para outros lotes.",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report
