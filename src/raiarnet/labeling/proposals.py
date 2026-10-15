"""Propostas automáticas de caixas para acelerar a anotação assistida.

As propostas vêm de um detector de vocabulário aberto (OWLv2) aplicado em blocos
ampliados. Elas servem apenas como ponto de partida da revisão visual: nenhuma
caixa entra no conjunto de referência sem ser revisada.
"""

from __future__ import annotations

import numpy as np
import torch
from torchvision.ops import nms

_MODEL = None


def _load(name: str = "google/owlv2-base-patch16-ensemble"):
    global _MODEL
    if _MODEL is None:
        from transformers import Owlv2ForObjectDetection, Owlv2Processor

        _MODEL = (Owlv2Processor.from_pretrained(name), Owlv2ForObjectDetection.from_pretrained(name).eval())
    return _MODEL


def owl_proposals(
    img_bgr: np.ndarray,
    roi_mask: np.ndarray | None = None,
    tile: int = 240,
    stride: int = 180,
    texts: tuple[str, ...] = ("a photo of a chicken", "a photo of a hen", "a bird"),
    threshold: float = 0.08,
    max_side_ratio: float = 0.9,
) -> np.ndarray:
    """Retorna array (N, 5) com x1, y1, x2, y2, score no sistema do quadro original."""
    proc, model = _load()
    h, w = img_bgr.shape[:2]
    ys = sorted(set(list(range(0, max(h - tile, 0) + 1, stride)) + [max(h - tile, 0)]))
    xs = sorted(set(list(range(0, max(w - tile, 0) + 1, stride)) + [max(w - tile, 0)]))
    boxes, scores = [], []
    for y0 in ys:
        for x0 in xs:
            if roi_mask is not None and roi_mask[y0 : y0 + tile, x0 : x0 + tile].mean() < 5:
                continue
            crop = img_bgr[y0 : y0 + tile, x0 : x0 + tile][:, :, ::-1].copy()
            inp = proc(text=[list(texts)], images=crop, return_tensors="pt")
            with torch.no_grad():
                out = model(**inp)
            res = proc.post_process_grounded_object_detection(
                out, threshold=threshold, target_sizes=torch.tensor([[tile, tile]])
            )[0]
            for b, s in zip(res["boxes"], res["scores"], strict=True):
                b = b.clamp(0, tile)
                bw, bh = float(b[2] - b[0]), float(b[3] - b[1])
                if bw > max_side_ratio * tile or bh > max_side_ratio * tile or bw < 3 or bh < 3:
                    continue
                # Descarta caixas cortadas pela borda interna do bloco.
                edge = 2
                if (b[0] < edge and x0 > 0) or (b[1] < edge and y0 > 0):
                    continue
                if (b[2] > tile - edge and x0 + tile < w) or (b[3] > tile - edge and y0 + tile < h):
                    continue
                boxes.append([b[0] + x0, b[1] + y0, b[2] + x0, b[3] + y0])
                scores.append(float(s))
    if not boxes:
        return np.zeros((0, 5), np.float32)
    bt = torch.tensor(boxes, dtype=torch.float32)
    st = torch.tensor(scores)
    keep = nms(bt, st, 0.45)
    return np.c_[bt[keep].numpy(), st[keep].numpy()].astype(np.float32)
