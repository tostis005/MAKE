#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
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
ASSET_DIR = COL_DIR / "assets"

ZIP_PATH = ASSET_DIR / "iconic-60-pngs-q50.zip"
PREVIEW_PATH = ASSET_DIR / "iconic-60-pngs-q50-mosaic.png"

WIDTH = 100
HEIGHT = 120
COLS = 10
ROWS = 6
COUNT = COLS * ROWS
MAX_COLORS = 50


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unique_colour_count(img: Image.Image) -> int:
    return len(set(img.convert("RGB").getdata()))


def encode_pixz(tile: Image.Image) -> tuple[str, int]:
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
        raise RuntimeError(f"Expected {WIDTH * HEIGHT} cells, got {len(indexes)}")

    raw = bytearray([len(colors)])
    for r, g, b in colors:
        raw.extend((r, g, b))
    raw.extend(indexes)

    return base64.b64encode(zlib.compress(bytes(raw), 9)).decode("ascii"), len(colors)


def expected_png_name(index: int) -> str:
    row, col = divmod(index, COLS)
    return f"destino_{row+1:02d}_{col+1:02d}.png"


def main():
    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} designs, got {len(designs)}")

    if not ZIP_PATH.is_file():
        raise SystemExit(f"Missing approved ZIP source: {ZIP_PATH}")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    # The ZIP is the only artwork source. Remove stale extracted PNGs first.
    for p in INPUT_DIR.glob("*.png"):
        p.unlink()

    queue_items = []
    preview = Image.new("RGB", (COLS * WIDTH, ROWS * HEIGHT))

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = zf.namelist()
        png_names = [n for n in names if n.lower().endswith(".png")]

        if len(png_names) != COUNT or len(set(png_names)) != COUNT:
            raise SystemExit(
                f"Approved ZIP must contain exactly {COUNT} unique PNG files; got {len(png_names)}"
            )

        expected = [expected_png_name(i) for i in range(COUNT)]
        if sorted(png_names) != sorted(expected):
            missing = sorted(set(expected) - set(png_names))
            extra = sorted(set(png_names) - set(expected))
            raise SystemExit(f"ZIP filenames do not match expected 6x10 order. missing={missing} extra={extra}")

        for idx, design in enumerate(designs):
            base = design["base_design_id"]
            slug = design["slug"]
            name = expected_png_name(idx)
            row, col = divmod(idx, COLS)

            raw = zf.read(name)
            with Image.open(io.BytesIO(raw)) as im:
                tile = im.convert("RGB")
                if tile.size != (WIDTH, HEIGHT):
                    raise SystemExit(
                        f"{base}: ZIP PNG {name} is {tile.size[0]}x{tile.size[1]}, expected 100x120"
                    )

                colour_count = unique_colour_count(tile)
                if not (1 <= colour_count <= MAX_COLORS):
                    raise SystemExit(
                        f"{base}: ZIP PNG {name} has {colour_count} colours, expected <= 50"
                    )

                input_path = INPUT_DIR / name
                input_path.write_bytes(raw)

                # Re-open from disk to prove the exact persisted PNG is what drives the product.
                with Image.open(input_path) as check:
                    check_rgb = check.convert("RGB")
                    if check_rgb.size != (WIDTH, HEIGHT):
                        raise SystemExit(f"{base}: persisted PNG changed size")
                    if unique_colour_count(check_rgb) != colour_count:
                        raise SystemExit(f"{base}: persisted PNG changed palette")

                    packed, packed_colours = encode_pixz(check_rgb)
                    if packed_colours != colour_count:
                        raise SystemExit(f"{base}: PNG/pixz palette mismatch")

                    preview.paste(check_rgb, (col * WIDTH, row * HEIGHT))

            (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")

            design["input_png"] = f"collections/iconic-destinations/input-pngs-q50/{name}"
            design["source_asset"] = design["input_png"]
            design["planned_source_asset"] = design["input_png"]
            design["artwork_status"] = "approved-zip-q50-png-100x120"
            design["palette_mode"] = "per-design"
            design["palette_status"] = "zip-source-ready-for-dmc-map"
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
                "input_png": design["input_png"],
                "pixel_source": f"collections/iconic-destinations/pixel-sources/{base}.pixz",
                "status": "pending",
                "attempts": 0,
                "last_run": None,
                "last_error": None,
            })

            print(
                f"ZIP_SOURCE_OK {base} file={name} size=100x120 colours={colour_count}"
            )

    preview.save(PREVIEW_PATH, "PNG", optimize=True)

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "direct-approved-zip-60-pngs-100x120-v2"
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["source_zip"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50.zip"
    queue["preview_mosaic"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50-mosaic.png"
    queue["notes"] = [
        "The ZIP is the only artwork source for D0001-D0060.",
        "The mosaic is not read, cropped, resized, cleaned, or used for product generation.",
        "Each product is generated from its matching PNG inside the ZIP in row-major order.",
        "Every ZIP PNG must already be exactly 100x120 and contain no more than 50 colours.",
        "The exact PNG bytes are extracted, validated, converted to .pixz, and then used for PDF/WooCommerce generation.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print("ZIP_ONLY_READY pngs=60 each=100x120 max_colours=50 auto_continue=0")


if __name__ == "__main__":
    main()
