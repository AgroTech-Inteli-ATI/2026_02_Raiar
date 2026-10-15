"""Densificação temporal dos rótulos de treino por fluxo óptico.

Entre dois quadros de treino anotados (1 s de distância), extraímos quadros
intermediários a cada 0,25 s e levamos até eles os pontos do quadro anotado mais
próximo (no máximo 0,5 s). Só usamos instantes da janela de treino, para não
vazar informação para validação e teste.
"""

from __future__ import annotations

import json

import numpy as np

from .annotate import ROOT, extract, frame_name, propagate, save_points
from .boxes import BOXES

TRAIN = json.loads((ROOT / "configs" / "dataset-splits.json").read_text(encoding="utf-8"))["treino"]

TRAIN_WINDOWS = {"v3": (0.0, 6.0), "v2": (0.0, 4.5)}
STEP = 0.25


def densify() -> list[str]:
    created = []
    for video, (t0, t1) in TRAIN_WINDOWS.items():
        anchors = sorted(float(f.split("_t")[1]) / 1000 for f in TRAIN if f.startswith(video + "_"))
        times = [round(t, 2) for t in np.arange(t0, t1 + 1e-6, STEP)]
        for t in times:
            if any(abs(t - a) < 1e-6 for a in anchors):
                continue
            near = min(anchors, key=lambda a: abs(a - t))
            if abs(near - t) > 0.5 + 1e-6:
                continue
            extract(video, [t])
            dst = frame_name(video, t)
            pts = propagate(frame_name(video, near), dst)
            src = frame_name(video, near)
            save_points(dst, pts, {"propagated_from": src, "densificado": True})
            # As caixas acompanham o deslocamento do ponto da âncora.
            anchor = json.loads((BOXES / f"{src}.json").read_text(encoding="utf-8"))
            recs = []
            for (x, y), r in zip(pts, anchor, strict=True):
                dx, dy = x - r["point"][0], y - r["point"][1]
                b = r["box"]
                box = [round(b[0] + dx, 1), round(b[1] + dy, 1), round(b[2] + dx, 1), round(b[3] + dy, 1)]
                recs.append({"point": [x, y], "box": box, "source": r["source"] + "-propagada"})
            (BOXES / f"{dst}.json").write_text(json.dumps(recs, indent=1), encoding="utf-8")
            created.append(dst)
    return created


if __name__ == "__main__":
    out = densify()
    print(len(out), "quadros densificados")
    print(" ".join(out))
