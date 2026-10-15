"""Reimplementação do Chicken-YOLO (Pan et al., 2025) como baseline do benchmark.

O artigo não publica código nem pesos. Reproduzimos a arquitetura a partir da
descrição textual, sobre o YOLO11n do Ultralytics (o mesmo ponto de partida dos
autores):

- MSEIExtractor no backbone: C3k2 seguido de MSEISelect (pooling adaptativo em
  3, 6, 9 e 12), EIEnhance (resíduo de alta frequência) e DSM (seleção espacial
  e na frequência, ponderadas por parâmetros aprendidos);
- CGDown no lugar das convoluções de redução do backbone e do pescoço: CBS 3x3
  com stride 2, ramos local (depthwise 3x3) e de contexto (dilatado, taxa 2),
  junção 1x1 e pesos de canal globais (GAP + duas FC + sigmoide);
- DHMSEAM: MultiSEAM (ramos 3x3/5x5/7x7 com stride igual ao kernel, depthwise
  separável e SiLU) substitui a segunda convolução do ramo de regressão e a
  segunda depthwise separável do ramo de classificação do Detect.

Escolhas não especificadas no artigo (documentadas no benchmark): redução 4 nas
FC, interpolação para o tamanho original antes da concatenação no MultiSEAM e
multiplicação elemento a elemento pelos pesos de canal.

O baseline usa a biblioteca Ultralytics; o modelo autoral (RaiarNet) não usa.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.nn.modules import C3k2, Conv
from ultralytics.nn.tasks import DetectionModel

# Índices do YOLO11n (cfg/models/11/yolo11.yaml).
BACKBONE_C3K2 = (2, 4, 6, 8)
DOWNSAMPLE_CONVS = (1, 3, 5, 7, 17, 20)


class MSEISelect(nn.Module):
    def __init__(self, c: int, bins=(3, 6, 9, 12)):
        super().__init__()
        self.bins = bins
        cb = max(c // 4, 8)
        self.reduce = nn.ModuleList(Conv(c, cb, 1) for _ in bins)
        self.fuse = Conv(c + cb * len(bins), c, 1)
        # EIEnhance: realce do resíduo de alta frequência (bordas de pena e crista).
        self.edge = Conv(c, c, 3, g=c)
        # DSM: seleção espacial (SSM) e na frequência (FSM).
        self.ssm = nn.Conv2d(2, 1, 7, padding=3)
        self.fsm = nn.Conv2d(2 * c, 2 * c, 1, groups=2)
        self.alpha = nn.Parameter(torch.zeros(1))
        self.beta = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        h, w = x.shape[-2:]
        pools = [F.interpolate(r(F.adaptive_avg_pool2d(x, b)), (h, w), mode="bilinear", align_corners=False) for r, b in zip(self.reduce, self.bins, strict=True)]
        y = self.fuse(torch.cat([x, *pools], 1))
        high = y - F.avg_pool2d(y, 3, 1, 1)
        y = y + self.edge(high)
        sa = torch.sigmoid(self.ssm(torch.cat([y.mean(1, keepdim=True), y.amax(1, keepdim=True)], 1)))
        ys = y * sa
        spec = torch.fft.rfft2(ys.float(), norm="ortho")
        mix = self.fsm(torch.cat([spec.real, spec.imag], 1))
        re, im = mix.chunk(2, 1)
        yf = torch.fft.irfft2(torch.complex(re, im), s=(h, w), norm="ortho").to(x.dtype)
        return x + torch.tanh(self.alpha) * ys + torch.tanh(self.beta) * yf


class MSEIExtractor(nn.Module):
    """C3k2 do YOLO11 seguido do MSEISelect."""

    def __init__(self, c3k2: nn.Module, c: int):
        super().__init__()
        self.c3k2 = c3k2
        self.select = MSEISelect(c)

    def forward(self, x):
        return self.select(self.c3k2(x))


class CGDown(nn.Module):
    def __init__(self, c1: int, c2: int):
        super().__init__()
        self.down = Conv(c1, c2, 3, 2)
        self.local = nn.Conv2d(c2, c2, 3, 1, 1, groups=c2, bias=False)
        self.context = nn.Conv2d(c2, c2, 3, 1, 2, dilation=2, groups=c2, bias=False)
        self.bn = nn.BatchNorm2d(2 * c2)
        self.joint = Conv(2 * c2, c2, 1)
        r = max(c2 // 4, 8)
        self.fc = nn.Sequential(nn.Linear(c2, r), nn.SiLU(), nn.Linear(r, c2), nn.Sigmoid())

    def forward(self, x):
        x = self.down(x)
        y = self.joint(F.silu(self.bn(torch.cat([self.local(x), self.context(x)], 1))))
        w = self.fc(y.mean((2, 3)))[:, :, None, None]
        return y * w


class MultiSEAM(nn.Module):
    def __init__(self, c1: int, c2: int | None = None, kernels=(3, 5, 7)):
        super().__init__()
        c2 = c2 or c1
        self.branches = nn.ModuleList(
            nn.Sequential(
                Conv(c1, c1, k, k),
                Conv(c1, c1, 3, g=c1),
                Conv(c1, c1, 1),
            )
            for k in kernels
        )
        r = max(c1 // 4, 8)
        self.fc = nn.Sequential(nn.Linear(4 * c1, r), nn.SiLU(), nn.Linear(r, c2), nn.Sigmoid())
        self.proj = Conv(c1, c2, 1) if c1 != c2 else nn.Identity()

    def forward(self, x):
        h, w = x.shape[-2:]
        outs = [x]
        for b in self.branches:
            y = b(x) if min(h, w) >= 7 else x
            outs.append(F.interpolate(y, (h, w), mode="nearest"))
        pooled = torch.cat(outs, 1).mean((2, 3))
        return self.proj(x) * self.fc(pooled)[:, :, None, None]


def _copy_meta(new: nn.Module, old: nn.Module) -> nn.Module:
    for attr in ("f", "i", "type", "np"):
        if hasattr(old, attr):
            setattr(new, attr, getattr(old, attr))
    new.np = sum(p.numel() for p in new.parameters())
    return new


def to_chicken_yolo(model: DetectionModel) -> DetectionModel:
    layers = model.model
    for i in BACKBONE_C3K2:
        old = layers[i]
        assert isinstance(old, C3k2)
        c = old.cv2.conv.out_channels
        layers[i] = _copy_meta(MSEIExtractor(old, c), old)
    for i in DOWNSAMPLE_CONVS:
        old = layers[i]
        assert isinstance(old, Conv) and old.conv.stride == (2, 2)
        layers[i] = _copy_meta(CGDown(old.conv.in_channels, old.conv.out_channels), old)
    det = layers[-1]
    for seq in det.cv2:  # regressão: Conv, Conv, Conv2d
        c = seq[1].conv.out_channels
        seq[1] = MultiSEAM(seq[0].conv.out_channels, c)
    for seq in det.cv3:  # classificação: Seq(DW, Conv), Seq(DW, Conv), Conv2d
        c_in = seq[0][1].conv.out_channels
        c_out = seq[1][1].conv.out_channels
        seq[1] = MultiSEAM(c_in, c_out)
    return model


class ChickenYoloTrainer(DetectionTrainer):
    def get_model(self, cfg=None, weights=None, verbose=True):
        model = DetectionModel(cfg, nc=self.data["nc"], ch=self.data["channels"], verbose=False)
        if weights:
            model.load(weights)
        return to_chicken_yolo(model)
