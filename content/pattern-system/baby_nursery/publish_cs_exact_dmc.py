#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "baby-nursery"
COL_DIR = SYSTEM / "collections" / COLLECTION_ID
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections" / COLLECTION_ID
PALETTE_PATH = SOURCE_ROOT / "palette50_dmc.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
MAPPED_DIR = COL_DIR / "mapped-designs"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

WIDTH = 100
HEIGHT = 120
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") + list("!@#$%&*+=?^~:;/\\")
ALPHA_THRESHOLD = 128


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def design_record(base_id: str):
    doc = read_json(DESIGNS_PATH)
    row = next((x for x in doc.get("designs", []) if x.get("base_design_id") == base_id), None)
    if not row:
        raise RuntimeError(f"Unknown Baby Nursery design: {base_id}")
    if row.get("variants") != [f"{base_id}-CS"]:
        raise RuntimeError(f"{base_id}: Baby Nursery must be cross-stitch only")
    return row


def load_palette():
    doc = read_json(PALETTE_PATH)
    colors = doc.get("colors") or []
    if len(colors) != 50:
        raise RuntimeError(f"Expected 50 DMC colours, got {len(colors)}")
    out = {}
    dmc_seen = set()
    for row in colors:
        rgb = tuple(int(x) for x in row["rgb"])
        dmc = str(row["dmc"])
        if rgb in out:
            raise RuntimeError(f"Duplicate RGB in source palette: {rgb}")
        if dmc in dmc_seen:
            raise RuntimeError(f"Duplicate DMC in source palette: {dmc}")
        dmc_seen.add(dmc)
        out[rgb] = {
            "dmc": dmc,
            "name": str(row.get("name") or f"DMC {dmc}"),
            "rgb": rgb,
            "hex": str(row["hex"]).upper(),
        }
    return out


def build_pattern(base_id: str, design: dict):
    source_rel = str(design["source_asset"])
    source = (SYSTEM / source_rel).resolve()
    if not source.is_file():
        raise RuntimeError(f"Missing source PNG: {source}")

    palette = load_palette()
    with Image.open(source) as im:
        rgba = im.convert("RGBA")
        if rgba.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"{base_id}: expected 100x120, got {rgba.size}")
        pixels = list(rgba.getdata())

    used_order = []
    seen_dmc = set()
    mapped_entries = []
    visible_count = 0

    for r, g, b, a in pixels:
        if a < ALPHA_THRESHOLD:
            mapped_entries.append(None)
            continue
        if a != 255:
            raise RuntimeError(f"{base_id}: source contains semi-transparent pixel alpha={a}")
        rgb = (r, g, b)
        entry = palette.get(rgb)
        if entry is None:
            raise RuntimeError(f"{base_id}: source pixel {rgb} is outside palette50_dmc.json")
        visible_count += 1
        mapped_entries.append(entry)
        if entry["dmc"] not in seen_dmc:
            seen_dmc.add(entry["dmc"])
            used_order.append(entry["dmc"])

    if not visible_count:
        raise RuntimeError(f"{base_id}: source produced no stitches")
    if len(used_order) > len(SYMBOLS):
        raise RuntimeError(f"{base_id}: too many colours for chart symbols: {len(used_order)}")

    symbol_for = {dmc: SYMBOLS[i] for i, dmc in enumerate(used_order)}
    entry_by_dmc = {}
    counts = Counter()
    matrix = []
    for y in range(HEIGHT):
        row = []
        for x in range(WIDTH):
            entry = mapped_entries[y * WIDTH + x]
            if entry is None:
                row.append(None)
                continue
            dmc = entry["dmc"]
            entry_by_dmc[dmc] = entry
            sym = symbol_for[dmc]
            row.append(sym)
            counts[sym] += 1
        matrix.append(row)

    threads = []
    for dmc in used_order:
        entry = entry_by_dmc[dmc]
        sym = symbol_for[dmc]
        threads.append({
            "symbol": sym,
            "dmc": dmc,
            "color": entry["hex"],
            "name": entry["name"],
            "stitches": counts[sym],
        })

    mapped_rel = f"collections/baby-nursery/mapped-designs/{base_id}-{design['slug']}-dmc.png"
    mapped_path = SYSTEM / mapped_rel
    mapped_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, mapped_path)

    code = f"{base_id}-CS"
    pattern_path = PATTERNS / code / "pattern.json"
    pattern = read_json(pattern_path) if pattern_path.is_file() else {}
    pattern.update({
        "code": code,
        "base_design_id": base_id,
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "palette_mode": "exact-dmc50-source-no-requantization",
        "status": "ready",
        "source_asset": source_rel,
        "mapped_asset": mapped_rel,
        "alpha_threshold": ALPHA_THRESHOLD,
        "stitch_width": WIDTH,
        "stitch_height": HEIGHT,
        "total_stitches": visible_count,
        "threads": threads,
        "matrix": matrix,
    })
    write_json(pattern_path, pattern)

    product_path = PRODUCTS / code / "product.json"
    product = read_json(product_path) if product_path.is_file() else {}
    product.update({
        "code": code,
        "base_design_id": base_id,
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "title": design["product_title_en"],
        "title_en": design["product_title_en"],
        "title_es": design["product_title_es"],
        "design_title_en": design["title_en"],
        "design_title_es": design["title_es"],
        "design_slug": design["slug"],
        "technique": "cross-stitch",
        "pattern_file": f"patterns/{code}/pattern.json",
        "template": "cross-stitch.html",
        "website": "www.drielo.com",
        "status": "active",
        "render_ready": True,
        "renderer": "multitech",
        "source_artwork": source_rel,
        "mapped_artwork": mapped_rel,
        "page_1_asset": "collections/baby-nursery/assets/cover-cross-stitch.jpg",
        "palette_mode": "exact-dmc50-source-no-requantization",
    })
    write_json(product_path, product)

    return {
        "matrix": matrix,
        "threads": threads,
        "total_stitches": visible_count,
        "source_rel": source_rel,
        "mapped_rel": mapped_rel,
    }


