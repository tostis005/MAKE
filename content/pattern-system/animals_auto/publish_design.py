#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "animals"
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

SUFFIXES = ("CS", "C2C", "TC", "LH")
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
TECH_ES = {
    "CS": "punto de cruz",
    "C2C": "crochet C2C",
    "TC": "tapestry crochet",
    "LH": "alfombra latch hook",
}
TITLE_ES = {
    "CS": "Patrón PDF de punto de cruz",
    "C2C": "Patrón PDF de crochet C2C",
    "TC": "Patrón PDF de tapestry crochet",
    "LH": "Patrón PDF de alfombra latch hook",
}
TECH_TAGS = {
    "CS": ["cross stitch", "cross stitch pdf", "counted cross stitch", "dmc pattern"],
    "C2C": ["c2c crochet", "crochet graph", "c2c pattern", "blanket graph"],
    "TC": ["tapestry crochet", "crochet chart", "colorwork crochet", "wall hanging"],
    "LH": ["latch hook", "rug pattern pdf", "rug making", "latch hook rug"],
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rgb(hexv: str):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def design_record(base_id: str):
    for item in read_json(DESIGNS_PATH)["designs"]:
        if item["base_design_id"] == base_id:
            return item
    raise RuntimeError(f"Unknown Animals design: {base_id}")


def validate_canonical_assets(base_id: str, design: dict, collection: dict):
    source_path = SYSTEM / design["source_asset"]
    reference_path = SYSTEM / design["reference_asset"]
    if not source_path.is_file():
        raise RuntimeError(f"{base_id}: canonical source missing: {source_path}")
    if not reference_path.is_file():
        raise RuntimeError(f"{base_id}: canonical reference master missing: {reference_path}")

    source = Image.open(source_path).convert("RGBA")
    reference = Image.open(reference_path).convert("RGBA")
    if source.size != (100, 120):
        raise RuntimeError(f"{base_id}: source must be 100x120, got {source.size}")
    if reference.size != (800, 960):
        raise RuntimeError(f"{base_id}: reference must be 800x960, got {reference.size}")

    alpha = source.getchannel("A")
    amin, amax = alpha.getextrema()
    bbox = alpha.getbbox()
    if amin != 0 or amax == 0 or not bbox:
        raise RuntimeError(f"{base_id}: source must contain real transparency")
    if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= 100 or bbox[3] >= 120:
        raise RuntimeError(f"{base_id}: canonical source touches an edge: {bbox}")

    expected = source.resize((800, 960), Image.Resampling.NEAREST)
    if ImageChops.difference(expected, reference).getbbox() is not None:
        raise RuntimeError(f"{base_id}: reference master is not the exact 8x nearest-neighbour canonical source")

    allowed = {rgb(p["hex"]) for p in collection["palette"]}
    if len(allowed) != 24:
        raise RuntimeError(f"Animals master palette must contain exactly 24 colours, got {len(allowed)}")
    bad = set()
    for r, g, b, a in source.getdata():
        if a >= 128 and (r, g, b) not in allowed:
            bad.add((r, g, b))
            if len(bad) >= 8:
                break
    if bad:
        raise RuntimeError(f"{base_id}: canonical source contains colours outside the strict Animals palette: {sorted(bad)}")
    return source, bbox


def build_patterns(base_id: str, design: dict, collection: dict):
    source, bbox = validate_canonical_assets(base_id, design, collection)
    palette = collection["palette"]
    exact = {rgb(p["hex"]): i for i, p in enumerate(palette)}

    matrix = []
    counts = Counter()
    pix = source.load()
    for y in range(120):
        row = []
        for x in range(100):
            r, g, b, a = pix[x, y]
            if a < 128:
                row.append(None)
                continue
            idx = exact[(r, g, b)]
            sym = SYMBOLS[idx]
            row.append(sym)
            counts[sym] += 1
        matrix.append(row)
    if not counts:
        raise RuntimeError(f"{base_id}: empty canonical matrix")

    threads = []
    for i, p in enumerate(palette):
        sym = SYMBOLS[i]
        if counts[sym]:
            threads.append({
                "symbol": sym,
                "dmc": str(p["dmc"]),
                "color": p["hex"].upper(),
                "name": p.get("name", f"DMC {p['dmc']}"),
                "stitches": counts[sym],
            })

    matrices = {"CS": (matrix, threads)}
    for suffix in ("C2C", "TC", "LH"):
        cfg = bg.TECHS[suffix]
        matrices[suffix] = bg.downsample(matrix, threads, cfg["w"], cfg["h"])

    covers = collection["mockup_spec"]["technique_assets"]
    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        cfg = bg.TECHS[suffix]
        mat, th = matrices[suffix]
        pattern_path = PATTERNS / code / "pattern.json"
        product_path = PRODUCTS / code / "product.json"
        pattern = read_json(pattern_path) if pattern_path.is_file() else {}
        product = read_json(product_path) if product_path.is_file() else {}
        pattern.update({
            "code": code,
            "base_design_id": base_id,
            "technique_code": suffix,
            "collection": "animals",
            "palette_collection": "animals",
            "status": "ready",
            "source_asset": design["source_asset"],
            "reference_asset": design["reference_asset"],
            "stitch_width": cfg["w"],
            "stitch_height": cfg["h"],
            "total_stitches": sum(1 for r in mat for v in r if v),
            "threads": th,
            "matrix": mat,
        })
        write_json(pattern_path, pattern)
        product.update({
            "code": code,
            "base_design_id": base_id,
            "technique_code": suffix,
            "collection": "animals",
            "source_artwork": design["source_asset"],
            "reference_artwork": design["reference_asset"],
            "page_1_asset": covers[suffix],
            "render_ready": True,
            "status": "active",
            "palette_mode": "strict",
            "palette_size": 24,
            "transparent_source": True,
        })
        write_json(product_path, product)
    return bbox


def prepare_renderer_assets(collection: dict):
    temp = Path("/tmp/drielo-animals-auto-assets")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)
    shutil.copy2(bg.ENGINE_ASSETS / "floral.png", temp / "floral.png")
    targets = {
        "CS": "cover-cross-stitch.webp",
        "C2C": "cover-crochet.webp",
        "TC": "cover-c2c-crochet.webp",
        "LH": "cover-rug.webp",
    }
    for suffix, target in targets.items():
        rel = collection["mockup_spec"]["technique_assets"][suffix]
        src = (COL_DIR / rel).resolve()
        if not src.is_file():
            raise RuntimeError(f"{suffix}: configured Animals cover missing: {rel} -> {src}")
        Image.open(src).convert("RGB").save(temp / target, "WEBP", quality=94, method=6)
    bg.ENGINE_ASSETS = temp


