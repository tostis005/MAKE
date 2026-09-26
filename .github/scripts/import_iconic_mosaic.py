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

WHITE_THRESHOLD = 238
GUIDE_RATIO = 0.90
GUIDE_SEARCH = 8
MAX_GUIDE_DISTANCE_FROM_EDGE = 8


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_near_white(pixel) -> bool:
    r, g, b = pixel[:3]
    return r >= WHITE_THRESHOLD and g >= WHITE_THRESHOLD and b >= WHITE_THRESHOLD


def column_white_ratio(img: Image.Image, x: int) -> float:
    return sum(1 for y in range(img.height) if is_near_white(img.getpixel((x, y)))) / img.height


def row_white_ratio(img: Image.Image, y: int) -> float:
    return sum(1 for x in range(img.width) if is_near_white(img.getpixel((x, y)))) / img.width


def find_guide_bands(img: Image.Image, axis: str, step: int, count: int) -> list[tuple[int, int]]:
    if axis == "x":
        limit = img.width
        score = lambda p: column_white_ratio(img, p)
    else:
        limit = img.height
        score = lambda p: row_white_ratio(img, p)

    bands: list[tuple[int, int]] = []
    for n in range(1, count):
        expected = n * step
        lo = max(0, expected - GUIDE_SEARCH)
        hi = min(limit - 1, expected + GUIDE_SEARCH)

        best = max(range(lo, hi + 1), key=score)
        best_score = score(best)
        if best_score < GUIDE_RATIO:
            raise RuntimeError(
                f"Missing white {axis}-guide near {expected}: best={best} ratio={best_score:.3f}"
            )

        left = best
        right = best
        while left - 1 >= lo and score(left - 1) >= GUIDE_RATIO:
            left -= 1
        while right + 1 <= hi and score(right + 1) >= GUIDE_RATIO:
            right += 1
        bands.append((left, right))

    return bands


def exact_cell_window(
    index: int,
    total: int,
    size: int,
    canvas_size: int,
    guide_bands: list[tuple[int, int]],
) -> tuple[int, int]:
    if index == 0:
        left_center = 0.0
    else:
        a, b = guide_bands[index - 1]
        left_center = (a + b) / 2.0

    if index == total - 1:
        right_center = float(canvas_size)
    else:
        a, b = guide_bands[index]
        right_center = (a + b) / 2.0

    center = (left_center + right_center) / 2.0
    start = int(round(center - size / 2))
    start = max(0, min(canvas_size - size, start))
    return start, start + size


def fill_rect_from_column(img: Image.Image, x0: int, x1: int, src_x: int) -> None:
    px = img.load()
    src_x = max(0, min(img.width - 1, src_x))
    for y in range(img.height):
        value = px[src_x, y]
        for x in range(max(0, x0), min(img.width, x1)):
            px[x, y] = value


def fill_rect_from_row(img: Image.Image, y0: int, y1: int, src_y: int) -> None:
    px = img.load()
    src_y = max(0, min(img.height - 1, src_y))
    for x in range(img.width):
        value = px[x, src_y]
        for y in range(max(0, y0), min(img.height, y1)):
            px[x, y] = value