def prepare_renderer_assets(collection: dict):
    temp = Path("/tmp/drielo-baby-exact-dmc-assets")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True, exist_ok=True)
    floral = bg.ENGINE_ASSETS / "floral.png"
    if floral.is_file():
        shutil.copy2(floral, temp / "floral.png")
    src_rel = collection["mockup_spec"]["technique_assets"]["CS"]
    src = SYSTEM / src_rel
    if not src.is_file():
        raise RuntimeError(f"Missing Baby Nursery cross-stitch cover: {src}")
    Image.open(src).convert("RGB").save(temp / "cover-cross-stitch.webp", "WEBP", quality=94, method=6)
    bg.ENGINE_ASSETS = temp


def render(base_id: str, design: dict, built: dict):
    code = f"{base_id}-CS"
    collection = read_json(COLLECTION_PATH)
    prepare_renderer_assets(collection)
    data = bg.pattern_data(code, design["title_en"], "CS", built["matrix"], built["threads"])
    data["collection"] = collection.get("name_en", "Baby & Nursery")
    data["collection_id"] = COLLECTION_ID
    layout = collection["mockup_spec"]["technique_layouts"]["CS"]
    data["cover_overlay"] = layout["cover_overlay"]
    data["cover_stage_scale"] = layout["cover_stage_scale"]

    result = bg.render_one((code, "CS", data))
    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)

    pdf = STORE_FILES / f"Drielo_{code}.pdf"
    image = STORE_ASSETS / f"{code}-product.webp"
    shutil.copy2(result["pdf"], pdf)
    shutil.copy2(result["image"], image)

    gallery = []
    sources = result.get("gallery", [])
    if len(sources) != 3:
        raise RuntimeError(f"{code}: expected three gallery images, got {len(sources)}")
    for n, src in enumerate(sources, start=2):
        dst = STORE_ASSETS / f"{code}-gallery-{n}.webp"
        shutil.copy2(src, dst)
        gallery.append(dst)

    if not pdf.is_file() or pdf.stat().st_size < 100000 or pdf.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(f"{code}: invalid PDF")
    if not image.is_file() or image.stat().st_size < 30000:
        raise RuntimeError(f"{code}: invalid product image")
    return {"pdf": pdf, "image": image, "gallery": gallery}


