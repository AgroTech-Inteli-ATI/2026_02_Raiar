"""Benchmark lado a lado: RaiarNet (do zero) x Chicken-YOLO (baseline).

Protocolo idêntico para todos os modelos:

1. mesmos quadros de teste, pré-processados pelo pipeline de cada modelo e
   mascarados fora da ROI dilatada;
2. caixas de referência e predições filtradas pelo centro dentro da ROI;
3. limiar de confiança escolhido na validação (melhor F1) e reaproveitado no teste;
4. contagem por nível pelo centro da caixa (detecção); a RaiarNet também reporta
   a contagem por densidade e a fusão sensível à oclusão;
5. FPS ponta a ponta em CPU (pré-processamento + rede + decodificação), lote 1.

Exemplo:
    python -m evaluation.benchmark --raiarnet runs/raiarnet/r1-base/best.pt \
        --yolo runs/chicken-yolo/cy-pretrained/weights/best.pt --out reports/benchmark.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from evaluation.metrics import best_f1_threshold, count_metrics, detection_metrics
from labeling.annotate import FRAMES
from models.counter import LevelCounter, load_counter
from models.decode import decode, forward_tta
from preprocessing.pipeline import run as run_pipeline
from preprocessing.roi import LEVELS, LevelROI
from training.dataset import ROI_DILATE, eval_boxes, load_frame, load_split, to_tensor

ROOT = Path(__file__).resolve().parents[2]


def roi_filter(boxes, scores, roi):
    if not len(boxes):
        return boxes, scores
    keep = np.array([roi.level_of((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) is not None for b in boxes], bool)
    return boxes[keep], scores[keep]


def gt_counts(gt: np.ndarray, roi: LevelROI) -> dict[str, int]:
    return roi.count(np.c_[(gt[:, 0] + gt[:, 2]) / 2, (gt[:, 1] + gt[:, 3]) / 2])


def det_counts(boxes, scores, thr, roi) -> dict[str, int]:
    b = boxes[scores >= thr]
    return roi.count(np.c_[(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2])


class RaiarNetRunner:
    name = "RaiarNet (nosso, do zero)"

    def __init__(self, weights: str, mode: str = "fused", window: int = 8, tta: bool = False):
        self.counter: LevelCounter = load_counter(weights, window=window, mode=mode, tta=tta)
        self.tta = tta
        self.model = self.counter.model
        self.pipeline = self.counter.pipeline
        self.mode = mode

    @torch.no_grad()
    def predict(self, img_masked: np.ndarray):
        out = forward_tta(self.model, to_tensor(img_masked), self.tta)
        boxes, scores, den = decode(out, self.model.stride, score_thr=0.05)[0]
        return boxes, scores, den

    def params(self) -> int:
        return sum(p.numel() for p in self.model.parameters())

    def counts(self, boxes, scores, den, thr, roi):
        self.counter.score_thr = thr
        c = self.counter.count(boxes, scores, den)
        return {m: {k: c[k][m] for k in LEVELS} for m in ("det", "density", "fused")}

    def end_to_end(self, raw: np.ndarray, roi: LevelROI):
        img = roi.apply_mask(run_pipeline(raw, self.pipeline), dilate=ROI_DILATE)
        return self.predict(img)


class YoloRunner:
    def __init__(self, weights: str, name: str, pipeline: str = "original", imgsz: int = 1024):
        import baseline.chicken_yolo  # noqa: F401  (registra as classes para o pickle)
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.name = name
        self.pipeline = pipeline
        self.imgsz = imgsz

    def predict(self, img_masked: np.ndarray):
        r = self.model.predict(img_masked, imgsz=self.imgsz, conf=0.01, iou=0.6, max_det=1000, verbose=False, device="cpu")[0]
        return r.boxes.xyxy.numpy(), r.boxes.conf.numpy(), None

    def params(self) -> int:
        return sum(p.numel() for p in self.model.model.parameters())

    def counts(self, boxes, scores, den, thr, roi):
        return {"det": det_counts(boxes, scores, thr, roi)}

    def end_to_end(self, raw: np.ndarray, roi: LevelROI):
        img = roi.apply_mask(run_pipeline(raw, self.pipeline), dilate=ROI_DILATE)
        return self.predict(img)


def collect(runner, frames, roi):
    res = []
    for f in frames:
        img = load_frame(f, runner.pipeline, roi)
        boxes, scores, den = runner.predict(img)
        boxes, scores = roi_filter(boxes, scores, roi)
        res.append({"frame": f, "pred": boxes, "scores": scores, "den": den, "gt": eval_boxes(f, roi)})
    return res


def measure_fps(runner, frames, roi, repeats: int = 3) -> float:
    raws = [cv2.imread(str(FRAMES / f"{f}.png")) for f in frames]
    runner.end_to_end(raws[0], roi)  # aquecimento
    t = time.perf_counter()
    n = 0
    for _ in range(repeats):
        for r in raws:
            runner.end_to_end(r, roi)
            n += 1
    return n / (time.perf_counter() - t)


def evaluate_runner(runner, roi, fps: bool = True) -> dict:
    val = collect(runner, load_split("val"), roi)
    thr, val_f1 = best_f1_threshold(val)
    test = collect(runner, load_split("test"), roi)
    det = detection_metrics(test, thr)
    gts = {k: [] for k in LEVELS}
    preds: dict[str, dict[str, list]] = {}
    per_frame = []
    for p in test:
        g = gt_counts(p["gt"], roi)
        c = runner.counts(p["pred"], p["scores"], p["den"], thr, roi)
        per_frame.append({"frame": p["frame"], "gt": g, "pred": {m: {k: float(v) for k, v in d.items()} for m, d in c.items()}})
        for k in LEVELS:
            gts[k].append(g[k])
        for m, d in c.items():
            for k in LEVELS:
                preds.setdefault(m, {kk: [] for kk in LEVELS})[k].append(float(d[k]))
    counts = {}
    for m, d in preds.items():
        counts[m] = {k: count_metrics(d[k], gts[k]) for k in LEVELS}
        counts[m]["total"] = count_metrics(np.sum([d[k] for k in LEVELS], 0), np.sum([gts[k] for k in LEVELS], 0))
    out = {
        "modelo": runner.name,
        "parametros_M": runner.params() / 1e6,
        "limiar_validacao": thr,
        "f1_validacao": val_f1,
        "deteccao": det,
        "contagem": counts,
        "por_quadro": per_frame,
    }
    if fps:
        out["fps_cpu"] = measure_fps(runner, load_split("test"), roi)
    return out, test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiarnet", nargs="*", default=[])
    ap.add_argument("--yolo", nargs="*", default=[], help="pares nome=caminho")
    ap.add_argument("--mode", default="fused")
    ap.add_argument("--window", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "reports" / "benchmark.json"))
    ap.add_argument("--no-fps", action="store_true")
    ap.add_argument("--tta", action="store_true", help="espelhamento horizontal na RaiarNet")
    args = ap.parse_args()
    torch.set_num_threads(6)
    roi = LevelROI.load()
    results = []
    for w in args.raiarnet:
        r = RaiarNetRunner(w, mode=args.mode, window=args.window, tta=args.tta)
        r.name = f"RaiarNet ({Path(w).parent.name}{', TTA' if args.tta else ''})"
        res, _ = evaluate_runner(r, roi, fps=not args.no_fps)
        res["pesos"] = w
        results.append(res)
        print_summary(res)
    for spec in args.yolo:
        name, w = spec.split("=", 1)
        r = YoloRunner(w, name)
        res, _ = evaluate_runner(r, roi, fps=not args.no_fps)
        res["pesos"] = w
        results.append(res)
        print_summary(res)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=float), encoding="utf-8", newline="\n")


def print_summary(res: dict) -> None:
    d = res["deteccao"]
    print(
        f"{res['modelo']}: mAP50={d['mAP50']:.3f} mAP50-95={d['mAP50_95']:.3f} P={d['precision']:.3f} "
        f"R={d['recall']:.3f} F1={d['f1']:.3f} thr={res['limiar_validacao']:.2f} FPS={res.get('fps_cpu', float('nan')):.2f}"
    )
    for m, c in res["contagem"].items():
        print(
            f"  contagem[{m}]: "
            + " ".join(f"{k}: MAE={c[k]['MAE']:.2f} RMSE={c[k]['RMSE']:.2f} MAPE={c[k]['MAPE']:.1f}%" for k in (*LEVELS, "total"))
        )


if __name__ == "__main__":
    main()
