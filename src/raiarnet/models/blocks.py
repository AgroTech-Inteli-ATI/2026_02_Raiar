"""Blocos convolucionais escritos do zero em PyTorch para a RaiarNet."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


class ConvBNAct(nn.Module):
    def __init__(self, c1: int, c2: int, k: int = 3, s: int = 1, g: int = 1, act: bool = True):
        super().__init__()
        self.conv = nn.Conv2d(c1, c2, k, s, k // 2, groups=g, bias=False)
        self.bn = nn.BatchNorm2d(c2)
        self.act = nn.SiLU(inplace=True) if act else nn.Identity()

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))


class DWSepConv(nn.Module):
    """Convolução separável em profundidade (depthwise 3x3 + pointwise 1x1)."""

    def __init__(self, c1: int, c2: int, k: int = 3, s: int = 1):
        super().__init__()
        self.dw = ConvBNAct(c1, c1, k, s, g=c1)
        self.pw = ConvBNAct(c1, c2, 1)

    def forward(self, x):
        return self.pw(self.dw(x))


class SPDConv(nn.Module):
    """Space-to-depth seguido de convolução sem passo (Sunkara e Luo, 2022).

    Reduz a resolução pela metade reorganizando cada bloco 2 x 2 em canais, sem
    descartar pixels como faz a convolução com stride 2. Preserva o detalhe das
    aves pequenas do fundo do corredor.
    """

    def __init__(self, c1: int, c2: int):
        super().__init__()
        self.conv = ConvBNAct(4 * c1, c2, 3, 1)

    def forward(self, x):
        x = torch.cat([x[..., ::2, ::2], x[..., 1::2, ::2], x[..., ::2, 1::2], x[..., 1::2, 1::2]], 1)
        return self.conv(x)


class Bottleneck(nn.Module):
    def __init__(self, c: int, shortcut: bool = True):
        super().__init__()
        self.cv1 = ConvBNAct(c, c, 3)
        self.cv2 = ConvBNAct(c, c, 3)
        self.add = shortcut

    def forward(self, x):
        y = self.cv2(self.cv1(x))
        return x + y if self.add else y


class CSPBlock(nn.Module):
    """Bloco Cross Stage Partial: metade dos canais atravessa n gargalos."""

    def __init__(self, c1: int, c2: int, n: int = 1):
        super().__init__()
        c = c2 // 2
        self.cv1 = ConvBNAct(c1, 2 * c, 1)
        self.m = nn.ModuleList(Bottleneck(c) for _ in range(n))
        self.cv2 = ConvBNAct((2 + n) * c, c2, 1)

    def forward(self, x):
        y = list(self.cv1(x).chunk(2, 1))
        for m in self.m:
            y.append(m(y[-1]))
        return self.cv2(torch.cat(y, 1))


class CoordAttention(nn.Module):
    """Atenção por coordenadas (Hou, Zhou e Feng, 2021).

    Codifica separadamente as direções horizontal e vertical; ajuda a destacar
    aves atrás das barras da grade, que têm orientação dominante.
    """

    def __init__(self, c: int, reduction: int = 16):
        super().__init__()
        m = max(8, c // reduction)
        self.conv1 = ConvBNAct(c, m, 1)
        self.conv_h = nn.Conv2d(m, c, 1)
        self.conv_w = nn.Conv2d(m, c, 1)

    def forward(self, x):
        _, _, h, w = x.shape
        xh = x.mean(dim=3, keepdim=True)
        xw = x.mean(dim=2, keepdim=True).transpose(2, 3)
        y = self.conv1(torch.cat([xh, xw], dim=2))
        yh, yw = torch.split(y, [h, w], dim=2)
        ah = torch.sigmoid(self.conv_h(yh))
        aw = torch.sigmoid(self.conv_w(yw.transpose(2, 3)))
        return x * ah * aw


class CBAM(nn.Module):
    """Convolutional Block Attention Module (Woo et al., 2018): canal + espacial."""

    def __init__(self, c: int, reduction: int = 16, k: int = 7):
        super().__init__()
        m = max(8, c // reduction)
        self.mlp = nn.Sequential(nn.Conv2d(c, m, 1), nn.SiLU(inplace=True), nn.Conv2d(m, c, 1))
        self.spatial = nn.Conv2d(2, 1, k, padding=k // 2)

    def forward(self, x):
        ca = torch.sigmoid(self.mlp(x.mean((2, 3), keepdim=True)) + self.mlp(x.amax((2, 3), keepdim=True)))
        x = x * ca
        sa = torch.sigmoid(self.spatial(torch.cat([x.mean(1, keepdim=True), x.amax(1, keepdim=True)], 1)))
        return x * sa


class SPPF(nn.Module):
    """Pooling espacial em pirâmide rápido: amplia o campo receptivo do último estágio."""

    def __init__(self, c1: int, c2: int, k: int = 5):
        super().__init__()
        c = c1 // 2
        self.cv1 = ConvBNAct(c1, c, 1)
        self.cv2 = ConvBNAct(4 * c, c2, 1)
        self.k = k

    def forward(self, x):
        x = self.cv1(x)
        y1 = F.max_pool2d(x, self.k, 1, self.k // 2)
        y2 = F.max_pool2d(y1, self.k, 1, self.k // 2)
        y3 = F.max_pool2d(y2, self.k, 1, self.k // 2)
        return self.cv2(torch.cat([x, y1, y2, y3], 1))


class WeightedFusion(nn.Module):
    """Fusão com pesos normalizados aprendidos (fast normalized fusion do BiFPN)."""

    def __init__(self, n: int, c: int):
        super().__init__()
        self.w = nn.Parameter(torch.ones(n))
        self.conv = DWSepConv(c, c)

    def forward(self, xs: list[torch.Tensor]):
        w = F.relu(self.w)
        w = w / (w.sum() + 1e-4)
        return self.conv(sum(wi * xi for wi, xi in zip(w, xs, strict=True)))


class BiFPN(nn.Module):
    """Pescoço BiFPN com três níveis (strides 4, 8 e 16) e um caminho ida e volta.

    Tan, Pang e Le (2020). A saída de maior resolução (stride 4) alimenta as cabeças.
    """

    def __init__(self, chans: tuple[int, int, int], c: int):
        super().__init__()
        self.lat = nn.ModuleList(ConvBNAct(ci, c, 1) for ci in chans)
        self.td1 = WeightedFusion(2, c)  # P3_td = f(P3, up(P4))
        self.td0 = WeightedFusion(2, c)  # P2_out = f(P2, up(P3_td))
        self.bu1 = WeightedFusion(3, c)  # P3_out = f(P3, P3_td, down(P2_out))
        self.bu2 = WeightedFusion(2, c)  # P4_out = f(P4, down(P3_out))
        self.down1 = DWSepConv(c, c, 3, 2)
        self.down2 = DWSepConv(c, c, 3, 2)

    def forward(self, feats):
        p2, p3, p4 = (lat(f) for lat, f in zip(self.lat, feats, strict=True))
        p3_td = self.td1([p3, F.interpolate(p4, size=p3.shape[-2:], mode="nearest")])
        p2_out = self.td0([p2, F.interpolate(p3_td, size=p2.shape[-2:], mode="nearest")])
        p3_out = self.bu1([p3, p3_td, self.down1(p2_out)])
        p4_out = self.bu2([p4, self.down2(p3_out)])
        return p2_out, p3_out, p4_out
