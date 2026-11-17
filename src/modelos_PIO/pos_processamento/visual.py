"""Figuras para leigos: o que o modelo viu, quanto errou e como o pós-processamento ajuda."""

from __future__ import annotations

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .niveis import NIVEIS, NiveisROI  # noqa: E402

COR = {"N0": (255, 200, 0), "N1": (200, 0, 200), "N2": (0, 170, 255)}  # BGR
COR_MPL = {"N0": "#1f9bd1", "N1": "#c000c0", "N2": "#ff9d00"}


def desenhar(img, resultado: dict, roi: NiveisROI, titulo: str, contagem: dict):
    vis = img.copy()
    over = vis.copy()
    for k in NIVEIS:
        cv2.fillPoly(over, [roi.poligonos[k].astype(np.int32)], COR[k])
    vis = cv2.addWeighted(over, 0.15, vis, 0.85, 0)
    for k in NIVEIS:
        cv2.polylines(vis, [roi.poligonos[k].astype(np.int32)], True, COR[k], 1)
    for b, lv, ok in zip(resultado["caixas"], resultado["niveis"], resultado["aceitas"], strict=True):
        cor = COR[lv] if ok else (160, 160, 160)
        cv2.rectangle(vis, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), cor, 1)
    cv2.rectangle(vis, (0, 0), (1024, 26), (25, 25, 25), -1)
    txt = f"{titulo} | " + "  ".join(f"{k}: {contagem[k]:.0f}" for k in NIVEIS)
    cv2.putText(vis, txt, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return vis


def antes_depois(img, res_antes, res_depois, roi, cont_antes, cont_depois, real, destino):
    a = desenhar(img, res_antes, roi, "ANTES (conf 0,25)", cont_antes)
    d = desenhar(img, res_depois, roi, "DEPOIS (pos-processado)", cont_depois)
    r = img.copy()
    cv2.rectangle(r, (0, 0), (1024, 26), (25, 25, 25), -1)
    cv2.putText(
        r,
        "ANOTACAO MANUAL | " + "  ".join(f"{k}: {real[k]}" for k in NIVEIS),
        (8, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.imwrite(str(destino), np.vstack([a, d]))


def barras_por_nivel(series: dict, real: dict, destino, titulo: str):
    """series: {nome: {nivel: valor médio}}; real: {nivel: média}."""
    nomes = list(series)
    fig, eixos = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, k in zip(eixos, NIVEIS, strict=True):
        vals = [real[k]] + [series[n][k] for n in nomes]
        rot = ["Anotação\nmanual"] + [n.replace(" + ", "\n+ ") for n in nomes]
        cores = ["#444444"] + [COR_MPL[k]] * len(nomes)
        bars = ax.bar(range(len(vals)), vals, color=cores)
        for b, v in zip(bars, vals, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
        ax.set_xticks(range(len(vals)), rot, fontsize=7)
        ax.set_title(f"{k} — aves por quadro")
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(titulo)
    fig.tight_layout()
    fig.savefig(destino, dpi=140)
    plt.close(fig)


def serie_tempo(tempos, brutas: dict, suaves: dict, real_pts: dict, destino):
    fig, eixos = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True)
    for ax, k in zip(eixos, NIVEIS, strict=True):
        ax.plot(tempos, brutas[k], color=COR_MPL[k], alpha=0.35, label="por quadro")
        ax.plot(tempos, suaves[k], color=COR_MPL[k], lw=2, label="com filtro de Kalman")
        if k in real_pts:
            ax.scatter(*zip(*real_pts[k], strict=True), color="red", zorder=5, label="anotação manual")
        ax.set_ylabel(f"{k} (aves)")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7, loc="best")
    eixos[-1].set_xlabel("tempo no vídeo (s)")
    fig.tight_layout()
    fig.savefig(destino, dpi=140)
    plt.close(fig)


def erro_por_iteracao(rotulos, mae_total, destino):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.barh(range(len(rotulos)), mae_total, color="#2b7a5b")
    ax.set_yticks(range(len(rotulos)), rotulos, fontsize=8)
    ax.invert_yaxis()
    for b, v in zip(bars, mae_total, strict=True):
        ax.text(v, b.get_y() + b.get_height() / 2, f" {v:.1f}", va="center", fontsize=8)
    ax.set_xlabel("erro médio do total de aves (aves por quadro, vs. ~130 reais) — menor é melhor")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(destino, dpi=140)
    plt.close(fig)


def erro_por_nivel(sistemas: dict, destino, titulo: str):
    """sistemas: {nome: {nivel: erro absoluto médio por quadro}} (menor é melhor)."""
    nomes = list(sistemas)
    cores = ["#9a9a9a", "#2b7a5b", "#1b4f8a", "#c0392b"][: len(nomes)]
    fig, eixos = plt.subplots(1, 3, figsize=(13, 4.4))
    for ax, k in zip(eixos, NIVEIS, strict=True):
        vals = [sistemas[n][k] for n in nomes]
        bars = ax.bar(range(len(vals)), vals, color=cores)
        for b, v in zip(bars, vals, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
        ax.set_xticks(range(len(vals)), [n.replace(" + ", "\n+ ") for n in nomes], fontsize=7)
        ax.set_title(f"{k} — erro por quadro (aves)")
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(titulo)
    fig.tight_layout()
    fig.savefig(destino, dpi=140)
    plt.close(fig)
