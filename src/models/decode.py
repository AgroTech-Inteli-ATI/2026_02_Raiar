"""Decodificação das saídas da RaiarNet em caixas, escores e mapa de densidade."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

from .losses import SIZE_NORM


def soft_nms(boxes: np.ndarray, scores: np.ndarray, sigma: float = 0.5, thr: float = 0.001):
    """Soft-NMS gaussiano (Bodla et al., 2017): reduz o escore de sobreposições em vez de apagar."""
    boxes = boxes.copy()
    scores = scores.copy()
    keep_b, keep_s = [], []
    while len(scores):
        i = int(np.argmax(scores))
        b, s = boxes[i], scores[i]
        keep_b.append(b)
        keep_s.append(s)
        boxes = np.delete(boxes, i, 0)
        scores = np.delete(scores, i)
        if not len(scores):
            break
        lt = np.maximum(boxes[:, :2], b[:2])
        rb = np.minimum(boxes[:, 2:], b[2:])
        inter = np.clip(rb - lt, 0, None).prod(1)
        union = (boxes[:, 2:] - boxes[:, :2]).prod(1) + (b[2:] - b[:2]).prod() - inter
        iou = inter / np.maximum(union, 1e-7)
        scores = scores * np.exp(-(iou**2) / sigma)
        sel = scores > thr
        boxes, scores = boxes[sel], scores[sel]
    return np.array(keep_b).reshape(-1, 4), np.array(keep_s)


@torch.no_grad()
def forward_tta(model, x: torch.Tensor, flip: bool = True) -> dict:
    """Inferência com espelhamento horizontal (flip test do CenterNet).

    Média dos logits do heatmap, dos tamanhos e da densidade das duas passadas;
    o deslocamento subcélula vem da passada original.
    """
    out = model(x)
    if not flip:
        return out
    o2 = model(torch.flip(x, dims=[3]))
    merged = dict(out)
    merged["hm"] = (out["hm"] + torch.flip(o2["hm"], dims=[3])) / 2
    merged["wh"] = (out["wh"] + torch.flip(o2["wh"], dims=[3])) / 2
    if "den" in out:
        merged["den"] = (out["den"] + torch.flip(o2["den"], dims=[3])) / 2
    return merged


@torch.no_grad()
def decode(out: dict, stride: int, score_thr: float = 0.05, max_det: int = 1000, use_soft_nms: bool = False):
    """Retorna, por imagem, (caixas Nx4, escores N, mapa de densidade HxW ou None)."""
    hm = torch.sigmoid(out["hm"])
    peaks = (hm == F.max_pool2d(hm, 3, 1, 1)) & (hm >= score_thr)
    B, _, H, W = hm.shape
    results = []
    for b in range(B):
        ys, xs = torch.nonzero(peaks[b, 0], as_tuple=True)
        sc = hm[b, 0, ys, xs]
        if len(sc) > max_det:
            top = torch.topk(sc, max_det).indices
            ys, xs, sc = ys[top], xs[top], sc[top]
        off = out["off"][b, :, ys, xs]
        wh = out["wh"][b, :, ys, xs].clamp(-4, 4).exp() * SIZE_NORM
        cx = (xs.float() + off[0]) * stride
        cy = (ys.float() + off[1]) * stride
        boxes = torch.stack([cx - wh[0] / 2, cy - wh[1] / 2, cx + wh[0] / 2, cy + wh[1] / 2], 1).cpu().numpy()
        scores = sc.cpu().numpy()
        if use_soft_nms and len(scores):
            boxes, scores = soft_nms(boxes, scores)
        den = out["den"][b, 0].cpu().numpy() if "den" in out else None
        results.append((boxes, scores, den))
    return results
