#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import zipfile
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "iconic-destinations"
DESIGNS_PATH = COL_DIR / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PIXEL_DIR = COL_DIR / "pixel-sources"
INPUT_DIR = COL_DIR / "input-pngs-q50"
SOURCE_DIR = COL_DIR / "source-designs"
ASSET_DIR = COL_DIR / "assets"

# This is the 1000x720 white-grid mosaic approved for the 60-product batch.
SOURCE_MOSAIC = ASSET_DIR / "iconic-mosaic-grid-1000x720.png"
ZIP_PATH = ASSET_DIR / "iconic-60-pngs-q50.zip"
PREVIEW_PATH = ASSET_DIR / "iconic-60-pngs-q50-mosaic.png"

WIDTH = 100
HEIGHT = 120
COLS = 10
ROWS = 6
COUNT = COLS * ROWS
MOSAIC_SIZE = (COLS * WIDTH, ROWS * HEIGHT)
MAX_COLORS = 50
CLEAN_BORDER = 2


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_fixed_border(tile: Image.Image) -> Image.Image:
    """Remove the white grid halo without ever reading a neighbouring tile."""
    if tile.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"raw tile is {tile.size}, expected {(WIDTH, HEIGHT)}")

    out = tile.convert("RGB").copy()
    px = out.load()

    # Replace only the 2-pixel perimeter, using pixels from inside the same
    # 100x120 tile. Geometry stays exactly 100x120; no resize/resampling.
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

    return out


def quantize_50(tile: Image.Image) -> Image.Image:
    q = tile.convert("RGB").quantize(
        colors=MAX_COLORS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    return q.convert("RGB")


def unique_colour_count(img: Image.Image) -> int:
    return len(set(img.convert("RGB").getdata()))


def encode_pixz(tile: Image.Image) -> tuple[str, int]:
    """Encode the exact q50 PNG pixels as the importer source."""
    rgb = tile.convert("RGB")
    colors = []
    color_to_index = {}
    indexes = bytearray()

    for pixel in rgb.getdata():
        if pixel not in color_to_index:
            if len(colors) >= MAX_COLORS:
                raise RuntimeError("PNG exceeds 50 colours")
            color_to_index[pixel] = len(colors)
            colors.append(pixel)
        indexes.append(color_to_index[pixel])

    if len(indexes) != WIDTH * HEIGHT:
        raise RuntimeError(f"Expected 12000 cells, got {len(indexes)}")

    raw = bytearray([len(colors)])
    for r, g, b in colors:
        raw.extend((r, g, b))
    raw.extend(indexes)

    return base64.b64encode(zlib.compress(bytes(raw), 9)).decode("ascii"), len(colors)


def main():
    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} designs, got {len(designs)}")

    if not SOURCE_MOSAIC.is_file():
        raise SystemExit(f"Missing approved source mosaic: {SOURCE_MOSAIC}")

    mosaic = Image.open(SOURCE_MOSAIC).convert("RGB")
    if mosaic.size != MOSAIC_SIZE:
        raise SystemExit(
            f"Approved mosaic must be exactly 1000x720, got {mosaic.size}. "
            "No mosaic resizing is allowed."
        )

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale pack files so the ZIP is guaranteed to contain exactly 60.
    for p in INPUT_DIR.glob("*.png"):
        p.unlink()

    preview = Image.new("RGB", MOSAIC_SIZE)
    queue_items = []
    zip_entries = []

    for idx, design in enumerate(designs):
        row, col = divmod(idx, COLS)
        base = design["base_design_id"]
        slug = design["slug"]
        x0 = col * WIDTH
        y0 = row * HEIGHT

        raw_tile = mosaic.crop((x0, y0, x0 + WIDTH, y0 + HEIGHT))
        if raw_tile.size != (WIDTH, HEIGHT):
            raise SystemExit(f"{base}: mathematical crop is not exactly 100x120")

        cleaned = clean_fixed_border(raw_tile)
        tile = quantize_50(cleaned)

        if tile.size != (WIDTH, HEIGHT):
            raise SystemExit(f"{base}: q50 image is not exactly 100x120")

        colour_count = unique_colour_count(tile)
        if not (1 <= colour_count <= MAX_COLORS):
            raise SystemExit(f"{base}: invalid PNG colour count {colour_count}")

        pack_name = f"destino_{row+1:02d}_{col+1:02d}.png"
        pack_path = INPUT_DIR / pack_name
        tile.save(pack_path, "PNG", optimize=True)

        # Re-open the actual saved PNG: this is the file that is zipped and
        # from which the product's .pixz is encoded.
        with Image.open(pack_path) as check:
            check_rgb = check.convert("RGB")
            if check_rgb.size != (WIDTH, HEIGHT):
                raise SystemExit(f"{base}: saved PNG is not 100x120")
            saved_colours = unique_colour_count(check_rgb)
            if saved_colours > MAX_COLORS:
                raise SystemExit(f"{base}: saved PNG has {saved_colours} colours")
            packed, packed_colours = encode_pixz(check_rgb)
            if packed_colours != saved_colours:
                raise SystemExit(f"{base}: PNG/pixz palette mismatch")
            preview.paste(check_rgb, (x0, y0))

        (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")
        zip_entries.append(pack_path)

        design["input_png"] = f"collections/iconic-destinations/input-pngs-q50/{pack_name}"
        design["source_asset"] = design["input_png"]
        design["planned_source_asset"] = design["input_png"]
        design["artwork_status"] = "approved-q50-png-100x120"
        design["palette_mode"] = "per-design"
        design["palette_status"] = "q50-source-ready-for-dmc-map"
        design["source_colour_count"] = saved_colours
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
            "input_png": design["input_png"],
            "pixel_source": f"collections/iconic-destinations/pixel-sources/{base}.pixz",
            "status": "pending",
            "attempts": 0,
            "last_run": None,
            "last_error": None,
        })

        print(
            f"PNG_READY {base} {pack_name} crop={x0},{y0},100,120 "
            f"colours={saved_colours}"
        )

    if len(zip_entries) != COUNT:
        raise SystemExit(f"Expected 60 PNGs, got {len(zip_entries)}")

    preview.save(PREVIEW_PATH, "PNG", optimize=True)

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in zip_entries:
            zf.write(path, arcname=path.name)

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        png_names = [n for n in zf.namelist() if n.lower().endswith(".png")]
        if len(png_names) != COUNT or len(set(png_names)) != COUNT:
            raise SystemExit(f"ZIP must contain exactly 60 unique PNGs, got {len(png_names)}")

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "approved-q50-png-pack-100x120-v1"
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["source_zip"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50.zip"
    queue["preview_mosaic"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50-mosaic.png"
    queue["notes"] = [
        "The batch source is the approved 1000x720 white-grid mosaic.",
        "It is split mathematically into 60 cells of exactly 100x120.",
        "Only the outer 2px separator halo is cleaned, using pixels from the same cell.",
        "Each individual PNG is quantized to at most 50 colours with no dithering.",
        "The exact saved PNG is encoded into the corresponding .pixz and drives the WooCommerce/PDF product.",
        "The ZIP contains exactly those 60 individual PNGs.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print(f"APPROVED_PNG_PACK_READY pngs=60 zip={ZIP_PATH} preview={PREVIEW_PATH}")
    print("QUEUE_PAUSED auto_continue=0")


if __name__ == "__main__":
    main()
