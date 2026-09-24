#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "florals"
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
SOURCE_MANIFEST = COL_DIR / "source-designs" / "manifest.json"
SOURCE_DIR = COL_DIR / "source-designs"
REFERENCE_DIR = COL_DIR / "reference-masters"
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
    "CS": ["cross stitch pdf", "counted cross stitch", "dmc pattern"],
    "C2C": ["c2c crochet", "crochet graph", "corner to corner"],
    "TC": ["tapestry crochet", "crochet chart", "colorwork crochet"],
    "LH": ["latch hook", "rug pattern pdf", "rug making"],
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rgb(hexv: str):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def nearest_palette_index(col, palette_rgb):
    r, g, b = col
    return min(
        range(len(palette_rgb)),
        key=lambda i: (
            2 * (r - palette_rgb[i][0]) ** 2
            + 4 * (g - palette_rgb[i][1]) ** 2
            + 3 * (b - palette_rgb[i][2]) ** 2
        ),
    )


def threads_from_matrix(matrix, palette):
    counts = Counter(v for row in matrix for v in row if v)
    out = []
    for i, p in enumerate(palette):
        sym = SYMBOLS[i]
        if counts[sym]:
            out.append(
                {
                    "symbol": sym,
                    "dmc": str(p["dmc"]),
                    "color": p["hex"].upper(),
                    "name": p.get("name", f"DMC {p['dmc']}"),
                    "stitches": counts[sym],
                }
            )
    return out


def design_record(base_id: str):
    doc = read_json(DESIGNS_PATH)
    for item in doc["designs"]:
        if item["base_design_id"] == base_id:
            return item
    raise RuntimeError(f"Unknown Florals design: {base_id}")


def _parse_cell(cell: str):
    m = re.fullmatch(r"r([12])c([123])", cell or "")
    if not m:
        raise RuntimeError(f"Invalid reference cell: {cell}")
    return int(m.group(1)) - 1, int(m.group(2)) - 1


def _normalize_artwork(cell: Image.Image, collection: dict):
    alpha_threshold = int(collection.get("pattern_rules", {}).get("alpha_threshold", 96))
    max_colors = int(collection.get("pattern_rules", {}).get("per_design_max_colors", 14))
    palette = collection["palette"]
    palette_rgb = [rgb(p["hex"]) for p in palette]

    src = cell.convert("RGBA")
    bbox = src.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("Reference cell contains no visible artwork")
    src = src.crop(bbox)

    alpha = src.getchannel("A")
    q = src.quantize(
        colors=max(2, min(24, max_colors + 1)),
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    ).convert("RGBA")

    sp = src.load()
    qp = q.load()
    mapped = {}
    for y in range(src.height):
        for x in range(src.width):
            sr, sg, sb, sa = sp[x, y]
            if sa < alpha_threshold:
                qp[x, y] = (0, 0, 0, 0)
                continue
            qr, qg, qb, _ = qp[x, y]
            key = (qr, qg, qb)
            idx = mapped.get(key)
            if idx is None:
                idx = nearest_palette_index(key, palette_rgb)
                mapped[key] = idx
            rr, gg, bb = palette_rgb[idx]
            qp[x, y] = (rr, gg, bb, 255)

    bbox2 = q.getchannel("A").getbbox()
    if not bbox2:
        raise RuntimeError("Palette-normalized artwork became empty")
    return q.crop(bbox2)


def prepare_reference_master(base_id: str, design: dict, collection: dict):
    ref = design.get("canonical_reference") or {}
    sheet_rel = ref.get("sheet")
    cell_name = ref.get("cell")
    if not sheet_rel or not cell_name:
        raise RuntimeError(f"{base_id}: canonical reference is missing")

    sheet_path = COL_DIR / sheet_rel
    if not sheet_path.is_file():
        raise RuntimeError(f"{base_id}: reference sheet missing: {sheet_path}")

    sheet = Image.open(sheet_path).convert("RGBA")
    row, col = _parse_cell(cell_name)
    cell_w = sheet.width // 3
    cell_h = sheet.height // 2
    x0 = col * cell_w
    y0 = row * cell_h
    x1 = sheet.width if col == 2 else (col + 1) * cell_w
    y1 = sheet.height if row == 1 else (row + 1) * cell_h
    art = _normalize_artwork(sheet.crop((x0, y0, x1, y1)), collection)

    canvas = Image.new("RGBA", (800, 960), (0, 0, 0, 0))
    max_w, max_h = 736, 896
    scale = min(max_w / art.width, max_h / art.height)
    new_size = (max(1, round(art.width * scale)), max(1, round(art.height * scale)))
    art = art.resize(new_size, Image.Resampling.NEAREST)
    pos = ((canvas.width - art.width) // 2, (canvas.height - art.height) // 2)
    canvas.alpha_composite(art, pos)

    bbox = canvas.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"{base_id}: empty canonical master")
    margins = (bbox[0], bbox[1], canvas.width - bbox[2], canvas.height - bbox[3])
    if min(margins) < 24:
        raise RuntimeError(f"{base_id}: canonical master too close to edge: {bbox}")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    src_name = f"{base_id}-{design['slug']}.png"
    ref_name = f"{base_id}-{design['slug']}-reference.png"
    src_path = SOURCE_DIR / src_name
    ref_path = REFERENCE_DIR / ref_name
    canvas.save(src_path, "PNG", optimize=True)
    canvas.save(ref_path, "PNG", optimize=True)

    source_rel = f"collections/florals/source-designs/{src_name}"
    reference_rel = f"collections/florals/reference-masters/{ref_name}"
    update_design_metadata(base_id, source_rel)
    return source_rel, reference_rel, ref_path, bbox


