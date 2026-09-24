#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "baby-nursery"
OUT = COL / "source-designs" / "I0002-baby-elephant.png"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    collection = read_json(COL / "collection.json")
    by_dmc = {str(p["dmc"]): p["hex"].upper() for p in collection["palette"]}

    colors = {
        "outline": by_dmc["3760"],
        "blue": by_dmc["3325"],
        "light": by_dmc["3752"],
        "gray": by_dmc["415"],
        "dark": by_dmc["3799"],
        "pink": by_dmc["3713"],
        "pink2": by_dmc["761"],
        "white": by_dmc["3865"],
    }

    W, H = 100, 120
    grid = [[None for _ in range(W)] for _ in range(H)]

    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            grid[y][x] = c

    def ellipse(cx, cy, rx, ry, c):
        for y in range(max(0, int(cy - ry - 1)), min(H, int(cy + ry + 2))):
            for x in range(max(0, int(cx - rx - 1)), min(W, int(cx + rx + 2))):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    put(x, y, c)

    def disk(cx, cy, r, c):
        ellipse(cx, cy, r, r, c)

    def line(x0, y0, x1, y1, width, c):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            t = i / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            disk(round(x), round(y), width, c)

    # Tail behind the body.
    line(69, 67, 79, 73, 2.1, colors["outline"])
    line(69, 67, 78, 72, 1.1, colors["blue"])
    disk(80, 74, 2.2, colors["outline"])
    disk(80, 74, 1.2, colors["pink2"])

    # Body.
    ellipse(50, 70, 24, 27, colors["outline"])
    ellipse(50, 70, 21.5, 24.5, colors["blue"])
    ellipse(45, 62, 8, 10, colors["light"])

    # Ears, intentionally fully inside the safe frame.
    ellipse(28, 42, 16, 20, colors["outline"])
    ellipse(28, 42, 13.5, 17.5, colors["blue"])
    ellipse(28, 43, 8.5, 12.5, colors["pink"])
    ellipse(72, 42, 16, 20, colors["outline"])
    ellipse(72, 42, 13.5, 17.5, colors["blue"])
    ellipse(72, 43, 8.5, 12.5, colors["pink"])

    # Head over the ears.
    ellipse(50, 40, 25, 23, colors["outline"])
    ellipse(50, 40, 22.5, 20.5, colors["blue"])
    ellipse(45, 31, 8, 6, colors["light"])

    # Soft cheeks.
    ellipse(38, 45, 4.5, 3.5, colors["pink2"])
    ellipse(62, 45, 4.5, 3.5, colors["pink2"])

    # Eyes.
    ellipse(42, 37, 2.2, 2.5, colors["dark"])
    ellipse(58, 37, 2.2, 2.5, colors["dark"])
    put(41, 36, colors["white"])
    put(57, 36, colors["white"])

    # Small brows.
    line(39, 33, 44, 32, 0.7, colors["outline"])
    line(56, 32, 61, 33, 0.7, colors["outline"])

    # Trunk, with a curved, rounded end.
    trunk_points = [(50, 45), (50, 51), (51, 57), (52, 63), (54, 68), (57, 72)]
    for a, b in zip(trunk_points, trunk_points[1:]):
        line(a[0], a[1], b[0], b[1], 4.2, colors["outline"])
    for a, b in zip(trunk_points, trunk_points[1:]):
        line(a[0], a[1], b[0], b[1], 2.7, colors["blue"])
    disk(58, 72, 4.2, colors["outline"])
    disk(58, 72, 2.7, colors["blue"])
    put(60, 72, colors["dark"])

    # Arms.
    ellipse(31, 68, 8.5, 13, colors["outline"])
    ellipse(32, 68, 6.5, 11, colors["blue"])
    ellipse(69, 68, 8.5, 13, colors["outline"])
    ellipse(68, 68, 6.5, 11, colors["blue"])

    # Legs.
    ellipse(36, 83, 11, 15, colors["outline"])
    ellipse(36, 83, 8.5, 13, colors["blue"])
    ellipse(64, 83, 11, 15, colors["outline"])
    ellipse(64, 83, 8.5, 13, colors["blue"])

    # Complete rounded feet with visible soles/toes.
    ellipse(35, 96, 14, 10, colors["outline"])
    ellipse(35, 95, 11.5, 7.5, colors["blue"])
    ellipse(35, 96, 6.5, 4.5, colors["pink"])
    ellipse(65, 96, 14, 10, colors["outline"])
    ellipse(65, 95, 11.5, 7.5, colors["blue"])
    ellipse(65, 96, 6.5, 4.5, colors["pink"])

    # Toe highlights, kept inside the feet.
    for x in (31, 35, 39):
        disk(x, 93, 1.1, colors["pink2"])
    for x in (61, 65, 69):
        disk(x, 93, 1.1, colors["pink2"])

    # A few subtle body highlights.
    ellipse(43, 73, 3, 5, colors["light"])
    ellipse(57, 78, 2.5, 4, colors["light"])

    # Rasterize one design cell to 8x8 pixels. This is the canonical HD master
    # used as the visible reference before any technique JSON is generated.
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pix = im.load()
    for y in range(H):
        for x in range(W):
            c = grid[y][x]
            if c:
                h = c.lstrip("#")
                pix[x, y] = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    hd = im.resize((800, 960), Image.Resampling.NEAREST)

    alpha = hd.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError("Generated elephant is empty")
    margins = (bbox[0], bbox[1], 800 - bbox[2], 960 - bbox[3])
    if min(margins) < 64:
        raise RuntimeError(f"Generated elephant does not have enough safe margin: bbox={bbox}, margins={margins}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    hd.save(OUT, "PNG", optimize=True)

    # Structural foot validation: scan the lower foot band and require at least
    # one row where the two rounded feet are clearly visible as separate masses.
    a = alpha.load()
    best_y = None
    substantial = []
    for y in range(max(bbox[1], bbox[3] - 96), bbox[3] - 7, 8):
        runs = []
        start = None
        for x in range(bbox[0], bbox[2]):
            opaque = a[x, y] >= 128
            if opaque and start is None:
                start = x
            elif not opaque and start is not None:
                runs.append((start, x - 1))
                start = None
        if start is not None:
            runs.append((start, bbox[2] - 1))
        candidate = [r for r in runs if r[1] - r[0] + 1 >= 40]
        if len(candidate) >= 2:
            best_y = y
            substantial = candidate
            break
    if best_y is None:
        raise RuntimeError("Feet validation failed; no lower row shows two separate complete foot masses")

    print(f"I0002_MASTER_READY path={OUT} bbox={bbox} margins={margins} foot_row={best_y} lower_runs={substantial}")


if __name__ == "__main__":
    main()
