#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import json
import zipfile
import zlib
from pathlib import Path

import fitz
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "iconic-destinations"
DESIGNS_PATH = COL_DIR / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PDF_PATH = COL_DIR / "assets" / "iconic-60-source.pdf"
INPUT_DIR = COL_DIR / "pdf-pngs-q50"
PIXEL_DIR = COL_DIR / "pixel-sources"
PREVIEW_PATH = COL_DIR / "assets" / "iconic-60-pdf-preview.png"
ZIP_PATH = COL_DIR / "assets" / "iconic-60-pdf-pngs-q50.zip"

WIDTH = 100
HEIGHT = 120
COUNT = 60
MAX_COLORS = 50


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trim_white_margin(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda v: 255 if v > 8 else 0)
    bbox = mask.getbbox()
    if not bbox:
        raise RuntimeError("design page/image is blank")
    return rgb.crop(bbox)


def normalize_design(img: Image.Image) -> Image.Image:
    img = trim_white_margin(img)
    if img.width < 8 or img.height < 8:
        raise RuntimeError(f"design too small after trim: {img.size}")
    img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    q = img.quantize(
        colors=MAX_COLORS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    return q.convert("RGB")


def best_embedded_image(doc: fitz.Document, page: fitz.Page) -> Image.Image | None:
    best = None
    best_score = 0.0
    seen = set()
    for item in page.get_images(full=True):
        xref = int(item[0])
        if xref in seen:
            continue
        seen.add(xref)
        try:
            info = doc.extract_image(xref)
            data = info.get("image")
            if not data:
                continue
            im = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            continue
        area = im.width * im.height
        if im.width < 120 or im.height < 120 or area < 40000:
            continue
        aspect = im.width / im.height
        score = area * (1.25 if 0.55 <= aspect <= 1.15 else 1.0)
        if score > best_score:
            best_score = score
            best = im
    return best


def render_page(page: fitz.Page) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def extract_designs(pdf_path: Path) -> list[tuple[int, Image.Image]]:
    doc = fitz.open(pdf_path)
    if doc.page_count != COUNT:
        raise RuntimeError(
            f"PDF must contain exactly {COUNT} design pages; found {doc.page_count}. "
            "Refusing to guess or use a mosaic."
        )
    out = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        embedded = best_embedded_image(doc, page)
        source = embedded if embedded is not None else render_page(page)
        out.append((i + 1, source))
    return out


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
        raise RuntimeError(f"Expected 12000 pixels, got {len(indexes)}")

    raw = bytearray([len(colors)])
    for r, g, b in colors:
        raw.extend((r, g, b))
    raw.extend(indexes)
    return base64.b64encode(zlib.compress(bytes(raw), 9)).decode("ascii"), len(colors)


def main():
    if not PDF_PATH.is_file():
        raise SystemExit(
            f"Missing PDF source: {PDF_PATH}. This importer will not fall back to a mosaic or ZIP."
        )

    designs_doc = load_json(DESIGNS_PATH)
    designs = sorted(designs_doc.get("designs", []), key=lambda x: int(x["order"]))
    if len(designs) != COUNT:
        raise SystemExit(f"Expected {COUNT} design metadata rows, got {len(designs)}")

    extracted = extract_designs(PDF_PATH)
    if len(extracted) != COUNT:
        raise SystemExit(f"Expected {COUNT} PDF designs, got {len(extracted)}")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    for p in INPUT_DIR.glob("*.png"):
        p.unlink()

    preview = Image.new("RGB", (1000, 720), (255, 255, 255))
    queue_items = []
    png_paths = []

    for idx, ((page_number, source), design) in enumerate(zip(extracted, designs)):
        base = design["base_design_id"]
        slug = design["slug"]
        tile = normalize_design(source)

        if tile.size != (WIDTH, HEIGHT):
            raise SystemExit(f"{base}: normalized image is {tile.size}, expected 100x120")
        colour_count = len(set(tile.getdata()))
        if not (1 <= colour_count <= MAX_COLORS):
            raise SystemExit(f"{base}: image has {colour_count} colours, expected <=50")

        png_name = f"{base}-{slug}.png"
        png_path = INPUT_DIR / png_name
        tile.save(png_path, "PNG", optimize=True)

        with Image.open(png_path) as check:
            check_rgb = check.convert("RGB")
            if check_rgb.size != (WIDTH, HEIGHT):
                raise SystemExit(f"{base}: saved PNG is not 100x120")
            saved_colours = len(set(check_rgb.getdata()))
            if saved_colours > MAX_COLORS:
                raise SystemExit(f"{base}: saved PNG exceeds 50 colours")
            packed, packed_colours = encode_pixz(check_rgb)
            if packed_colours != saved_colours:
                raise SystemExit(f"{base}: PNG/pixz palette mismatch")

        (PIXEL_DIR / f"{base}.pixz").write_text(packed + "\n", encoding="ascii")
        png_paths.append(png_path)

        row, col = divmod(idx, 10)
        preview.paste(tile, (col * WIDTH, row * HEIGHT))

        rel = f"collections/iconic-destinations/pdf-pngs-q50/{png_name}"
        design["source_asset"] = rel
        design["planned_source_asset"] = rel
        design["input_png"] = rel
        design["source_pdf"] = "collections/iconic-destinations/assets/iconic-60-source.pdf"
        design["source_pdf_page"] = page_number
        design["artwork_status"] = "pdf-source-q50-100x120"
        design["palette_mode"] = "per-design"
        design["palette_status"] = "pdf-source-mapped-on-publish"
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
            "input_png": rel,
            "source_pdf_page": page_number,
            "pixel_source": f"collections/iconic-destinations/pixel-sources/{base}.pixz",
            "status": "pending",
            "attempts": 0,
            "last_run": None,
            "last_error": None,
        })
        print(f"PDF_DESIGN_READY {base} page={page_number} size=100x120 colours={saved_colours}")

    preview.save(PREVIEW_PATH, "PNG", optimize=True)

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in png_paths:
            zf.write(p, arcname=p.name)

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".png")]
        if len(names) != COUNT or len(set(names)) != COUNT:
            raise SystemExit("PDF-derived ZIP does not contain exactly 60 unique PNGs")

    designs_doc["count"] = COUNT
    designs_doc["designs"] = designs
    save_json(DESIGNS_PATH, designs_doc)

    queue = load_json(QUEUE_PATH)
    queue["mode"] = "pdf-source-60-designs-q50-v1"
    queue["auto_continue"] = False
    queue["max_attempts_per_design"] = 3
    queue["source_pdf"] = "collections/iconic-destinations/assets/iconic-60-source.pdf"
    queue["source_zip"] = "collections/iconic-destinations/assets/iconic-60-pdf-pngs-q50.zip"
    queue["preview_mosaic"] = "collections/iconic-destinations/assets/iconic-60-pdf-preview.png"
    queue["notes"] = [
        "The PDF is the only design source. No mosaic or previous PNG pack is used.",
        "The PDF must contain exactly 60 pages, one destination design per page.",
        "For each page the largest embedded artwork image is used; if unavailable, that page is rendered directly.",
        "Outer white page margins are removed, then the complete design is normalized to exactly 100x120 and quantized to at most 50 colours without dithering.",
        "The exact saved 100x120 PNG drives the corresponding .pixz, PDF pattern, storefront image, and WooCommerce product.",
    ]
    queue["items"] = queue_items
    queue.pop("invalid_items", None)
    save_json(QUEUE_PATH, queue)

    print("PDF_SOURCE_READY designs=60 each=100x120 max_colours=50 auto_continue=0")


if __name__ == "__main__":
    main()
