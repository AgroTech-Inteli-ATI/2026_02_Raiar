"""RaiarNet: detector de aves por centro (heatmap) com cabeça de densidade.

Arquitetura escrita do zero em PyTorch, sem pesos pré-treinados:

    imagem -> backbone CSP com SPD-Conv e atenção (strides 4, 8, 16)
           -> pescoço BiFPN (2 repetições)
           -> cabeça de detecção em stride 4: heatmap de centros + tamanho + deslocamento
           -> cabeça de densidade em stride 4: mapa cuja soma estima a contagem

A detecção por centros dispensa âncoras e NMS entre caixas: cada ave é um pico
local do heatmap, o que evita suprimir aves aglomeradas. A cabeça de densidade
recupera aves parcialmente ocultas que não formam um pico nítido.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn

from .blocks import BiFPN, CBAM, ConvBNAct, CoordAttention, CSPBlock, DWSepConv, SPDConv, SPPF


@dataclass
class RaiarNetConfig:
    width: float = 1.0
    depth: int = 1
    attention: str = "coord"  # coord | cbam | none
    downsample: str = "spd"  # spd | stride
    neck_repeats: int = 2
    density_head: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _down(kind: str, c1: int, c2: int) -> nn.Module:
    return SPDConv(c1, c2) if kind == "spd" else ConvBNAct(c1, c2, 3, 2)


def _att(kind: str, c: int) -> nn.Module:
    return {"coord": CoordAttention, "cbam": CBAM}.get(kind, lambda c: nn.Identity())(c)


class RaiarNet(nn.Module):
    stride = 4

    def __init__(self, cfg: RaiarNetConfig | None = None):
        super().__init__()
        self.cfg = cfg = cfg or RaiarNetConfig()
        c = [int(v * cfg.width) for v in (16, 32, 64, 96, 128)]
        n = cfg.depth
        self.s1 = nn.Sequential(_down(cfg.downsample, 3, c[1]), CSPBlock(c[1], c[1], n))  # /2
        self.s2 = nn.Sequential(
            _down(cfg.downsample, c[1], c[2]), CSPBlock(c[2], c[2], n), _att(cfg.attention, c[2])
        )  # /4
        self.s3 = nn.Sequential(
            _down(cfg.downsample, c[2], c[3]), CSPBlock(c[3], c[3], 2 * n), _att(cfg.attention, c[3])
        )  # /8
        self.s4 = nn.Sequential(
            _down(cfg.downsample, c[3], c[4]), CSPBlock(c[4], c[4], n), SPPF(c[4], c[4]), _att(cfg.attention, c[4])
        )  # /16
        nc = c[2]
        necks = [BiFPN((c[2], c[3], c[4]), nc)]
        necks += [BiFPN((nc, nc, nc), nc) for _ in range(cfg.neck_repeats - 1)]
        self.necks = nn.ModuleList(necks)

        self.det_stem = nn.Sequential(DWSepConv(nc, nc), DWSepConv(nc, nc))
        self.hm = nn.Conv2d(nc, 1, 1)
        self.wh = nn.Conv2d(nc, 2, 1)
        self.off = nn.Conv2d(nc, 2, 1)
        if cfg.density_head:
            self.den = nn.Sequential(
                DWSepConv(nc, nc), DWSepConv(nc, nc // 2), nn.Conv2d(nc // 2, 1, 1), nn.Softplus()
            )
        self._init_heads()

    def _init_heads(self):
        nn.init.constant_(self.hm.bias, -2.19)  # probabilidade a priori ~0,1
        nn.init.normal_(self.hm.weight, std=0.01)
        nn.init.zeros_(self.wh.bias)
        nn.init.normal_(self.wh.weight, std=0.01)
        nn.init.zeros_(self.off.bias)
        nn.init.normal_(self.off.weight, std=0.01)
        if self.cfg.density_head:
            # softplus(-6) ~ 0,0025 por célula: contagem inicial próxima de zero.
            nn.init.constant_(self.den[2].bias, -6.0)
            nn.init.normal_(self.den[2].weight, std=0.01)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        x = self.s1(x)
        p2 = self.s2(x)
        p3 = self.s3(p2)
        p4 = self.s4(p3)
        feats = (p2, p3, p4)
        for neck in self.necks:
            feats = neck(feats)
        f = feats[0]
        d = self.det_stem(f)
        out = {
            "hm": self.hm(d),  # logits
            "wh": self.wh(d),  # log(largura, altura) em pixels de entrada / 16
            "off": torch.sigmoid(self.off(d)),  # deslocamento subcélula (0..1)
        }
        if self.cfg.density_head:
            out["den"] = self.den(f)
        return out


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
