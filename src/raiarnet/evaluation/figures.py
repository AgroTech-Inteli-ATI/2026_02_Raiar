"""Figuras da documentação: diagrama da arquitetura, curvas e gráficos do benchmark."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT.parent.parent / "docs" / "static" / "img" / "visao-computacional"
INK = "#1f2a30"
C_BACK, C_NECK, C_HEAD, C_OUT = "#dbe9f6", "#e8def8", "#fde7c8", "#d9f2e3"


def _box(ax, x, y, w, h, text, color, fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=color, ec=INK, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK)


def _arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, lw=1, color=INK))


def architecture_diagram(out: Path = FIG / "arquitetura-raiarnet.png") -> None:
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=150)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    _box(ax, 0.1, 2.7, 1.5, 0.9, "Quadro C1\n1024 × 576\n(realçado e\nmascarado)", "#ffffff", 8)
    stages = [
        ("SPD-Conv ↓2\nCSP (32)", "/2"),
        ("SPD-Conv ↓2\nCSP (64)\nCoordAtt", "/4  P2"),
        ("SPD-Conv ↓2\nCSP ×2 (96)\nCoordAtt", "/8  P3"),
        ("SPD-Conv ↓2\nCSP (128)\nSPPF + CoordAtt", "/16  P4"),
    ]
    ys = [5.0, 3.75, 2.5, 1.25]
    for (txt, lab), y in zip(stages, ys, strict=True):
        _box(ax, 2.2, y - 0.45, 2.0, 0.95, txt, C_BACK, 8)
        ax.text(4.3, y, lab, fontsize=8, va="center", color="#4a5a63")
    _arrow(ax, 1.6, 3.15, 2.2, 5.0)
    for y1, y2 in zip(ys[:-1], ys[1:], strict=True):
        _arrow(ax, 3.2, y1 - 0.45, 3.2, y2 + 0.5)
    ax.text(3.2, 5.75, "Backbone (do zero)", ha="center", fontsize=10, weight="bold", color=INK)
    _box(ax, 5.2, 1.0, 2.3, 4.4, "BiFPN × 2\n\ncaminho descendente\n+ ascendente\n\nfusão com pesos\nnormalizados\n\nconvoluções\nseparáveis", C_NECK, 9)
    ax.text(6.35, 5.75, "Pescoço", ha="center", fontsize=10, weight="bold", color=INK)
    for y in ys[1:]:
        _arrow(ax, 4.75, y, 5.2, y)
    _box(ax, 8.1, 3.4, 2.1, 1.7, "Cabeça de detecção\n(stride 4)\n\nheatmap de centros\ntamanho (w, h)\ndeslocamento", C_HEAD, 8)
    _box(ax, 8.1, 1.1, 2.1, 1.6, "Cabeça de densidade\n(stride 4)\n\nmapa D ≥ 0\nΣD = nº de aves", C_HEAD, 8)
    ax.text(9.15, 5.75, "Cabeças", ha="center", fontsize=10, weight="bold", color=INK)
    _arrow(ax, 7.5, 3.75, 8.1, 4.25)
    _arrow(ax, 7.5, 2.5, 8.1, 1.9)
    _box(ax, 10.8, 3.4, 2.1, 1.7, "Picos locais 3×3\n(sem NMS entre caixas)\n→ aves identificadas", C_OUT, 8)
    _box(ax, 10.8, 1.1, 2.1, 1.6, "Contagem por nível\nfusão sensível à\noclusão + Kalman\n→ N0, N1, N2", C_OUT, 8)
    ax.text(11.85, 5.75, "Saídas", ha="center", fontsize=10, weight="bold", color=INK)
    _arrow(ax, 10.2, 4.25, 10.8, 4.25)
    _arrow(ax, 10.2, 1.9, 10.8, 1.9)
    _arrow(ax, 11.85, 3.4, 11.85, 2.7)
    ax.text(6.5, 0.3, "Perdas: focal no heatmap + L1 (tamanho e deslocamento) + Wise-IoU + MSE da densidade + consistência de contagem", ha="center", fontsize=8.5, color="#4a5a63")
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    architecture_diagram()


def training_curves(history: Path, out: Path = FIG / "curvas-treino-raiarnet.png") -> None:
    h = json.loads(history.read_text(encoding="utf-8"))
    it = [r["iter"] for r in h]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), dpi=150)
    axes[0].plot(it, [r["loss"]["total"] for r in h], "o-", color="#3b6ea8", label="perda total (treino)")
    axes[0].plot(it, [r["loss"]["hm"] for r in h], "s--", color="#c46b2b", label="focal do heatmap (treino)")
    axes[0].set_xlabel("iteração")
    axes[0].set_ylabel("perda")
    axes[0].legend(frameon=False)
    axes[0].grid(alpha=0.3)
    for key, lab, st in (("mAP50", "mAP@50", "o-"), ("mAP50_95", "mAP@50:95", "s-"), ("f1", "F1", "^-")):
        axes[1].plot(it, [r["det"][key] for r in h], st, label=lab)
    axes[1].set_xlabel("iteração")
    axes[1].set_ylabel("validação")
    axes[1].set_ylim(0, 1)
    axes[1].legend(frameon=False)
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def count_series(csv_path: Path, gt: dict, out: Path = FIG / "serie-contagem-video-dia.png") -> None:
    import csv

    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    t = [float(r["tempo_s"]) for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), dpi=150)
    for ax, k in zip(axes, ("N0", "N1", "N2"), strict=True):
        ax.plot(t, [float(r[f"{k}_fused"]) for r in rows], color="#9db7d5", lw=1, label="por quadro (fusão)")
        ax.plot(t, [float(r[f"{k}_kalman"]) for r in rows], color="#1f4e79", lw=2, label="filtro de Kalman")
        gx = [g[0] for g in gt[k]]
        gy = [g[1] for g in gt[k]]
        ax.plot(gx, gy, "o", color="#c0392b", ms=5, label="anotação manual")
        ax.axvspan(9, 11.9, color="#f2e6d0", alpha=0.6, lw=0)
        ax.set_title(k)
        ax.set_xlabel("tempo no vídeo (s)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("aves no nível")
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
