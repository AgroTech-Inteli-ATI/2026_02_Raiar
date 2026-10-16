"""Exporta o conjunto anotado no formato YOLO e treina o baseline Chicken-YOLO.

Os mesmos quadros pré-processados e mascarados usados pela RaiarNet alimentam o
baseline, com as mesmas partições. Hiperparâmetros seguem o artigo (SGD, lr 0,01,
momento 0,937, decaimento 5e-4, Mosaic e Mixup), ajustados à resolução nativa
das câmeras (imgsz 1024) e ao treino em CPU.

Exemplos:
    python -m baseline.train_chicken_yolo --name cy-scratch --epochs 300
    python -m baseline.train_chicken_yolo --name cy-pretrained --pretrained --epochs 300
    python -m baseline.train_chicken_yolo --name y11n-pretrained --plain --pretrained
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from preprocessing.roi import LevelROI
from training.dataset import load_frame, load_split, train_boxes, train_frames

ROOT = Path(__file__).resolve().parents[1]
YOLO_DATA = ROOT / "data" / "processed" / "yolo"
RUNS = ROOT / "runs" / "chicken-yolo"
PRETRAINED = ROOT / "models" / "pretrained" / "yolo11n.pt"


def export(pipeline: str = "original", densified: bool = False, repeat: int = 1) -> Path:
    roi = LevelROI.load()
    base = YOLO_DATA / (pipeline + ("-densificado" if densified else ""))
    for split in ("train", "val", "test"):
        (base / "images" / split).mkdir(parents=True, exist_ok=True)
        (base / "labels" / split).mkdir(parents=True, exist_ok=True)
        frames = train_frames(densified) if split == "train" else load_split(split)
        for f in frames:
            img = load_frame(f, pipeline, roi)
            h, w = img.shape[:2]
            cv2.imwrite(str(base / "images" / split / f"{f}.png"), img)
            lines = []
            for x1, y1, x2, y2 in train_boxes(f, roi):
                lines.append(f"0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
            (base / "labels" / split / f"{f}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    yaml = base / "data.yaml"
    yaml.write_text(
        f"path: {base.as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: chicken\n",
        encoding="utf-8",
    )
    return yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--pipeline", default="original")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--imgsz", type=int, default=1024)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--pretrained", action="store_true", help="inicializa camadas compatíveis com YOLO11n COCO")
    ap.add_argument("--plain", action="store_true", help="YOLO11n sem os módulos do Chicken-YOLO")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--densified", action="store_true", help="mesmos quadros extras de treino da RaiarNet")
    ap.add_argument("--repeat", type=int, default=1, help="repetições da lista de treino por época")
    args = ap.parse_args()

    from ultralytics import YOLO

    from baseline.chicken_yolo import ChickenYoloTrainer

    data = export(args.pipeline, args.densified, args.repeat)
    model = YOLO("yolo11n.yaml")
    kw = {}
    if args.pretrained:
        kw["pretrained"] = str(PRETRAINED)
    else:
        kw["pretrained"] = False
    model.train(
        data=str(data),
        trainer=None if args.plain else ChickenYoloTrainer,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        optimizer="SGD",
        lr0=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        mosaic=1.0,
        mixup=0.1,
        close_mosaic=max(args.epochs // 10, 10),
        patience=args.epochs,
        device="cpu",
        workers=args.workers,
        project=str(RUNS),
        name=args.name,
        exist_ok=True,
        seed=0,
        deterministic=False,
        plots=True,
        verbose=False,
        **kw,
    )


if __name__ == "__main__":
    main()
