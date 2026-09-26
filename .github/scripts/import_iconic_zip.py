#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "iconic-destinations"
DESIGNS_PATH = COL_DIR / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
INPUT_DIR = COL_DIR / "input-pngs-q50"
PIXEL_DIR = COL_DIR / "pixel-sources"
ASSET_DIR = COL_DIR / "assets"

ZIP_PATH = ASSET_DIR / "iconic-60-pngs-q50.zip"

WIDTH = 100
HEIGHT = 120
COLS = 10
ROWS = 6
COUNT = COLS * ROWS
MAX_COLORS = 50
QUEUE_MODE = "direct-zip-png-only-60x100x120-v3"

OBSOLETE_MOSAIC_ASSETS = (
    ASSET_DIR / "iconic-60-pngs-q50-mosaic.png",
    ASSET_DIR / "iconic-mosaic-grid-1000x720.png",
    ASSET_DIR / "iconic-mosaic-grid-source.webp",
    COL_DIR / "reference-boards.json",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unique_colour_count(img: Image.Image) -> int:
    return len(set(img.convert("RGB").getdata()))


def expected_png_name(index: int) -> str:
    row, col = divmod(index, COLS)
    return f"destino_{row+1:02d}_{col+1:02d}.png"


def remove_obsolete_sources():
    # Iconic Destinations is ZIP/individual-PNG only. Remove every old mosaic
    # and board artifact so it cannot be selected accidentally by future code.
    for path in OBSOLETE_MOSAIC_ASSETS:
        path.unlink(missing_ok=True)

    # .pixz was an unnecessary intermediate source. The publisher now opens the
    # exact extracted PNG directly, so remove the old alternate source path too.
    if PIXEL_DIR.exists():
        for path in PIXEL_DIR.iterdir():
            if path.is_file() or path.is_symlink():
                path.unlink()
        try:
            PIXEL_DIR.rmdir()
        except OSError:
            pass


def main():
    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} designs, got {len(designs)}")

    if not ZIP_PATH.is_file():
        raise SystemExit(f"Missing approved ZIP source: {ZIP_PATH}")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    remove_obsolete_sources()

    # The ZIP is the only artwork source. Remove stale extracted PNGs first.
    for path in INPUT_DIR.glob("*.png"):
        path.unlink()

    queue_items = []

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
            raise SystemExit(
                f"ZIP filenames do not match expected set. missing={missing} extra={extra}"
            )

        for idx, design in enumerate(designs):
            base = design["base_design_id"]
            slug = design["slug"]
            name = expected_png_name(idx)
            raw = zf.read(name)

            with Image.open(io.BytesIO(raw)) as im:
                rgb = im.convert("RGB")
                if rgb.size != (WIDTH, HEIGHT):
                    raise SystemExit(
                        f"{base}: ZIP PNG {name} is {rgb.size[0]}x{rgb.size[1]}, expected 100x120"
                    )
                colour_count = unique_colour_count(rgb)
                if not (1 <= colour_count <= MAX_COLORS):
                    raise SystemExit(
                        f"{base}: ZIP PNG {name} has {colour_count} colours, expected <= 50"
                    )

            input_path = INPUT_DIR / name
            input_path.write_bytes(raw)
            if input_path.read_bytes() != raw:
                raise SystemExit(f"{base}: persisted PNG bytes differ from ZIP member {name}")

            with Image.open(input_path) as check:
                check_rgb = check.convert("RGB")
                if check_rgb.size != (WIDTH, HEIGHT):
                    raise SystemExit(f"{base}: persisted PNG changed dimensions")
                if unique_colour_count(check_rgb) != colour_count:
                    raise SystemExit(f"{base}: persisted PNG changed palette")

            input_rel = f"collections/iconic-destinations/input-pngs-q50/{name}"
            design["input_png"] = input_rel
            design["source_asset"] = input_rel
            design["artwork_status"] = "approved-zip-individual-png-100x120"
            design["palette_mode"] = "per-design"
            design["palette_status"] = "ready-for-direct-png-dmc-map"
            design["source_colour_count"] = colour_count
            design["dmc_colour_count"] = None
            design["target_master_grid"] = {
                "width": WIDTH,
                "height": HEIGHT,
                "max_long_side_stitches": HEIGHT,
            }
            design["target_chart_pages"] = 4

            # Remove legacy board/mosaic provenance. It is not valid production
            # artwork and must never participate in product generation.
            for key in (
                "reference_board",
                "planned_source_asset",
                "preview_mosaic",
                "mosaic_source",
                "mosaic_crop",
                "board_source",
            ):
                design.pop(key, None)

            queue_items.append({
                "base_design_id": base,
                "title_en": design["title_en"],
                "title_es": design["title_es"],
                "slug": slug,
                "input_png": input_rel,
                "status": "pending",
                "attempts": 0,
                "last_run": None,
                "last_error": None,
            })

            print(f"ZIP_PNG_SOURCE_OK {base} file={name} size=100x120 colours={colour_count}")

    designs_doc["count"] = COUNT
    designs_doc["source_policy"] = "individual-pngs-from-approved-zip-only"
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = QUEUE_MODE
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["source_zip"] = "collections/iconic-destinations/assets/iconic-60-pngs-q50.zip"
    queue.pop("preview_mosaic", None)
    queue["notes"] = [
        "The approved ZIP is the only artwork container for D0001-D0060.",
        "Each product reads its matching extracted input_png directly; there is no mosaic, board crop, or .pixz source path.",
        "Every PNG must be exactly 100x120 and contain no more than 50 colours.",
        "The publisher validates the extracted PNG against the corresponding ZIP member before generating PDF or WooCommerce assets.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print("ZIP_PNG_ONLY_READY pngs=60 each=100x120 max_colours=50 auto_continue=0")


if __name__ == "__main__":
    main()
