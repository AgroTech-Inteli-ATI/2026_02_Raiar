"""Conjunto de dados dos quadros anotados da Raiar.

Os quadros completos (1024 x 576) são pré-processados com o pipeline escolhido,
mascarados fora da ROI dilatada e cortados em recortes aleatórios no treino.
As augmentations simulam as condições do aviário: grade sobreposta (oclusão do
Jump Start), motion blur, variação de exposição e quadros noturnos em tons de cinza.
"""

from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from labeling.annotate import FRAMES
from labeling.boxes import BOXES
from preprocessing.pipeline import run as run_pipeline
from preprocessing.roi import LevelROI

ROOT = Path(__file__).resolve().parents[1]
# A partição pode ser trocada pela variável RAIAR_SPLITS (ex.: configs/dataset-splits-v3.json).
SPLITS = ROOT / os.environ.get("RAIAR_SPLITS", "configs/dataset-splits.json")
CACHE = ROOT / "data" / "processed"
ROI_DILATE = 16


def load_split(name: str) -> list[str]:
    key = {"train": "treino", "val": "validacao", "test": "teste"}[name]
    return json.loads(SPLITS.read_text(encoding="utf-8"))[key]


def densified_frames() -> list[str]:
    """Quadros intermediários da janela de treino com rótulos propagados (labeling.densify).

    Só entram quadros dos vídeos presentes no treino da partição ativa.
    """
    from labeling.annotate import ANN

    videos = {f.split("_t")[0] for f in load_split("train")}
    out = []
    for p in sorted(ANN.glob("*.json")):
        if p.stem.split("_t")[0] in videos and json.loads(p.read_text(encoding="utf-8")).get("densificado"):
            out.append(p.stem)
    return out


def train_frames(densified: bool = False) -> list[str]:
    return load_split("train") + (densified_frames() if densified else [])


def load_boxes(frame: str) -> np.ndarray:
    recs = json.loads((BOXES / f"{frame}.json").read_text(encoding="utf-8"))
    return np.array([r["box"] for r in recs], np.float32).reshape(-1, 4)


def load_frame(frame: str, pipeline: str = "original", roi: LevelROI | None = None) -> np.ndarray:
    """Quadro pré-processado e mascarado, com cache em data/processed/<pipeline>/."""
    out = CACHE / pipeline / f"{frame}.png"
    if out.exists():
        return cv2.imread(str(out))
    img = cv2.imread(str(FRAMES / f"{frame}.png"))
    img = run_pipeline(img, pipeline)
    roi = roi or LevelROI.load()
    img = roi.apply_mask(img, dilate=ROI_DILATE)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)
    return img


def eval_boxes(frame: str, roi: LevelROI) -> np.ndarray:
    """Caixas de referência cujo centro está dentro da ROI (sem dilatação)."""
    b = load_boxes(frame)
    keep = [roi.level_of((x1 + x2) / 2, (y1 + y2) / 2) is not None for x1, y1, x2, y2 in b]
    return b[np.array(keep, bool)] if len(b) else b


def train_boxes(frame: str, roi: LevelROI) -> np.ndarray:
    """Caixas usadas no treino: centro dentro da ROI dilatada (a área visível)."""
    b = load_boxes(frame)
    m = roi.mask(dilate=ROI_DILATE)
    keep = []
    for x1, y1, x2, y2 in b:
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
        keep.append(0 <= cy < m.shape[0] and 0 <= cx < m.shape[1] and m[cy, cx] > 0)
    return b[np.array(keep, bool)] if len(b) else b


