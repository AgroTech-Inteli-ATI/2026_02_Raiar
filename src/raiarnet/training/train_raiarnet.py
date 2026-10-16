"""Treino da RaiarNet do zero (sem pesos pré-treinados) em CPU.

Exemplo:
    python -m training.train_raiarnet --name base --pipeline original --iters 3000
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from evaluation.metrics import best_f1_threshold, count_metrics, detection_metrics
from models.counter import LevelCounter
from models.decode import decode
from models.losses import build_targets, raiarnet_loss
from models.raiarnet import RaiarNet, RaiarNetConfig, count_parameters
from preprocessing.roi import LEVELS, LevelROI
from training.dataset import FrameCrops, collate, eval_boxes, load_frame, load_split, to_tensor, train_frames

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "raiarnet"


def filter_roi(boxes: np.ndarray, scores: np.ndarray, roi: LevelROI):
    if not len(boxes):
        return boxes, scores
    keep = np.array([roi.level_of((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) is not None for b in boxes], bool)
    return boxes[keep], scores[keep]


@torch.no_grad()
def predict_frames(model: RaiarNet, frames: list[str], pipeline: str, roi: LevelROI):
    model.eval()
    res = []
    for f in frames:
        img = load_frame(f, pipeline, roi)
        out = model(to_tensor(img))
        boxes, scores, den = decode(out, model.stride, score_thr=0.05)[0]
        boxes, scores = filter_roi(boxes, scores, roi)
        res.append({"frame": f, "pred": boxes, "scores": scores, "den": den, "gt": eval_boxes(f, roi)})
    return res


def evaluate(model, frames, pipeline, roi, score_thr=None, counter_mode="fused", window=8):
    preds = predict_frames(model, frames, pipeline, roi)
    if score_thr is None:
        score_thr, _ = best_f1_threshold(preds)
    det = detection_metrics(preds, score_thr)
    counter = LevelCounter(model, roi, pipeline, score_thr=score_thr, window=window)
    per_level = {k: ([], []) for k in LEVELS}
    per_mode = {m: {k: [] for k in LEVELS} for m in ("det", "density", "fused")}
    for p in preds:
        c = counter.count(p["pred"], p["scores"], p["den"])
        gt = roi.count(np.c_[(p["gt"][:, 0] + p["gt"][:, 2]) / 2, (p["gt"][:, 1] + p["gt"][:, 3]) / 2])
        for k in LEVELS:
            per_level[k][1].append(gt[k])
            for m in per_mode:
                v = c[k][m]
                per_mode[m][k].append(float(v) if v is not None else np.nan)
    counts = {}
    for m in per_mode:
        counts[m] = {k: count_metrics(per_mode[m][k], per_level[k][1]) for k in LEVELS}
        tot_p = np.sum([per_mode[m][k] for k in LEVELS], 0)
        tot_g = np.sum([per_level[k][1] for k in LEVELS], 0)
        counts[m]["total"] = count_metrics(tot_p, tot_g)
    det["score_thr"] = score_thr
    return {"det": det, "count": counts, "counter_mode": counter_mode}, preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--pipeline", default="original")
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--crop", type=int, default=320)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--wd", type=float, default=5e-4)
    ap.add_argument("--eval-every", type=int, default=250)
    ap.add_argument("--width", type=float, default=1.0)
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--attention", default="coord")
    ap.add_argument("--downsample", default="spd")
    ap.add_argument("--neck-repeats", type=int, default=2)
    ap.add_argument("--no-density", action="store_true")
    ap.add_argument("--grid-aug", type=float, default=0.3)
    ap.add_argument("--w-den", type=float, default=1.0)
    ap.add_argument("--w-box", type=float, default=1.0)
    ap.add_argument("--w-wh", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--init", default="", help="checkpoint próprio para continuar o treino")
    ap.add_argument("--densified", action="store_true", help="inclui quadros intermediários com rótulos propagados")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if args.threads:
        torch.set_num_threads(args.threads)
    cfg = RaiarNetConfig(
        width=args.width,
        depth=args.depth,
        attention=args.attention,
        downsample=args.downsample,
        neck_repeats=args.neck_repeats,
        density_head=not args.no_density,
    )
    model = RaiarNet(cfg)
    if args.init:
        model.load_state_dict(torch.load(args.init, map_location="cpu", weights_only=False)["state_dict"])
    roi = LevelROI.load()
    out_dir = RUNS / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    ds = FrameCrops(
        train_frames(args.densified),
        args.pipeline,
        crop=args.crop,
        samples_per_epoch=args.iters * args.batch,
        grid_aug=args.grid_aug,
        seed=args.seed,
    )
    dl = DataLoader(ds, batch_size=args.batch, shuffle=False, num_workers=0, collate_fn=collate)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=args.iters, pct_start=0.05)
    val_frames = load_split("val")
    history = []
    best = -1.0
    t0 = time.time()
    run_logs = {}
    print(f"parâmetros: {count_parameters(model) / 1e6:.3f} M")
    for it, (imgs, boxes) in enumerate(dl, 1):
        model.train()
        out = model(imgs)
        H, W = out["hm"].shape[-2:]
        t = build_targets(boxes, H, W, model.stride, density=cfg.density_head)
        loss, logs = raiarnet_loss(out, t, model.stride, w_box=args.w_box, w_den=args.w_den, w_wh=args.w_wh)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
        opt.step()
        sched.step()
        for k, v in logs.items():
            run_logs.setdefault(k, []).append(v)
        if it % 50 == 0:
            msg = " ".join(f"{k}={np.mean(v[-50:]):.3f}" for k, v in run_logs.items())
            print(f"[{it}/{args.iters}] {msg} ({time.time() - t0:.0f}s)", flush=True)
        if it % args.eval_every == 0 or it == args.iters:
            res, _ = evaluate(model, val_frames, args.pipeline, roi)
            d = res["det"]
            score = d["mAP50"] + d["f1"]
            rec = {"iter": it, "time_s": time.time() - t0, "loss": {k: float(np.mean(v[-args.eval_every:])) for k, v in run_logs.items()}, **res}
            history.append(rec)
            print(
                f"  val: mAP50={d['mAP50']:.3f} mAP50-95={d['mAP50_95']:.3f} P={d['precision']:.3f} "
                f"R={d['recall']:.3f} F1={d['f1']:.3f} thr={d['score_thr']:.2f} "
                f"MAE(fused,total)={res['count']['fused']['total']['MAE']:.2f} "
                f"MAE(det,total)={res['count']['det']['total']['MAE']:.2f}",
                flush=True,
            )
            ck = {"config": cfg.to_dict(), "state_dict": model.state_dict(), "pipeline": args.pipeline, "iter": it, "score_thr": d["score_thr"], "args": vars(args)}
            torch.save(ck, out_dir / "last.pt")
            if score > best:
                best = score
                torch.save(ck, out_dir / "best.pt")
            (out_dir / "history.json").write_text(json.dumps(history, indent=1, default=float), encoding="utf-8")
    print("melhor (mAP50+F1) na validação:", round(best, 4))


if __name__ == "__main__":
    main()
