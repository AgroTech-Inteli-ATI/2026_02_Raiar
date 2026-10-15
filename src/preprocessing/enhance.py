"""Técnicas de realce para os quadros do aviário.

Cada função recebe e devolve uma imagem BGR uint8 do mesmo tamanho. As hipóteses
ópticas que motivam cada técnica estão na documentação (tratamento de imagens):

- sombra sob a plataforma (N1) -> correção gama adaptativa e Retinex (MSRCR);
- baixo contraste entre plumagem marrom e maravalha (N0) -> CLAHE e destaque cromático;
- grade metálica e ruído de compressão -> filtros que preservam bordas (bilateral, guiado);
- iluminação lateral estourada -> CLAHE com limite de recorte e gama > 1 em áreas claras.
"""

from __future__ import annotations

import cv2
import numpy as np


def clahe_lab(img: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid)).apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def clahe_hsv(img: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv[:, :, 2] = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid)).apply(hsv[:, :, 2])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def msrcr(
    img: np.ndarray,
    sigmas: tuple[float, ...] = (15.0, 80.0, 200.0),
    alpha: float = 125.0,
    beta: float = 46.0,
    gain: float = 192.0,
    offset: float = -30.0,
    low_clip: float = 0.01,
    high_clip: float = 0.99,
) -> np.ndarray:
    """Retinex multiescala com restauração de cor (Jobson, Rahman e Woodell, 1997)."""
    f = img.astype(np.float32) + 1.0
    log_f = np.log(f)
    retinex = np.zeros_like(f)
    for s in sigmas:
        retinex += log_f - np.log(cv2.GaussianBlur(f, (0, 0), s) + 1.0)
    retinex /= len(sigmas)
    color = beta * (np.log(alpha * f) - np.log(f.sum(axis=2, keepdims=True)))
    out = gain * (retinex * color + offset)
    # Recorte por percentis em cada canal, como no algoritmo original.
    res = np.empty_like(out)
    for c in range(3):
        lo, hi = np.quantile(out[:, :, c], [low_clip, high_clip])
        res[:, :, c] = np.clip((out[:, :, c] - lo) / max(hi - lo, 1e-6), 0, 1)
    return (res * 255).astype(np.uint8)


def adaptive_gamma(img: np.ndarray, sigma: float = 25.0, strength: float = 1.0) -> np.ndarray:
    """Gama local: < 1 nas regiões escuras (sombra de N1) e > 1 nas estouradas."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lum = lab[:, :, 0].astype(np.float32) / 255.0
    local = cv2.GaussianBlur(lum, (0, 0), sigma)
    gamma = np.power(2.0, strength * (local - 0.5) / 0.5)
    out = np.power(np.clip(lum, 1e-4, 1.0), gamma)
    lab[:, :, 0] = np.clip(out * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def bilateral(img: np.ndarray, d: int = 7, sigma_color: float = 35.0, sigma_space: float = 7.0):
    return cv2.bilateralFilter(img, d, sigma_color, sigma_space)


def _box(x: np.ndarray, r: int) -> np.ndarray:
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1), normalize=True, borderType=cv2.BORDER_REFLECT)


def guided_filter(img: np.ndarray, radius: int = 4, eps: float = 0.01) -> np.ndarray:
    """Filtro guiado (He, Sun e Tang, 2013) com a própria imagem como guia, por canal."""
    p = img.astype(np.float32) / 255.0
    out = np.empty_like(p)
    for c in range(3):
        i = p[:, :, c]
        mean_i = _box(i, radius)
        var_i = _box(i * i, radius) - mean_i * mean_i
        a = var_i / (var_i + eps)
        b = mean_i - a * mean_i
        out[:, :, c] = _box(a, radius) * i + _box(b, radius)
    return np.clip(out * 255.0, 0, 255).astype(np.uint8)


def chroma_boost(img: np.ndarray, hue: float = 12.0, width: float = 10.0, gain: float = 0.8):
    """Aumenta a saturação nas matizes marrom-avermelhadas da plumagem.

    A grade galvanizada e a maravalha são pouco saturadas; a plumagem das aves
    vermelhas tem matiz entre ~0 e ~25 no HSV do OpenCV (0-180).
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    h = hsv[:, :, 0]
    dist = np.minimum(np.abs(h - hue), 180.0 - np.abs(h - hue))
    w = np.exp(-0.5 * (dist / width) ** 2)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.0 + gain * w), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def unsharp(img: np.ndarray, sigma: float = 1.5, amount: float = 0.6) -> np.ndarray:
    """Nitidez leve para compensar parte do motion blur."""
    blur = cv2.GaussianBlur(img, (0, 0), sigma)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)
