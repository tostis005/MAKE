#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import zlib
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "iconic-destinations"
COL_DIR = SYSTEM / "collections" / COLLECTION_ID
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
PIXEL_DIR = COL_DIR / "pixel-sources"
APPROVED_DIR = COL_DIR / "approved-pixel-designs"
SOURCE_DIR = COL_DIR / "source-designs"
DMC_PATH = SYSTEM / "data" / "dmc-colors.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

WIDTH = 100
HEIGHT = 120
CELL_COUNT = WIDTH * HEIGHT
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") + list("!@#$%&*+=?^~:;/\\")
if len(SYMBOLS) != 48:
    raise RuntimeError(f"Expected 48 safe chart symbols, got {len(SYMBOLS)}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def design_record(base_id: str):
    doc = read_json(DESIGNS_PATH)
    for item in doc["designs"]:
        if item["base_design_id"] == base_id:
            return item, doc
    raise RuntimeError(f"Unknown Iconic Destinations design: {base_id}")


def decode_pixel_source(base_id: str):
    path = PIXEL_DIR / f"{base_id}.pixz"
    if not path.is_file():
        raise FileNotFoundError(f"Missing exact pixel source: {path}")
    packed = base64.b64decode(path.read_text(encoding="utf-8").strip(), validate=True)
    raw = zlib.decompress(packed)
    if not raw:
        raise RuntimeError(f"{base_id}: empty pixel source")
    n = raw[0]
    palette_end = 1 + n * 3
    expected = palette_end + CELL_COUNT
    if n < 1 or n > 255 or len(raw) != expected:
        raise RuntimeError(f"{base_id}: malformed source palette={n} bytes={len(raw)} expected={expected}")
    palette = [tuple(raw[1+i*3:1+i*3+3]) for i in range(n)]
    indexes = list(raw[palette_end:])
    if max(indexes) >= n:
        raise RuntimeError(f"{base_id}: source contains invalid palette index")
    return palette, indexes


def dmc_table():
    rows = read_json(DMC_PATH)
    out = []
    seen = set()
    for row in rows:
        code = str(row.get("floss", "")).strip()
        if not code or code in seen:
            continue
        try:
            rgb = (int(row["r"]), int(row["g"]), int(row["b"]))
        except Exception:
            continue
        out.append({
            "dmc": code,
            "name": str(row.get("description") or f"DMC {code}"),
            "rgb": rgb,
            # The upstream sheet contains a handful of spreadsheet-corrupted
            # HEX cells. RGB is authoritative, so derive canonical HEX from it.
            "hex": "#%02X%02X%02X" % rgb,
        })
        seen.add(code)
    if len(out) < 400:
        raise RuntimeError(f"DMC reference looks incomplete: {len(out)} colours")
    return out


def nearest_dmc(colour, table):
    r, g, b = colour
    return min(
        table,
        key=lambda p: (
            2 * (r - p["rgb"][0]) ** 2
            + 4 * (g - p["rgb"][1]) ** 2
            + 3 * (b - p["rgb"][2]) ** 2
        ),
    )


def save_rgb_image(path: Path, pixels):
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (WIDTH, HEIGHT))
    im.putdata(pixels)
    im.save(path, "PNG", optimize=True)


