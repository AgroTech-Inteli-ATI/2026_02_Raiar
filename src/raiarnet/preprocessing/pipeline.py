"""Pipelines de pré-processamento comparados no estudo de ablação."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from . import enhance as E

Step = Callable[[np.ndarray], np.ndarray]

PIPELINES: dict[str, list[Step]] = {
    "original": [],
    "clahe-lab": [E.clahe_lab],
    "clahe-hsv": [E.clahe_hsv],
    "msrcr": [E.msrcr],
    "gama-adaptativa": [E.adaptive_gamma],
    "bilateral": [E.bilateral],
    "guiado": [E.guided_filter],
    "cromatico": [E.chroma_boost],
    "gama+clahe": [E.adaptive_gamma, E.clahe_lab],
    "gama+clahe+guiado+cromatico": [E.adaptive_gamma, E.clahe_lab, E.guided_filter, E.chroma_boost],
}


def run(img: np.ndarray, name: str) -> np.ndarray:
    for step in PIPELINES[name]:
        img = step(img)
    return img


def image_stats(img: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float]:
    """Indicadores sem referência: contraste RMS, entropia e nitidez (Laplaciano)."""
    import cv2

    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sel = g[mask > 0] if mask is not None else g.ravel()
    hist = np.bincount(sel, minlength=256).astype(np.float64)
    p = hist / hist.sum()
    entropy = float(-(p[p > 0] * np.log2(p[p > 0])).sum())
    lap = cv2.Laplacian(g, cv2.CV_64F)
    lap_sel = lap[mask > 0] if mask is not None else lap.ravel()
    return {
        "brilho": float(sel.mean()),
        "contraste_rms": float(sel.std()),
        "entropia": entropy,
        "nitidez": float(lap_sel.var()),
    }
