"""Experimento completo de pós-processamento: validação cruzada diurna + teste noturno + referência ingênua.

Mede, para cada estratégia, o erro de contagem por nível em:
 (a) 6 quadros diurnos (VC alternada A/B);
 (b) 1 quadro NOTURNO (v2, 13,5 s) com parâmetros ajustados só no dia -> teste de generalização;
 (c) comparação com um preditor constante ("sempre a média do dia"), que mostra o que é coincidência.
Uso: python avaliar_generalizacao.py --pesos best.pt --pasta resultados/pos_processamento
"""

import argparse
import json
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from pos_processamento.avaliacao import contar_quadros, metricas
from pos_processamento.deteccoes import detectar_fatiado, extrair_quadro
from pos_processamento.niveis import NIVEIS, NiveisROI
from pos_processamento.posprocessamento import Config, processar
from rodar_experimentos import GTQ, A, B, ajustar_fator, ajustar_limiares

NOITE = {"N0": 2, "N1": 2, "N2": 19}  # v2 a 13,5 s (src/raiarnet/reports/avaliacao-raiarnet.json)
VIDEO_NOITE = (
    Path(__file__).resolve().parents[1] / "raiarnet" / "img" / "WhatsApp Video 2026-09-29 at 12.02.02.mp4"
)


def ajustar_soma(det, quadros, roi, base: Config) -> Config:
    melhor = None
    for p in (0.5, 1.0, 2.0, 3.0):
        c = ajustar_fator(det, quadros, roi, base.com(soma_p=p, fator=dict.fromkeys(NIVEIS, 1.0)))
        c = c.com(fator={k: v for k, v in c.fator.items()})
        e = contar_quadros(det, GTQ, c, roi, quadros)["metricas"]["total"]["MAE"]
        if melhor is None or e < melhor[0]:
            melhor = (e, c)
    return melhor[1]


def vc(det, roi, ajusta):
    prev = {k: [] for k in (*NIVEIS, "total")}
    real = {k: [] for k in (*NIVEIS, "total")}
    cfgs = []
    for fit, teste in ((A, B), (B, A)):
        c = ajusta(det, fit, roi)
        cfgs.append(c)
        r = contar_quadros(det, GTQ, c, roi, teste)
        for k in prev:
            prev[k] += r["previsto"][k]
            real[k] += r["real"][k]
    return cfgs, prev, real


def resumo(prev, real):
    return {k: metricas(prev[k], real[k]) for k in prev}


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--pasta", required=True)
    a = ap.parse_args()
    pasta = Path(a.pasta)
    roi = NiveisROI()
    m = YOLO(a.pesos)
    estrategias = {
        "A. limiar 0,25": lambda d, q, r: Config(),
        "B. limiar por nível": lambda d, q, r: ajustar_limiares(d, q, r, Config()),
        "C. soma ponderada + calibração": lambda d, q, r: ajustar_soma(d, q, r, Config(conf_piso=0.05)),
    }
    saida = {}
    # referência ingênua: sempre a média por nível dos quadros de ajuste
    for grade in ("3x2", "3x3", "4x3", "4x4"):
        from pos_processamento.deteccoes import carregar_cache

        det = carregar_cache(pasta / f"deteccoes_roi_{grade}.npz")
        img_n = roi.mascarar(extrair_quadro(VIDEO_NOITE, 13500))
        gx, gy = map(int, grade.split("x"))
        bn, sn = detectar_fatiado(m, img_n, (gx, gy), 640, conf=0.01)
        saida[grade] = {}
        for nome, ajusta in estrategias.items():
            cfgs, prev, real = vc(det, roi, ajusta)
            dia = resumo(prev, real)
            cfg_all = ajusta(det, A + B, roi)  # ajuste com os 6 quadros -> aplicado à noite
            noite = processar(bn, sn, cfg_all, roi)["contagem"]
            saida[grade][nome] = {
                "dia": dia,
                "noite_prevista": noite,
                "noite_real": NOITE,
                "cfg_final": {
                    "limiar": cfg_all.limiar,
                    "fator": cfg_all.fator,
                    "soma_p": cfg_all.soma_p,
                },
            }
            e = lambda k: f"{dia[k]['MAE']:6.1f}"  # noqa: E731
            print(
                f"{grade} {nome:32s} dia MAE N0 {e('N0')} N1 {e('N1')} N2 {e('N2')} tot {e('total')} | noite prev "
                f"{ {k: round(v) for k, v in noite.items()} } real {NOITE}",
                flush=True,
            )
    media = {k: float(np.mean([sum(GTQ[str(ms)][k] for _ in [0]) for ms in A + B])) for k in NIVEIS}
    const = {k: metricas([media[k]] * 6, [GTQ[str(ms)][k] for ms in sorted(A + B)]) for k in NIVEIS}
    print(
        "constante (média diurna): MAE dia",
        {k: round(v["MAE"], 2) for k, v in const.items()},
        "| noite erro",
        {k: abs(media[k] - NOITE[k]) for k in NIVEIS},
    )
    saida["constante"] = {"media": media, "mae_dia": {k: v["MAE"] for k, v in const.items()}}
    (pasta / "generalizacao.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )


if __name__ == "__main__":
    principal()