def render_design(base_id: str, design: dict, collection: dict):
    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    prepare_renderer_assets(collection)
    results = {}
    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        pattern = read_json(PATTERNS / code / "pattern.json")
        data = bg.pattern_data(code, design["title_en"], suffix, pattern["matrix"], pattern["threads"])
        data["collection"] = collection["name_en"]
        data["collection_id"] = "animals"
        result = bg.render_one((code, suffix, data))

        pdf = STORE_FILES / f"Drielo_{code}.pdf"
        image = STORE_ASSETS / f"{code}-product.webp"
        gallery = [STORE_ASSETS / f"{code}-gallery-{i}.webp" for i in (2, 3, 4)]
        shutil.copy2(result["pdf"], pdf)
        shutil.copy2(result["image"], image)
        if len(result.get("gallery", [])) != 3:
            raise RuntimeError(f"{code}: renderer did not return three gallery previews")
        for src, dst in zip(result["gallery"], gallery):
            shutil.copy2(src, dst)

        if pdf.stat().st_size < 100000 or pdf.read_bytes()[:4] != b"%PDF":
            raise RuntimeError(f"{code}: invalid generated PDF")
        if image.stat().st_size < 50000:
            raise RuntimeError(f"{code}: invalid product image")
        for g in gallery:
            if not g.is_file() or g.stat().st_size < 30000:
                raise RuntimeError(f"{code}: invalid gallery preview {g.name}")
        results[suffix] = {
            "pdf_bytes": pdf.stat().st_size,
            "image_bytes": image.stat().st_size,
            "gallery_bytes": [g.stat().st_size for g in gallery],
            "stitches": pattern["total_stitches"],
            "colors": len(pattern["threads"]),
        }
    return results