def build_exact_pattern(base_id: str, design: dict):
    source_palette, indexes = decode_pixel_source(base_id)

    approved_path = APPROVED_DIR / f"{base_id}-{design['slug']}.png"
    save_rgb_image(approved_path, [source_palette[i] for i in indexes])

    table = dmc_table()
    source_to_dmc = [nearest_dmc(c, table) for c in source_palette]

    dmc_order = []
    by_code = {}
    for p in source_to_dmc:
        if p["dmc"] not in by_code:
            by_code[p["dmc"]] = p
            dmc_order.append(p["dmc"])

    if len(dmc_order) > len(SYMBOLS):
        raise RuntimeError(f"{base_id}: {len(dmc_order)} DMC colours exceed symbol capacity")

    symbol_for = {code: SYMBOLS[i] for i, code in enumerate(dmc_order)}
    matrix = []
    counts = Counter()
    final_pixels = []
    for y in range(HEIGHT):
        row = []
        for x in range(WIDTH):
            src_idx = indexes[y * WIDTH + x]
            dmc = source_to_dmc[src_idx]
            sym = symbol_for[dmc["dmc"]]
            row.append(sym)
            counts[sym] += 1
            final_pixels.append(dmc["rgb"])
        matrix.append(row)

    threads = []
    for code in dmc_order:
        p = by_code[code]
        sym = symbol_for[code]
        threads.append({
            "symbol": sym,
            "dmc": code,
            "name": p["name"],
            "color": p["hex"],
            "stitches": counts[sym],
        })

    final_rel = f"collections/{COLLECTION_ID}/source-designs/{base_id}-{design['slug']}.png"
    final_path = SYSTEM / final_rel
    save_rgb_image(final_path, final_pixels)

    # Hard one-to-one guardrail: the stored 100x120 image and the JSON matrix
    # must describe exactly the same 12,000 cells. There is no resampling here.
    colours_by_symbol = {t["symbol"]: tuple(int(t["color"][i:i+2], 16) for i in (1, 3, 5)) for t in threads}
    check = list(Image.open(final_path).convert("RGB").getdata())
    if len(check) != CELL_COUNT:
        raise RuntimeError(f"{base_id}: final image has wrong pixel count")
    for pos, rgb in enumerate(check):
        y, x = divmod(pos, WIDTH)
        if colours_by_symbol[matrix[y][x]] != rgb:
            raise RuntimeError(f"{base_id}: pixel/matrix mismatch at {x},{y}")

    return {
        "approved_path": approved_path,
        "final_path": final_path,
        "final_rel": final_rel,
        "matrix": matrix,
        "threads": threads,
        "total_stitches": CELL_COUNT,
        "source_colour_count": len(source_palette),
        "dmc_colour_count": len(threads),
    }


def render_design(base_id: str, design: dict, built: dict):
    code = f"{base_id}-CS"
    cfg = bg.TECHS["CS"]
    data = {
        "product_code": code,
        "collection": "Iconic Destinations",
        "collection_id": COLLECTION_ID,
        "title": design["title_en"],
        "subtitle": "A premium landmark cross-stitch pattern",
        "technique": "cross-stitch",
        "stitch_width": WIDTH,
        "stitch_height": HEIGHT,
        "total_stitches": CELL_COUNT,
        "threads": built["threads"],
        "matrix": built["matrix"],
        "skill_level": "Intermediate",
        "stitch_type": "Full cross stitch",
        "website": "www.drielo.com",
        "materials": cfg["materials"],
        "fabric_counts": [14, 16, 18],
        "unit_label": "stitches",
        "measure_label": "Stitches",
        "cover_colour_label": "Threads",
        "cover_colour_value": f"{len(built['threads'])} DMC colours",
        "facts_colour_label": "Threads used",
        "colour_unit": "DMC colours",
        "finished_title": "Finished design",
        "finished_subtitle": "Exact 100 × 120 cross-stitch preview",
        "finished_caption": "Every square in the source image corresponds to exactly one full cross stitch.",
        "facts_title": "Pattern facts",
        "facts_subtitle": "Everything you need before you start stitching",
        "preview_label": "Finished cross-stitch preview",
        "cover_overlay": cfg["cover_overlay"],
        "cover_stage_scale": cfg["cover_stage_scale"],
        "colour_page_title": "Thread colours",
        "colour_page_subtitle": "Per-design DMC colour key and stitch counts",
    }
    result = bg.render_one((code, "CS", data))

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(result["image"], STORE_ASSETS / f"{code}-product.webp")
    shutil.copy2(result["pdf"], STORE_FILES / f"Drielo_{code}.pdf")
    for n, src in enumerate(result["gallery"], start=2):
        shutil.copy2(src, STORE_ASSETS / f"{code}-gallery-{n}.webp")

    exact_preview = STORE_ASSETS / f"{code}-design.webp"
    # Use the exact organic stitch renderer for the pixel-by-pixel gallery image.
    # The source matrix remains 100 x 120 with one pixel = one stitch, but the
    # customer-facing preview now matches the same thread relief/grid model as
    # the PDF and product render instead of showing flat nearest-neighbour blocks.
    shutil.copy2(result["design_preview"], exact_preview)

    return result


