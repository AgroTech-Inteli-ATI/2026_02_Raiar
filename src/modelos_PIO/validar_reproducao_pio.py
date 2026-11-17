"""Confere a reprodução do YOLOPIO na validação PIO (452 imagens): detecção e erro de contagem.

Mesmo protocolo da seção 7 do notebook YOLOPIO.ipynb (conf 0,25, max_det 1000, 640 px).
Uso: python validar_reproducao_pio.py --pesos best.pt --saida relatorios/reproducao-pio.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
from ultralytics import YOLO

AQUI = Path(__file__).resolve().parent
PIO = AQUI / "midias" / "PIO" / "data"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    m = YOLO(a.pesos)
    yaml = PIO / "dataset_local.yaml"
    v = m.val(data=str(yaml), split="val", imgsz=640, batch=4, device="cpu", workers=4, plots=False, verbose=False)
    reais, prev = [], []
    for r in m.predict(
        source=str(PIO / "images" / "val"), stream=True, imgsz=640, conf=0.25, max_det=1000, device="cpu", verbose=False
    ):
        rot = PIO / "labels" / "val" / f"{Path(r.path).stem}.txt"
        n = 0
        for linha in rot.read_text().splitlines():
            c = linha.split()
            if len(c) == 5 and float(c[3]) > 0 and float(c[4]) > 0:
                n += 1
        reais.append(n)
        prev.append(len(r.boxes))
    reais, prev = np.array(reais, float), np.array(prev, float)
    d = prev - reais
    out = {
        "precisao": float(v.box.mp), "recall": float(v.box.mr), "mAP50": float(v.box.map50), "mAP50_95": float(v.box.map),
        "MAE": float(np.abs(d).mean()), "RMSE": float(np.sqrt((d**2).mean())),
        "MAPE": float(100 * np.mean(np.abs(d) / reais)), "vies": float(d.mean()),
        "total_anotado": int(reais.sum()), "total_detectado": int(prev.sum()), "imagens": len(reais),
    }
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
