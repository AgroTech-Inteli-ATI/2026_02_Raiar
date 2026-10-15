"""Alvos e funções de perda da RaiarNet, implementados do zero."""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F

SIZE_NORM = 16.0  # escala de referência do tamanho (log(w / 16))


def gaussian_radius(h: float, w: float, min_overlap: float = 0.7) -> float:
    """Raio do CenterNet (Zhou, Wang e Krähenbühl, 2019) que mantém IoU >= min_overlap."""
    a1, b1 = 1, h + w
    c1 = w * h * (1 - min_overlap) / (1 + min_overlap)
    r1 = (b1 + math.sqrt(b1**2 - 4 * a1 * c1)) / 2
    a2, b2 = 4, 2 * (h + w)
    c2 = (1 - min_overlap) * w * h
    r2 = (b2 + math.sqrt(b2**2 - 4 * a2 * c2)) / 2
    a3, b3 = 4 * min_overlap, -2 * min_overlap * (h + w)
    c3 = (min_overlap - 1) * w * h
    r3 = (b3 + math.sqrt(b3**2 - 4 * a3 * c3)) / 2
    return min(r1, r2, r3)


def build_targets(boxes: list[torch.Tensor], out_h: int, out_w: int, stride: int, density: bool = True):
    """Gera heatmap, tamanhos, deslocamentos e mapa de densidade em stride `stride`."""
    B = len(boxes)
    hm = torch.zeros(B, 1, out_h, out_w)
    den = torch.zeros(B, 1, out_h, out_w) if density else None
    ys_grid = torch.arange(out_h).float()[:, None]
    xs_grid = torch.arange(out_w).float()[None, :]
    inds, wh_t, off_t, box_t, bidx = [], [], [], [], []
    for b, bx in enumerate(boxes):
        for x1, y1, x2, y2 in bx.tolist():
            w, h = max(x2 - x1, 2.0), max(y2 - y1, 2.0)
            cx, cy = (x1 + x2) / 2 / stride, (y1 + y2) / 2 / stride
            ix, iy = int(min(max(cx, 0), out_w - 1)), int(min(max(cy, 0), out_h - 1))
            r = max(0.0, gaussian_radius(h / stride, w / stride))
            sigma = max((2 * r + 1) / 6, 0.6)
            g = torch.exp(-((xs_grid - ix) ** 2 + (ys_grid - iy) ** 2) / (2 * sigma**2))
            hm[b, 0] = torch.maximum(hm[b, 0], g)
            if density:
                sd = max(1.0, 0.2 * min(w, h) / stride)
                gd = torch.exp(-((xs_grid - cx + 0.5) ** 2 + (ys_grid - cy + 0.5) ** 2) / (2 * sd**2))
                den[b, 0] += gd / gd.sum().clamp(min=1e-6)
            inds.append(iy * out_w + ix)
            bidx.append(b)
            wh_t.append([math.log(w / SIZE_NORM), math.log(h / SIZE_NORM)])
            off_t.append([cx - ix, cy - iy])
            box_t.append([x1, y1, x2, y2])
    t = {
        "hm": hm,
        "den": den,
        "ind": torch.tensor(inds, dtype=torch.long),
        "bidx": torch.tensor(bidx, dtype=torch.long),
        "wh": torch.tensor(wh_t, dtype=torch.float32).reshape(-1, 2),
        "off": torch.tensor(off_t, dtype=torch.float32).reshape(-1, 2),
        "box": torch.tensor(box_t, dtype=torch.float32).reshape(-1, 4),
        "count": torch.tensor([len(bx) for bx in boxes], dtype=torch.float32),
    }
    return t


def focal_heatmap_loss(logits: torch.Tensor, gt: torch.Tensor, alpha: float = 2.0, beta: float = 4.0):
    """Focal loss modificada do CornerNet/CenterNet para heatmaps gaussianos."""
    pred = torch.sigmoid(logits).clamp(1e-4, 1 - 1e-4)
    pos = gt.eq(1).float()
    neg = 1 - pos
    pos_loss = torch.log(pred) * (1 - pred) ** alpha * pos
    neg_loss = torch.log(1 - pred) * pred**alpha * (1 - gt) ** beta * neg
    n = pos.sum()
    return -(pos_loss.sum() + neg_loss.sum()) / n.clamp(min=1.0)