def update_pattern_and_product(base_id: str, design: dict, built: dict):
    code = f"{base_id}-CS"
    pattern_path = PATTERNS / code / "pattern.json"
    product_path = PRODUCTS / code / "product.json"

    pattern = read_json(pattern_path)
    pattern.update({
        "code": code,
        "base_design_id": base_id,
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "palette_mode": "per-design",
        "status": "ready",
        "source_asset": built["final_rel"],
        "stitch_width": WIDTH,
        "stitch_height": HEIGHT,
        "total_stitches": CELL_COUNT,
        "threads": built["threads"],
        "matrix": built["matrix"],
    })
    write_json(pattern_path, pattern)

    product = read_json(product_path)
    product.update({
        "code": code,
        "base_design_id": base_id,
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "title": design["title_en"],
        "title_en": design["title_en"],
        "title_es": design["title_es"],
        "design_slug": design["slug"],
        "technique": "cross-stitch",
        "pattern_file": f"patterns/{code}/pattern.json",
        "template": "cross-stitch.html",
        "website": "www.drielo.com",
        "status": "ready",
        "render_ready": True,
        "renderer": "multitech",
        "source_artwork": built["final_rel"],
        "page_1_asset": "../../multitech/assets/cover-cross-stitch.webp",
        "palette_mode": "per-design",
    })
    write_json(product_path, product)