def update_design_metadata(base_id: str, source_rel: str):
    doc = read_json(DESIGNS_PATH)
    for item in doc["designs"]:
        if item["base_design_id"] == base_id:
            item["source_asset"] = source_rel
            item["artwork_status"] = "canonical-pattern-ready"
            break
    write_json(DESIGNS_PATH, doc)

    if SOURCE_MANIFEST.is_file():
        manifest = read_json(SOURCE_MANIFEST)
        for item in manifest.get("designs", []):
            if item.get("base_design_id") == base_id:
                item["source_asset"] = source_rel
                item["status"] = "canonical-pattern-ready"
                break
        if all(x.get("status") == "canonical-pattern-ready" for x in manifest.get("designs", [])):
            manifest["status"] = "canonical-sources-ready"
        write_json(SOURCE_MANIFEST, manifest)


def matrix_from_master(image_path: Path, collection: dict):
    im = Image.open(image_path).convert("RGBA")
    if im.size != (800, 960):
        raise RuntimeError(f"Canonical master must be 800x960, got {im.size}")

    palette = collection["palette"]
    palette_rgb = [rgb(p["hex"]) for p in palette]
    exact = {c: i for i, c in enumerate(palette_rgb)}
    min_samples = int(collection.get("pattern_rules", {}).get("min_opaque_samples_per_stitch", 6))
    pix = im.load()

    matrix = []
    counts = Counter()
    for gy in range(120):
        row = []
        for gx in range(100):
            samples = []
            x0, y0 = gx * 8, gy * 8
            for yy in range(y0, y0 + 8):
                for xx in range(x0, x0 + 8):
                    r, g, b, a = pix[xx, yy]
                    if a >= 128:
                        samples.append((r, g, b))
            if len(samples) < min_samples:
                row.append(None)
                continue
            col, _ = Counter(samples).most_common(1)[0]
            idx = exact.get(col)
            if idx is None:
                idx = nearest_palette_index(col, palette_rgb)
            sym = SYMBOLS[idx]
            row.append(sym)
            counts[sym] += 1
        matrix.append(row)

    if not counts:
        raise RuntimeError("Canonical master produced an empty pattern")
    return matrix, threads_from_matrix(matrix, palette)


def build_pattern_jsons(base_id: str, design: dict, collection: dict, source_rel: str, reference_rel: str, reference_path: Path):
    matrix_cs, threads_cs = matrix_from_master(reference_path, collection)
    matrices = {"CS": (matrix_cs, threads_cs)}
    for suffix in ("C2C", "TC", "LH"):
        cfg = bg.TECHS[suffix]
        matrices[suffix] = bg.downsample(matrix_cs, threads_cs, cfg["w"], cfg["h"])

    max_colors = int(collection.get("pattern_rules", {}).get("per_design_max_colors", 14))
    for suffix in SUFFIXES:
        cfg = bg.TECHS[suffix]
        code = f"{base_id}-{suffix}"
        matrix, threads = matrices[suffix]
        if len(threads) > max_colors:
            raise RuntimeError(f"{code}: uses {len(threads)} colours; max is {max_colors}")

        pattern = {
            "code": code,
            "base_design_id": base_id,
            "technique_code": suffix,
            "collection": "florals",
            "palette_collection": "florals",
            "status": "ready",
            "source_asset": source_rel,
            "reference_asset": reference_rel,
            "stitch_width": cfg["w"],
            "stitch_height": cfg["h"],
            "total_stitches": sum(1 for row in matrix for v in row if v),
            "threads": threads,
            "matrix": matrix,
            "outline_policy": {"enabled": False},
            "external_white_cleanup": {"enabled": False},
        }
        write_json(PATTERNS / code / "pattern.json", pattern)

        product = {
            "code": code,
            "base_design_id": base_id,
            "technique_code": suffix,
            "collection": "florals",
            "title": design["title_en"],
            "pattern_file": f"patterns/{code}/pattern.json",
            "website": "www.drielo.com",
            "technique": cfg["technique"],
            "template": cfg["template"],
            "source_artwork": source_rel,
            "reference_artwork": reference_rel,
            "page_1_asset": {
                "CS": "multitech/assets/cover-cross-stitch.webp",
                "C2C": "multitech/assets/cover-c2c-crochet.webp",
                "TC": "multitech/assets/cover-crochet.webp",
                "LH": "multitech/assets/cover-rug.webp",
            }[suffix],
            "render_ready": True,
            "status": "active",
        }
        write_json(PRODUCTS / code / "product.json", product)