def clean_tile_guides(
    tile: Image.Image,
    col: int,
    row: int,
    x0: int,
    y0: int,
    vertical_bands: list[tuple[int, int]],
    horizontal_bands: list[tuple[int, int]],
) -> dict:
    if tile.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"raw tile is {tile.size}, expected {(WIDTH, HEIGHT)}")

    cleaned = tile.copy()
    meta = {"left": 0, "right": 0, "top": 0, "bottom": 0}

    if col > 0:
        band_lo, band_hi = vertical_bands[col - 1]
        rel_hi = band_hi - x0
        if rel_hi < 0 or rel_hi >= MAX_GUIDE_DISTANCE_FROM_EDGE:
            raise RuntimeError(
                f"left separator is not at tile edge: col={col+1} band={band_lo}-{band_hi} x0={x0}"
            )
        src_x = rel_hi + 1
        fill_rect_from_column(cleaned, 0, src_x, src_x)
        meta["left"] = src_x
    else:
        leading = 0
        while leading < 4 and column_white_ratio(cleaned, leading) >= GUIDE_RATIO:
            leading += 1
        if leading:
            fill_rect_from_column(cleaned, 0, leading, leading)
            meta["left"] = leading

    if col < COLS - 1:
        band_lo, band_hi = vertical_bands[col]
        rel_lo = band_lo - x0
        distance = WIDTH - 1 - rel_lo
        if rel_lo < WIDTH - MAX_GUIDE_DISTANCE_FROM_EDGE or rel_lo >= WIDTH:
            raise RuntimeError(
                f"right separator is not at tile edge: col={col+1} band={band_lo}-{band_hi} x0={x0}"
            )
        src_x = rel_lo - 1
        fill_rect_from_column(cleaned, rel_lo, WIDTH, src_x)
        meta["right"] = WIDTH - rel_lo
    else:
        trailing = 0
        while trailing < 4 and column_white_ratio(cleaned, WIDTH - 1 - trailing) >= GUIDE_RATIO:
            trailing += 1
        if trailing:
            fill_rect_from_column(cleaned, WIDTH - trailing, WIDTH, WIDTH - trailing - 1)
            meta["right"] = trailing

    if row > 0:
        band_lo, band_hi = horizontal_bands[row - 1]
        rel_hi = band_hi - y0
        if rel_hi < 0 or rel_hi >= MAX_GUIDE_DISTANCE_FROM_EDGE:
            raise RuntimeError(
                f"top separator is not at tile edge: row={row+1} band={band_lo}-{band_hi} y0={y0}"
            )
        src_y = rel_hi + 1
        fill_rect_from_row(cleaned, 0, src_y, src_y)
        meta["top"] = src_y
    else:
        leading = 0
        while leading < 4 and row_white_ratio(cleaned, leading) >= GUIDE_RATIO:
            leading += 1
        if leading:
            fill_rect_from_row(cleaned, 0, leading, leading)
            meta["top"] = leading

    if row < ROWS - 1:
        band_lo, band_hi = horizontal_bands[row]
        rel_lo = band_lo - y0
        if rel_lo < HEIGHT - MAX_GUIDE_DISTANCE_FROM_EDGE or rel_lo >= HEIGHT:
            raise RuntimeError(
                f"bottom separator is not at tile edge: row={row+1} band={band_lo}-{band_hi} y0={y0}"
            )
        src_y = rel_lo - 1
        fill_rect_from_row(cleaned, rel_lo, HEIGHT, src_y)
        meta["bottom"] = HEIGHT - rel_lo
    else:
        trailing = 0
        while trailing < 4 and row_white_ratio(cleaned, HEIGHT - 1 - trailing) >= GUIDE_RATIO:
            trailing += 1
        if trailing:
            fill_rect_from_row(cleaned, HEIGHT - trailing, HEIGHT, HEIGHT - trailing - 1)
            meta["bottom"] = trailing

    if cleaned.size != (WIDTH, HEIGHT):
        raise RuntimeError(f"cleaned tile is {cleaned.size}, expected {(WIDTH, HEIGHT)}")

    # A separator line inside the tile means the crop contains another image.
    for x in range(8, WIDTH - 8):
        if column_white_ratio(cleaned, x) >= 0.97:
            raise RuntimeError(f"interior vertical white separator remains at x={x}")
    for y in range(8, HEIGHT - 8):
        if row_white_ratio(cleaned, y) >= 0.97:
            raise RuntimeError(f"interior horizontal white separator remains at y={y}")

    return cleaned, meta


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

    if not SOURCE_MOSAIC.is_file():
        raise SystemExit(f"Missing source mosaic: {SOURCE_MOSAIC}")

    mosaic = Image.open(SOURCE_MOSAIC).convert("RGB")
    if mosaic.size != MOSAIC_SIZE:
        raise SystemExit(
            f"Source mosaic must already be exactly {MOSAIC_SIZE[0]}x{MOSAIC_SIZE[1]}; got {mosaic.size}. "
            "No mosaic resizing is allowed."
        )

    vertical_bands = find_guide_bands(mosaic, "x", WIDTH, COLS)
    horizontal_bands = find_guide_bands(mosaic, "y", HEIGHT, ROWS)

    print("VERTICAL_GUIDES", vertical_bands)
    print("HORIZONTAL_GUIDES", horizontal_bands)

    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    queue_items = []
    failures = []

    for idx, design in enumerate(designs):
        row, col = divmod(idx, COLS)
        base = design["base_design_id"]
        slug = design["slug"]

        x0, x1 = exact_cell_window(col, COLS, WIDTH, mosaic.width, vertical_bands)
        y0, y1 = exact_cell_window(row, ROWS, HEIGHT, mosaic.height, horizontal_bands)
        raw_tile = mosaic.crop((x0, y0, x1, y1))

        try:
            tile, trim_meta = clean_tile_guides(
                raw_tile,
                col,
                row,
                x0,
                y0,
                vertical_bands,
                horizontal_bands,
            )
        except Exception as exc:
            failures.append((base, slug, str(exc)))
            continue

        if tile.size != (WIDTH, HEIGHT):
            failures.append((base, slug, f"final size {tile.size[0]}x{tile.size[1]}"))
            continue

        source_name = f"{base}-{slug}.png"
        tile.save(SOURCE_DIR / source_name, optimize=True)

        packed, colour_count = quantize_pixz(tile)
        (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")

        design["source_asset"] = f"collections/iconic-destinations/source-designs/{source_name}"
        design["planned_source_asset"] = design["source_asset"]
        design["artwork_status"] = "strict-clean-grid-100x120"
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
            f"VALID {base} crop={x0},{y0},{WIDTH},{HEIGHT} "
            f"cleaned_edges={trim_meta} size={tile.size[0]}x{tile.size[1]}"
        )

    if failures:
        for base, slug, error in failures:
            print(f"INVALID {base} {slug}: {error}")
        raise SystemExit(
            f"Strict import stopped: {len(failures)} of {COUNT} images are invalid. "
            "Nothing should be published until all 60 are exactly 100x120."
        )

    if len(queue_items) != COUNT:
        raise SystemExit(f"Expected 60 valid tiles, got {len(queue_items)}")

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "strict-clean-grid-exact-100x120-v3"
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["notes"] = [
        "All 60 sources are extracted from the exact 1000x720 mosaic without resizing the mosaic.",
        "White separator bands and any sliver outside each separator are removed in-place without importing pixels from adjacent images.",
        "Every cleaned source is validated at exactly 100x120 before it can enter the publish queue.",
        "The reset workflow enables auto_continue only after all 60 sources pass validation and old WooCommerce products are deleted.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print("STRICT_MOSAIC_READY valid=60 size=100x120 auto_continue=0")


if __name__ == "__main__":
    main()
