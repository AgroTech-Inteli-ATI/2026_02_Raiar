"""Comparação quantitativa e visual dos pipelines de pré-processamento.

Para cada pipeline e nível, mede nos quadros de validação e treino:

- separabilidade ave x fundo (d de Cohen) na luminância L* e distância cromática
  média no plano a*b* entre o interior das caixas de aves e um anel de fundo ao redor;
- entropia, contraste RMS e nitidez (variância do Laplaciano) dentro da ROI.

Gera também as figuras usadas na documentação.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from labeling.annotate import FRAMES
from preprocessing.pipeline import PIPELINES, image_stats, run
from preprocessing.roi import LEVELS, LevelROI
from training.dataset import load_boxes, load_split

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT.parent.parent / "docs" / "static" / "img" / "visao-computacional"
REPORT = ROOT / "reports" / "preprocessamento.json"


def bird_background_separability(img: np.ndarray, boxes: np.ndarray, roi: LevelROI, level: str):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lvl_mask = roi.mask(level)
    d_l, d_ab = [], []
    h, w = img.shape[:2]
    occupied = np.zeros((h, w), np.uint8)
    for x1, y1, x2, y2 in boxes.astype(int):
        cv2.rectangle(occupied, (x1, y1), (x2, y2), 255, -1)
    for x1, y1, x2, y2 in boxes:
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if roi.level_of(cx, cy) != level:
            continue
        bw, bh = x2 - x1, y2 - y1
        ix1, iy1 = int(cx - bw * 0.25), int(cy - bh * 0.25)
        ix2, iy2 = int(cx + bw * 0.25), int(cy + bh * 0.25)
        ox1, oy1 = max(int(x1 - bw * 0.4), 0), max(int(y1 - bh * 0.4), 0)
        ox2, oy2 = min(int(x2 + bw * 0.4), w - 1), min(int(y2 + bh * 0.4), h - 1)
        inner = lab[iy1:iy2, ix1:ix2].reshape(-1, 3)
        ring_mask = np.zeros((h, w), np.uint8)
        ring_mask[oy1:oy2, ox1:ox2] = 255
        ring_mask[occupied > 0] = 0
        ring_mask[lvl_mask == 0] = 0
        ring = lab[ring_mask > 0]
        if len(inner) < 4 or len(ring) < 8:
            continue
        pooled = np.sqrt((inner[:, 0].var() + ring[:, 0].var()) / 2) + 1e-6
        d_l.append(abs(inner[:, 0].mean() - ring[:, 0].mean()) / pooled)
        d_ab.append(float(np.linalg.norm(inner[:, 1:].mean(0) - ring[:, 1:].mean(0))))
    return (float(np.mean(d_l)) if d_l else float("nan"), float(np.mean(d_ab)) if d_ab else float("nan"), len(d_l))


def evaluate_pipelines(frames: list[str]) -> dict:
    roi = LevelROI.load()
    res = {}
    for name in PIPELINES:
        acc = {k: {"d_L": [], "d_ab": [], "entropia": [], "contraste_rms": [], "nitidez": [], "n": 0} for k in LEVELS}
        for f in frames:
            img = run(cv2.imread(str(FRAMES / f"{f}.png")), name)
            boxes = load_boxes(f)
            for k in LEVELS:
                dl, dab, n = bird_background_separability(img, boxes, roi, k)
                st = image_stats(img, roi.mask(k))
                if n:
                    acc[k]["d_L"].append(dl)
                    acc[k]["d_ab"].append(dab)
                    acc[k]["n"] += n
                for s in ("entropia", "contraste_rms", "nitidez"):
                    acc[k][s].append(st[s])
        res[name] = {k: {m: (float(np.nanmean(v)) if isinstance(v, list) and v else v) for m, v in d.items()} for k, d in acc.items()}
        print(name, {k: round(res[name][k]["d_L"], 3) for k in LEVELS})
    return res


def comparison_figure(frame: str, out: Path, names=("original", "clahe-lab", "msrcr", "gama-adaptativa", "gama+clahe+guiado+cromatico")):
    """Quadro comparativo: linhas = pipelines, colunas = recortes de N0, N1 e N2."""
    img = cv2.imread(str(FRAMES / f"{frame}.png"))
    crops = {"N0": (520, 230, 760, 420), "N1": (150, 380, 420, 576), "N2": (0, 300, 300, 520)}
    if frame.startswith("v2"):
        crops = {"N0": (420, 300, 700, 576), "N1": (200, 380, 480, 576), "N2": (0, 140, 300, 340)}
    rows = []
    for name in names:
        proc = run(img, name)
        tiles = []
        for k in LEVELS:
            x1, y1, x2, y2 = crops[k]
            t = cv2.resize(proc[y1:y2, x1:x2], (300, 220), interpolation=cv2.INTER_AREA)
            cv2.rectangle(t, (0, 0), (299, 219), (255, 255, 255), 1)
            tiles.append(t)
        label = np.full((220, 170, 3), 255, np.uint8)
        for j, part in enumerate(name.split("+")):
            cv2.putText(label, part, (8, 95 + 24 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
        rows.append(np.hstack([label, *tiles]))
    head = np.full((34, rows[0].shape[1], 3), 255, np.uint8)
    for j, k in enumerate(LEVELS):
        cv2.putText(head, {"N0": "N0 - piso", "N1": "N1 - meio", "N2": "N2 - plataforma"}[k], (170 + 300 * j + 90, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 1, cv2.LINE_AA)
    fig = np.vstack([head, *rows])
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), fig)


def roi_figure(out: Path):
    roi = LevelROI.load()
    a = roi.draw(cv2.imread(str(FRAMES / "v3_t00000.png")))
    b = roi.draw(cv2.convertScaleAbs(cv2.imread(str(FRAMES / "v2_t00000.png")), alpha=1.6, beta=10))
    masked = roi.apply_mask(cv2.imread(str(FRAMES / "v3_t00000.png")))
    top = np.hstack([cv2.resize(a, (640, 360)), cv2.resize(b, (640, 360))])
    bottom = np.hstack([cv2.resize(masked, (640, 360)), np.full((360, 640, 3), 255, np.uint8)])
    legend = bottom[:, 640:]
    items = [("N0 - piso (cama/maravalha)", (255, 200, 0)), ("N1 - meio, sob a borda da mesa", (200, 0, 200)), ("N2 - plataforma superior", (0, 170, 255)), ("Divisoria verde fixa (fundo)", (0, 220, 0)), ("Cinza: fora da ROI (mascarado)", (114, 114, 114))]
    for j, (txt, col) in enumerate(items):
        cv2.rectangle(legend, (30, 60 + 50 * j), (60, 85 + 50 * j), col, -1)
        cv2.putText(legend, txt, (75, 80 + 50 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
    cv2.imwrite(str(out), np.vstack([top, bottom]))


def main():
    frames = load_split("train") + load_split("val")
    res = evaluate_pipelines(frames)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    comparison_figure("v3_t07500", FIG / "comparacao-pre-processamento-dia.png")
    comparison_figure("v2_t07500", FIG / "comparacao-pre-processamento-noite.png")
    roi_figure(FIG / "roi-niveis-c1.png")


if __name__ == "__main__":
    main()
