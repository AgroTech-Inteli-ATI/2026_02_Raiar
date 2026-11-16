"""Avalia o pós-processamento em TODOS os quadros do vídeo diurno, não só nos 6 anotados.

Referência fraca: a documentação da equipe (niveis-e-regra-de-contagem.md) registra que, nos
12 s do vídeo diurno, a contagem manual de aves na ROI variou de 122 a 138. Usamos essa
faixa como verdade aproximada do TOTAL (N0+N1+N2) em cada quadro amostrado, além das contagens
por nível dos 6 quadros anotados. Validação TEMPORAL: ajusta-se numa metade do vídeo (0–6 s)
e mede-se na outra (6–12 s), e vice-versa.
Uso: python avaliar_video_inteiro.py --pesos best.pt --video VIDEO.mp4 --pasta resultados/pos_processamento
"""

import argparse
import itertools
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from pos_processamento.deteccoes import GT, detectar_fatiado
from pos_processamento.niveis import NIVEIS, NiveisROI
from pos_processamento.posprocessamento import Config, processar
from pos_processamento.temporal import suavizar_serie

FAIXA = (122, 138)
CENTRO = 130.0
LIMIARES = [0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6]
GRADES = [(3, 2), (3, 3), (4, 3), (4, 4)]


def extrair_deteccoes(video, m, roi, grade, passo=3):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    dets, tempos, i = [], [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % passo == 0:
            dets.append(detectar_fatiado(m, roi.mascarar(fr), grade, 640, conf=0.01))
            tempos.append(i / fps)
        i += 1
    return dets, np.array(tempos)


def pre_niveis(dets, roi):
    """Atribui o nível de cada caixa UMA vez (o custo está nos testes de polígono)."""
    out = []
    for b, s in dets:
        r = processar(b, s, Config(limiar=dict.fromkeys(NIVEIS, 0.0)), roi)
        out.append((r["scores"], r["niveis"]))
    return out


def contar_pre(pre, lim):
    return np.array([[float(((s >= lim[k]) & (nv == k)).sum()) for k in NIVEIS] for s, nv in pre])


def contagens(pre, cfg, roi=None):
    return contar_pre(pre, cfg.limiar)


def perda(c, tempos, idx):
    """Erro do total contra a faixa fraca (0 dentro da faixa) + erro por nível nos quadros anotados."""
    tot = c[idx].sum(1)
    fora = np.where(tot < FAIXA[0], FAIXA[0] - tot, np.where(tot > FAIXA[1], tot - FAIXA[1], 0.0))
    e = float(fora.mean())
    conj = set(idx)
    for ms, g in GT["quadros"].items():
        j = int(np.argmin(np.abs(tempos - int(ms) / 1000)))
        if j in conj:
            e += 0.5 * sum(abs(c[j, n] - g[k]) for n, k in enumerate(NIVEIS) if k != "N0") / 2
    return e


def ajustar(pre, tempos, idx):
    melhor = None
    sub = [pre[i] for i in idx]
    for t0, t1, t2 in itertools.product(LIMIARES, LIMIARES, LIMIARES):
        lim = {"N0": t0, "N1": t1, "N2": t2}
        full = np.zeros((len(pre), 3))
        full[idx] = contar_pre(sub, lim)
        p = perda(full, tempos, list(idx))
        if melhor is None or p < melhor[0]:
            melhor = (p, Config(limiar=lim))
    return melhor[1]


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--pasta", required=True)
    a = ap.parse_args()
    roi = NiveisROI()
    m = YOLO(a.pesos)
    pasta = Path(a.pasta)
    saida = {}
    for grade in GRADES:
        dets, tempos = extrair_deteccoes(a.video, m, roi, grade)
        pre = pre_niveis(dets, roi)
        n = len(dets)
        h1, h2 = list(range(n // 2)), list(range(n // 2, n))
        res = {}
        # ajuste temporal alternado
        tot_prev = np.zeros(n)
        cfgs = []
        for fit, teste in ((h1, h2), (h2, h1)):
            cfg = ajustar(pre, tempos, fit)
            cfgs.append(cfg.limiar)
            c = contagens([pre[i] for i in teste], cfg)
            tot_prev[teste] = c.sum(1)
        dentro = float(np.mean((tot_prev >= FAIXA[0]) & (tot_prev <= FAIXA[1])))
        mae = float(np.mean(np.abs(tot_prev - CENTRO)))
        suave = np.array(suavizar_serie(tot_prev))
        res["bruto"] = {"MAE_vs_130": mae, "dentro_da_faixa": dentro}
        res["kalman"] = {
            "MAE_vs_130": float(np.mean(np.abs(suave - CENTRO))),
            "dentro_da_faixa": float(np.mean((suave >= FAIXA[0]) & (suave <= FAIXA[1]))),
        }
        res["limiares_por_metade"] = cfgs
        # referência: limiares do notebook (0,25) e os ajustados só nos 6 quadros
        c25 = contagens(pre, Config()).sum(1)
        res["limiar_0.25"] = {
            "MAE_vs_130": float(np.mean(np.abs(c25 - CENTRO))),
            "dentro_da_faixa": float(np.mean((c25 >= FAIXA[0]) & (c25 <= FAIXA[1]))),
        }
        saida[f"{grade[0]}x{grade[1]}"] = res
        print(
            f"{grade}: temporal-CV bruto MAE {mae:.1f} dentro {dentro:.0%} | kalman MAE {res['kalman']['MAE_vs_130']:.1f} dentro {res['kalman']['dentro_da_faixa']:.0%} | conf .25: MAE {res['limiar_0.25']['MAE_vs_130']:.1f} | limiares {cfgs}",
            flush=True,
        )
    (pasta / "video_inteiro.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    principal()
