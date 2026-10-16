"""Resultados por quadro sem extrapolar aves ocultas ou atribuições ambíguas."""

import time
import uuid
from dataclasses import asdict

from .config import InferenceConfig, fingerprint
from .domain import Frame, InferenceOutput, utc_now
from .quality import assess_quality
from .zones import ZoneConfig


class Pipeline:
    def __init__(self, config: InferenceConfig, detector, zones: ZoneConfig | None = None):
        self.config = config
        self.detector = detector
        self.zones = zones

    def process(
        self,
        frame: Frame,
        inference: InferenceOutput | None = None,
        inference_error: str | None = None,
    ) -> dict:
        start = time.perf_counter()
        cfg = self.config
        levels = [zone.id for zone in self.zones.zones] if self.zones else []
        result = {
            "analise_id": str(uuid.uuid4()),
            **frame.metadata,
            "modelo_versao": self.detector.metadata["sha256"],
            "modelo": self.detector.metadata,
            "zonas_versao": self.zones.version if self.zones else None,
            "zonas_sha256": self.zones.sha256 if self.zones else None,
            "regra_atribuicao_versao": self.zones.rule_version if self.zones else None,
            "config_sha256": fingerprint(cfg.snapshot()),
            "config": cfg.snapshot(),
            "limiar_confianca": cfg.confidence,
            "status": "valido",
            "motivo_status": None,
            "detections": [],
            "quantidade_aves_visiveis": None,
            "contagens_por_nivel": dict.fromkeys(levels),
            "percentuais_por_nivel": dict.fromkeys(levels),
            "total_atribuido_quadro": None,
            "quantidade_sem_nivel": None,
            "inference_ms": None,
            "escopo_contagem": "regiao_configurada" if cfg.roi else "quadro_completo",
            "inference_details": {},
        }
        if frame.image is not None:
            result["altura_px"], result["largura_px"] = frame.image.shape[:2]
        reason, metrics = assess_quality(frame, cfg.quality)
        result["quality_metrics"] = metrics
        if reason is None and self.zones:
            height, width = frame.image.shape[:2]
            reason = self.zones.check_frame(width, height, frame.metadata.get("camera_id"))
        if reason:
            result.update(status="imagem_inadequada", motivo_status=reason)
        else:
            try:
                if inference_error:
                    raise RuntimeError(inference_error)
                output = inference if inference is not None else self.detector.predict(frame.image)
                result["inference_ms"] = output.duration_ms
                result["inference_details"] = output.details
                counts = dict.fromkeys(levels, 0)
                unassigned = 0
                height, width = frame.image.shape[:2]
                for detection in output.detections:
                    if detection.confidence < cfg.confidence:
                        continue
                    level, why = (
                        self.zones.assign(detection.bbox_px, width, height)
                        if self.zones
                        else (None, "zonas_nao_configuradas")
                    )
                    if level is None:
                        unassigned += 1
                    else:
                        counts[level] += 1
                    result["detections"].append(
                        {**asdict(detection), "nivel_id": level, "motivo_indeterminado": why}
                    )
                total = sum(counts.values())
                result.update(
                    quantidade_aves_visiveis=len(result["detections"]),
                    contagens_por_nivel=counts,
                    total_atribuido_quadro=total,
                    quantidade_sem_nivel=unassigned,
                    percentuais_por_nivel={
                        key: 100 * value / total if total else None for key, value in counts.items()
                    },
                )
            except Exception as exc:
                result.update(status="falha_processamento", motivo_status=str(exc), detections=[])
        result["processado_em"] = utc_now()
        result["processing_ms"] = (time.perf_counter() - start) * 1000
        if inference is not None:
            result["processing_ms"] += inference.duration_ms
        return result


def annotate(image, result: dict, zones: ZoneConfig | None):
    import cv2
    import numpy as np

    annotated = image.copy()
    height, width = image.shape[:2]
    roi = result.get("config", {}).get("roi")
    if roi:
        x1, y1, x2, y2 = [round(roi[i] * (width if i % 2 == 0 else height)) for i in range(4)]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 160, 0), 2)
        cv2.putText(
            annotated,
            "Regiao analisada",
            (x1, max(15, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 160, 0),
            1,
        )
    if zones:
        for zone in zones.zones:
            points = np.array(
                [(round(x * width), round(y * height)) for x, y in zone.polygon], dtype=np.int32
            )
            cv2.polylines(annotated, [points], True, (255, 160, 0), 2)
            cv2.putText(
                annotated,
                zone.id,
                tuple(points[0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 160, 0),
                1,
            )
    for detection in result["detections"]:
        x1, y1, x2, y2 = [round(v) for v in detection["bbox_px"]]
        color = (0, 200, 0) if detection["nivel_id"] else (0, 160, 255)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        text = f"{detection['class_name']} {detection['confidence']:.2f}"
        cv2.putText(annotated, text, (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.putText(
        annotated,
        f"{result['status']} | aves: {result['quantidade_aves_visiveis']}",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 100, 0),
        2,
    )
    return annotated