def product_catalog_row(base_id: str, design: dict, built: dict):
    code = f"{base_id}-CS"
    title_en = f"{design['title_en']} Cross Stitch Pattern PDF"
    title_es = f"Patrón PDF de punto de cruz: {design['title_es']}"
    colours = len(built["threads"])
    short_en = (
        f"Downloadable {design['title_en']} cross-stitch pattern from the Iconic Destinations collection. "
        f"Exact 100 × 120 chart; one source pixel equals one full cross stitch; {colours} DMC colours. Code: {code}."
    )
    short_es = (
        f"Patrón descargable de {design['title_es']} de la colección Destinos icónicos. "
        f"Gráfico exacto de 100 × 120; cada píxel de la imagen equivale a una puntada; {colours} colores DMC. Código: {code}."
    )
    desc_en = (
        f"<p><strong>{title_en}</strong> is a downloadable digital counted cross-stitch pattern from Drielo's Iconic Destinations collection.</p>"
        f"<p>The artwork uses an exact 100 × 120 source grid: <strong>one image pixel equals one full cross stitch</strong>, so the chart does not reinterpret or distort the design.</p>"
        f"<h3>Pattern details</h3><ul><li>Code: {code}</li><li>Grid: 100 × 120 stitches</li>"
        f"<li>Total stitches: {CELL_COUNT:,}</li><li>Colours: {colours} DMC colours selected for this design</li>"
        f"<li>Technique: Full cross stitch</li><li>Skill level: Intermediate</li></ul>"
        f"<h3>What you receive</h3><p>Printable PDF with finished preview, DMC key, colour and symbol charts, four enlarged chart sections and working guide.</p>"
        f"<p>Digital product only. Personal use only.</p>"
    )
    desc_es = (
        f"<p><strong>{title_es}</strong> es un patrón digital descargable de la colección Destinos icónicos.</p>"
        f"<p>El diseño utiliza una cuadrícula fuente exacta de 100 × 120: <strong>cada píxel equivale a una puntada completa</strong>, sin reinterpretar ni deformar la imagen.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {code}</li><li>Cuadrícula: 100 × 120</li>"
        f"<li>Puntadas: {CELL_COUNT:,}</li><li>Colores: {colours} colores DMC propios de este diseño</li>"
        f"<li>Técnica: punto de cruz completo</li><li>Nivel: intermedio</li></ul>"
        f"<p>Incluye PDF imprimible con vista previa, clave DMC, gráficos a color y con símbolos y cuatro secciones ampliadas.</p>"
        f"<p>Producto digital. Solo para uso personal.</p>"
    )

    tags = [
        "cross stitch", "travel pattern", "landmark pattern", "city cross stitch",
        "digital pattern", "instant download", "dmc pattern", design["slug"][:20],
    ]
    return {
        "code": code,
        "sku": f"DRIELO-{code}",
        "price": 2.99,
        "categories": ["cross-stitch-patterns"],
        "purchase_note_en": "Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
        "purchase_note_es": "Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        "title": title_en,
        "title_en": title_en,
        "title_es": title_es,
        "slug": f"{design['slug']}-cross-stitch-pattern",
        "collection": COLLECTION_ID,
        "stitches": CELL_COUNT,
        "grid": "100 × 120 stitches",
        "colours": colours,
        "color_count": colours,
        "grid_width": WIDTH,
        "grid_height": HEIGHT,
        "skill": "Intermediate",
        "skill_en": "Intermediate",
        "skill_es": "Intermedio",
        "stitch_type": "Full cross stitch",
        "stitch_type_en": "Full cross stitch",
        "stitch_type_es": "Punto de cruz completo",
        "short_description": short_en,
        "short_description_en": short_en,
        "short_description_es": short_es,
        "description": desc_en,
        "description_en": desc_en,
        "description_es": desc_es,
        "gallery": [
            f"assets/{code}-design.webp",
            f"assets/{code}-gallery-2.webp",
            f"assets/{code}-gallery-3.webp",
            f"assets/{code}-gallery-4.webp",
        ],
        "gallery_preview_pages": {"facts": 3, "colour_a1": 8, "symbol_a1": 12},
        "download": f"files/Drielo_{code}.pdf",
        "featured_image": f"assets/{code}-product.webp",
        "gallery_revision": int(os.environ.get("GITHUB_RUN_ID", "20260924")),
        "seo_title": f"{title_en} | Drielo",
        "seo_title_en": f"{title_en} | Drielo",
        "seo_title_es": f"{title_es} | Drielo",
        "meta_description": short_en[:155],
        "meta_description_en": short_en[:155],
        "meta_description_es": short_es[:155],
        "etsy_title_en": title_en,
        "etsy_title_es": title_es,
        "etsy_description_en": short_en,
        "etsy_description_es": short_es,
        "tags": tags[:13],
        "etsy_tags_en": tags[:13],
        "etsy_tags_es": ["punto de cruz", "viajes", "lugar emblemático", "patrón digital", "descarga pdf", design["title_es"].lower()[:20]],
        "design_id": code,
        "base_design_id": base_id,
        "technique_code": "CS",
        "technique": "cross-stitch",
        "size_attribute_label": "Pattern size",
        "colour_attribute_label": "DMC colours",
        "type_attribute_label": "Technique",
        "count_attribute_label": "Total stitches",
        "filters": {
            "technique": ["cross-stitch"],
            "theme": ["architecture-places"],
            "style": ["colorful"],
            "project": ["wall-art"],
            "orientation": ["portrait"],
            "difficulty": ["intermediate"],
            "color-family": ["multicolor"],
            "season": [],
        },
    }


