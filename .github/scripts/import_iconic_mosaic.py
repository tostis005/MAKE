#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import json
import shutil
import zlib
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "iconic-destinations"
DESIGNS_PATH = COL_DIR / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PIXEL_DIR = COL_DIR / "pixel-sources"
SOURCE_DIR = COL_DIR / "source-designs"
ASSET_DIR = COL_DIR / "assets"
PACK_DIR = SYSTEM / "iconic_destinations" / "mosaic-upload"

WIDTH = 100
HEIGHT = 120
COLS = 10
ROWS = 6
COUNT = COLS * ROWS


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def decode_upload() -> bytes:
    parts = sorted(PACK_DIR.glob("part-*.txt"))
    if not parts:
        raise SystemExit(f"No mosaic upload parts found in {PACK_DIR}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    try:
        return base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f"Invalid mosaic upload: {exc}") from exc


def quantize_pixz(tile: Image.Image) -> tuple[str, int]:
    q = tile.convert("RGB").quantize(
        colors=50,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    data = list(q.getdata())
    used = sorted(set(data))
    if not 1 <= len(used) <= 50:
        raise RuntimeError(f"Unexpected palette size: {len(used)}")

    pal = q.getpalette()
    remap = {old: new for new, old in enumerate(used)}
    rgb = [tuple(pal[i * 3:i * 3 + 3]) for i in used]
    indexes = bytes(remap[i] for i in data)

    raw = bytearray([len(rgb)])
    for color in rgb:
        raw.extend(color)
    raw.extend(indexes)

    return base64.b64encode(zlib.compress(bytes(raw), 9)).decode("ascii"), len(rgb)


def main():
    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} designs, got {len(designs)}")

    source_bytes = decode_upload()
    try:
        mosaic = Image.open(io.BytesIO(source_bytes)).convert("RGB")
    except Exception as exc:
        raise SystemExit(f"Cannot decode mosaic image: {exc}") from exc

    # Normalize the uploaded inspection image to the exact production grid.
    mosaic = mosaic.resize((COLS * WIDTH, ROWS * HEIGHT), Image.Resampling.LANCZOS)

    # Re-establish pure white guide lines after image compression/resizing.
    # Two-pixel separators straddle each exact tile boundary.
    draw = ImageDraw.Draw(mosaic)
    for x in range(WIDTH, COLS * WIDTH, WIDTH):
        draw.rectangle((x - 1, 0, x, ROWS * HEIGHT - 1), fill=(255, 255, 255))
    for y in range(HEIGHT, ROWS * HEIGHT, HEIGHT):
        draw.rectangle((0, y - 1, COLS * WIDTH - 1, y), fill=(255, 255, 255))

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    mosaic.save(ASSET_DIR / "iconic-mosaic-grid-1000x720.png", optimize=True)

    queue_items = []
    for idx, design in enumerate(designs):
        row, col = divmod(idx, COLS)
        base = design["base_design_id"]
        slug = design["slug"]

        x0, y0 = col * WIDTH, row * HEIGHT
        cell = mosaic.crop((x0, y0, x0 + WIDTH, y0 + HEIGHT))

        # Remove the white separator pixel belonging to each adjacent grid line.
        left = 1 if col > 0 else 0
        top = 1 if row > 0 else 0
        right = WIDTH - (1 if col < COLS - 1 else 0)
        bottom = HEIGHT - (1 if row < ROWS - 1 else 0)
        content = cell.crop((left, top, right, bottom))

        # Restore the clean artwork to the exact production size.
        tile = content.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        source_name = f"{base}-{slug}.png"
        tile.save(SOURCE_DIR / source_name, optimize=True)

        packed, colour_count = quantize_pixz(tile)
        (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")

        design["source_asset"] = f"collections/iconic-destinations/source-designs/{source_name}"
        design["planned_source_asset"] = design["source_asset"]
        design["artwork_status"] = "production-ready-from-grid-mosaic"
        design["palette_mode"] = "per-design"
        design["palette_status"] = "source-mapped-on-publish"
        design["source_colour_count"] = colour_count
        design["dmc_colour_count"] = None
        design["target_master_grid"] = {
            "width": WIDTH,
            "height": HEIGHT,
            "max_long_side_stitches": HEIGHT,
        }
        design["target_chart_pages"] = 4

        queue_items.append({
            "base_design_id": base,
            "title_en": design["title_en"],
            "title_es": design["title_es"],
            "slug": slug,
            "pixel_source": f"collections/iconic-destinations/pixel-sources/{base}.pixz",
            "status": "pending",
            "attempts": 0,
            "last_run": None,
            "last_error": None,
        })

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "exact-grid-mosaic-cross-stitch-v2"
    queue["auto_continue"] = True
    queue["max_attempts_per_design"] = 3
    queue["notes"] = [
        "D0001-D0060 are rebuilt from the single 1000x720 grid mosaic.",
        "The workflow removes the white separator pixels and restores every tile to exactly 100x120.",
        "Each exact tile is quantized to at most 50 source colours, then the publisher maps it to DMC and generates PDF/storefront assets.",
    ]
    queue["items"] = queue_items
    save_json(QUEUE_PATH, queue)

    print("MOSAIC_READY size=1000x720 tiles=60 each=100x120 white_guides_removed=1")
    for idx, item in enumerate(queue_items, 1):
        print(f"{idx:02d} {item['base_design_id']} {item['slug']} pending")


if __name__ == "__main__":
    main()
