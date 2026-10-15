"""Métricas de detecção (P, R, F1, mAP) e de contagem (MAE, RMSE, MAPE)."""

from __future__ import annotations

import numpy as np

IOU_THRESHOLDS = np.round(np.arange(0.5, 0.96, 0.05), 2)


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), np.float32)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(rb - lt, 0, None).prod(2)
    area_a = (a[:, 2:] - a[:, :2]).prod(1)
    area_b = (b[:, 2:] - b[:, :2]).prod(1)
    return inter / np.maximum(area_a[:, None] + area_b[None] - inter, 1e-7)


def match(pred: np.ndarray, scores: np.ndarray, gt: np.ndarray, thr: float) -> np.ndarray:
    """Casamento guloso por escore (protocolo COCO). Retorna flag TP por predição ordenada."""
    order = np.argsort(-scores)
    ious = iou_matrix(pred[order], gt)
    used = np.zeros(len(gt), bool)
    tp = np.zeros(len(order), bool)
    for i in range(len(order)):
        if len(gt) == 0:
            break
        cand = np.where(~used, ious[i], -1)
        j = int(np.argmax(cand))
        if cand[j] >= thr:
            used[j] = True
            tp[i] = True
    return tp


def average_precision(tps: np.ndarray, scores: np.ndarray, n_gt: int) -> float:
    """AP com interpolação de 101 pontos (COCO)."""
    if n_gt == 0:
        return float("nan")
    order = np.argsort(-scores)
    tps = tps[order]
    ctp = np.cumsum(tps)
    cfp = np.cumsum(~tps)
    rec = ctp / n_gt
    prec = ctp / np.maximum(ctp + cfp, 1e-9)
    prec = np.maximum.accumulate(prec[::-1])[::-1] if len(prec) else prec
    ap = 0.0
    for r in np.linspace(0, 1, 101):
        idx = np.searchsorted(rec, r, side="left")
        ap += prec[idx] if idx < len(prec) else 0.0
    return ap / 101


def detection_metrics(frames: list[dict], score_thr: float) -> dict[str, float]:
    """frames: [{'pred': Nx4, 'scores': N, 'gt': Mx4}]. P/R/F1 em IoU 0,5 no limiar dado."""
    out = {}
    aps = []
    for thr in IOU_THRESHOLDS:
        all_tp, all_sc, n_gt = [], [], 0
        for f in frames:
            tp = match(f["pred"], f["scores"], f["gt"], thr)
            all_tp.append(tp)
            all_sc.append(np.sort(f["scores"])[::-1])
            n_gt += len(f["gt"])
        ap = average_precision(np.concatenate(all_tp), np.concatenate(all_sc), n_gt)
        aps.append(ap)
        if thr == 0.5:
            out["mAP50"] = ap
    out["mAP50_95"] = float(np.mean(aps))
    tp = fp = fn = 0
    for f in frames:
        sel = f["scores"] >= score_thr
        t = match(f["pred"][sel], f["scores"][sel], f["gt"], 0.5)
        tp += int(t.sum())
        fp += int((~t).sum())
        fn += len(f["gt"]) - int(t.sum())
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    out.update(precision=p, recall=r, f1=2 * p * r / max(p + r, 1e-9), tp=tp, fp=fp, fn=fn)
    return out


def best_f1_threshold(frames: list[dict], grid: np.ndarray | None = None) -> tuple[float, float]:
    grid = grid if grid is not None else np.round(np.arange(0.05, 0.95, 0.025), 3)
    best = (0.0, 0.25)
    for thr in grid:
        f1 = detection_metrics_fast(frames, thr)
        if f1 > best[0]:
            best = (f1, float(thr))
    return best[1], best[0]


def detection_metrics_fast(frames: list[dict], score_thr: float) -> float:
    tp = fp = fn = 0
    for f in frames:
        sel = f["scores"] >= score_thr
        t = match(f["pred"][sel], f["scores"][sel], f["gt"], 0.5)
        tp += int(t.sum())
        fp += int((~t).sum())
        fn += len(f["gt"]) - int(t.sum())
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    return 2 * p * r / max(p + r, 1e-9)


def count_metrics(pred: list[float], gt: list[float]) -> dict[str, float]:
    p = np.asarray(pred, np.float64)
    g = np.asarray(gt, np.float64)
    err = p - g
    nz = g > 0
    return {
        "MAE": float(np.abs(err).mean()),
        "RMSE": float(np.sqrt((err**2).mean())),
        "MAPE": float((np.abs(err[nz]) / g[nz]).mean() * 100) if nz.any() else float("nan"),
        "vies": float(err.mean()),
    }
