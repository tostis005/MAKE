#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "florals"
PATTERN_DIR = SYSTEM / "patterns" / "F0001-CS"
PRODUCT_DIR = SYSTEM / "products" / "F0001-CS"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
CATALOG = ROOT / "content" / "products" / "catalog.json"
SOURCE = COL_DIR / "source-designs" / "F0001-blue-daisy-pitcher.png"
REFERENCE = COL_DIR / "reference-masters" / "F0001-blue-daisy-pitcher-reference.png"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
CODE = "F0001-CS"
TITLE = "Blue Daisy Pitcher"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_pattern(collection: dict):
    if not SOURCE.is_file():
        raise RuntimeError(f"Missing redesigned source: {SOURCE}")
    im = Image.open(SOURCE).convert("RGBA")
    if im.size != (100, 120):
        raise RuntimeError(f"F0001 source must be exactly 100x120, got {im.size}")

    palette = collection["palette"]
    rgb_to_idx = {
        tuple(int(p["hex"][i:i+2], 16) for i in (1, 3, 5)): idx
        for idx, p in enumerate(palette)
    }

    matrix = []
    counts = Counter()
    for y in range(120):
        row = []
        for x in range(100):
            r, g, b, a = im.getpixel((x, y))
            if a < 128:
                row.append(None)
                continue
            idx = rgb_to_idx.get((r, g, b))
            if idx is None:
                raise RuntimeError(f"Out-of-palette pixel at {x},{y}: {(r,g,b)}")
            symbol = SYMBOLS[idx]
            row.append(symbol)
            counts[symbol] += 1
        matrix.append(row)

    if not counts:
        raise RuntimeError("F0001 source is empty")
    if len(counts) > 14:
        raise RuntimeError(f"F0001 uses {len(counts)} colours; max is 14")

    threads = []
    for idx, p in enumerate(palette):
        symbol = SYMBOLS[idx]
        if counts[symbol]:
            threads.append({
                "symbol": symbol,
                "dmc": str(p["dmc"]),
                "color": p["hex"].upper(),
                "name": p["name"],
                "stitches": counts[symbol],
            })

    pattern = {
        "code": CODE,
        "base_design_id": "F0001",
        "technique_code": "CS",
        "collection": "florals",
        "palette_collection": "florals",
        "status": "ready",
        "source_asset": "collections/florals/source-designs/F0001-blue-daisy-pitcher.png",
        "reference_asset": "collections/florals/reference-masters/F0001-blue-daisy-pitcher-reference.png",
        "stitch_width": 100,
        "stitch_height": 120,
        "total_stitches": sum(counts.values()),
        "threads": threads,
        "matrix": matrix,
        "outline_policy": {"enabled": False},
        "external_white_cleanup": {"enabled": False},
        "source_policy": "manual-redesign-from-high-resolution-approved-reference",
    }
    write_json(PATTERN_DIR / "pattern.json", pattern)
    return pattern


def render_product(collection: dict, pattern: dict):
    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)

    data = bg.pattern_data(CODE, TITLE, "CS", pattern["matrix"], pattern["threads"])
    data["collection"] = collection["name_en"]
    data["collection_id"] = collection["id"]
    layout = collection["mockup_spec"]["technique_layouts"]["CS"]
    data["cover_overlay"] = layout["cover_overlay"]
    data["cover_stage_scale"] = layout["cover_stage_scale"]

    result = bg.render_one((CODE, "CS", data))
    pdf_target = STORE_FILES / f"Drielo_{CODE}.pdf"
    image_target = STORE_ASSETS / f"{CODE}-product.webp"
    galleries = [STORE_ASSETS / f"{CODE}-gallery-{i}.webp" for i in (2, 3, 4)]

    shutil.copy2(result["pdf"], pdf_target)
    shutil.copy2(result["image"], image_target)
    sources = result.get("gallery", [])
    if len(sources) != 3:
        raise RuntimeError(f"Renderer returned {len(sources)} gallery previews, expected 3")
    for src, dst in zip(sources, galleries):
        shutil.copy2(src, dst)

    if pdf_target.stat().st_size < 100000 or pdf_target.read_bytes()[:4] != b"%PDF":
        raise RuntimeError("Invalid F0001-CS PDF")
    if image_target.stat().st_size < 40000:
        raise RuntimeError("Invalid F0001-CS featured image")
    for g in galleries:
        if g.stat().st_size < 25000:
            raise RuntimeError(f"Invalid gallery image {g.name}")

    product = {
        "code": CODE,
        "base_design_id": "F0001",
        "technique_code": "CS",
        "collection": "florals",
        "title": TITLE,
        "pattern_file": "patterns/F0001-CS/pattern.json",
        "website": "www.drielo.com",
        "technique": "cross-stitch",
        "template": "cross-stitch",
        "source_artwork": "collections/florals/source-designs/F0001-blue-daisy-pitcher.png",
        "reference_artwork": "collections/florals/reference-masters/F0001-blue-daisy-pitcher-reference.png",
        "page_1_asset": "multitech/assets/cover-cross-stitch.webp",
        "render_ready": True,
        "status": "active",
    }
    write_json(PRODUCT_DIR / "product.json", product)


