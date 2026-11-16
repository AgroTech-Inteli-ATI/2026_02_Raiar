"""Ajuste final dos limiares por nível (grade 4x3) usando todos os quadros do vídeo diurno.

Gera resultados/pos_processamento/config_final.json. O desempenho que reportamos vem da
validação temporal (avaliar_video_inteiro.py); este ajuste usa todos os quadros e, por isso,
seus números são otimistas (dentro da amostra).
"""

import argparse
import json
from pathlib import Path

from ultralytics import YOLO

from avaliar_video_inteiro import ajustar, extrair_deteccoes, pre_niveis
from pos_processamento.niveis import NiveisROI

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--pasta", required=True)
    a = ap.parse_args()
    roi = NiveisROI()
    dets, tempos = extrair_deteccoes(a.video, YOLO(a.pesos), roi, (4, 3))
    cfg = ajustar(pre_niveis(dets, roi), tempos, list(range(len(dets))))
    (Path(a.pasta) / "config_final.json").write_text(
        json.dumps(
            {
                "grade": [4, 3],
                "limiar": cfg.limiar,
                "kalman": {"q": 0.5, "r": 4.0},
                "quadros_ajuste": len(dets),
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(cfg.limiar)