def ensure_catalog_structure(catalog: dict, collection: dict):
    collections = catalog.setdefault("collections", [])
    if not any(c.get("slug") == "animals" for c in collections):
        collections.append({
            "id": "animals",
            "name": "Animals",
            "slug": "animals",
            "name_en": "Animals",
            "name_es": "Animales",
            "description": collection["description"],
            "description_en": collection["description"],
            "description_es": collection["description_es"],
            "palette_hex": [p["hex"].upper() for p in collection["palette"]],
            "thread_codes": [str(p["dmc"]) for p in collection["palette"]],
            "cover_asset": "assets/A0001-CS-product.webp",
            "techniques": collection["techniques"],
        })

    parents = {
        "CS": "cross-stitch-patterns",
        "C2C": "c2c-crochet-patterns",
        "TC": "tapestry-crochet-patterns",
        "LH": "latch-hook-rug-patterns",
    }
    categories = catalog.setdefault("categories", [])
    existing = {c.get("slug") for c in categories}
    for suffix, parent in parents.items():
        slug = f"{parent.replace('-patterns', '')}-animals"
        if slug not in existing:
            categories.append({
                "name": "Animals",
                "slug": slug,
                "parent": parent,
                "name_en": "Animals",
                "name_es": "Animales",
            })
    return parents