def update_catalog(collection: dict, pattern: dict):
    catalog = read_json(CATALOG)

    collection_row = {
        "id": "florals",
        "name": "Florals",
        "slug": "florals",
        "name_en": "Florals",
        "name_es": "Florales",
        "description": "Floral and botanical downloadable patterns in a coordinated 24-colour palette.",
        "description_en": "Floral and botanical downloadable patterns in a coordinated 24-colour palette.",
        "description_es": "Patrones florales y botánicos descargables con una paleta coordinada de 24 colores.",
        "palette_hex": [p["hex"] for p in collection["palette"]],
        "thread_codes": [str(p["dmc"]) for p in collection["palette"]],
        "cover_asset": "assets/F0001-CS-product.webp",
        "techniques": ["cross-stitch"],
    }
    cols = catalog.setdefault("collections", [])
    for i, row in enumerate(cols):
        if row.get("slug") == "florals":
            cols[i] = collection_row
            break
    else:
        cols.append(collection_row)

    cat = {
        "name": "Florals",
        "slug": "cross-stitch-florals",
        "parent": "cross-stitch-patterns",
        "name_en": "Florals",
        "name_es": "Florales",
    }
    cats = catalog.setdefault("categories", [])
    for i, row in enumerate(cats):
        if row.get("slug") == cat["slug"]:
            cats[i] = cat
            break
    else:
        cats.append(cat)

    total = pattern["total_stitches"]
    colors = len(pattern["threads"])
    short_en = (
        f"Downloadable Blue Daisy Pitcher cross stitch pattern PDF. "
        f"100 × 120 stitches; {total:,} stitches; {colors} DMC colours. Pattern code: {CODE}."
    )
    short_es = (
        f"Patrón PDF descargable de punto de cruz de una jarra azul con margaritas. "
        f"100 × 120 puntos; {total:,} puntos; {colors} colores DMC. Código: {CODE}."
    )
    desc_en = (
        f"<p><strong>Blue Daisy Pitcher Cross Stitch Pattern PDF</strong> is a redesigned, "
        f"clean pixel-by-pixel floral pattern from Drielo's Florals collection.</p>"
        f"<p><strong>Digital product only:</strong> no finished item or physical materials are included.</p>"
        f"<h3>Pattern details</h3><ul><li>Pattern code: {CODE}</li><li>Grid: 100 × 120 stitches</li>"
        f"<li>Total stitches: {total:,}</li><li>Colours: {colors} DMC colours</li>"
        f"<li>Technique: Counted cross stitch</li><li>Skill level: Beginner friendly</li></ul>"
        f"<h3>What you receive</h3><ul><li>PDF pattern</li><li>Finished-design preview</li>"
        f"<li>Colour key</li><li>Full-colour chart</li><li>Black-and-white symbol chart</li>"
        f"<li>Enlarged chart sections</li></ul><p>Personal use only.</p>"
    )
    desc_es = (
        f"<p><strong>Patrón PDF de punto de cruz: Jarra azul con margaritas</strong>.</p>"
        f"<p><strong>Solo producto digital:</strong> no incluye pieza terminada ni materiales físicos.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {CODE}</li><li>Cuadrícula: 100 × 120 puntos</li>"
        f"<li>Total: {total:,} puntos</li><li>Colores: {colors} colores DMC</li>"
        f"<li>Técnica: punto de cruz contado</li><li>Nivel: apto para principiantes</li></ul>"
        f"<p>Solo para uso personal.</p>"
    )
    revision = int(os.environ.get("DRIELO_GALLERY_REVISION", "0") or 0)
    if revision <= 0:
        revision = 202609240001

    row = {
        "code": CODE,
        "sku": "DRIELO-F0001-CS",
        "title": "Blue Daisy Pitcher Cross Stitch Pattern PDF",
        "title_en": "Blue Daisy Pitcher Cross Stitch Pattern PDF",
        "title_es": "Patrón PDF de punto de cruz: Jarra azul con margaritas",
        "slug": "blue-daisy-pitcher-cross-stitch-pattern",
        "price": 4.99,
        "collection": "florals",
        "stitches": total,
        "grid": "100 × 120 stitches",
        "colours": colors,
        "color_count": colors,
        "grid_width": 100,
        "grid_height": 120,
        "skill": "Beginner friendly",
        "skill_en": "Beginner friendly",
        "skill_es": "Apto para principiantes",
        "stitch_type": "Counted cross stitch",
        "stitch_type_en": "Counted cross stitch",
        "stitch_type_es": "Punto de cruz contado",
        "short_description": short_en,
        "short_description_en": short_en,
        "short_description_es": short_es,
        "description": desc_en,
        "description_en": desc_en,
        "description_es": desc_es,
        "categories": ["cross-stitch-patterns", "cross-stitch-florals"],
        "tags": ["blue daisy pitcher", "cross stitch pdf", "floral cross stitch", "daisy pattern", "cottagecore", "digital pattern", "beginner pattern"],
        "gallery": [
            "assets/F0001-CS-gallery-2.webp",
            "assets/F0001-CS-gallery-3.webp",
            "assets/F0001-CS-gallery-4.webp",
        ],
        "gallery_preview_pages": {"facts": 3, "colour_a1": 8, "symbol_a1": 12},
        "download": "files/Drielo_F0001-CS.pdf",
        "featured_image": "assets/F0001-CS-product.webp",
        "gallery_revision": revision,
        "seo_title": "Blue Daisy Pitcher Cross Stitch Pattern PDF | Drielo",
        "seo_title_en": "Blue Daisy Pitcher Cross Stitch Pattern PDF | Drielo",
        "seo_title_es": "Patrón de punto de cruz Jarra azul con margaritas | Drielo",
        "meta_description": short_en[:155],
        "meta_description_en": short_en[:155],
        "meta_description_es": short_es[:155],
        "etsy_title_en": "Blue Daisy Pitcher Cross Stitch Pattern PDF",
        "etsy_title_es": "Patrón punto de cruz jarra azul con margaritas PDF",
        "etsy_description_en": short_en,
        "etsy_description_es": short_es,
        "etsy_tags_en": ["daisy cross stitch", "floral pattern", "cross stitch pdf", "blue pitcher", "cottagecore", "beginner pattern"],
        "etsy_tags_es": ["punto de cruz", "margaritas", "patrón floral", "jarra azul", "patrón pdf"],
        "design_id": CODE,
        "base_design_id": "F0001",
        "technique_code": "CS",
        "technique": "cross-stitch",
        "size_attribute_label": "Pattern size",
        "colour_attribute_label": "DMC colours",
        "type_attribute_label": "Technique",
        "count_attribute_label": "Total stitches",
        "filters": {
            "technique": ["cross-stitch"],
            "theme": ["flowers-botanicals"],
            "style": ["cottagecore"],
            "project": ["wall-art"],
            "orientation": ["portrait"],
            "difficulty": ["beginner"],
            "color-family": ["blue"],
            "season": ["spring"],
        },
    }

    products = [p for p in catalog.setdefault("products", []) if p.get("code") != CODE and p.get("collection") != "florals"]
    products.append(row)
    catalog["products"] = sorted(products, key=lambda x: x.get("code", ""))
    write_json(CATALOG, catalog)


def main():
    collection = read_json(COL_DIR / "collection.json")
    pattern = build_pattern(collection)

    src = Image.open(SOURCE).convert("RGBA")
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    ref = src.resize((800, 960), Image.Resampling.NEAREST)
    ref.save(REFERENCE, "PNG", optimize=True)

    render_product(collection, pattern)
    update_catalog(collection, pattern)
    print(json.dumps({
        "code": CODE,
        "stitches": pattern["total_stitches"],
        "colors": len(pattern["threads"]),
        "source": str(SOURCE.relative_to(SYSTEM)),
        "reference": str(REFERENCE.relative_to(SYSTEM)),
    }, indent=2))


if __name__ == "__main__":
    main()
