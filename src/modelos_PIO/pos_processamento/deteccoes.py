"""Extrai quadros do vídeo de validação e guarda as detecções BRUTAS do YOLOPIO.

O modelo roda uma única vez, com limiar baixo (0,05). As caixas ficam em cache
(`.npz`), e todo o pós-processamento é testado em cima delas. Assim, o YOLOPIO
não é tocado e cada experimento de pós-processamento leva milissegundos.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent
GT = json.loads((AQUI / "gt_c1.json").read_text(encoding="utf-8"))
CONF_BRUTA = 0.05


def extrair_quadro(video: Path | str, ms: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, ms)
    ok, img = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Não consegui ler o quadro em {ms} ms de {video}")
    return img


def detectar(modelo, img: np.ndarray, imgsz: int = 640, conf: float = CONF_BRUTA, **kw):
    """Inferência do YOLOPIO sem alterar pesos. Devolve (caixas xyxy, confianças)."""
    r = modelo.predict(img, imgsz=imgsz, conf=conf, max_det=1000, verbose=False, device="cpu", **kw)[0]
    return r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()


def cache_quadros(
    video, modelo, destino: Path, imgsz: int = 640, instantes=None, mascarar=None, **kw
) -> dict:
    """Roda o modelo nos quadros com anotação e salva {ms: (caixas, confianças)}."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    out = {}
    for ms in instantes or [int(k) for k in GT["quadros"]]:
        img = extrair_quadro(video, ms)
        if mascarar is not None:
            img = mascarar(img)
        out[ms] = detectar(modelo, img, imgsz=imgsz, **kw)
    np.savez_compressed(
        destino,
        **{f"b{ms}": v[0] for ms, v in out.items()},
        **{f"s{ms}": v[1] for ms, v in out.items()},
    )
    return out


def carregar_cache(caminho: Path) -> dict:
    z = np.load(caminho)
    return {int(k[1:]): (z[k], z["s" + k[1:]]) for k in z.files if k.startswith("b")}


def detectar_fatiado(
    modelo,
    img: np.ndarray,
    grade=(2, 2),
    imgsz: int = 640,
    sobreposicao: float = 0.2,
    conf: float = CONF_BRUTA,
    iou_fusao: float = 0.5,
):
    """Roda o YOLOPIO em fatias com sobreposição (como o SAHI) e funde as caixas com NMS.

    Cada fatia é ampliada para `imgsz`, então aves pequenas do fundo ficam maiores para o
    modelo. Os pesos não mudam; só a forma de alimentar o modelo.
    """
    import torch
    from torchvision.ops import nms

    h, w = img.shape[:2]
    gx, gy = grade
    tw, th = w / (gx - (gx - 1) * sobreposicao), h / (gy - (gy - 1) * sobreposicao)
    caixas, confs = [], []
    for j in range(gy):
        for i in range(gx):
            x0 = int(round(i * tw * (1 - sobreposicao)))
            y0 = int(round(j * th * (1 - sobreposicao)))
            x1, y1 = min(int(x0 + tw), w), min(int(y0 + th), h)
            b, s = detectar(modelo, img[y0:y1, x0:x1], imgsz=imgsz, conf=conf)
            if len(b):
                b = b + np.array([x0, y0, x0, y0], np.float32)
                caixas.append(b)
                confs.append(s)
    if not caixas:
        return np.zeros((0, 4), np.float32), np.zeros(0, np.float32)
    b, s = np.concatenate(caixas), np.concatenate(confs)
    keep = nms(torch.from_numpy(b), torch.from_numpy(s), iou_fusao).numpy()
    return b[keep], s[keep]
