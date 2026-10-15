"""Diagnóstico das estratégias de contagem na validação (escolha da fusão).

Compara, por nível, detecção pura, densidade pura e fusões sensíveis à oclusão
com diferentes janelas e tolerâncias, sempre no limiar escolhido na validação.
"""

from __future__ import annotations

import argparse

import numpy as np

from evaluation.benchmark import RaiarNetRunner, collect, gt_counts
from evaluation.metrics import best_f1_threshold
from preprocessing.roi import LEVELS, LevelROI
from training.dataset import load_split


def fused_count(counter, boxes, scores, den, thr, window, tol, gain):
    s = counter.model.stride
    sel = scores >= thr
    b = boxes[sel]
    cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
    levels = [counter.roi.level_of(x, y) for x, y in zip(cx, cy, strict=True)]
    out = {}
    for k in LEVELS:
        dmap = den * counter.level_masks[k]
        H, W = dmap.shape
        det_map = np.zeros_like(dmap)
        for x, y, lv in zip(cx, cy, levels, strict=True):
            if lv == k:
                det_map[min(int(y // s), H - 1), min(int(x // s), W - 1)] += 1
        total = 0.0
        for y0 in range(0, H, window):
            for x0 in range(0, W, window):
                d = dmap[y0 : y0 + window, x0 : x0 + window].sum()
                n = det_map[y0 : y0 + window, x0 : x0 + window].sum()
                total += n + gain * max(0.0, d - n - tol)
        out[k] = total
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("weights")
    ap.add_argument("--split", default="val")
    args = ap.parse_args()
    roi = LevelROI.load()
    r = RaiarNetRunner(args.weights)
    val = collect(r, load_split("val"), roi)
    thr, _ = best_f1_threshold(val)
    data = collect(r, load_split(args.split), roi) if args.split != "val" else val
    gts = [gt_counts(p["gt"], roi) for p in data]
    print("limiar", thr)
    for p, g in zip(data, gts, strict=True):
        c = r.counts(p["pred"], p["scores"], p["den"], thr, roi)
        print(p["frame"], "gt", g, "det", c["det"], "den", {k: round(v, 1) for k, v in c["density"].items()})
    print("\nvariante -> MAE por nível e total")
    variants = [("det", None)] + [(f"fus w{w} tol{t} g{gn}", (w, t, gn)) for w in (4, 8, 16) for t in (0.0, 0.5, 1.0) for gn in (0.5, 1.0)]
    for name, v in variants:
        errs = {k: [] for k in (*LEVELS, "total")}
        for p, g in zip(data, gts, strict=True):
            if v is None:
                c = r.counts(p["pred"], p["scores"], p["den"], thr, roi)["det"]
            else:
                c = fused_count(r.counter, p["pred"], p["scores"], p["den"], thr, *v)
            for k in LEVELS:
                errs[k].append(c[k] - g[k])
            errs["total"].append(sum(c[k] for k in LEVELS) - sum(g.values()))
        print(f"{name:22s} " + " ".join(f"{k}={np.mean(np.abs(e)):.2f}({np.mean(e):+.1f})" for k, e in errs.items()))


if __name__ == "__main__":
    main()