def overlay_grid(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Desenha uma grade metálica sintética sobre parte do recorte."""
    h, w = img.shape[:2]
    out = img.copy()
    layer = out.copy()
    spacing = rng.randint(6, 16)
    thick = rng.randint(1, 2)
    angle = rng.uniform(-35, 35)
    color = tuple(int(rng.uniform(150, 235)) for _ in range(3))
    diag = int(math.hypot(w, h))
    cx, cy = w / 2, h / 2
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for d in range(-diag, diag, spacing):
        for rot in (0, 1):
            dx, dy = (ca, sa) if rot == 0 else (-sa, ca)
            px, py = cx + d * -dy, cy + d * dx
            p1 = (int(px - dx * diag), int(py - dy * diag))
            p2 = (int(px + dx * diag), int(py + dy * diag))
            cv2.line(layer, p1, p2, color, thick, cv2.LINE_AA)
    # Aplica a grade numa faixa aleatória, como a borda das mesas.
    mask = np.zeros((h, w), np.float32)
    y0 = rng.randint(0, h // 2)
    mask[y0 : y0 + rng.randint(h // 4, h // 2)] = 1.0
    mask = cv2.GaussianBlur(mask, (0, 0), 6)[:, :, None]
    alpha = rng.uniform(0.5, 0.9)
    return (out * (1 - alpha * mask) + layer * (alpha * mask)).astype(np.uint8)


def motion_blur(img: np.ndarray, rng: random.Random) -> np.ndarray:
    k = rng.choice([3, 5, 7])
    kern = np.zeros((k, k), np.float32)
    kern[k // 2, :] = 1.0 / k
    rot = cv2.getRotationMatrix2D((k / 2 - 0.5, k / 2 - 0.5), rng.uniform(0, 180), 1.0)
    kern = cv2.warpAffine(kern, rot, (k, k))
    kern /= max(kern.sum(), 1e-6)
    return cv2.filter2D(img, -1, kern)


class FrameCrops(Dataset):
    """Recortes aleatórios dos quadros de treino com alvos em caixas (x1, y1, x2, y2)."""

    def __init__(
        self,
        frames: list[str],
        pipeline: str = "original",
        crop: int = 384,
        samples_per_epoch: int = 400,
        augment: bool = True,
        grid_aug: float = 0.3,
        seed: int = 0,
    ):
        self.roi = LevelROI.load()
        self.imgs = [load_frame(f, pipeline, self.roi) for f in frames]
        self.boxes = [train_boxes(f, self.roi) for f in frames]
        self.valid = self.roi.mask(dilate=ROI_DILATE)
        self.crop = crop
        self.n = samples_per_epoch
        self.augment = augment
        self.grid_aug = grid_aug
        self.rng = random.Random(seed)
        # Pontos dentro da ROI para centralizar recortes onde há aves ou estrutura.
        ys, xs = np.nonzero(self.valid)
        self.valid_pts = np.stack([xs, ys], 1)

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int):
        rng = self.rng
        i = rng.randrange(len(self.imgs))
        img, boxes = self.imgs[i], self.boxes[i].copy()
        h, w = img.shape[:2]
        scale = rng.uniform(0.7, 1.4) if self.augment else 1.0
        cs = int(round(self.crop / scale))
        cs = min(cs, h, w)
        if len(boxes) and rng.random() < 0.7:
            b = boxes[rng.randrange(len(boxes))]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        else:
            cx, cy = self.valid_pts[rng.randrange(len(self.valid_pts))]
        x0 = int(np.clip(cx - cs / 2 + rng.uniform(-cs / 3, cs / 3), 0, w - cs))
        y0 = int(np.clip(cy - cs / 2 + rng.uniform(-cs / 3, cs / 3), 0, h - cs))
        patch = img[y0 : y0 + cs, x0 : x0 + cs]
        patch = cv2.resize(patch, (self.crop, self.crop), interpolation=cv2.INTER_LINEAR)
        s = self.crop / cs
        bx = boxes.copy()
        if len(bx):
            bx[:, [0, 2]] = (bx[:, [0, 2]] - x0) * s
            bx[:, [1, 3]] = (bx[:, [1, 3]] - y0) * s
            cxs, cys = (bx[:, 0] + bx[:, 2]) / 2, (bx[:, 1] + bx[:, 3]) / 2
            inside = (cxs >= 0) & (cxs < self.crop) & (cys >= 0) & (cys < self.crop)
            bx = bx[inside]
            bx = np.clip(bx, 0, self.crop - 1)
        if self.augment:
            if rng.random() < 0.5:
                patch = patch[:, ::-1].copy()
                if len(bx):
                    bx[:, [0, 2]] = self.crop - 1 - bx[:, [2, 0]]
            if rng.random() < self.grid_aug:
                patch = overlay_grid(patch, rng)
            if rng.random() < 0.3:
                patch = motion_blur(patch, rng)
            if rng.random() < 0.15:
                g = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
                patch = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
            # Exposição e contraste.
            a = rng.uniform(0.7, 1.3)
            b = rng.uniform(-25, 25)
            patch = cv2.convertScaleAbs(patch, alpha=a, beta=b)
            if rng.random() < 0.5:
                hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv[:, :, 0] = (hsv[:, :, 0] + rng.uniform(-6, 6)) % 180
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * rng.uniform(0.7, 1.3), 0, 255)
                patch = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        t = torch.from_numpy(np.ascontiguousarray(patch[:, :, ::-1])).permute(2, 0, 1).float() / 255.0
        return t, torch.from_numpy(bx.astype(np.float32))


def collate(batch):
    imgs = torch.stack([b[0] for b in batch])
    return imgs, [b[1] for b in batch]


def to_tensor(img_bgr: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(img_bgr[:, :, ::-1])).permute(2, 0, 1).float()[None] / 255.0
