"""Experimentos iterativos de pós-processamento do YOLOPIO no vídeo de validação da C1.

Cada iteração liga UMA técnica a mais sobre a anterior e mede o erro de contagem
contra a anotação manual dos 6 quadros de teste (9,0 a 11,5 s). Os pesos do YOLOPIO
não mudam. Parâmetros ajustados (limiar e fator por nível) usam validação cruzada
alternada entre quadros (A = 9,0/10,0/11,0 s; B = 9,5/10,5/11,5 s): ajusta-se em uma
metade e mede-se na outra, para não avaliar no mesmo dado em que se calibrou.

Uso: python rodar_experimentos.py --pesos CAMINHO/best.pt --saida resultados/pos_processamento
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from pos_processamento.avaliacao import contar_quadros, metricas
from pos_processamento.deteccoes import GT, carregar_cache
from pos_processamento.niveis import NIVEIS, NiveisROI
from pos_processamento.posprocessamento import Config

GTQ = GT["quadros"]
A, B = [9000, 10000, 11000], [9500, 10500, 11500]
LIMIARES = [0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]


def erro_total(res):
    return res["metricas"]["total"]["MAE"]


def ajustar_limiares(det, quadros, roi, base: Config) -> Config:
    """Escolhe o limiar de cada nível que minimiza o MAE do nível nos quadros de ajuste."""
    lim = {}
    for k in NIVEIS:
        melhor = min(
            LIMIARES,
            key=lambda t: contar_quadros(det, GTQ, base.com(limiar={**base.limiar, k: t}), roi, quadros)[
                "metricas"
            ][k]["MAE"],
        )
        lim[k] = melhor
    return base.com(limiar=lim)


def ajustar_fator(det, quadros, roi, cfg: Config) -> Config:
    """Fator multiplicativo por nível = real / previsto nos quadros de ajuste (limitado a 0,5–3)."""
    r = contar_quadros(det, GTQ, cfg, roi, quadros)
    fator = {}
    for k in NIVEIS:
        p, g = np.mean(r["previsto"][k]), np.mean(r["real"][k])
        fator[k] = float(np.clip(g / p, 0.5, 3.0)) if p > 0.5 else 1.0
    return cfg.com(fator=fator)


def validacao_cruzada(det, roi, cfg_base: Config, ajusta_lim=False, ajusta_fat=False):
    """Ajusta em A e mede em B, ajusta em B e mede em A; devolve contagens e métricas conjuntas."""
    prev = {k: [] for k in (*NIVEIS, "total")}
    real = {k: [] for k in (*NIVEIS, "total")}
    cfgs = []
    for fit, teste in ((A, B), (B, A)):
        c = cfg_base
        if ajusta_lim:
            c = ajustar_limiares(det, fit, roi, c)
        if ajusta_fat:
            c = ajustar_fator(det, fit, roi, c)
        cfgs.append(c)
        r = contar_quadros(det, GTQ, c, roi, teste)
        for k in prev:
            prev[k] += r["previsto"][k]
            real[k] += r["real"][k]
    return {
        "previsto": prev,
        "real": real,
        "metricas": {k: metricas(prev[k], real[k]) for k in prev},
        "configs": cfgs,
    }


ESCADA = [
    ("A. conf 0,25 fixo", {}, False, False),
    ("B. + limiar por nível", {}, True, False),
    ("C1. + filtro tamanho 0,4–2,5", {"filtro_tamanho": (0.4, 2.5)}, True, False),
    ("C2. + filtro tamanho 0,5–1,8", {"filtro_tamanho": (0.5, 1.8)}, True, False),
    ("C3. + filtro tamanho 0,6–1,6", {"filtro_tamanho": (0.6, 1.6)}, True, False),
]


def escada(det, roi, filtro, extra_fim=True):
    """Roda a escada de iterações sobre um cache; `filtro` é a faixa de tamanho adotada nas etapas seguintes."""
    out = []
    for nome, kw, lim, fat in ESCADA:
        out.append((nome, validacao_cruzada(det, roi, Config(**kw), lim, fat)))
    base = Config(filtro_tamanho=filtro)
    etapas = [
        ("D. + remoção de caixas contidas", base.com(contencao=0.7), True, False),
        (
            "E. + contagem suave (oclusão)",
            base.com(contencao=0.7, suave=True, conf_piso=0.05),
            True,
            False,
        ),
        (
            "F. + calibração por nível",
            base.com(contencao=0.7, suave=True, conf_piso=0.05),
            True,
            True,
        ),
    ]
    for nome, cfg, lim, fat in etapas:
        out.append((nome, validacao_cruzada(det, roi, cfg, lim, fat)))
    return out


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", required=True, help="pasta com deteccoes_*.npz (ver gerar_deteccoes.py)")
    ap.add_argument("--filtro", type=float, nargs=2, default=(0.4, 2.5))
    args = ap.parse_args()
    roi = NiveisROI()
    pasta = Path(args.pasta)
    resultado = {}
    det640 = carregar_cache(pasta / "deteccoes_640.npz")
    ids = sorted(det640)
    tot0 = [int((det640[ms][1] >= 0.25).sum()) for ms in ids]
    real_tot = [sum(GTQ[str(ms)].values()) for ms in ids]
    m0 = metricas(tot0, real_tot)
    print(
        f"0. baseline notebook (640, imagem inteira, conf 0,25): MAE total {m0['MAE']:.1f} viés {m0['vies']:+.1f} previsto {tot0} real {real_tot}"
    )
    resultado["baseline_notebook"] = {"previsto": tot0, "real": real_tot, "metricas": m0}
    for arq in sorted(pasta.glob("deteccoes_roi_*.npz")):
        grade = arq.stem.replace("deteccoes_roi_", "")
        det = carregar_cache(arq)
        print(f"\n=== ROI cinza + fatias {grade}")
        linhas = []
        for nome, r in escada(det, roi, tuple(args.filtro)):
            m = r["metricas"]
            c = lambda k: f"{m[k]['MAE']:6.2f} ({m[k]['vies']:+7.2f})"  # noqa: E731
            print(f"{nome:36s} N0 {c('N0')} | N1 {c('N1')} | N2 {c('N2')} | total {c('total')}")
            linhas.append(
                {
                    "iteracao": nome,
                    "metricas": m,
                    "previsto": r["previsto"],
                    "real": r["real"],
                    "configs": [{"limiar": cf.limiar, "fator": cf.fator} for cf in r["configs"]],
                }
            )
        resultado[grade] = linhas
    (pasta / "iteracoes.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )


if __name__ == "__main__":
    principal()
