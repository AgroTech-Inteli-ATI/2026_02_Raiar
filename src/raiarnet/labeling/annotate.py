"""Ferramenta de anotação assistida por pontos.

Fluxo: extrair quadros -> renderizar blocos ampliados com grade de coordenadas ->
registrar o centro de cada ave visível -> revisar a sobreposição -> propagar
pontos para o quadro seguinte por fluxo óptico e corrigir as diferenças.
Os rótulos ficam em data/annotations/<quadro>.json (fora do Git).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "data" / "interim" / "frames"
ANN = ROOT / "data" / "annotations"
DEFAULT_ROIS = ROOT / "configs" / "cameras" / "c1-jump-start.json"
VIDEOS = {
    "v1": "WhatsApp Video 2026-09-29 at 12.02.02 (1).mp4",
    "v2": "WhatsApp Video 2026-09-29 at 12.02.02.mp4",
    "v3": "WhatsApp Video 2026-09-29 at 12.02.03.mp4",
    "v4": "WhatsApp Video 2026-10-09 at 10.45.21.mp4",
}
LEVEL_COLORS = {"N0": (255, 255, 0), "N1": (255, 0, 200), "N2": (0, 180, 255)}


def video_path(key: str) -> Path:
    raw = ROOT / "data" / "raw" / VIDEOS[key]
    return raw if raw.exists() else ROOT / "img" / VIDEOS[key]


def frame_name(video: str, t: float) -> str:
    return f"{video}_t{int(round(t * 1000)):05d}"


def extract(video: str, times: list[float]) -> list[Path]:
    FRAMES.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path(video)))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
        ok, fr = cap.read()
        if not ok:
            raise RuntimeError(f"Falha ao ler {video} em {t}s")
        p = FRAMES / f"{frame_name(video, t)}.png"
        cv2.imwrite(str(p), fr)
        out.append(p)
    return out


def load_points(name: str) -> list[list[float]]:
    p = ANN / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))["points"] if p.exists() else []


def save_points(name: str, pts: list[list[float]], meta: dict | None = None) -> None:
    ANN.mkdir(parents=True, exist_ok=True)
    pts = [[round(float(x), 1), round(float(y), 1)] for x, y in pts]
    data = {"frame": name, "points": pts, **(meta or {})}
    (ANN / f"{name}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")


def load_rois(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def enhance_for_review(img: np.ndarray) -> np.ndarray:
    """Realce usado somente na revisão visual: ganho linear e saturação 1,8x."""
    gain = float(np.clip(120.0 / max(img.mean(), 1.0), 1.0, 2.5))
    hsv = cv2.cvtColor(cv2.convertScaleAbs(img, alpha=gain, beta=5), cv2.COLOR_BGR2HSV)
    hsv = hsv.astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.8, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def render_tile(img, pts, x0, y0, size, scale, rois=None) -> np.ndarray:
    crop = enhance_for_review(img[y0 : y0 + size, x0 : x0 + size])
    big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    big = cv2.addWeighted(big, 1.6, cv2.GaussianBlur(big, (0, 0), 2), -0.6, 0)
    grid = big.copy()
    for g in range(-(-x0 // 8) * 8, x0 + crop.shape[1] + 1, 8):
        X = int((g - x0) * scale)
        if g % 32 == 0:
            cv2.line(grid, (X, 0), (X, big.shape[0]), (0, 230, 255), 1)
            cv2.putText(big, str(g), (X + 2, 11), 0, 0.38, (0, 255, 255), 1)
        cv2.line(big, (X, 0), (X, 6 if g % 32 else 14), (0, 255, 255), 1)
        cv2.line(big, (X, big.shape[0] - 1), (X, big.shape[0] - 7), (0, 255, 255), 1)
    for g in range(-(-y0 // 8) * 8, y0 + crop.shape[0] + 1, 8):
        Y = int((g - y0) * scale)
        if g % 32 == 0:
            cv2.line(grid, (0, Y), (big.shape[1], Y), (255, 230, 0), 1)
            cv2.putText(big, str(g), (2, Y - 2), 0, 0.38, (255, 255, 0), 1)
        cv2.line(big, (0, Y), (6 if g % 32 else 14, Y), (255, 255, 0), 1)
        cv2.line(big, (big.shape[1] - 1, Y), (big.shape[1] - 7, Y), (255, 255, 0), 1)
    big = cv2.addWeighted(grid, 0.3, big, 0.7, 0)
    if rois:
        for k, poly in rois.items():
            if k in LEVEL_COLORS:
                a = ((np.array(poly, np.float32) - [x0, y0]) * scale).astype(np.int32)
                cv2.polylines(big, [a], True, LEVEL_COLORS[k], 2)
    for x, y in pts:
        if x0 <= x < x0 + size and y0 <= y < y0 + size:
            X, Y = int((x - x0) * scale), int((y - y0) * scale)
            cv2.circle(big, (X, Y), 3, (0, 0, 255), -1)
            cv2.circle(big, (X, Y), 4, (255, 255, 255), 1)
    return big


def overview(img, pts, rois=None, scale=1.5) -> np.ndarray:
    vis = img.copy()
    if rois:
        for k, poly in rois.items():
            if k in LEVEL_COLORS:
                cv2.polylines(vis, [np.array(poly, np.int32)], True, LEVEL_COLORS[k], 1)
    for x, y in pts:
        cv2.circle(vis, (int(x), int(y)), 2, (0, 0, 255), -1)
    vis = cv2.resize(vis, None, fx=scale, fy=scale)
    for g in range(0, img.shape[1], 64):
        cv2.putText(vis, str(g), (int(g * scale) + 2, 12), 0, 0.4, (0, 255, 255), 1)
    for g in range(0, img.shape[0], 32):
        cv2.putText(vis, str(g), (2, int(g * scale)), 0, 0.4, (255, 255, 0), 1)
    return vis


def propagate(src: str, dst: str) -> list[list[float]]:
    """Move os pontos de src para dst com fluxo óptico denso (Farneback)."""
    a = cv2.imread(str(FRAMES / f"{src}.png"), cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(str(FRAMES / f"{dst}.png"), cv2.IMREAD_GRAYSCALE)
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 4, 21, 5, 7, 1.5, 0)
    out = []
    for x, y in load_points(src):
        xi, yi = int(np.clip(x, 0, a.shape[1] - 1)), int(np.clip(y, 0, a.shape[0] - 1))
        win = flow[max(yi - 3, 0) : yi + 4, max(xi - 3, 0) : xi + 4].reshape(-1, 2)
        dx, dy = np.median(win, axis=0)
        out.append([x + float(dx), y + float(dy)])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("video")
    e.add_argument("times", type=float, nargs="+")
    t = sub.add_parser("tile")
    t.add_argument("frame")
    t.add_argument("x0", type=int)
    t.add_argument("y0", type=int)
    t.add_argument("--size", type=int, default=160)
    t.add_argument("--scale", type=float, default=4.0)
    t.add_argument("--out", required=True)
    t.add_argument("--rois", default=str(DEFAULT_ROIS))
    o = sub.add_parser("overview")
    o.add_argument("frame")
    o.add_argument("--out", required=True)
    o.add_argument("--rois", default=str(DEFAULT_ROIS))
    a = sub.add_parser("add")
    a.add_argument("frame")
    a.add_argument("coords", type=float, nargs="+")
    a.add_argument("--dedupe", type=float, default=0, help="ignora pontos a menos de R px")
    r = sub.add_parser("remove")
    r.add_argument("frame")
    r.add_argument("coords", type=float, nargs="+")
    r.add_argument("--radius", type=float, default=6)
    m = sub.add_parser("move")
    m.add_argument("frame")
    m.add_argument("coords", type=float, nargs="+", help="x_old y_old x_new y_new ...")
    p = sub.add_parser("propagate")
    p.add_argument("src")
    p.add_argument("dst")
    c = sub.add_parser("count")
    c.add_argument("frames", nargs="+")
    args = ap.parse_args()

    if args.cmd == "extract":
        for p_ in extract(args.video, args.times):
            print(p_.name)
    elif args.cmd in ("tile", "overview"):
        img = cv2.imread(str(FRAMES / f"{args.frame}.png"))
        rois = load_rois(args.rois) if args.rois else None
        pts = load_points(args.frame)
        if args.cmd == "tile":
            vis = render_tile(img, pts, args.x0, args.y0, args.size, args.scale, rois)
        else:
            vis = overview(img, pts, rois)
        cv2.imwrite(args.out, vis)
        print(len(pts), "pontos")
    elif args.cmd == "add":
        pts = load_points(args.frame)
        c = args.coords
        for i in range(0, len(c), 2):
            near = [p_ for p_ in pts if np.hypot(p_[0] - c[i], p_[1] - c[i + 1]) < args.dedupe]
            if near:
                print("duplicado ignorado", c[i], c[i + 1])
            else:
                pts.append([c[i], c[i + 1]])
        save_points(args.frame, pts)
        print(len(pts), "pontos")
    elif args.cmd in ("remove", "move"):
        pts = np.array(load_points(args.frame), np.float32).reshape(-1, 2)
        c = args.coords
        k = 2 if args.cmd == "remove" else 4
        for i in range(0, len(c), k):
            if len(pts) == 0:
                break
            d = np.hypot(pts[:, 0] - c[i], pts[:, 1] - c[i + 1])
            j = int(np.argmin(d))
            if d[j] > getattr(args, "radius", 8):
                print("sem ponto perto de", c[i], c[i + 1])
                continue
            if args.cmd == "remove":
                pts = np.delete(pts, j, axis=0)
            else:
                pts[j] = [c[i + 2], c[i + 3]]
        save_points(args.frame, pts.tolist())
        print(len(pts), "pontos")
    elif args.cmd == "propagate":
        save_points(args.dst, propagate(args.src, args.dst), {"propagated_from": args.src})
        print("ok")
    elif args.cmd == "count":
        for f in args.frames:
            print(f, len(load_points(f)))


if __name__ == "__main__":
    main()