def prepare_renderer_assets(collection: dict):
    temp_assets = Path("/tmp/drielo-florals-auto-assets")
    if temp_assets.exists():
        shutil.rmtree(temp_assets)
    temp_assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bg.ENGINE_ASSETS / "floral.png", temp_assets / "floral.png")

    legacy_targets = {
        "CS": "cover-cross-stitch.webp",
        "C2C": "cover-crochet.webp",
        "TC": "cover-c2c-crochet.webp",
        "LH": "cover-rug.webp",
    }
    for suffix, target in legacy_targets.items():
        rel = collection["mockup_spec"]["technique_assets"][suffix]
        src = (COL_DIR / rel).resolve()
        if not src.is_file():
            raise RuntimeError(f"{suffix}: configured cover missing: {rel}")
        Image.open(src).convert("RGB").save(temp_assets / target, "WEBP", quality=94, method=6)
    bg.ENGINE_ASSETS = temp_assets


def render_design(base_id: str, design: dict, collection: dict):
    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    prepare_renderer_assets(collection)
    layouts = collection["mockup_spec"]["technique_layouts"]
    results = {}

    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        pattern = read_json(PATTERNS / code / "pattern.json")
        data = bg.pattern_data(code, design["title_en"], suffix, pattern["matrix"], pattern["threads"])
        data["collection"] = collection["name_en"]
        data["collection_id"] = collection["id"]
        data["cover_overlay"] = layouts[suffix]["cover_overlay"]
        data["cover_stage_scale"] = layouts[suffix]["cover_stage_scale"]

        result = bg.render_one((code, suffix, data))
        pdf_target = STORE_FILES / f"Drielo_{code}.pdf"
        image_target = STORE_ASSETS / f"{code}-product.webp"
        gallery_targets = [STORE_ASSETS / f"{code}-gallery-{i}.webp" for i in (2, 3, 4)]

        shutil.copy2(result["pdf"], pdf_target)
        shutil.copy2(result["image"], image_target)
        gallery_sources = result.get("gallery", [])
        if len(gallery_sources) != 3:
            raise RuntimeError(f"{code}: renderer returned {len(gallery_sources)} gallery images")
        for src, dst in zip(gallery_sources, gallery_targets):
            shutil.copy2(src, dst)

        if pdf_target.stat().st_size < 100000 or pdf_target.read_bytes()[:4] != b"%PDF":
            raise RuntimeError(f"{code}: invalid PDF")
        if image_target.stat().st_size < 40000:
            raise RuntimeError(f"{code}: invalid featured image")
        for gallery in gallery_targets:
            if gallery.stat().st_size < 25000:
                raise RuntimeError(f"{code}: invalid gallery image {gallery.name}")
        results[suffix] = {
            "pdf_bytes": pdf_target.stat().st_size,
            "image_bytes": image_target.stat().st_size,
            "gallery_bytes": [x.stat().st_size for x in gallery_targets],
            "stitches": pattern["total_stitches"],
            "colors": len(pattern["threads"]),
        }
    return results


