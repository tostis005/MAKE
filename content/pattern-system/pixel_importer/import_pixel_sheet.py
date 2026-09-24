#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SYSTEM = HERE.parent
TEMPLATE = SYSTEM / "multitech" / "templates" / "cross-stitch.html"
ENGINE_ASSETS = SYSTEM / "multitech" / "assets"

# Single-character symbols only. The importer never merges/reduces colours.
SYMBOLS = list(
    "ABCDEFGHJKLMNPQRSTUVWXYZ"
    "23456789"
    "!@#$%*+=?^~:;/\\|_-.,()[]{}"
)


def read_image(path: Path) -> Image.Image:
    im = Image.open(path)
    rgba = im.convert("RGBA")
    alpha = rgba.getchannel("A")
    lo, hi = alpha.getextrema()
    if lo != 255 or hi != 255:
        raise ValueError(
            "Pixel importer requires a fully opaque source. "
            "Every source pixel must represent one stitch colour."
        )
    return rgba.convert("RGB")


def expected_sheet_size(
    tile_width: int,
    tile_height: int,
    rows: int,
    cols: int,
    origin_x: int = 0,
    origin_y: int = 0,
    gap_x: int = 0,
    gap_y: int = 0,
) -> tuple[int, int]:
    width = origin_x + cols * tile_width + max(0, cols - 1) * gap_x
    height = origin_y + rows * tile_height + max(0, rows - 1) * gap_y
    return width, height


def validate_sheet_geometry(
    im: Image.Image,
    tile_width: int,
    tile_height: int,
    rows: int,
    cols: int,
    origin_x: int = 0,
    origin_y: int = 0,
    gap_x: int = 0,
    gap_y: int = 0,
) -> None:
    for name, value in {
        "tile_width": tile_width,
        "tile_height": tile_height,
        "rows": rows,
        "cols": cols,
    }.items():
        if value <= 0:
            raise ValueError(f"{name} must be > 0")
    for name, value in {
        "origin_x": origin_x,
        "origin_y": origin_y,
        "gap_x": gap_x,
        "gap_y": gap_y,
    }.items():
        if value < 0:
            raise ValueError(f"{name} must be >= 0")

    expected = expected_sheet_size(
        tile_width, tile_height, rows, cols, origin_x, origin_y, gap_x, gap_y
    )
    if im.size != expected:
        raise ValueError(
            f"Sheet size is {im.width}x{im.height}, but the supplied geometry "
            f"requires exactly {expected[0]}x{expected[1]}. "
            "The importer will not resize, crop heuristically, or compensate."
        )


def extract_tiles(
    im: Image.Image,
    tile_width: int,
    tile_height: int,
    rows: int,
    cols: int,
    origin_x: int = 0,
    origin_y: int = 0,
    gap_x: int = 0,
    gap_y: int = 0,
):
    validate_sheet_geometry(
        im, tile_width, tile_height, rows, cols, origin_x, origin_y, gap_x, gap_y
    )
    number = 0
    for row in range(rows):
        for col in range(cols):
            number += 1
            left = origin_x + col * (tile_width + gap_x)
            top = origin_y + row * (tile_height + gap_y)
            box = (left, top, left + tile_width, top + tile_height)
            yield number, row, col, im.crop(box)


def build_exact_pattern(tile: Image.Image, code: str, title: str) -> dict:
    if tile.mode != "RGB":
        tile = tile.convert("RGB")

    width, height = tile.size
    pixels = list(tile.getdata())
    unique = list(dict.fromkeys(pixels))

    if len(unique) > len(SYMBOLS):
        raise ValueError(
            f"{code}: tile contains {len(unique)} exact RGB colours, but the "
            f"current one-character chart supports {len(SYMBOLS)}. "
            "No colours were merged. Provide a source with fewer exact colours."
        )

    symbol_for_rgb = {rgb: SYMBOLS[i] for i, rgb in enumerate(unique)}
    counts = Counter(pixels)
    threads = []
    for rgb in unique:
        symbol = symbol_for_rgb[rgb]
        hex_colour = "#%02X%02X%02X" % rgb
        threads.append(
            {
                "symbol": symbol,
                "dmc": hex_colour,
                "name": f"Exact RGB {rgb[0]}, {rgb[1]}, {rgb[2]}",
                "color": hex_colour,
                "stitches": counts[rgb],
            }
        )

    matrix = []
    for y in range(height):
        start = y * width
        row = pixels[start : start + width]
        matrix.append([symbol_for_rgb[rgb] for rgb in row])

    pattern = {
        "code": code,
        "source_mode": "pixel-exact",
        "title": title,
        "technique_code": "CS",
        "stitch_width": width,
        "stitch_height": height,
        "total_stitches": width * height,
        "threads": threads,
        "matrix": matrix,
    }

    assert len(pattern["matrix"]) == height
    assert all(len(row) == width for row in pattern["matrix"])
    assert sum(t["stitches"] for t in threads) == width * height
    return pattern


