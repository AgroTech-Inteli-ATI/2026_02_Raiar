"""Gera as detecções BRUTAS do YOLOPIO (conf 0,05) em cache, para três formas de alimentar o modelo.

Uso: python gerar_deteccoes.py --pesos best.pt --video VIDEO.mp4 --saida resultados/pos_processamento
Estratégias: '640' (padrão do notebook) e 'roi_GxL' (máscara de ROI cinza + fatias GxL com sobreposição).
"""

import argparse
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from pos_processamento.deteccoes import GT, detectar, detectar_fatiado, extrair_quadro
from pos_processamento.niveis import NiveisROI


def salvar(destino, dados):
    np.savez_compressed(
        destino,
        **{f"b{k}": v[0] for k, v in dados.items()},
        **{f"s{k}": v[1] for k, v in dados.items()},
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    m = YOLO(a.pesos)
    ms = [int(k) for k in GT["quadros"]]
    quadros = {t: extrair_quadro(a.video, t) for t in ms}
    roi = NiveisROI()
    estrategias = {"640": (False, lambda im: detectar(m, im, imgsz=640, conf=0.01))}
    for g in ((3, 2), (3, 3), (4, 3), (4, 4)):
        estrategias[f"roi_{g[0]}x{g[1]}"] = (
            True,
            lambda im, g=g: detectar_fatiado(m, im, g, 640, conf=0.01),
        )
    for nome, (mascarar, fn) in estrategias.items():
        dados = {t: fn(roi.mascarar(im) if mascarar else im) for t, im in quadros.items()}
        salvar(out / f"deteccoes_{nome}.npz", dados)
        print(nome, {t: len(v[0]) for t, v in dados.items()})
