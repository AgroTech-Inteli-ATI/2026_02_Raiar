"""Gera as figuras e tabelas finais (para leigos) a partir dos caches e do vídeo.

Uso: python gerar_figuras.py --pesos best.pt --video VIDEO.mp4 --pasta resultados/pos_processamento --saida ../../docs/static/img/pos-processamento
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from pos_processamento import visual
from pos_processamento.deteccoes import (
    GT,
    carregar_cache,
    detectar,
    detectar_fatiado,
    extrair_quadro,
)
from pos_processamento.niveis import NIVEIS, NiveisROI
from pos_processamento.posprocessamento import Config, escolher_config, processar
from pos_processamento.temporal import suavizar_serie

VIDEO_NOITE = (
    Path(__file__).resolve().parents[1] / "raiarnet" / "img" / "WhatsApp Video 2026-09-29 at 12.02.02.mp4"
)
GRADE = (4, 3)


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    pasta, saida = Path(a.pasta), Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    roi = NiveisROI()
    m = YOLO(a.pesos)
    cfgd = json.loads((pasta / "config_final.json").read_text(encoding="utf-8"))
    cfg = Config(limiar=cfgd["limiar"])
    base = Config()  # 0,25 em todos os níveis, como o notebook
    gtq = GT["quadros"]
    cache = carregar_cache(pasta / "deteccoes_roi_4x3.npz")
    cache640 = carregar_cache(pasta / "deteccoes_640.npz")

    # 1) antes x depois no quadro de 10 s
    img = extrair_quadro(a.video, 10000)
    r_ant = processar(*cache640[10000], base, roi)
    r_dep = processar(*cache[10000], cfg, roi)
    visual.antes_depois(
        img,
        r_ant,
        r_dep,
        roi,
        r_ant["contagem"],
        r_dep["contagem"],
        gtq["10000"],
        saida / "antes-depois-dia.png",
    )

    # 2) médias por nível: manual, RaiarNet, YOLOPIO puro, YOLOPIO + pós
    ids = sorted(int(k) for k in gtq)
    med = lambda f: {k: float(np.mean([f(ms)[k] for ms in ids])) for k in NIVEIS}  # noqa: E731
    real = med(lambda ms: gtq[str(ms)])
    rn = med(lambda ms: GT["raiarnet_teste"][str(ms)]["det"])
    puro = med(lambda ms: processar(*cache640[ms], base, roi)["contagem"])
    pos = med(lambda ms: processar(*cache[ms], cfg, roi)["contagem"])
    # erro por quadro (absoluto médio): sem compensação entre quadros
    def mae_nivel(f):
        return {k: float(np.mean([abs(f(ms)[k] - gtq[str(ms)][k]) for ms in ids])) for k in NIVEIS}

    mae_rn = mae_nivel(lambda ms: GT["raiarnet_teste"][str(ms)]["det"])
    mae_puro = mae_nivel(lambda ms: processar(*cache640[ms], base, roi)["contagem"])
    mae_pos = mae_nivel(lambda ms: processar(*cache[ms], cfg, roi)["contagem"])

    # 3) escada de iterações (MAE total) para a grade 3x2
    vi = json.loads((pasta / "video_inteiro.json").read_text(encoding="utf-8"))["4x3"]
    rot = [
        "0. YOLOPIO original (640 px, conf 0,25)",
        "1. + ROI, níveis e fatias 4x3 (conf 0,25)",
        "2. + limiar por nível (validação temporal)",
        "3. + filtro de Kalman",
    ]
    mae = [
        130.0,
        vi["limiar_0.25"]["MAE_vs_130"],
        vi["bruto"]["MAE_vs_130"],
        vi["kalman"]["MAE_vs_130"],
    ]
    visual.erro_por_iteracao(rot, mae, saida / "erro-por-iteracao.png")

    # 4) série temporal (1 quadro a cada 3) com Kalman
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    tempos, brutas = [], {k: [] for k in NIVEIS}
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % 3 == 0:
            b, s = detectar_fatiado(m, roi.mascarar(fr), GRADE, 640, conf=0.01)
            c = processar(b, s, cfg, roi)["contagem"]
            tempos.append(i / fps)
            for k in NIVEIS:
                brutas[k].append(c[k])
        i += 1
    suaves = {k: suavizar_serie(brutas[k]) for k in NIVEIS}
    pts = {k: [(ms / 1000, gtq[str(ms)][k]) for ms in ids] for k in NIVEIS}
    visual.serie_tempo(tempos, brutas, suaves, pts, saida / "serie-temporal.png")
    osc = lambda v: float(np.mean(np.abs(np.diff(v))))  # noqa: E731
    estab = {k: {"bruta": osc(brutas[k]), "kalman": osc(suaves[k])} for k in NIVEIS}
    kal = {
        k: float(
            np.mean(
                [
                    abs(suaves[k][int(np.argmin(np.abs(np.array(tempos) - ms / 1000)))] - gtq[str(ms)][k])
                    for ms in ids
                ]
            )
        )
        for k in NIVEIS
    }

    # 5) teste noturno
    imn = extrair_quadro(VIDEO_NOITE, 13500)
    bn, sn = detectar_fatiado(m, roi.mascarar(imn), GRADE, 640, conf=0.01)
    b640, s640 = detectar(m, imn, imgsz=640, conf=0.01)
    rn_noite = {
        "original": processar(b640, s640, base, roi)["contagem"],
        "fatiado_025": processar(bn, sn, base, roi)["contagem"],
        "fatiado_limiar_dia": processar(bn, sn, cfg, roi)["contagem"],
    }
    cfg_auto, perfil = escolher_config(imn, cfgd["limiar"])
    rn_noite["perfil_automatico"] = processar(bn, sn, cfg_auto, roi)["contagem"]
    rn_noite["perfil_escolhido"] = perfil
    real_n = {"N0": 2, "N1": 2, "N2": 19}
    visual.barras_por_nivel(
        {
            "YOLOPIO original": rn_noite["original"],
            "pós (limiares do dia)": rn_noite["fatiado_limiar_dia"],
            "pós (perfil automático)": rn_noite["perfil_automatico"],
        },
        real_n,
        saida / "teste-noturno.png",
        "Quadro noturno (v2, 13,5 s): aves por nível",
    )
    r_n = processar(bn, sn, cfg_auto, roi)
    visual.antes_depois(
        imn,
        processar(b640, s640, base, roi),
        r_n,
        roi,
        processar(b640, s640, base, roi)["contagem"],
        r_n["contagem"],
        real_n,
        saida / "antes-depois-noite.png",
    )
    visual.erro_por_nivel(
        {"YOLOPIO original": mae_puro, "YOLOPIO + pós-proc.": mae_pos, "+ Kalman": kal, "RaiarNet": mae_rn},
        saida / "erro-por-nivel.png",
        "Erro absoluto médio por quadro, nos 6 quadros diurnos anotados (menor é melhor)",
    )
    resumo = {
        "erro_por_quadro": {"yolopio_original": mae_puro, "yolopio_pos": mae_pos, "yolopio_pos_kalman": kal,
                            "raiarnet_det": mae_rn},
        "medias": {"real": real, "raiarnet_det": rn, "yolopio_puro": puro, "yolopio_pos": pos},
        "estabilidade_kalman": estab,
        "erro_kalman_nos_quadros_gt": kal,
        "noite": rn_noite,
        "limiares": cfgd["limiar"],
        "grade": list(GRADE),
    }
    (pasta / "resumo_final.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    principal()