def box_iou_pairs(a: torch.Tensor, b: torch.Tensor):
    lt = torch.maximum(a[:, :2], b[:, :2])
    rb = torch.minimum(a[:, 2:], b[:, 2:])
    inter = (rb - lt).clamp(min=0).prod(1)
    area_a = (a[:, 2:] - a[:, :2]).clamp(min=0).prod(1)
    area_b = (b[:, 2:] - b[:, :2]).clamp(min=0).prod(1)
    return inter / (area_a + area_b - inter + 1e-7)


def wise_iou_loss(pred: torch.Tensor, target: torch.Tensor):
    """Wise-IoU v1 (Tong et al., 2023): IoU com foco por distância normalizada dos centros."""
    iou = box_iou_pairs(pred, target)
    pc = (pred[:, :2] + pred[:, 2:]) / 2
    tc = (target[:, :2] + target[:, 2:]) / 2
    enc_lt = torch.minimum(pred[:, :2], target[:, :2])
    enc_rb = torch.maximum(pred[:, 2:], target[:, 2:])
    wg2 = ((enc_rb - enc_lt) ** 2).sum(1).detach()
    r = torch.exp(((pc - tc) ** 2).sum(1) / (wg2 + 1e-7))
    return (r * (1 - iou)).mean()


def gather(feat: torch.Tensor, bidx: torch.Tensor, ind: torch.Tensor) -> torch.Tensor:
    """Extrai vetores (N, C) de feat (B, C, H, W) nas posições achatadas `ind`."""
    B, C, H, W = feat.shape
    flat = feat.view(B, C, H * W)
    return flat[bidx, :, ind]


def decode_boxes_at(out, bidx, ind, stride: int):
    W = out["hm"].shape[-1]
    ys = (ind // W).float()
    xs = (ind % W).float()
    off = gather(out["off"], bidx, ind)
    wh = gather(out["wh"], bidx, ind).clamp(-4, 4).exp() * SIZE_NORM
    cx = (xs + off[:, 0]) * stride
    cy = (ys + off[:, 1]) * stride
    return torch.stack([cx - wh[:, 0] / 2, cy - wh[:, 1] / 2, cx + wh[:, 0] / 2, cy + wh[:, 1] / 2], 1)


def raiarnet_loss(out: dict, t: dict, stride: int, w_box: float = 1.0, w_den: float = 1.0, w_wh: float = 0.5):
    l_hm = focal_heatmap_loss(out["hm"], t["hm"])
    logs = {"hm": l_hm.item()}
    loss = l_hm
    if len(t["ind"]):
        wh_p = gather(out["wh"], t["bidx"], t["ind"])
        off_p = gather(out["off"], t["bidx"], t["ind"])
        l_wh = F.l1_loss(wh_p, t["wh"])
        l_off = F.l1_loss(off_p, t["off"])
        boxes_p = decode_boxes_at(out, t["bidx"], t["ind"], stride)
        l_iou = wise_iou_loss(boxes_p, t["box"])
        loss = loss + w_wh * l_wh + l_off + w_box * l_iou
        logs.update(wh=l_wh.item(), off=l_off.item(), iou=l_iou.item())
    if "den" in out and t["den"] is not None:
        B = out["den"].shape[0]
        l_map = ((out["den"] - t["den"]) ** 2).sum() / B
        pred_count = out["den"].sum((1, 2, 3))
        l_cnt = (F.smooth_l1_loss(pred_count, t["count"], reduction="none") / (t["count"] + 1).sqrt()).mean()
        loss = loss + w_den * (l_map + 0.1 * l_cnt)
        logs.update(den=l_map.item(), cnt=l_cnt.item())
    logs["total"] = loss.item()
    return loss, logs