def ensure_catalog_meta(catalog: dict, collection: dict):
    collections = catalog.setdefault("collections", [])
    entry = {
        "id": "florals",
        "name": "Florals",
        "slug": "florals",
        "name_en": "Florals",
        "name_es": "Florales",
        "description": "Floral and botanical patterns in one coordinated 24-colour palette for cross stitch, C2C crochet, tapestry crochet and latch-hook rugs.",
        "description_en": "Floral and botanical patterns in one coordinated 24-colour palette for cross stitch, C2C crochet, tapestry crochet and latch-hook rugs.",
        "description_es": "Patrones florales y botánicos con una paleta coordinada de 24 colores para punto de cruz, crochet C2C, tapestry crochet y alfombra latch hook.",
        "palette_hex": [x["hex"] for x in collection["palette"]],
        "thread_codes": [str(x["dmc"]) for x in collection["palette"]],
        "cover_asset": "assets/F0001-CS-product.webp",
        "techniques": ["cross-stitch", "c2c-crochet", "tapestry-crochet", "latch-hook"],
    }
    for i, old in enumerate(collections):
        if old.get("slug") == "florals":
            collections[i] = entry
            break
    else:
        collections.append(entry)

    cats = catalog.setdefault("categories", [])
    wanted = [
        {"name":"Florals","slug":"cross-stitch-florals","parent":"cross-stitch-patterns","name_en":"Florals","name_es":"Florales"},
        {"name":"Florals","slug":"c2c-crochet-florals","parent":"c2c-crochet-patterns","name_en":"Florals","name_es":"Florales"},
        {"name":"Florals","slug":"tapestry-crochet-florals","parent":"tapestry-crochet-patterns","name_en":"Florals","name_es":"Florales"},
        {"name":"Florals","slug":"latch-hook-rug-florals","parent":"latch-hook-rug-patterns","name_en":"Florals","name_es":"Florales"},
    ]
    by_slug = {x.get("slug"): i for i, x in enumerate(cats)}
    for cat in wanted:
        if cat["slug"] in by_slug:
            cats[by_slug[cat["slug"]]] = cat
        else:
            cats.append(cat)


def catalog_row(template: dict, base_id: str, design: dict, suffix: str, pattern: dict, revision: int):
    cfg = bg.TECHS[suffix]
    code = f"{base_id}-{suffix}"
    row = deepcopy(template) if template else {}
    row.pop("previous_skus", None)

    title_en = f"{design['title_en']} {cfg['display']} Pattern PDF"
    title_es = f"{TITLE_ES[suffix]}: {design['title_es']}"
    total = int(pattern["total_stitches"])
    colors = len(pattern["threads"])
    w, h = cfg["w"], cfg["h"]
    unit = cfg["unit_label"]
    count_label = cfg["count_label"]
    tech_es = TECH_ES[suffix]
    slug = f"{design['slug']}-{cfg['technique']}-pattern"

    short_en = (
        f"Downloadable {design['title_en']} {cfg['display']} pattern PDF from the Florals collection. "
        f"{w} × {h} {unit}; {total:,} {count_label.lower()}; {colors} coordinated colours; "
        f"beginner friendly. Pattern code: {code}."
    )
    short_es = (
        f"Patrón PDF descargable de {design['title_es'].lower()} para {tech_es}. "
        f"{w} × {h}; {total:,} celdas ocupadas; {colors} colores coordinados; "
        f"apto para principiantes. Código: {code}."
    )
    desc_en = (
        f"<p><strong>{title_en}</strong> is a downloadable digital pattern from the Florals collection.</p>"
        f"<p><strong>Digital product only:</strong> no finished item or physical materials are included.</p>"
        f"<h3>Pattern details</h3><ul><li>Pattern code: {code}</li><li>Grid: {w} × {h} {unit}</li>"
        f"<li>{count_label}: {total:,}</li><li>Colours: {colors} coordinated collection colours</li>"
        f"<li>Technique: {cfg['stitch_type']}</li><li>Skill level: Beginner friendly</li></ul>"
        f"<h3>What you receive</h3><ul><li>17-page PDF pattern</li><li>Finished-design preview</li>"
        f"<li>Colour key with counts</li><li>Full-colour chart overview</li><li>Black-and-white symbol chart</li>"
        f"<li>Enlarged chart sections</li><li>Print-and-make guide</li></ul>"
        f"<p>Personal use only. The pattern and PDF may not be redistributed or resold.</p>"
    )
    desc_es = (
        f"<p><strong>{title_es}</strong> es un patrón digital descargable de la colección Florales.</p>"
        f"<p><strong>Solo producto digital:</strong> no se incluye la pieza terminada ni materiales físicos.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {code}</li><li>Cuadrícula: {w} × {h}</li>"
        f"<li>Celdas ocupadas: {total:,}</li><li>Colores: {colors} colores coordinados</li>"
        f"<li>Técnica: {tech_es}</li><li>Nivel: apto para principiantes</li></ul>"
        f"<h3>Qué recibirás</h3><ul><li>PDF de 17 páginas</li><li>Vista previa del diseño</li>"
        f"<li>Clave de colores</li><li>Gráfico general a color</li><li>Gráfico con símbolos</li>"
        f"<li>Secciones ampliadas</li><li>Guía para realizar el proyecto</li></ul><p>Solo para uso personal.</p>"
    )
    tags = [
        design["title_en"].lower(),
        "floral pattern",
        "botanical pattern",
        "cottagecore",
        "digital pattern",
        "beginner pattern",
        *TECH_TAGS[suffix],
    ][:13]

    row.update(
        {
            "code": code,
            "sku": f"DRIELO-{code}",
            "title": title_en,
            "title_en": title_en,
            "title_es": title_es,
            "slug": slug,
            "price": float(row.get("price") or 4.99),
            "collection": "florals",
            "stitches": total,
            "grid": f"{w} × {h} {unit}",
            "colours": colors,
            "color_count": colors,
            "grid_width": w,
            "grid_height": h,
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
            "categories": [
                {
                    "CS": "cross-stitch-patterns",
                    "C2C": "c2c-crochet-patterns",
                    "TC": "tapestry-crochet-patterns",
                    "LH": "latch-hook-rug-patterns",
                }[suffix],
                {
                    "CS": "cross-stitch-florals",
                    "C2C": "c2c-crochet-florals",
                    "TC": "tapestry-crochet-florals",
                    "LH": "latch-hook-rug-florals",
                }[suffix],
            ],
            "tags": tags,
            "gallery": [
                f"assets/{code}-gallery-2.webp",
                f"assets/{code}-gallery-3.webp",
                f"assets/{code}-gallery-4.webp",
            ],
            "gallery_preview_pages": {"facts": 3, "colour_a1": 8, "symbol_a1": 12},
            "download": f"files/Drielo_{code}.pdf",
            "featured_image": f"assets/{code}-product.webp",
            "gallery_revision": revision,
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
            "etsy_tags_en": tags,
            "etsy_tags_es": [design["title_es"].lower(), "floral", "botánico", "patrón digital", "descarga pdf", tech_es, "principiantes"],
            "design_id": code,
            "base_design_id": base_id,
            "technique_code": suffix,
            "technique": cfg["technique"],
            "size_attribute_label": cfg["size_label"],
            "colour_attribute_label": cfg["colour_label"],
            "type_attribute_label": "Technique",
            "count_attribute_label": count_label,
            "filters": {
                "technique": [cfg["technique"]],
                "theme": ["florals"],
                "style": ["floral", "botanical", "cottagecore"],
                "project": [cfg["project"]],
                "orientation": ["portrait"],
                "difficulty": ["beginner"],
                "color-family": ["multicolor"],
                "season": ["spring"],
            },
        }
    )
    return row


