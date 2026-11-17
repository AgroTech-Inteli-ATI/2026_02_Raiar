"""Testa o YOLOPIO (sem alterar pesos) no vídeo RPReplay cortado a partir de 12 s (CAM 7, galpão de cria).

Não há contagem manual nem polígonos de nível para esta câmera, então NÃO medimos erro de contagem.
Medimos o que dá para medir sem referência: contagem ao longo do tempo, estabilidade entre quadros,
fração das caixas que cai no piso (proxy de falsos positivos em parede, canos e grade) e a sensibilidade
ao limiar. Máscara de piso por cor (cama laranja/bege) no lugar da ROI da C1.
Uso: python testar_video_novo.py --pesos best.pt --video rpreplay_cortado_12s.mp4 --saida ../../docs/static/img/pos-processamento
"""

import argparse
import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ultralytics import YOLO

from pos_processamento.deteccoes import detectar, detectar_fatiado
from pos_processamento.temporal import suavizar_serie

GRADE = (6, 3)
PASSO_S = 2.0
# Textos da interface do DVR (data/hora, "CAM 7", "7/19") que viram falsos positivos.
RETANGULOS_UI = ((1560, 0, 1920, 70), (1700, 830, 1920, 888), (900, 840, 1020, 888))


def limpar_ui(img):
    out = img.copy()
    for x0, y0, x1, y1 in RETANGULOS_UI:
        out[y0:y1, x0:x1] = 114
    return out


def mascara_piso(img):
    """Cama (laranja/bege) por cor HSV, fechada e dilatada; exclui parede azul, canos e grade."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[:, :, 0] >= 5) & (hsv[:, :, 0] <= 32) & (hsv[:, :, 1] >= 35) & (hsv[:, :, 2] >= 70)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))


def no_piso(b, mask):
    if len(b) == 0:
        return np.zeros(0, bool)
    cx = np.clip(((b[:, 0] + b[:, 2]) / 2).astype(int), 0, mask.shape[1] - 1)
    cy = np.clip(((b[:, 1] + b[:, 3]) / 2).astype(int), 0, mask.shape[0] - 1)
    return mask[cy, cx] > 0


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--saida", required=True, help="pasta das figuras")
    ap.add_argument("--relatorio", default="relatorios/video-novo.json")
    a = ap.parse_args()
    m = YOLO(a.pesos)
    cap = cv2.VideoCapture(a.video)
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    tempos = np.arange(1.0, dur - 0.5, PASSO_S)  # 1 s: evita o quadro exato da troca de câmera (12,0 s)
    limiares = (0.1, 0.25, 0.4)
    orig, fat_sem, fat_piso = [], [], {t: [] for t in limiares}
    frac_piso, exemplo = [], None
    for t in tempos:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, img = cap.read()
        if not ok:
            break
        img = limpar_ui(img)
        b0, s0 = detectar(m, img, imgsz=640, conf=0.05)
        orig.append(int((s0 >= 0.25).sum()))
        b, s = detectar_fatiado(m, img, GRADE, 640, conf=0.05)
        mask = mascara_piso(img)
        dentro = no_piso(b, mask)
        fat_sem.append(int((s >= 0.25).sum()))
        for th in limiares:
            fat_piso[th].append(int(((s >= th) & dentro).sum()))
        sel = s >= 0.25
        frac_piso.append(float(dentro[sel].mean()) if sel.any() else 0.0)
        if exemplo is None and t >= 46:
            exemplo = (img, b0[s0 >= 0.25], b[(s >= 0.25) & dentro], b[(s >= 0.25) & ~dentro], mask)
    n = len(orig)
    tempos = tempos[:n]
    sel = np.array(fat_piso[0.25], float)
    kal = suavizar_serie(sel)
    osc = lambda v: float(np.mean(np.abs(np.diff(v))))  # noqa: E731
    res = {
        "quadros": n, "passo_s": PASSO_S, "grade": list(GRADE), "duracao_s": float(dur),
        "original_640_conf025": {"media": float(np.mean(orig)), "maximo": int(np.max(orig))},
        "fatias_sem_mascara_conf025": {"media": float(np.mean(fat_sem)), "oscilacao": osc(fat_sem)},
        "fatias_piso": {str(th): {"media": float(np.mean(v)), "desvio": float(np.std(v)), "oscilacao": osc(v)} for th, v in fat_piso.items()},
        "fatias_piso_kalman_conf025": {"media": float(np.mean(kal)), "oscilacao": osc(kal)},
        "fracao_das_caixas_no_piso_sem_mascara": float(np.mean(frac_piso)),
        "serie": {"t": tempos.tolist(), "original": orig, "fatias_sem_mascara": fat_sem,
                  "fatias_piso_025": fat_piso[0.25], "kalman": kal},
    }
    Path(a.relatorio).parent.mkdir(parents=True, exist_ok=True)
    Path(a.relatorio).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(tempos, orig, color="#9a9a9a", lw=2, label="YOLOPIO original (640 px, conf 0,25)")
    ax.plot(tempos, fat_sem, color="#c0392b", alpha=0.7, label="fatias 6x3, sem máscara")
    ax.plot(tempos, fat_piso[0.25], color="#2b7a5b", alpha=0.45, label="fatias 6x3 + máscara de piso")
    ax.plot(tempos, kal, color="#2b7a5b", lw=2.4, label="+ filtro de Kalman")
    ax.set_xlabel("tempo no vídeo cortado (s); 0 s equivale a 12 s do vídeo original")
    ax.set_ylabel("aves contadas por quadro")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(saida / "video-novo-serie.png", dpi=140)
    plt.close(fig)
    img, c0, cp, cf, mask = exemplo
    v1, v2 = img.copy(), img.copy()
    for bb in c0:
        cv2.rectangle(v1, (int(bb[0]), int(bb[1])), (int(bb[2]), int(bb[3])), (0, 255, 0), 2)
    for bb in cp:
        cv2.rectangle(v2, (int(bb[0]), int(bb[1])), (int(bb[2]), int(bb[3])), (0, 255, 0), 1)
    for bb in cf:
        cv2.rectangle(v2, (int(bb[0]), int(bb[1])), (int(bb[2]), int(bb[3])), (0, 0, 255), 1)
    for v, txt in ((v1, f"ORIGINAL: {len(c0)} aves"), (v2, f"FATIAS + PISO (verde): {len(cp)} | descartadas fora do piso (vermelho): {len(cf)}")):
        cv2.rectangle(v, (0, 0), (1100, 40), (25, 25, 25), -1)
        cv2.putText(v, txt, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(saida / "video-novo-antes-depois.jpg"), cv2.resize(np.vstack([v1, v2]), None, fx=0.6, fy=0.6), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(json.dumps({k: v for k, v in res.items() if k != "serie"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