def update_catalog(base_id: str, design: dict, built: dict):
    catalog = read_json(CATALOG_PATH)
    rows = catalog.setdefault("products", [])
    new_row = product_catalog_row(base_id, design, built)
    idx = next((i for i, p in enumerate(rows) if p.get("code") == new_row["code"]), None)
    if idx is None:
        rows.append(new_row)
    else:
        rows[idx] = new_row

    coll = next((c for c in catalog.get("collections", []) if c.get("slug") == COLLECTION_ID), None)
    if coll is None:
        raise RuntimeError("Iconic Destinations collection missing from catalog")
    coll["palette_mode"] = "per-design"
    coll["show_collection_palette"] = False
    coll["palette_hex"] = []
    coll["thread_codes"] = []
    coll["techniques"] = ["cross-stitch"]
    if base_id == "D0001" or not coll.get("cover_asset"):
        coll["cover_asset"] = "assets/D0001-CS-product.webp"

    write_json(CATALOG_PATH, catalog)


def update_design_manifest(base_id: str, doc: dict, built: dict):
    for item in doc["designs"]:
        if item["base_design_id"] != base_id:
            continue
        item["source_asset"] = built["final_rel"]
        item["artwork_status"] = "production-ready-exact-100x120"
        item["palette_status"] = "mapped-to-per-design-dmc"
        item["source_colour_count"] = built["source_colour_count"]
        item["dmc_colour_count"] = built["dmc_colour_count"]
        item["target_master_grid"] = {"width": WIDTH, "height": HEIGHT, "max_long_side_stitches": HEIGHT}
        item["target_chart_pages"] = 4
        break
    write_json(DESIGNS_PATH, doc)


def validate_outputs(base_id: str, built: dict):
    code = f"{base_id}-CS"
    pat = read_json(PATTERNS / code / "pattern.json")
    if (pat.get("stitch_width"), pat.get("stitch_height")) != (WIDTH, HEIGHT):
        raise RuntimeError(f"{code}: wrong dimensions")
    if len(pat.get("matrix", [])) != HEIGHT or any(len(r) != WIDTH for r in pat["matrix"]):
        raise RuntimeError(f"{code}: malformed matrix")
    if pat.get("total_stitches") != CELL_COUNT:
        raise RuntimeError(f"{code}: expected {CELL_COUNT} stitches")
    if not (30 <= len(pat.get("threads", [])) <= 48):
        raise RuntimeError(f"{code}: unexpected DMC colour count {len(pat.get('threads', []))}")
    pdf = STORE_FILES / f"Drielo_{code}.pdf"
    image = STORE_ASSETS / f"{code}-product.webp"
    if not pdf.is_file() or pdf.stat().st_size < 100000 or pdf.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(f"{code}: invalid PDF")
    if not image.is_file() or image.stat().st_size < 30000:
        raise RuntimeError(f"{code}: invalid product image")
    for suffix in ("design", "gallery-2", "gallery-3", "gallery-4"):
        p = STORE_ASSETS / f"{code}-{suffix}.webp"
        if not p.is_file() or p.stat().st_size < 5000:
            raise RuntimeError(f"{code}: missing gallery asset {p.name}")
    print(f"{code} VALID colours={len(pat['threads'])} stitches={pat['total_stitches']} pdf={pdf.stat().st_size}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: publish_design.py D0001")
    base_id = sys.argv[1].upper()
    if not base_id.startswith("D") or not base_id[1:].isdigit():
        raise SystemExit("Expected D#### base design id")

    design, doc = design_record(base_id)
    if design.get("variants") != [f"{base_id}-CS"]:
        raise RuntimeError(f"{base_id}: this collection is cross-stitch only")

    built = build_exact_pattern(base_id, design)
    update_pattern_and_product(base_id, design, built)
    render_design(base_id, design, built)
    update_catalog(base_id, design, built)
    update_design_manifest(base_id, doc, built)
    validate_outputs(base_id, built)


if __name__ == "__main__":
    main()
