#!/usr/bin/env python3
"""Generate clean WooCommerce featured images from page-1 PDF preview artwork.

The PDF/gallery page contains a fixed Drielo layout: the ambient product photo
is the large left panel and technical metadata lives in the right rail.
This script crops only the ambient photo so WooCommerce never uses the
technical page composition as its catalogue thumbnail.
"""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "products" / "catalog.json"

# Normalised crop measured from the 636x900 master page-1 preview.
# x: 29..483, y: 207..769. This excludes title/footer/right metadata.
CROP = (29 / 636, 207 / 900, 483 / 636, 769 / 900)
OUTPUT_WIDTH = 1000


def generate(source: Path, target: Path) -> tuple[int, int]:
    with Image.open(source) as image:
        image = image.convert("RGB")
        w, h = image.size
        left = round(CROP[0] * w)
        top = round(CROP[1] * h)
        right = round(CROP[2] * w)
        bottom = round(CROP[3] * h)
        if right <= left or bottom <= top:
            raise RuntimeError(f"Invalid crop for {source}: {image.size}")

        crop = image.crop((left, top, right, bottom))
        out_h = round(OUTPUT_WIDTH * crop.height / crop.width)
        crop = crop.resize((OUTPUT_WIDTH, out_h), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        crop.save(target, "WEBP", quality=93, method=6)
        return crop.size


def main() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    generated = 0

    for row in data.get("products", []):
        source_rel = str(row.get("featured_source", "")).strip()
        target_rel = str(row.get("featured_image", "")).strip()
        if not source_rel:
            continue
        if not target_rel:
            raise SystemExit(f"{row.get('sku')}: featured_source requires featured_image")

        source = ROOT / "products" / source_rel
        target = ROOT / "products" / target_rel
        if not source.is_file():
            raise SystemExit(f"{row.get('sku')}: missing featured source {source_rel}")

        size = generate(source, target)
        generated += 1
        print(f"{row.get('sku')}: {source_rel} -> {target_rel} {size[0]}x{size[1]}")

    print(f"Generated {generated} clean featured images")


if __name__ == "__main__":
    main()