def update_catalog(base_id: str, design: dict, collection: dict):
    catalog = read_json(CATALOG_PATH)
    parents = ensure_catalog_structure(catalog, collection)
    rows = catalog.setdefault("products", [])
    by = {p.get("code"): p for p in rows}
    templates = {}
    for suffix in SUFFIXES:
        template = by.get(f"I0001-{suffix}") or by.get(f"P0001-{suffix}")
        if not template:
            raise RuntimeError(f"No catalogue template available for {suffix}")
        templates[suffix] = deepcopy(template)

    revision = int(os.environ.get("DRIELO_GALLERY_REVISION", 202609240000 + int(base_id[1:])))
    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        pattern = read_json(PATTERNS / code / "pattern.json")
        cfg = bg.TECHS[suffix]
        tech_es = TECH_ES[suffix]
        total = int(pattern["total_stitches"])
        colors = len(pattern["threads"])
        title_en = f"{design['title_en']} {cfg['display']} Pattern PDF"
        title_es = f"{TITLE_ES[suffix]}: {design['title_es']}"
        short_en = (
            f"Downloadable {design['title_en']} {cfg['display']} pattern PDF from Drielo's Animals collection. "
            f"{cfg['w']} × {cfg['h']} {cfg['unit_label']}; {total:,} {cfg['count_label'].lower()}; "
            f"{colors} colours from the fixed 24-colour Animals palette; beginner friendly. Pattern code: {code}."
        )
        short_es = (
            f"Patrón PDF descargable de {design['title_es'].lower()} para {tech_es}. "
            f"{cfg['w']} × {cfg['h']}; {total:,} posiciones; {colors} colores de la paleta fija de 24 colores de Animales; "
            f"apto para principiantes. Código: {code}."
        )
        desc_en = (
            f"<p><strong>{title_en}</strong> is a downloadable digital pattern from Drielo's Animals collection.</p>"
            f"<p><strong>Pattern code:</strong> {code}</p>"
            f"<p>The artwork comes directly from the approved canonical Animals reference and uses only the fixed 24-colour collection palette.</p>"
            f"<h3>Pattern details</h3><ul><li>Chart: {cfg['w']} × {cfg['h']} {cfg['unit_label']}</li>"
            f"<li>{cfg['count_label']}: {total:,}</li><li>Colours used: {colors}</li>"
            f"<li>Technique: {cfg['stitch_type']}</li><li>Beginner friendly</li></ul>"
            f"<h3>What you receive</h3><p>A complete printable PDF with finished preview, pattern facts, colour key, charts, symbols, enlarged sections and working guide.</p>"
            f"<p>Digital product only. Personal use only.</p>"
        )
        desc_es = (
            f"<p><strong>{title_es}</strong> es un patrón digital descargable de la colección Animales de Drielo.</p>"
            f"<p><strong>Código:</strong> {code}</p>"
            f"<p>El diseño procede directamente de la referencia canónica aprobada y utiliza únicamente la paleta fija de 24 colores de la colección.</p>"
            f"<h3>Detalles</h3><ul><li>Gráfico: {cfg['w']} × {cfg['h']}</li><li>Posiciones: {total:,}</li>"
            f"<li>Colores usados: {colors}</li><li>Técnica: {tech_es}</li><li>Apto para principiantes</li></ul>"
            f"<h3>Qué recibirás</h3><p>PDF completo e imprimible con vista previa, datos del patrón, clave de colores, gráficos, símbolos, secciones ampliadas y guía de trabajo.</p>"
            f"<p>Producto digital. Solo para uso personal.</p>"
        )
        tags = [
            "animal pattern",
            "cute animals",
            "digital pattern",
            "instant download",
            "beginner pattern",
            *TECH_TAGS[suffix],
            design["slug"][:20],
        ][:13]
        child = f"{parents[suffix].replace('-patterns', '')}-animals"
        row = by.get(code)
        if row is None:
            row = templates[suffix]
            rows.append(row)
            by[code] = row
        row.update({
            "code": code,
            "sku": f"DRIELO-{code}",
            "base_design_id": base_id,
            "design_id": code,
            "technique_code": suffix,
            "technique": cfg["technique"],
            "title": title_en,
            "title_en": title_en,
            "title_es": title_es,
            "slug": f"{design['slug']}-{cfg['technique']}-pattern",
            "price": 4.99,
            "collection": "animals",
            "stitches": total,
            "grid": f"{cfg['w']} × {cfg['h']} {cfg['unit_label']}",
            "colours": colors,
            "color_count": colors,
            "grid_width": cfg["w"],
            "grid_height": cfg["h"],
            "skill": "Beginner friendly",
            "skill_en": "Beginner friendly",
            "skill_es": "Apto para principiantes",
            "stitch_type": cfg["stitch_type"],
            "stitch_type_en": cfg["stitch_type"],
            "stitch_type_es": tech_es,
            "short_description": short_en,
            "short_description_en": short_en,
            "short_description_es": short_es,
            "description": desc_en,
            "description_en": desc_en,
            "description_es": desc_es,
            "categories": [parents[suffix], child],
            "tags": tags,
            "etsy_title_en": title_en,
            "etsy_title_es": title_es,
            "etsy_description_en": short_en,
            "etsy_description_es": short_es,
            "etsy_tags_en": tags,
            "etsy_tags_es": ["animales", "patrón digital", "descarga pdf", tech_es, "principiantes", design["title_es"].lower()][:13],
            "gallery": [f"assets/{code}-gallery-{i}.webp" for i in (2, 3, 4)],
            "gallery_preview_pages": {"facts": 3, "colour_a1": 8, "symbol_a1": 12},
            "featured_image": f"assets/{code}-product.webp",
            "download": f"files/Drielo_{code}.pdf",
            "gallery_revision": revision,
            "seo_title": f"{title_en} | Drielo",
            "seo_title_en": f"{title_en} | Drielo",
            "seo_title_es": f"{title_es} | Drielo",
            "meta_description": short_en[:155],
            "meta_description_en": short_en[:155],
            "meta_description_es": short_es[:155],
            "purchase_note_en": "Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
            "purchase_note_es": "Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
            "size_attribute_label": cfg["size_label"],
            "colour_attribute_label": cfg["colour_label"],
            "type_attribute_label": "Technique",
            "count_attribute_label": cfg["count_label"],
        })
        row["filters"] = {
            "technique": [cfg["technique"]],
            "theme": ["animals"],
            "style": ["cute", "colorful"],
            "project": [cfg["project"]],
            "orientation": ["portrait"],
            "difficulty": ["beginner"],
            "color-family": ["multicolor"],
            "season": [],
        }
        row.pop("previous_skus", None)

    rows.sort(key=lambda x: x.get("code", ""))
    write_json(CATALOG_PATH, catalog)

    doc = read_json(DESIGNS_PATH)
    for item in doc["designs"]:
        if item["base_design_id"] == base_id:
            item["product_status"] = "ready"
            item["transparent_background"] = True
    write_json(DESIGNS_PATH, doc)
    return revision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_id", help="Base design id, e.g. A0001")
    args = ap.parse_args()
    base = args.design_id.strip().upper()
    if not base.startswith("A") or len(base) != 5 or not base[1:].isdigit():
        raise SystemExit("Expected base design id like A0001")
    n = int(base[1:])
    if n < 1 or n > 30:
        raise SystemExit("Animals design id must be A0001 through A0030")

    design = design_record(base)
    collection = read_json(COLLECTION_PATH)
    bbox = build_patterns(base, design, collection)
    results = render_design(base, design, collection)
    revision = update_catalog(base, design, collection)
    print(json.dumps({
        "design_id": base,
        "title": design["title_en"],
        "source_asset": design["source_asset"],
        "reference_asset": design["reference_asset"],
        "source_bbox": bbox,
        "gallery_revision": revision,
        "products": {f"{base}-{s}": results[s] for s in SUFFIXES},
    }, ensure_ascii=False, indent=2))
    print(f"AUTO_DESIGN_READY={base}")


if __name__ == "__main__":
    main()
