"""Níveis N0 (piso), N1 (meio) e N2 (plataforma) da câmera C1 e geometria da ave.

Reutiliza o mesmo arquivo de calibração da RaiarNet
(`src/raiarnet/configs/cameras/c1-jump-start.json`), para que as duas abordagens
contem nas mesmas regiões. Esta cópia da lógica de ROI evita importar a RaiarNet
inteira (que depende de módulos de treino) só para ler polígonos.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

NIVEIS = ("N0", "N1", "N2")
RAIZ = Path(__file__).resolve().parents[2]  # .../src
CONFIG_CAMERA = RAIZ / "raiarnet" / "configs" / "cameras" / "c1-jump-start.json"
TAMANHO_QUADRO = (1024, 576)

# Âncoras (x, y, largura, altura) medidas pela equipe em aves isoladas da C1
# (mesmos valores de `src/raiarnet/labeling/boxes.py`). Descrevem o tamanho
# esperado de uma ave em cada ponto da imagem (perspectiva).
ANCORAS = np.array(
    [
        (400, 520, 52, 46),
        (520, 540, 50, 44),
        (600, 500, 44, 40),
        (650, 450, 40, 36),
        (600, 400, 36, 32),
        (700, 400, 32, 30),
        (550, 350, 34, 30),
        (650, 330, 28, 26),
        (600, 260, 22, 20),
        (700, 260, 20, 18),
        (650, 200, 18, 16),
        (720, 180, 16, 15),
        (700, 130, 13, 12),
        (760, 100, 11, 10),
        (720, 300, 24, 22),
        (480, 430, 44, 40),
        (330, 560, 56, 50),
        (150, 540, 66, 52),
        (250, 470, 58, 48),
        (330, 400, 50, 42),
        (430, 330, 40, 34),
        (520, 270, 32, 28),
        (600, 210, 24, 22),
        (680, 150, 18, 16),
        (60, 560, 70, 55),
        (40, 250, 55, 48),
        (150, 210, 50, 44),
        (330, 130, 40, 36),
        (450, 110, 32, 28),
        (560, 100, 26, 24),
        (640, 88, 22, 20),
        (700, 70, 18, 16),
        (100, 450, 64, 52),
        (250, 330, 50, 44),
    ],
    dtype=np.float32,
)


class NiveisROI:
    def __init__(self, caminho: Path | str = CONFIG_CAMERA):
        bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
        self.poligonos = {k: np.array(bruto[k], np.float32) for k in NIVEIS}

    def nivel_de(self, x: float, y: float) -> str | None:
        for k in NIVEIS:
            if cv2.pointPolygonTest(self.poligonos[k], (float(x), float(y)), False) >= 0:
                return k
        return None

    def niveis_de(self, centros: np.ndarray) -> list[str | None]:
        return [self.nivel_de(x, y) for x, y in np.asarray(centros).reshape(-1, 2)]

    def mascara(self, dilatar: int = 0) -> np.ndarray:
        w, h = TAMANHO_QUADRO
        m = np.zeros((h, w), np.uint8)
        for k in NIVEIS:
            cv2.fillPoly(m, [self.poligonos[k].astype(np.int32)], 255)
        if dilatar > 0:
            e = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dilatar + 1, 2 * dilatar + 1))
            m = cv2.dilate(m, e)
        return m

    def mascarar(self, imagem: np.ndarray, dilatar: int = 16, preenchimento: int = 114) -> np.ndarray:
        """Cinza fora da ROI (mesma máscara usada na RaiarNet antes da inferência)."""
        saida = imagem.copy()
        saida[self.mascara(dilatar) == 0] = preenchimento
        return saida

    def contar(self, centros: np.ndarray) -> dict[str, int]:
        out = dict.fromkeys(NIVEIS, 0)
        for lv in self.niveis_de(centros):
            if lv:
                out[lv] += 1
        return out


def tamanho_esperado(x: float, y: float, k: int = 4) -> tuple[float, float]:
    """Largura e altura esperadas de uma ave centrada em (x, y) (IDW em escala log)."""
    d = np.hypot(ANCORAS[:, 0] - x, ANCORAS[:, 1] - y) + 1.0
    idx = np.argsort(d)[:k]
    w = 1.0 / d[idx] ** 2
    lw = np.sum(w * np.log(ANCORAS[idx, 2])) / w.sum()
    lh = np.sum(w * np.log(ANCORAS[idx, 3])) / w.sum()
    return float(np.exp(lw)), float(np.exp(lh))