def update_catalog(base_id: str, design: dict, built: dict):
    code = f"{base_id}-CS"
    catalog = read_json(CATALOG_PATH)
    collection = read_json(COLLECTION_PATH)

    rows = catalog.setdefault("products", [])
    rows[:] = [p for p in rows if p.get("collection") != COLLECTION_ID or p.get("code") == code]

    colours = len(built["threads"])
    total = built["total_stitches"]
    title_en = design["product_title_en"]
    title_es = design["product_title_es"]
    short_en = (
        f"Downloadable {design['title_en']} cross-stitch pattern PDF from the Baby & Nursery collection. "
        f"Exact 100 × 120 source grid; transparent pixels remain unstitched; {total:,} full cross stitches "
        f"and {colours} exact DMC colours. Code: {code}."
    )
    short_es = (
        f"Patrón PDF descargable de {design['title_es'].lower()} para punto de cruz. "
        f"Cuadrícula fuente exacta de 100 × 120; los píxeles transparentes quedan sin bordar; "
        f"{total:,} cruces completas y {colours} colores DMC exactos. Código: {code}."
    )
    desc_en = (
        f"<p><strong>{title_en}</strong> is a digital counted cross-stitch pattern from the Baby & Nursery collection.</p>"
        f"<p>The approved 100 × 120 PNG is read pixel-for-pixel. Transparent pixels stay as blank Aida canvas, "
        f"and every visible RGB value is already tied directly to its DMC thread. No second colour quantization is applied.</p>"
        f"<h3>Pattern details</h3><ul><li>Code: {code}</li><li>Grid: 100 × 120</li>"
        f"<li>Full cross stitches: {total:,}</li><li>DMC colours: {colours}</li><li>Skill level: Beginner friendly</li></ul>"
        f"<p>Includes printable PDF, DMC key, colour and symbol charts and enlarged working sections. Digital product only.</p>"
    )
    desc_es = (
        f"<p><strong>{title_es}</strong> es un patrón digital de punto de cruz de la colección Bebé e Infantil.</p>"
        f"<p>El PNG aprobado de 100 × 120 se lee píxel a píxel. Los píxeles transparentes quedan como lienzo Aida sin bordar "
        f"y cada RGB visible ya corresponde directamente a su hilo DMC. No se realiza una segunda cuantización de color.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {code}</li><li>Cuadrícula: 100 × 120</li>"
        f"<li>Puntadas completas: {total:,}</li><li>Colores DMC: {colours}</li><li>Nivel: apto para principiantes</li></ul>"
        f"<p>Incluye PDF imprimible, clave DMC, gráficos a color y con símbolos y secciones ampliadas. Producto digital.</p>"
    )

    row = {
        "code": code,
        "sku": f"DRIELO-{code}",
        "price": 2.99,
        "categories": ["cross-stitch-patterns", "cross-stitch-baby-nursery"],
        "purchase_note_en": "Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
        "purchase_note_es": "Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        "title": title_en,
        "title_en": title_en,
        "title_es": title_es,
        "slug": f"{design['slug']}-cross-stitch-pattern",
        "collection": COLLECTION_ID,
        "stitches": total,
        "grid": "100 × 120 stitches",
        "colours": colours,
        "color_count": colours,
        "grid_width": 100,
        "grid_height": 120,
        "skill": "Beginner friendly",
        "skill_en": "Beginner friendly",
        "skill_es": "Apto para principiantes",
        "stitch_type": "Full cross stitch",
        "stitch_type_en": "Full cross stitch",
        "stitch_type_es": "Punto de cruz completo",
        "short_description": short_en,
        "short_description_en": short_en,
        "short_description_es": short_es,
        "description": desc_en,
        "description_en": desc_en,
        "description_es": desc_es,
        "gallery": [f"assets/{code}-gallery-{i}.webp" for i in (2, 3, 4)],
        "gallery_preview_pages": {"facts": 3, "colour_a1": 8, "symbol_a1": 12},
        "download": f"files/Drielo_{code}.pdf",
        "featured_image": f"assets/{code}-product.webp",
        "seo_title": f"{title_en} | Drielo",
        "seo_title_en": f"{title_en} | Drielo",
        "seo_title_es": f"{title_es} | Drielo",
        "meta_description": short_en[:155],
        "meta_description_en": short_en[:155],
        "meta_description_es": short_es[:155],
        "tags": [design["title_en"].lower(), "baby nursery", "cross stitch pdf", "counted cross stitch", "dmc pattern", "digital pattern"],
        "etsy_tags_en": [design["title_en"].lower(), "baby nursery", "cross stitch pdf", "counted cross stitch", "dmc pattern", "digital pattern"],
        "etsy_tags_es": [design["title_es"].lower(), "bebé", "infantil", "punto de cruz", "patrón digital", "descarga pdf"],
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
            "theme": ["baby-nursery"],
            "style": ["cute", "soft", "nursery"],
            "project": ["wall-art"],
            "orientation": ["portrait"],
            "difficulty": ["beginner"],
            "color-family": ["multicolor"],
            "season": [],
        },
    }

    idx = next((i for i, p in enumerate(rows) if p.get("code") == code), None)
    if idx is None:
        rows.append(row)
    else:
        rows[idx] = row
    catalog["retired_products"] = [x for x in catalog.get("retired_products", []) if x != row["sku"]]

    coll = next((c for c in catalog.get("collections", []) if c.get("slug") == COLLECTION_ID), None)
    if coll is None:
        coll = {"id": COLLECTION_ID, "slug": COLLECTION_ID}
        catalog.setdefault("collections", []).append(coll)
    coll.update({
        "id": COLLECTION_ID,
        "slug": COLLECTION_ID,
        "name": "Baby & Nursery",
        "name_en": "Baby & Nursery",
        "name_es": "Bebé e Infantil",
        "description": collection.get("description", ""),
        "description_en": collection.get("description", ""),
        "description_es": collection.get("description_es", ""),
        "techniques": ["cross-stitch"],
        "cover_asset": f"assets/{code}-product.webp",
        "visible": bool(collection.get("visible", False)),
        "palette_mode": "exact-dmc50-source-no-requantization",
    })
    write_json(CATALOG_PATH, catalog)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_id")
    args = ap.parse_args()
    base_id = args.design_id.strip().upper()
    if not base_id.startswith("I") or len(base_id) != 5:
        raise SystemExit("Expected I#### design id")

    design = design_record(base_id)
    built = build_pattern(base_id, design)
    rendered = render(base_id, design, built)
    update_catalog(base_id, design, built)

    print(json.dumps({
        "design_id": base_id,
        "code": f"{base_id}-CS",
        "title": design["title_en"],
        "stitches": built["total_stitches"],
        "dmc_colours": len(built["threads"]),
        "pdf_bytes": rendered["pdf"].stat().st_size,
        "image_bytes": rendered["image"].stat().st_size,
    }, ensure_ascii=False))
    print(f"BABY_EXACT_DMC_READY={base_id}")


if __name__ == "__main__":
    main()
