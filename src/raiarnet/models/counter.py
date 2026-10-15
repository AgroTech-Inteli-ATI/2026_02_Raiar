"""Adaptação do detector para contagem direta de aves por nível (N0, N1, N2).

Regras do domínio aplicadas aqui:

- cada nível é medido diretamente na sua ROI; N1 nunca é calculado como
  total - N0 - N2;
- 1 contagem por nível e instante; câmeras não são somadas. Cada câmera
  responde apenas pelos níveis que observa com confiabilidade.

A contagem combina duas estimativas da RaiarNet em cada nível:

- detecção: número de picos do heatmap com escore >= limiar cujo centro cai no polígono;
- densidade: integral do mapa de densidade dentro do polígono.

A fusão sensível à oclusão parte das detecções e, em cada janela de 32 x 32
pixels, soma o excedente da densidade sobre as detecções que passar de uma
tolerância (aves aglomeradas ou atrás da grade que não formam pico nítido):
contagem = n + max(0, d - n - tol). Janela e tolerância foram escolhidas na validação.
Em vídeo, um filtro de Kalman 1D por nível estabiliza a série entre quadros.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
import torch

from preprocessing.pipeline import run as run_pipeline
from preprocessing.roi import LEVELS, LevelROI

from .decode import decode, forward_tta
from .raiarnet import RaiarNet


@dataclass
class Kalman1D:
    """Filtro de Kalman de nível constante: x_k = x_{k-1} + w, z_k = x_k + v."""

    q: float = 0.5  # variância do processo (aves entrando/saindo por quadro)
    r: float = 4.0  # variância da medição
    x: float | None = None
    p: float = 10.0

    def update(self, z: float) -> float:
        if self.x is None:
            self.x = z
            return z
        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (z - self.x)
        self.p *= 1 - k
        return self.x


@dataclass
class EMA:
    alpha: float = 0.3
    x: float | None = None

    def update(self, z: float) -> float:
        self.x = z if self.x is None else self.alpha * z + (1 - self.alpha) * self.x
        return self.x


@dataclass
class LevelCounter:
    model: RaiarNet
    roi: LevelROI
    pipeline: str = "original"
    score_thr: float = 0.3
    window: int = 8  # janela (em células de stride 4) da fusão sensível à oclusão
    tol: float = 0.5  # excedente mínimo da densidade para indicar ave oculta
    mode: str = "fused"  # det | density | fused
    tta: bool = False  # espelhamento horizontal na inferência
    filters: dict = field(default_factory=dict)

    def __post_init__(self):
        self.model.eval()
        s = self.model.stride
        w, h = self.roi.size
        self.level_masks = {}
        for k in LEVELS:
            m = self.roi.mask(k).astype(np.float32) / 255.0
            self.level_masks[k] = cv2.resize(m, (w // s, h // s), interpolation=cv2.INTER_AREA)

    def prepare(self, img_bgr: np.ndarray) -> np.ndarray:
        img = run_pipeline(img_bgr, self.pipeline)
        return self.roi.apply_mask(img, dilate=16)

    @torch.no_grad()
    def infer(self, img_bgr: np.ndarray, prepared: bool = False):
        img = img_bgr if prepared else self.prepare(img_bgr)
        x = torch.from_numpy(np.ascontiguousarray(img[:, :, ::-1])).permute(2, 0, 1).float()[None] / 255.0
        out = forward_tta(self.model, x, self.tta)
        return decode(out, self.model.stride, score_thr=0.05)[0]

    def count(self, boxes: np.ndarray, scores: np.ndarray, den: np.ndarray | None) -> dict:
        s = self.model.stride
        sel = scores >= self.score_thr
        b = boxes[sel]
        cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
        levels = [self.roi.level_of(x, y) for x, y in zip(cx, cy, strict=True)]
        res = {}
        for k in LEVELS:
            det = int(sum(lv == k for lv in levels))
            if den is None:
                res[k] = {"det": det, "density": None, "fused": float(det)}
                continue
            dmap = den * self.level_masks[k]
            dens = float(dmap.sum())
            # Fusão por janelas: detecções + excedente da densidade acima da tolerância.
            H, W = dmap.shape
            win = self.window
            det_map = np.zeros_like(dmap)
            for (x, y), lv in zip(zip(cx, cy, strict=True), levels, strict=True):
                if lv == k:
                    det_map[min(int(y // s), H - 1), min(int(x // s), W - 1)] += 1
            fused = 0.0
            for y0 in range(0, H, win):
                for x0 in range(0, W, win):
                    d = dmap[y0 : y0 + win, x0 : x0 + win].sum()
                    n = det_map[y0 : y0 + win, x0 : x0 + win].sum()
                    fused += n + max(0.0, d - n - self.tol)
            res[k] = {"det": det, "density": dens, "fused": fused}
        return res

    def count_frame(self, img_bgr: np.ndarray) -> dict:
        boxes, scores, den = self.infer(img_bgr)
        return self.count(boxes, scores, den)

    def smooth(self, counts: dict, method: str = "kalman") -> dict[str, float]:
        out = {}
        for k in LEVELS:
            if k not in self.filters:
                self.filters[k] = Kalman1D() if method == "kalman" else EMA()
            out[k] = self.filters[k].update(float(counts[k][self.mode]))
        return out


def load_counter(weights: str, pipeline: str | None = None, **kw) -> LevelCounter:
    from .raiarnet import RaiarNetConfig

    ck = torch.load(weights, map_location="cpu", weights_only=False)
    model = RaiarNet(RaiarNetConfig(**ck["config"]))
    model.load_state_dict(ck["state_dict"])
    return LevelCounter(model, LevelROI.load(), pipeline or ck.get("pipeline", "original"), **kw)
