#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "iconic-destinations"
DESIGNS_PATH = COL_DIR / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PIXEL_DIR = COL_DIR / "pixel-sources"
SOURCE_DIR = COL_DIR / "source-designs"
ASSET_DIR = COL_DIR / "assets"
SOURCE_MOSAIC = ASSET_DIR / "iconic-mosaic-grid-source.webp"

WIDTH = 100
HEIGHT = 120
COLS = 10
ROWS = 6
COUNT = COLS * ROWS
MOSAIC_SIZE = (COLS * WIDTH, ROWS * HEIGHT)

# The generated mosaic has its separator centered exactly on the nominal
# 100x120 cell boundaries. We never search for a "whiter" nearby column:
# doing that can lock onto white architecture/clouds inside a neighbouring
# image. We crop only at the fixed mathematical grid and clean the two
# outermost pixels of each tile in-place, so no adjacent-image pixel can
# ever enter the result.
CLEAN_BORDER = 2


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_fixed_border(tile: Image.Image) -> Image.Image:
    if tile.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"raw tile is {tile.size}, expected {(WIDTH, HEIGHT)}")

    out = tile.copy()
    px = out.load()

    # Replace border pixels only with pixels from the same tile.
    # This removes white separator lines/compression halos while preserving
    # the exact 100x120 geometry and never resampling the artwork.
    for y in range(HEIGHT):
        left_value = px[CLEAN_BORDER, y]
        right_value = px[WIDTH - CLEAN_BORDER - 1, y]
        for x in range(CLEAN_BORDER):
            px[x, y] = left_value
        for x in range(WIDTH - CLEAN_BORDER, WIDTH):
            px[x, y] = right_value

    for x in range(WIDTH):
        top_value = px[x, CLEAN_BORDER]
        bottom_value = px[x, HEIGHT - CLEAN_BORDER - 1]
        for y in range(CLEAN_BORDER):
            px[x, y] = top_value
        for y in range(HEIGHT - CLEAN_BORDER, HEIGHT):
            px[x, y] = bottom_value

    if out.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"cleaned tile is {out.size}, expected {(WIDTH, HEIGHT)}")
    return out


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

    if len(indexes) != WIDTH * HEIGHT:
        raise RuntimeError(f"Expected {WIDTH * HEIGHT} pixels, got {len(indexes)}")

    return base64.b64encode(zlib.compress(bytes(raw), 9)).decode("ascii"), len(rgb)


def main():
    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} designs, got {len(designs)}")

    if not SOURCE_MOSAIC.is_file():
        raise SystemExit(f"Missing source mosaic: {SOURCE_MOSAIC}")

    mosaic = Image.open(SOURCE_MOSAIC).convert("RGB")
    if mosaic.size != MOSAIC_SIZE:
        raise SystemExit(
            f"Source mosaic must be exactly {MOSAIC_SIZE[0]}x{MOSAIC_SIZE[1]}; "
            f"got {mosaic.size}. No resizing is allowed."
        )

    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    queue_items = []

    for idx, design in enumerate(designs):
        row, col = divmod(idx, COLS)
        base = design["base_design_id"]
        slug = design["slug"]

        x0 = col * WIDTH
        y0 = row * HEIGHT
        raw_tile = mosaic.crop((x0, y0, x0 + WIDTH, y0 + HEIGHT))

        if raw_tile.size != (WIDTH, HEIGHT):
            raise SystemExit(
                f"{base}: mathematical crop is {raw_tile.size}, expected 100x120; refusing import"
            )

        tile = clean_fixed_border(raw_tile)

        # Guardrail: the interior must be byte-for-byte the same as the
        # corresponding region of the mosaic. Only the 2px outer border may
        # be changed, so neighbouring artwork cannot leak into this image.
        raw_px = raw_tile.load()
        clean_px = tile.load()
        for y in range(CLEAN_BORDER, HEIGHT - CLEAN_BORDER):
            for x in range(CLEAN_BORDER, WIDTH - CLEAN_BORDER):
                if clean_px[x, y] != raw_px[x, y]:
                    raise SystemExit(f"{base}: interior pixel changed at {x},{y}; refusing import")

        if tile.size != (WIDTH, HEIGHT):
            raise SystemExit(f"{base}: final image is not exactly 100x120; refusing import")

        source_name = f"{base}-{slug}.png"
        source_path = SOURCE_DIR / source_name
        tile.save(source_path, optimize=True)

        with Image.open(source_path) as check:
            if check.size != (WIDTH, HEIGHT):
                raise SystemExit(
                    f"{base}: saved image is {check.size[0]}x{check.size[1]}, not 100x120; refusing import"
                )

        packed, colour_count = quantize_pixz(tile)
        (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")

        design["source_asset"] = f"collections/iconic-destinations/source-designs/{source_name}"
        design["planned_source_asset"] = design["source_asset"]
        design["artwork_status"] = "strict-fixed-grid-clean-border-100x120"
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

        print(
            f"VALID {base} row={row+1} col={col+1} "
            f"crop={x0},{y0},100,120 border_cleaned={CLEAN_BORDER}px size=100x120"
        )

    if len(queue_items) != COUNT:
        raise SystemExit(f"Expected 60 valid tiles, got {len(queue_items)}")

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "strict-fixed-grid-clean-border-100x120-v4"
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["notes"] = [
        "The 1000x720 source mosaic is split only on the mathematical 10x6 grid: x=0,100,...,1000 and y=0,120,...,720.",
        "No separator-search heuristic is used, so white architecture/clouds can never shift a crop into a neighbouring image.",
        "The outer 2px border of each 100x120 cell is cleaned in-place using pixels from that same cell; there is no resize/resample.",
        "Every saved source is validated at exactly 100x120 before the WooCommerce reset is allowed to run.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print("STRICT_MOSAIC_READY valid=60 exact=100x120 auto_continue=0")


if __name__ == "__main__":
    main()
