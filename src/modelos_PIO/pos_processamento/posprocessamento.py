"""Pós-processamento das caixas do YOLOPIO para contagem por nível (N0, N1, N2).

Entrada: caixas (x1, y1, x2, y2) e confianças que o YOLOPIO já devolveu, com
limiar baixo, SEM alterar o modelo. Saída: contagem por nível.

Etapas (cada uma pode ser ligada/desligada para medir seu efeito isolado):

1. ROI e nível: a ave é atribuída ao nível pelo centro da caixa; o que cai fora
   dos polígonos (região azul, fundo além da divisória) é descartado.
   Equivale ao `LevelCounter.count` da RaiarNet.
2. Limiar por nível: como a RaiarNet escolhe o limiar na validação, cada nível
   pode ter o seu (N0 tem aves pequenas e aglomeradas; N2, aves grandes).
3. Filtro de tamanho por perspectiva: descarta caixas muito maiores ou menores
   do que uma ave daquela posição da imagem (usa as âncoras medidas da C1).
4. NMS extra por contenção: remove caixas pequenas quase inteiras dentro de
   outra caixa de maior confiança (duplicatas típicas de aves sobrepostas).
5. Contagem suave sensível à oclusão: análoga à "fusão" da RaiarNet. Detecções
   fracas (entre `conf_piso` e o limiar do nível) não viram ave inteira, mas
   contribuem com um peso proporcional à confiança, recuperando aves ocultas.
6. Calibração por nível (fator multiplicativo estimado na validação).
7. Soma ponderada de confianças (alternativa a 2 e 5): cada caixa contribui com
   conf**p em vez de 0 ou 1, o que dispensa um limiar duro e torna a contagem
   menos sensível a ele. Análoga à integral do mapa de densidade da RaiarNet.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .niveis import NIVEIS, NiveisROI, tamanho_esperado


@dataclass
class Config:
    limiar: dict[str, float] = field(default_factory=lambda: dict.fromkeys(NIVEIS, 0.25))
    filtro_tamanho: tuple[float, float] | None = None  # (razão mínima, razão máxima) do tamanho esperado
    contencao: float | None = None  # fração da caixa menor dentro da maior para remover
    suave: bool = False
    conf_piso: float = 0.08  # abaixo disso a detecção não contribui na contagem suave
    peso_suave: float = 1.0
    fator: dict[str, float] = field(default_factory=lambda: dict.fromkeys(NIVEIS, 1.0))
    soma_p: float | None = (
        None  # se definido: contagem = fator * soma(conf**p) das caixas com conf >= conf_piso
    )

    def com(self, **kw) -> Config:
        return replace(self, **kw)


def _centros(b: np.ndarray) -> np.ndarray:
    return np.c_[(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2]


def _razao_tamanho(b: np.ndarray) -> np.ndarray:
    c = _centros(b)
    w = b[:, 2] - b[:, 0]
    h = b[:, 3] - b[:, 1]
    esp = np.array([tamanho_esperado(x, y) for x, y in c]).reshape(-1, 2)
    return np.sqrt((w / esp[:, 0]) * (h / esp[:, 1]))


def _remover_contidas(b: np.ndarray, s: np.ndarray, frac: float) -> np.ndarray:
    """Máscara das caixas mantidas: remove a menor quando `frac` da sua área está em outra de maior escore."""
    n = len(b)
    manter = np.ones(n, bool)
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    ordem = np.argsort(-s)
    for ii, i in enumerate(ordem):
        if not manter[i]:
            continue
        for j in ordem[ii + 1 :]:
            if not manter[j]:
                continue
            lt = np.maximum(b[i, :2], b[j, :2])
            rb = np.minimum(b[i, 2:], b[j, 2:])
            inter = np.clip(rb - lt, 0, None).prod()
            if inter / max(min(area[i], area[j]), 1e-6) >= frac and area[j] <= area[i]:
                manter[j] = False
    return manter


def processar(boxes: np.ndarray, scores: np.ndarray, cfg: Config, roi: NiveisROI) -> dict:
    """Retorna contagens por nível e as caixas mantidas (com nível)."""
    boxes = np.asarray(boxes, np.float32).reshape(-1, 4)
    scores = np.asarray(scores, np.float32)
    usa_piso = cfg.suave or cfg.soma_p is not None
    piso = min(min(cfg.limiar.values()), cfg.conf_piso if usa_piso else 1.0)
    sel = scores >= piso
    b, s = boxes[sel], scores[sel]

    niveis = np.array([lv or "" for lv in roi.niveis_de(_centros(b))]) if len(b) else np.array([], str)
    dentro = niveis != ""
    b, s, niveis = b[dentro], s[dentro], niveis[dentro]

    if cfg.filtro_tamanho and len(b):
        r = _razao_tamanho(b)
        ok = (r >= cfg.filtro_tamanho[0]) & (r <= cfg.filtro_tamanho[1])
        b, s, niveis = b[ok], s[ok], niveis[ok]

    if cfg.contencao is not None and len(b):
        ok = _remover_contidas(b, s, cfg.contencao)
        b, s, niveis = b[ok], s[ok], niveis[ok]

    contagem, bruta, aceitas = {}, {}, np.zeros(len(b), bool)
    for k in NIVEIS:
        m = niveis == k
        forte = m & (s >= cfg.limiar[k])
        aceitas |= forte
        n = float(forte.sum())
        bruta[k] = int(n)
        if cfg.soma_p is not None:
            mm = m & (s >= cfg.conf_piso)
            contagem[k] = float(np.sum(s[mm] ** cfg.soma_p)) * cfg.fator[k]
            continue
        if cfg.suave:
            fraca = m & ~forte & (s >= cfg.conf_piso)
            n += cfg.peso_suave * float((s[fraca] / cfg.limiar[k]).sum())
        contagem[k] = n * cfg.fator[k]
    return {
        "contagem": contagem,
        "forte": bruta,
        "caixas": b,
        "scores": s,
        "niveis": niveis,
        "aceitas": aceitas,
    }


# Perfis de limiar. O dia vem do ajuste em todo o vídeo diurno (ajustar_final.py); à noite a câmera
# opera em infravermelho e o YOLOPIO já responde bem em 0,25 (valor do notebook).
LIMIAR_NOITE = dict.fromkeys(NIVEIS, 0.25)
SATURACAO_NOITE = 25.0  # saturação média (0–255) abaixo da qual a imagem é tratada como infravermelha


def saturacao_media(imagem: np.ndarray) -> float:
    import cv2

    return float(cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)[:, :, 1].mean())


def escolher_config(imagem: np.ndarray, limiar_dia: dict[str, float]) -> tuple[Config, str]:
    """Perfil automático: imagem quase sem cor (infravermelho) usa o perfil noturno."""
    if saturacao_media(imagem) < SATURACAO_NOITE:
        return Config(limiar=dict(LIMIAR_NOITE)), "noite"
    return Config(limiar=dict(limiar_dia)), "dia"
