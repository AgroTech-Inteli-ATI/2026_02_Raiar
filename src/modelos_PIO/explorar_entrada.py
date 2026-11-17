"""Varre formas de alimentar o YOLOPIO (escala, fatias, realce, máscara) SEM alterar os pesos.

Motivo: a 640 px o modelo quase não responde às galinhas da C1 (escore máximo 0,013).
Para cada variante, mede o erro de contagem por nível com limiar por nível ajustado por
validação cruzada entre quadros (ver rodar_experimentos.py).
Uso: python explorar_entrada.py --pesos best.pt --video VIDEO.mp4 --saida resultados/pos_processamento
"""

import argparse
import json
from pathlib import Path

import cv2
from ultralytics import YOLO

from pos_processamento.deteccoes import GT, detectar, detectar_fatiado, extrair_quadro
from pos_processamento.niveis import NiveisROI
from pos_processamento.posprocessamento import Config
from rodar_experimentos import validacao_cruzada


def cinza(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)


def clahe(im, clip=3.0):
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    m = YOLO(a.pesos)
    roi = NiveisROI()
    ms = [int(k) for k in GT["quadros"]]
    quadros = {t: extrair_quadro(a.video, t) for t in ms}
    preps = {
        "original": lambda im: im,
        "ROI cinza-114": lambda im: roi.mascarar(im),
        "CLAHE": clahe,
        "tons de cinza": cinza,
    }
    envios = {
        "640 inteiro": lambda im: detectar(m, im, imgsz=640, conf=0.01),
        "1024 inteiro": lambda im: detectar(m, im, imgsz=1024, conf=0.01),
        "1280 inteiro": lambda im: detectar(m, im, imgsz=1280, conf=0.01),
        "fatias 2x2": lambda im: detectar_fatiado(m, im, (2, 2), 640, conf=0.01),
        "fatias 3x2": lambda im: detectar_fatiado(m, im, (3, 2), 640, conf=0.01),
        "fatias 3x3": lambda im: detectar_fatiado(m, im, (3, 3), 640, conf=0.01),
        "fatias 4x3": lambda im: detectar_fatiado(m, im, (4, 3), 640, conf=0.01),
        "fatias 4x4": lambda im: detectar_fatiado(m, im, (4, 4), 640, conf=0.01),
    }
    res = []
    for pn, pf in preps.items():
        prep = {t: pf(im) for t, im in quadros.items()}
        for en, ef in envios.items():
            det = {t: ef(im) for t, im in prep.items()}
            r = validacao_cruzada(det, roi, Config(), ajusta_lim=True)
            mm = r["metricas"]
            lin = {
                "preparo": pn,
                "entrada": en,
                **{k: mm[k]["MAE"] for k in ("N0", "N1", "N2", "total")},
                "vies_total": mm["total"]["vies"],
                "max_conf": float(max(d[1].max() if len(d[1]) else 0 for d in det.values())),
                "limiares": [c.limiar for c in r["configs"]],
            }
            res.append(lin)
            print(
                f"{pn:14s} {en:13s} MAE N0 {lin['N0']:6.1f} N1 {lin['N1']:5.1f} N2 {lin['N2']:5.1f} total {lin['total']:6.1f} (viés {lin['vies_total']:+6.1f}) maxconf {lin['max_conf']:.2f}",
                flush=True,
            )
    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    (out / "exploracao_entrada.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    principal()
