#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "baby-nursery"
SRC = COL / "source-designs" / "I0001-teddy-bear.png"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

SUFFIXES = ("CS","C2C","TC","LH")
GRIDS = {
    "CS": (100,120),
    "C2C": (60,72),
    "TC": (80,96),
    "LH": (60,72),
}
PAGE1 = {
    "CS": "collections/baby-nursery/assets/cover-cross-stitch.jpg",
    "C2C": "collections/baby-nursery/assets/cover-crochet.jpg",
    "TC": "collections/baby-nursery/assets/cover-c2c-crochet.jpg",
    "LH": "collections/baby-nursery/assets/cover-rug.jpg",
}
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def rgb(hexv: str):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def build_cs_matrix():
    collection = read_json(COL / "collection.json")
    palette = collection["palette"]
    palette_rgb = [rgb(p["hex"]) for p in palette]
    exact = {c:i for i,c in enumerate(palette_rgb)}

    im = Image.open(SRC).convert("RGBA")
    if im.size != (800,960):
        raise RuntimeError(f"Unexpected master size {im.size}")

    bbox = im.getchannel("A").getbbox()
    if bbox != (32,96,768,864):
        raise RuntimeError(f"Unexpected alpha bbox {bbox}; feet/canvas geometry changed")

    px = im.load()
    matrix = []
    counts = Counter()
    for gy in range(120):
        row = []
        for gx in range(100):
            r,g,b,a = px[gx*8+4, gy*8+4]
            if a < 128:
                row.append(None)
                continue
            idx = exact.get((r,g,b))
            if idx is None:
                # Safety fallback: nearest palette colour.
                idx = min(
                    range(len(palette_rgb)),
                    key=lambda i: sum((palette_rgb[i][k] - (r,g,b)[k]) ** 2 for k in range(3))
                )
            sym = SYMBOLS[idx]
            row.append(sym)
            counts[sym] += 1
        matrix.append(row)

    threads = []
    for i,p in enumerate(palette):
        sym = SYMBOLS[i]
        if counts[sym]:
            threads.append({
                "symbol": sym,
                "dmc": str(p["dmc"]),
                "color": p["hex"].upper(),
                "name": p.get("name", f"DMC {p['dmc']}"),
                "stitches": counts[sym],
            })
    return matrix, threads

def update_pattern(suffix, matrix, threads):
    code = f"I0001-{suffix}"
    w,h = GRIDS[suffix]
    path = PATTERNS / code / "pattern.json"
    d = read_json(path)
    d.update({
        "code": code,
        "base_design_id": "I0001",
        "technique_code": suffix,
        "collection": "baby-nursery",
        "palette_collection": "baby-nursery",
        "status": "ready",
        "source_asset": "collections/baby-nursery/source-designs/I0001-teddy-bear.png",
        "stitch_width": w,
        "stitch_height": h,
        "total_stitches": sum(1 for row in matrix for v in row if v),
        "threads": threads,
        "matrix": matrix,
    })
    write_json(path, d)

def update_product(suffix):
    code = f"I0001-{suffix}"
    path = PRODUCTS / code / "product.json"
    d = read_json(path)
    d["source_artwork"] = "collections/baby-nursery/source-designs/I0001-teddy-bear.png"
    d["page_1_asset"] = PAGE1[suffix]
    d["render_ready"] = True
    d["status"] = "active"
    write_json(path, d)

def main():
    cs_matrix, cs_threads = build_cs_matrix()
    update_pattern("CS", cs_matrix, cs_threads)

    for suffix in ("C2C","TC","LH"):
        w,h = GRIDS[suffix]
        m,t = bg.downsample(cs_matrix, cs_threads, w, h)
        update_pattern(suffix, m, t)

    for suffix in SUFFIXES:
        update_product(suffix)

    # Final structural checks: full feet must remain within the master and not touch bottom.
    im = Image.open(SRC).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox[3] > 864:
        raise RuntimeError(f"Feet extend below approved boundary: {bbox}")
    if 960 - bbox[3] < 80:
        raise RuntimeError(f"Insufficient transparent margin below feet: {960-bbox[3]}px")

    for suffix in SUFFIXES:
        code = f"I0001-{suffix}"
        p = read_json(PATTERNS / code / "pattern.json")
        q = read_json(PRODUCTS / code / "product.json")
        if q["page_1_asset"] != PAGE1[suffix]:
            raise RuntimeError(f"{code}: wrong cover mapping")
        print(code, "stitches", p["total_stitches"], "colors", len(p["threads"]))

    print("I0001_CLEAN_FULL_FEET_REBUILT")
    print("SOURCE_BBOX", bbox)

if __name__ == "__main__":
    main()