def update_catalog(base_id: str, design: dict, collection: dict):
    catalog = read_json(CATALOG_PATH)
    ensure_catalog_meta(catalog, collection)
    rows = catalog.setdefault("products", [])
    by_code = {p.get("code"): p for p in rows}
    revision = int(os.environ.get("DRIELO_GALLERY_REVISION", "0") or 0)
    if revision <= 0:
        revision = 202609240000 + int(base_id[1:])

    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        pattern = read_json(PATTERNS / code / "pattern.json")
        template = by_code.get(code) or by_code.get(f"I0001-{suffix}") or {}
        row = catalog_row(template, base_id, design, suffix, pattern, revision)
        if code in by_code:
            idx = rows.index(by_code[code])
            rows[idx] = row
        else:
            rows.append(row)
        by_code[code] = row

    rows.sort(key=lambda x: x.get("code", ""))
    write_json(CATALOG_PATH, catalog)
    return revision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_id", help="Base Florals design id, for example F0001")
    args = ap.parse_args()
    base_id = args.design_id.strip().upper()
    if not re.fullmatch(r"F\d{4}", base_id):
        raise SystemExit("Expected base design id like F0001")

    collection = read_json(COLLECTION_PATH)
    design = design_record(base_id)
    source_rel, reference_rel, reference_path, bbox = prepare_reference_master(base_id, design, collection)
    design = design_record(base_id)
    build_pattern_jsons(base_id, design, collection, source_rel, reference_rel, reference_path)
    results = render_design(base_id, design, collection)
    revision = update_catalog(base_id, design, collection)

    summary = {
        "design_id": base_id,
        "title": design["title_en"],
        "reference_sheet": design["canonical_reference"]["sheet"],
        "reference_cell": design["canonical_reference"]["cell"],
        "source_asset": source_rel,
        "reference_asset": reference_rel,
        "source_bbox": bbox,
        "gallery_revision": revision,
        "products": {f"{base_id}-{s}": results[s] for s in SUFFIXES},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"AUTO_DESIGN_READY={base_id}")


if __name__ == "__main__":
    main()