def pattern_pixels(pattern: dict) -> list[tuple[int, int, int]]:
    by_symbol = {
        t["symbol"]: tuple(int(t["color"][i : i + 2], 16) for i in (1, 3, 5))
        for t in pattern["threads"]
    }
    return [by_symbol[symbol] for row in pattern["matrix"] for symbol in row]


def validate_exact_roundtrip(tile: Image.Image, pattern: dict) -> None:
    original = list(tile.convert("RGB").getdata())
    reconstructed = pattern_pixels(pattern)
    if original != reconstructed:
        for i, (a, b) in enumerate(zip(original, reconstructed)):
            if a != b:
                y, x = divmod(i, tile.width)
                raise RuntimeError(
                    f"{pattern['code']}: exact pixel mismatch at x={x}, y={y}: "
                    f"source={a}, pattern={b}"
                )
        raise RuntimeError(f"{pattern['code']}: exact pixel validation failed")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def data_uri(path: Path) -> str:
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower())
    if not mime:
        raise ValueError(f"Unsupported asset type: {path}")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def pixel_template_html(data: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    thread_count_dmc = "$" + "{threadCount} DMC colours"
    thread_count_exact = "$" + "{threadCount} exact colours"
    replacements = {
        "<th>DMC</th>": "<th>Colour code</th>",
        thread_count_dmc: thread_count_exact,
        "Each chart symbol corresponds to one DMC colour.": "Each chart symbol corresponds to one exact source colour.",
        "Use this overview together with the enlarged symbol sections and the DMC colour key.": "Use this overview together with the enlarged symbol sections and the exact colour key.",
        "Keep the DMC key nearby": "Keep the colour key nearby",
        "Every symbol maps to the same DMC number shown on the thread-colour page.": "Every symbol maps to the same exact source colour shown on the thread-colour page.",
        "Use the DMC colour key on page 4 together with the colour and symbol charts throughout this booklet.": "Use the exact colour key on page 4 together with the colour and symbol charts throughout this booklet.",
    }
    for old, new in replacements.items():
        template = template.replace(old, new)

    template = re.sub(
        r'(<script id="template-pattern-data" type="application/json">)(.*?)(</script>)',
        lambda m: m.group(1)
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + m.group(3),
        template,
        count=1,
        flags=re.S,
    )

    cover = ENGINE_ASSETS / "cover-cross-stitch.webp"
    floral = ENGINE_ASSETS / "floral.png"
    assets = {"floral": data_uri(floral), "cover_image": data_uri(cover)}
    template = re.sub(
        r'(<script id="template-assets" type="application/json">)(.*?)(</script>)',
        lambda m: m.group(1)
        + json.dumps(assets, separators=(",", ":"))
        + m.group(3),
        template,
        count=1,
        flags=re.S,
    )
    return template


def render_pdf(pattern: dict, out_dir: Path, title: str) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "PDF rendering requires Playwright. Install playwright and Chromium first."
        ) from exc

    code = pattern["code"]
    data = {
        "product_code": code,
        "collection": "Pixel-by-pixel import",
        "collection_id": "pixel-by-pixel",
        "title": title,
        "technique": "cross-stitch",
        "subtitle": "Exact pixel-by-pixel cross-stitch pattern",
        "stitch_width": pattern["stitch_width"],
        "stitch_height": pattern["stitch_height"],
        "total_stitches": pattern["total_stitches"],
        "threads": pattern["threads"],
        "matrix": pattern["matrix"],
        "skill_level": "Pattern-defined",
        "stitch_type": "Full cross stitch",
        "website": "www.drielo.com",
        "materials": [
            "Embroidery floss matched to the listed exact colours",
            "Aida or preferred counted fabric",
            "Tapestry needle",
            "Embroidery hoop (optional)",
        ],
        "fabric_counts": [14, 16, 18],
        "size_options": [],
        "unit_label": "stitches",
        "measure_label": "Stitches",
        "cover_colour_label": "Colours",
        "cover_colour_value": f"{len(pattern['threads'])} exact colours",
        "facts_colour_label": "Colours used",
        "colour_unit": "exact colours",
        "finished_title": "Finished design",
        "finished_subtitle": f"Exact {pattern['stitch_width']} × {pattern['stitch_height']} cross-stitch preview",
        "finished_caption": "Every source pixel corresponds to exactly one full cross stitch.",
        "facts_title": "Pattern facts",
        "facts_subtitle": "Exact source geometry, with no resizing or colour reduction",
        "preview_label": "Exact cross-stitch preview",
        "cover_overlay": {
            "left": 29.0,
            "top": 12.0,
            "width": 48.0,
            "height": 58.0,
            "opacity": 0.96,
            "safe_inset_pct": 0.0,
        },
        "cover_stage_scale": 125,
        "colour_page_title": "Exact source colours",
        "colour_page_subtitle": "HEX/RGB colour key and stitch counts",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{code}.html"
    pdf_path = out_dir / f"Drielo_{code}.pdf"
    html_path.write_text(pixel_template_html(data), encoding="utf-8")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1600, "height": 2000}, device_scale_factor=1.5
        )
        page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=120000)
        page.wait_for_function(
            "document.documentElement.getAttribute('data-drielo-ready') === '1'",
            timeout=120000,
        )
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()

    if not pdf_path.is_file() or pdf_path.stat().st_size < 10000:
        raise RuntimeError(f"{code}: PDF export failed")
    return pdf_path


