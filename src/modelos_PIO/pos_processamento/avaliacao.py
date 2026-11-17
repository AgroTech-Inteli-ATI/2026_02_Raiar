"""Métricas de contagem por nível (mesmas definições da RaiarNet) e comparação de configurações."""

from __future__ import annotations

import numpy as np

from .niveis import NIVEIS, NiveisROI
from .posprocessamento import Config, processar


def metricas(previsto, real) -> dict:
    """MAE, RMSE, MAPE e viés (previsto - real) de duas séries."""
    p, r = np.asarray(previsto, float), np.asarray(real, float)
    d = p - r
    nz = r > 0
    return {
        "MAE": float(np.mean(np.abs(d))),
        "RMSE": float(np.sqrt(np.mean(d**2))),
        "MAPE": float(100 * np.mean(np.abs(d[nz]) / r[nz])) if nz.any() else None,
        "vies": float(np.mean(d)),
    }


def contar_quadros(deteccoes: dict, gt: dict, cfg: Config, roi: NiveisROI, quadros=None) -> dict:
    """Contagem por nível de cada quadro e métricas agregadas contra a anotação manual."""
    quadros = quadros or sorted(deteccoes)
    prev = {k: [] for k in NIVEIS}
    real = {k: [] for k in NIVEIS}
    for ms in quadros:
        b, s = deteccoes[ms]
        c = processar(b, s, cfg, roi)["contagem"]
        for k in NIVEIS:
            prev[k].append(c[k])
            real[k].append(gt[str(ms)][k])
    prev["total"] = [sum(prev[k][i] for k in NIVEIS) for i in range(len(quadros))]
    real["total"] = [sum(real[k][i] for k in NIVEIS) for i in range(len(quadros))]
    return {
        "quadros": list(quadros),
        "previsto": prev,
        "real": real,
        "metricas": {k: metricas(prev[k], real[k]) for k in (*NIVEIS, "total")},
    }


def resumo_linha(nome: str, res: dict) -> str:
    m = res["metricas"]
    cel = lambda k: f"{m[k]['MAE']:5.2f} ({m[k]['vies']:+6.2f})"  # noqa: E731
    return f"{nome:34s} N0 {cel('N0')} | N1 {cel('N1')} | N2 {cel('N2')} | total {cel('total')}"
