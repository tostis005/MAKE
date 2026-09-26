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


def encode_pixz(img: Image.Image) -> tuple[str, int]:
    rgb = img.convert("RGB")
    if rgb.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"PNG is {rgb.size}, expected {(WIDTH, HEIGHT)}")

    colors = []
    color_to_index = {}
    indexes = bytearray()

    for pixel in rgb.getdata():
        if pixel not in color_to_index:
            if len(colors) >= MAX_COLORS:
                raise RuntimeError(f"PNG exceeds {MAX_COLORS} colours")
            color_to_index[pixel] = len(colors)
            colors.append(pixel)
        indexes.append(color_to_index[pixel])

    if len(indexes) != WIDTH * HEIGHT:
        raise RuntimeError(f"Expected {WIDTH * HEIGHT} pixels, got {len(indexes)}")

    raw = bytearray([len(colors)])
    for r, g, b in colors:
        raw.extend((r, g, b))
    raw.extend(indexes)

    return base64.b64encode(zlib.compress(bytes(raw), 9)).decode("ascii"), len(colors)


def expected_name(index: int) -> str:
    row, col = divmod(index, COLS)
    return f"destino_{row+1:02d}_{col+1:02d}.png"


def main():
    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} designs, got {len(designs)}")

    if not ZIP_PATH.is_file():
        raise SystemExit(f"Missing approved PNG ZIP: {ZIP_PATH}")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    for p in INPUT_DIR.glob("*.png"):
        p.unlink()

    expected = [expected_name(i) for i in range(COUNT)]
    preview = Image.new("RGB", (COLS * WIDTH, ROWS * HEIGHT))
    queue_items = []

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        png_names = [n for n in zf.namelist() if n.lower().endswith(".png") and not n.endswith("/")]
        if len(png_names) != COUNT:
            raise SystemExit(f"ZIP must contain exactly 60 PNGs, got {len(png_names)}")
        if set(png_names) != set(expected):
            missing = sorted(set(expected) - set(png_names))
            extra = sorted(set(png_names) - set(expected))
            raise SystemExit(f"ZIP filenames mismatch; missing={missing} extra={extra}")

        for idx, design in enumerate(designs):
            base = design["base_design_id"]
            slug = design["slug"]
            name = expected_name(idx)
            raw_bytes = zf.read(name)

            try:
                with Image.open(io.BytesIO(raw_bytes)) as im:
                    rgb = im.convert("RGB")
                    if rgb.size != (WIDTH, HEIGHT):
                        raise RuntimeError(f"{name} is {rgb.size}, expected 100x120")
                    colour_count = len(set(rgb.getdata()))
                    if not (1 <= colour_count <= MAX_COLORS):
                        raise RuntimeError(f"{name} has {colour_count} colours; max is 50")
                    packed, packed_colours = encode_pixz(rgb)
                    if packed_colours != colour_count:
                        raise RuntimeError(f"{name}: PNG/pixz palette mismatch")

                    row, col = divmod(idx, COLS)
                    preview.paste(rgb, (col * WIDTH, row * HEIGHT))
            except Exception as exc:
                raise SystemExit(f"{base}: invalid ZIP PNG {name}: {exc}") from exc

            # Keep the exact PNG bytes from the ZIP as the canonical input file.
            input_path = INPUT_DIR / name
            input_path.write_bytes(raw_bytes)
            (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")

            design["input_png"] = f"collections/iconic-destinations/input-pngs-q50/{name}"
            design["source_asset"] = design["input_png"]
            design["planned_source_asset"] = design["input_png"]
            design["artwork_status"] = "approved-zip-png-100x120"
            design["palette_mode"] = "per-design"
            design["palette_status"] = "zip-q50-source-ready-for-dmc-map"
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

            print(f"ZIP_PNG_READY {base} file={name} size=100x120 colours={colour_count}")

    if len(queue_items) != COUNT:
        raise SystemExit(f"Expected 60 valid PNGs, got {len(queue_items)}")

    preview.save(PREVIEW_PATH, "PNG", optimize=True)

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "zip-only-approved-q50-pngs-100x120-v2"
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["source_zip"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50.zip"
    queue["preview_mosaic"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50-mosaic.png"
    queue["notes"] = [
        "The 60-product batch is generated only from the 60 PNG files already stored inside iconic-60-pngs-q50.zip.",
        "The mosaic is not read and is not used as a product source.",
        "Every PNG must already be exactly 100x120 and contain no more than 50 RGB colours.",
        "Each product .pixz is encoded directly from its corresponding ZIP PNG without cropping, resizing or border cleanup.",
        "The preview mosaic is rebuilt from the ZIP PNGs only for visual inspection.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print("ZIP_ONLY_READY pngs=60 each=100x120 max_colours=50 auto_continue=0")


if __name__ == "__main__":
    main()