def import_sheet(args: argparse.Namespace) -> dict:
    source = Path(args.image).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    im = read_image(source)
    validate_sheet_geometry(
        im,
        args.tile_width,
        args.tile_height,
        args.rows,
        args.cols,
        args.origin_x,
        args.origin_y,
        args.gap_x,
        args.gap_y,
    )

    run_id = args.run_id or source.stem
    run_root = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else HERE / "output" / run_id
    )
    tiles_dir = run_root / "tiles"
    patterns_dir = run_root / "patterns"
    pdfs_dir = run_root / "pdfs"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    patterns_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_pdf:
        pdfs_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for number, row, col, tile in extract_tiles(
        im,
        args.tile_width,
        args.tile_height,
        args.rows,
        args.cols,
        args.origin_x,
        args.origin_y,
        args.gap_x,
        args.gap_y,
    ):
        serial = args.start_number + number - 1
        code = f"{args.code_prefix}{serial:04d}-CS"
        title = f"{args.title_prefix} {number:02d}"

        tile_path = tiles_dir / f"{code}.png"
        tile.save(tile_path, "PNG", optimize=False)

        persisted = Image.open(tile_path).convert("RGB")
        pattern = build_exact_pattern(persisted, code, title)
        pattern.update(
            {
                "source_sheet": source.name,
                "source_tile": tile_path.name,
                "sheet_row": row,
                "sheet_col": col,
                "source_box": {
                    "x": args.origin_x + col * (args.tile_width + args.gap_x),
                    "y": args.origin_y + row * (args.tile_height + args.gap_y),
                    "width": args.tile_width,
                    "height": args.tile_height,
                },
            }
        )
        validate_exact_roundtrip(persisted, pattern)

        pattern_path = patterns_dir / f"{code}.json"
        write_json(pattern_path, pattern)

        pdf_path = None
        if not args.skip_pdf:
            pdf_path = render_pdf(pattern, pdfs_dir / code, title)

        items.append(
            {
                "index": number,
                "row": row,
                "col": col,
                "code": code,
                "title": title,
                "tile": str(tile_path.relative_to(run_root)),
                "pattern": str(pattern_path.relative_to(run_root)),
                "pdf": (
                    str(pdf_path.relative_to(run_root)) if pdf_path is not None else None
                ),
                "width": args.tile_width,
                "height": args.tile_height,
                "stitches": args.tile_width * args.tile_height,
                "exact_colours": len(pattern["threads"]),
            }
        )
        print(
            f"{code}: row={row} col={col} "
            f"{args.tile_width}x{args.tile_height} "
            f"colours={len(pattern['threads'])} exact=OK"
        )

    manifest = {
        "mode": "pixel-by-pixel",
        "source": str(source),
        "geometry": {
            "tile_width": args.tile_width,
            "tile_height": args.tile_height,
            "rows": args.rows,
            "cols": args.cols,
            "origin_x": args.origin_x,
            "origin_y": args.origin_y,
            "gap_x": args.gap_x,
            "gap_y": args.gap_y,
        },
        "design_count": len(items),
        "rules": {
            "pixel_to_stitch": "1:1",
            "resizing": False,
            "colour_quantization": False,
            "dmc_mapping": False,
            "anti_alias_cleanup": False,
        },
        "items": items,
    }
    write_json(run_root / "manifest.json", manifest)
    print(f"IMPORT_OK designs={len(items)} output={run_root}")
    return manifest


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Split a sprite sheet into exact cross-stitch patterns. "
            "One source pixel becomes one stitch; no resizing or colour reduction."
        )
    )
    p.add_argument("--image", required=True, help="Path to the source sprite sheet.")
    p.add_argument("--tile-width", type=int, required=True)
    p.add_argument("--tile-height", type=int, required=True)
    p.add_argument("--rows", type=int, required=True)
    p.add_argument("--cols", type=int, required=True)
    p.add_argument("--origin-x", type=int, default=0)
    p.add_argument("--origin-y", type=int, default=0)
    p.add_argument("--gap-x", type=int, default=0)
    p.add_argument("--gap-y", type=int, default=0)
    p.add_argument("--code-prefix", default="PX")
    p.add_argument("--start-number", type=int, default=1)
    p.add_argument("--title-prefix", default="Pixel pattern")
    p.add_argument("--run-id")
    p.add_argument("--output-dir")
    p.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Generate exact tiles/pattern JSON only; skip Playwright PDF rendering.",
    )
    return p


def main() -> None:
    args = parser().parse_args()
    import_sheet(args)


if __name__ == "__main__":
    main()
