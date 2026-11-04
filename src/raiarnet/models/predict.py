"""Inferência ponta a ponta: imagem ou vídeo .mp4 -> aves identificadas e contagem por nível.

Saídas em --out:
- contagens.csv: por quadro, contagem bruta (detecção, densidade, fusão) e suavizada (Kalman) em N0, N1 e N2;
- resumo.json: médias por nível, parâmetros usados e regra de contagem;
- anotado.mp4 ou anotado.png: caixas, ROI dos níveis e painel com as contagens.

Exemplo:
    python -m models.predict --source "img/WhatsApp Video 2026-09-29 at 12.02.03.mp4" \
        --weights runs/raiarnet/final/best.pt --out outputs/c1-v3 --stride-frames 3
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import cv2
import numpy as np
import torch

from preprocessing.roi import LEVELS

from .counter import load_counter

COLORS = {"N0": (255, 200, 0), "N1": (200, 0, 200), "N2": (0, 170, 255)}


def draw(img, boxes, scores, thr, counter, counts, smooth=None):
    vis = counter.roi.draw(img, alpha=0.18)
    for b, s in zip(boxes, scores, strict=True):
        if s < thr:
            continue
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        lv = counter.roi.level_of(cx, cy)
        if lv is None:
            continue
        cv2.rectangle(vis, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), COLORS[lv], 1)
    panel_w = 250
    cv2.rectangle(vis, (vis.shape[1] - panel_w, 0), (vis.shape[1], 118), (25, 25, 25), -1)
    for j, k in enumerate(LEVELS):
        v = counts[k][counter.mode]
        txt = f"{k}: {v:5.1f}" + (f"  (kalman {smooth[k]:5.1f})" if smooth else "")
        cv2.putText(vis, txt, (vis.shape[1] - panel_w + 10, 30 + 30 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLORS[k], 1, cv2.LINE_AA)
    cv2.putText(vis, "1 contagem por nivel e instante", (vis.shape[1] - panel_w + 10, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1, cv2.LINE_AA)
    return vis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--thr", type=float, default=None, help="padrão: limiar escolhido na validação")
    ap.add_argument("--mode", default="fused", choices=["det", "density", "fused"])
    ap.add_argument("--stride-frames", type=int, default=1, help="processa 1 a cada N quadros")
    ap.add_argument("--smooth", default="kalman", choices=["kalman", "ema"])
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()

    torch.set_num_threads(max(1, int(os.environ.get("RAIARNET_NUM_THREADS", "6"))))
    ck = torch.load(args.weights, map_location="cpu", weights_only=False)
    thr = args.thr if args.thr is not None else float(ck.get("score_thr", 0.3))
    counter = load_counter(args.weights, score_thr=thr, mode=args.mode)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src = Path(args.source)
    rows = []

    if src.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        img = cv2.imread(str(src))
        boxes, scores, den = counter.infer(img)
        counts = counter.count(boxes, scores, den)
        cv2.imwrite(str(out / "anotado.png"), draw(img, boxes, scores, thr, counter, counts))
        rows.append({"quadro": 0, "tempo_s": 0.0, **{f"{k}_{m}": counts[k][m] for k in LEVELS for m in ("det", "density", "fused")}})
    else:
        cap = cv2.VideoCapture(str(src))
        fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        writer = None
        i = 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if i % args.stride_frames == 0:
                boxes, scores, den = counter.infer(img)
                counts = counter.count(boxes, scores, den)
                smooth = counter.smooth(counts, args.smooth)
                row = {"quadro": i, "tempo_s": round(i / fps, 3)}
                for k in LEVELS:
                    for m in ("det", "density", "fused"):
                        row[f"{k}_{m}"] = counts[k][m]
                    row[f"{k}_{args.smooth}"] = smooth[k]
                rows.append(row)
                if not args.no_video:
                    vis = draw(img, boxes, scores, thr, counter, counts, smooth)
                    if writer is None:
                        writer = cv2.VideoWriter(str(out / "anotado.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps / args.stride_frames, (vis.shape[1], vis.shape[0]))
                    writer.write(vis)
            i += 1
        if writer is not None:
            writer.release()

    with open(out / "contagens.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {
        "fonte": str(src),
        "pesos": args.weights,
        "limiar": thr,
        "modo_contagem": args.mode,
        "regra": "medição direta por nível; N1 não é inferido por diferença; câmeras não são somadas",
        "quadros_processados": len(rows),
        "media_por_nivel": {k: float(np.mean([r[f"{k}_{args.mode}"] for r in rows])) for k in LEVELS},
    }
    (out / "resumo.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
