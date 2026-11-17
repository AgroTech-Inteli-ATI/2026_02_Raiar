"""Reproduz o treino do YOLOPIO exatamente com a receita do notebook YOLOPIO.ipynb.

Só existe porque os pesos do colega (best.pt) não estavam disponíveis. O modelo é o
mesmo (YOLO11n, 1 classe, 640 px, lote 4, 30 épocas, paciência 8, semente 42);
diferem apenas o dispositivo (CPU) e `workers` (para acelerar o carregamento).
Uso:  python treinar_yolopio.py [--retomar]
"""

import sys
from pathlib import Path

from ultralytics import YOLO

PASTA = Path(__file__).resolve().parent
DADOS = PASTA / "midias" / "PIO" / "data"
YAML = DADOS / "dataset_local.yaml"
PESOS_INICIAIS = PASTA / "pesos_iniciais" / "yolo11n.pt"
EXECUCOES = PASTA / "resultados" / "treinos_yolo11"
NOME = "pio_yolo11n"

YAML.write_text(
    f"path: '{DADOS.resolve().as_posix()}'\ntrain: images/train\nval: images/val\nnames:\n  0: galinha\n",
    encoding="utf-8",
)
if "--retomar" in sys.argv:
    YOLO(str(EXECUCOES / NOME / "weights" / "last.pt")).train(resume=True)
else:
    YOLO(str(PESOS_INICIAIS)).train(
        data=str(YAML),
        epochs=30,
        patience=8,
        imgsz=640,
        batch=4,
        device="cpu",
        workers=6,
        seed=42,
        project=str(EXECUCOES),
        name=NOME,
        exist_ok=False,
        save=True,
        plots=True,
    )
