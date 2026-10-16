"""Regiões de interesse por nível (N0, N1, N2) e regra de atribuição.

- A divisória verde do fundo da seção é fixa: ela limita a ROI no fundo do
  corredor e não muda ao longo da recria.
- A região azul (mesas e estruturas) é aberta e móvel: os polígonos de N1 e N2
  descrevem o que a câmera vê no enquadramento atual e devem ser revisados
  quando o manejo mudar a altura ou a posição das mesas.
- Cada ave é atribuída a um único nível pelo centro do corpo. Nunca derivamos
  N1 por diferença (total - N0 - N2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

LEVELS = ("N0", "N1", "N2")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMERA = ROOT / "configs" / "cameras" / "c1-jump-start.json"


@dataclass
class LevelROI:
    polygons: dict[str, np.ndarray]
    divider: np.ndarray | None
    size: tuple[int, int] = (1024, 576)

    @classmethod
    def load(cls, path: Path | str = DEFAULT_CAMERA) -> LevelROI:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        polys = {k: np.array(raw[k], np.float32) for k in LEVELS}
        div = np.array(raw["divisoria"], np.float32) if "divisoria" in raw else None
        return cls(polys, div)

    def mask(self, level: str | None = None, dilate: int = 0) -> np.ndarray:
        w, h = self.size
        m = np.zeros((h, w), np.uint8)
        for k in [level] if level else LEVELS:
            cv2.fillPoly(m, [self.polygons[k].astype(np.int32)], 255)
        if dilate > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dilate + 1, 2 * dilate + 1))
            m = cv2.dilate(m, k)
        return m

    def level_of(self, x: float, y: float) -> str | None:
        for k in LEVELS:
            if cv2.pointPolygonTest(self.polygons[k], (float(x), float(y)), False) >= 0:
                return k
        return None

    def count(self, points: np.ndarray) -> dict[str, int]:
        out = dict.fromkeys(LEVELS, 0)
        for x, y in np.asarray(points, np.float32).reshape(-1, 2):
            lv = self.level_of(x, y)
            if lv:
                out[lv] += 1
        return out

    def apply_mask(self, img: np.ndarray, dilate: int = 16, fill: int = 114) -> np.ndarray:
        """Preenche com cinza tudo o que está fora da ROI (dilatada) dos três níveis."""
        m = self.mask(dilate=dilate)
        out = img.copy()
        out[m == 0] = fill
        return out

    def draw(self, img: np.ndarray, alpha: float = 0.35) -> np.ndarray:
        colors = {"N0": (255, 200, 0), "N1": (200, 0, 200), "N2": (0, 170, 255)}
        over = img.copy()
        for k in LEVELS:
            cv2.fillPoly(over, [self.polygons[k].astype(np.int32)], colors[k])
        out = cv2.addWeighted(over, alpha, img, 1 - alpha, 0)
        for k in LEVELS:
            cv2.polylines(out, [self.polygons[k].astype(np.int32)], True, colors[k], 2)
            c = self.polygons[k].mean(axis=0).astype(int)
            cv2.putText(out, k, (int(c[0]), int(c[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if self.divider is not None:
            cv2.polylines(out, [self.divider.astype(np.int32)], False, (0, 220, 0), 4)
        return out
