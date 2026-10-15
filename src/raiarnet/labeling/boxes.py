"""Conversão dos pontos anotados em caixas de referência.

Cada ave foi anotada como um ponto no centro do corpo. Para medir mAP e treinar
detectores, derivamos uma caixa por ponto em duas etapas:

1. Prior de perspectiva: o tamanho esperado da ave em cada posição da imagem é
   interpolado (IDW em escala log) a partir de âncoras medidas manualmente em
   aves isoladas de N0, N1 e N2.
2. Refinamento com SAM: o ponto (positivo) e os quatro vizinhos mais próximos
   (negativos) viram prompt do Segment Anything. A caixa do SAM só é aceita
   quando contém o ponto perto do centro e tem largura e altura entre 0,6x e
   1,6x do prior; caso contrário, mantemos a caixa do prior.

O SAM é usado apenas como ferramenta de rotulagem, nunca no modelo.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from .annotate import ANN, FRAMES, load_points

BOXES = ANN / "boxes"

# (x, y, largura, altura) em pixels de aves isoladas medidas no quadro 1024 x 576.
ANCHORS = np.array(
    [
        # N0 - piso
        (400, 520, 52, 46), (520, 540, 50, 44), (600, 500, 44, 40), (650, 450, 40, 36),
        (600, 400, 36, 32), (700, 400, 32, 30), (550, 350, 34, 30), (650, 330, 28, 26),
        (600, 260, 22, 20), (700, 260, 20, 18), (650, 200, 18, 16), (720, 180, 16, 15),
        (700, 130, 13, 12), (760, 100, 11, 10), (720, 300, 24, 22), (480, 430, 44, 40),
        (330, 560, 56, 50),
        # N1 - meio, sob a borda da plataforma
        (150, 540, 66, 52), (250, 470, 58, 48), (330, 400, 50, 42), (430, 330, 40, 34),
        (520, 270, 32, 28), (600, 210, 24, 22), (680, 150, 18, 16), (60, 560, 70, 55),
        # N2 - plataforma e borda distante
        (40, 250, 55, 48), (150, 210, 50, 44), (330, 130, 40, 36), (450, 110, 32, 28),
        (560, 100, 26, 24), (640, 88, 22, 20), (700, 70, 18, 16), (100, 450, 64, 52),
        (250, 330, 50, 44),
    ],
    dtype=np.float32,
)


def prior_size(x: float, y: float, k: int = 4) -> tuple[float, float]:
    d = np.hypot(ANCHORS[:, 0] - x, ANCHORS[:, 1] - y) + 1.0
    idx = np.argsort(d)[:k]
    wgt = 1.0 / d[idx] ** 2
    lw = np.sum(wgt * np.log(ANCHORS[idx, 2])) / wgt.sum()
    lh = np.sum(wgt * np.log(ANCHORS[idx, 3])) / wgt.sum()
    return float(np.exp(lw)), float(np.exp(lh))


def prior_box(x: float, y: float, w_img: int = 1024, h_img: int = 576) -> list[float]:
    w, h = prior_size(x, y)
    return [max(x - w / 2, 0), max(y - h / 2, 0), min(x + w / 2, w_img - 1), min(y + h / 2, h_img - 1)]


class SamRefiner:
    def __init__(self, name: str = "facebook/sam-vit-base"):
        import torch
        from transformers import SamModel, SamProcessor

        self.torch = torch
        self.proc = SamProcessor.from_pretrained(name)
        self.model = SamModel.from_pretrained(name).eval()

    def boxes(self, img_bgr: np.ndarray, pts: list[list[float]]) -> list[list[float] | None]:
        torch = self.torch
        rgb = img_bgr[:, :, ::-1].copy()
        h_img, w_img = rgb.shape[:2]
        inp = self.proc(rgb, return_tensors="pt")
        with torch.no_grad():
            emb = self.model.get_image_embeddings(inp["pixel_values"])
        arr = np.array(pts, np.float32)
        out_boxes: list[list[float] | None] = []
        for i in range(0, len(pts), 32):
            chunk = pts[i : i + 32]
            ip, il = [], []
            for p in chunk:
                d = np.hypot(*(arr - p).T)
                nn = np.argsort(d)[1:5]
                negs = [list(map(float, arr[j])) for j in nn]
                while len(negs) < 4:
                    negs.append([float(p[0]), float(p[1])])
                ip.append([list(map(float, p))] + negs)
                il.append([1] + [0 if j < len(nn) else -10 for j in range(4)])
            enc = self.proc(rgb, input_points=[ip], input_labels=[il], return_tensors="pt")
            with torch.no_grad():
                out = self.model(
                    image_embeddings=emb,
                    input_points=enc["input_points"],
                    input_labels=enc["input_labels"],
                    multimask_output=True,
                )
            masks = self.proc.image_processor.post_process_masks(
                out.pred_masks, enc["original_sizes"], enc["reshaped_input_sizes"]
            )[0]
            scores = out.iou_scores[0]
            for k, p in enumerate(chunk):
                px = int(np.clip(p[0], 0, w_img - 1))
                py = int(np.clip(p[1], 0, h_img - 1))
                pw, ph = prior_size(p[0], p[1])
                best = None
                for j in range(masks.shape[1]):
                    mk = masks[k, j].numpy().astype(np.uint8)
                    _, lab = cv2.connectedComponents(mk)
                    lbl = lab[py, px]
                    if lbl == 0:
                        continue
                    ys, xs = np.nonzero(lab == lbl)
                    b = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
                    bw, bh = b[2] - b[0] + 1, b[3] - b[1] + 1
                    if not (0.6 * pw <= bw <= 1.6 * pw and 0.6 * ph <= bh <= 1.6 * ph):
                        continue
                    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                    if abs(cx - p[0]) > 0.3 * bw or abs(cy - p[1]) > 0.3 * bh:
                        continue
                    s = float(scores[k, j])
                    if best is None or s > best[0]:
                        best = (s, b)
                out_boxes.append(best[1] if best else None)
        return out_boxes


def build(frames: list[str], use_sam: bool = True) -> None:
    BOXES.mkdir(parents=True, exist_ok=True)
    refiner = SamRefiner() if use_sam else None
    for name in frames:
        pts = load_points(name)
        img = cv2.imread(str(FRAMES / f"{name}.png"))
        sam = refiner.boxes(img, pts) if refiner and pts else [None] * len(pts)
        recs = []
        for p, b in zip(pts, sam, strict=True):
            src = "sam" if b is not None else "prior"
            box = b if b is not None else prior_box(p[0], p[1], img.shape[1], img.shape[0])
            recs.append({"point": p, "box": [round(v, 1) for v in box], "source": src})
        (BOXES / f"{name}.json").write_text(json.dumps(recs, indent=1), encoding="utf-8")
        n_sam = sum(r["source"] == "sam" for r in recs)
        print(f"{name}: {len(recs)} caixas, {n_sam} do SAM")


if __name__ == "__main__":
    import sys

    names = sys.argv[1:] or sorted(p.stem for p in ANN.glob("*.json"))
    build(names)
