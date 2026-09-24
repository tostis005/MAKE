#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "baby-nursery"
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
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
    "C2C": ["c2c crochet", "crochet graph", "baby blanket"],
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


def design_record(base_id: str):
    designs = read_json(DESIGNS_PATH)["designs"]
    for item in designs:
        if item["base_design_id"] == base_id:
            return item
    raise RuntimeError(f"Unknown Baby & Nursery design: {base_id}")


def _longest_true_run(values):
    best = cur = 0
    for value in values:
        if value:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def _crop_wall_score(alpha, bbox, side):
    x0, y0, x1, y1 = bbox
    px = alpha.load()
    if side in ("top", "bottom"):
        span = max(1, x1 - x0)
        ys = [y0 + i for i in range(5)] if side == "top" else [y1 - 1 - i for i in range(5)]
        ratios = []
        for y in ys:
            vals = [px[x, y] >= 128 for x in range(x0, x1)]
            ratios.append(_longest_true_run(vals) / span)
    else:
        span = max(1, y1 - y0)
        xs = [x0 + i for i in range(5)] if side == "left" else [x1 - 1 - i for i in range(5)]
        ratios = []
        for x in xs:
            vals = [px[x, y] >= 128 for y in range(y0, y1)]
            ratios.append(_longest_true_run(vals) / span)
    return sum(ratios) / len(ratios)


def validate_reference_master(base_id: str, image: Image.Image):
    if image.size != (800, 960):
        raise RuntimeError(f"{base_id}: reference master must be 800x960, got {image.size}")

    alpha = image.getchannel("A")
    amin, amax = alpha.getextrema()
    bbox = alpha.getbbox()
    if amin != 0 or amax == 0 or not bbox:
        raise RuntimeError(f"{base_id}: reference master must contain transparent background")

    x0, y0, x1, y1 = bbox
    margins = {
        "left": x0,
        "top": y0,
        "right": image.width - x1,
        "bottom": image.height - y1,
    }
    if min(margins.values()) < 32:
        raise RuntimeError(f"{base_id}: reference artwork is too close to canvas edge: bbox={bbox}, margins={margins}")

    scores = {side: _crop_wall_score(alpha, bbox, side) for side in ("top", "bottom", "left", "right")}
    # A long, repeated opaque wall at the artwork boundary is the signature of a
    # sprite/tile crop. Reject it before any JSON/PDF can be created.
    suspicious = {side: score for side, score in scores.items() if score >= 0.80}
    if suspicious:
        raise RuntimeError(
            f"{base_id}: reference master looks cropped at artwork boundary: "
            f"bbox={bbox}, crop_wall_scores={scores}"
        )
    return bbox, margins, scores


def prepare_reference_master(base_id: str, design: dict):
    source_rel = design["source_asset"]
    source = SYSTEM / source_rel
    if not source.is_file():
        raise RuntimeError(f"{base_id}: source master missing: {source_rel}")

    image = Image.open(source).convert("RGBA")
    bbox, margins, scores = validate_reference_master(base_id, image)

    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    ref_name = f"{base_id}-{design['slug']}-reference.png"
    ref_path = REFERENCE_DIR / ref_name
    image.save(ref_path, "PNG", optimize=True)
    ref_rel = f"collections/baby-nursery/reference-masters/{ref_name}"

    # Re-open the persisted reference and validate again. Pattern JSONs are built
    # from this file, never from an unvalidated intermediate.
    persisted = Image.open(ref_path).convert("RGBA")
    bbox2, _, _ = validate_reference_master(base_id, persisted)
    if bbox2 != bbox:
        raise RuntimeError(f"{base_id}: persisted reference geometry changed: {bbox} -> {bbox2}")

    print(
        f"REFERENCE_MASTER_OK {base_id} path={ref_rel} bbox={bbox} "
        f"margins={margins} crop_wall_scores={scores}"
    )
    return ref_rel, ref_path, bbox


def rebuild_from_master(base_id: str, design: dict, collection: dict):
    source_rel = design["source_asset"]
    reference_rel, reference_path, bbox = prepare_reference_master(base_id, design)
    im = Image.open(reference_path).convert("RGBA")

    palette = collection["palette"]
    palette_rgb = [rgb(p["hex"]) for p in palette]
    exact = {c: i for i, c in enumerate(palette_rgb)}
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
            if len(samples) < 8:
                row.append(None)
                continue
            freq = Counter(samples)
            col, _ = freq.most_common(1)[0]
            idx = exact.get(col)
            if idx is None:
                idx = nearest_palette_index(col, palette_rgb)
            sym = SYMBOLS[idx]
            row.append(sym)
            counts[sym] += 1
        matrix.append(row)

    if not counts:
        raise RuntimeError(f"{base_id}: source master produced an empty pattern")

    threads = []
    for i, p in enumerate(palette):
        sym = SYMBOLS[i]
        if counts[sym]:
            threads.append(
                {
                    "symbol": sym,
                    "dmc": str(p["dmc"]),
                    "color": p["hex"].upper(),
                    "name": p.get("name", f"DMC {p['dmc']}"),
                    "stitches": counts[sym],
                }
            )

    matrices = {"CS": (matrix, threads)}
    for suffix in ("C2C", "TC", "LH"):
        cfg = bg.TECHS[suffix]
        matrices[suffix] = bg.downsample(matrix, threads, cfg["w"], cfg["h"])

    page_assets = collection["mockup_spec"]["technique_assets"]
    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        cfg = bg.TECHS[suffix]
        mat, th = matrices[suffix]
        pattern_path = PATTERNS / code / "pattern.json"
        product_path = PRODUCTS / code / "product.json"
        pattern = read_json(pattern_path)
        product = read_json(product_path)

        pattern.update(
            {
                "code": code,
                "base_design_id": base_id,
                "technique_code": suffix,
                "collection": "baby-nursery",
                "palette_collection": "baby-nursery",
                "status": "ready",
                "source_asset": source_rel,
                "reference_asset": reference_rel,
                "stitch_width": cfg["w"],
                "stitch_height": cfg["h"],
                "total_stitches": sum(1 for r in mat for v in r if v),
                "threads": th,
                "matrix": mat,
            }
        )
        write_json(pattern_path, pattern)

        product.update(
            {
                "source_artwork": source_rel,
                "reference_artwork": reference_rel,
                "page_1_asset": page_assets[suffix],
                "render_ready": True,
                "status": "active",
            }
        )
        write_json(product_path, product)

    return bbox


def prepare_renderer_assets(collection: dict):
    temp_assets = Path("/tmp/drielo-baby-auto-assets")
    if temp_assets.exists():
        shutil.rmtree(temp_assets)
    temp_assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bg.ENGINE_ASSETS / "floral.png", temp_assets / "floral.png")

    # bulk_generate.py has legacy fixed cover filenames. The collection config is
    # canonical, so copy each configured image into the filename expected by the
    # renderer for that technique.
    targets = {
        "CS": "cover-cross-stitch.webp",
        "C2C": "cover-crochet.webp",
        "TC": "cover-c2c-crochet.webp",
        "LH": "cover-rug.webp",
    }
    for suffix, target in targets.items():
        src_rel = collection["mockup_spec"]["technique_assets"][suffix]
        src = SYSTEM / src_rel
        if not src.is_file():
            raise RuntimeError(f"{suffix}: collection cover missing: {src_rel}")
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
        shutil.copy2(result["pdf"], pdf_target)
        shutil.copy2(result["image"], image_target)

        if pdf_target.stat().st_size < 100000 or pdf_target.read_bytes()[:4] != b"%PDF":
            raise RuntimeError(f"{code}: invalid generated PDF")
        if image_target.stat().st_size < 50000:
            raise RuntimeError(f"{code}: invalid generated product image")
        results[suffix] = {
            "pdf_bytes": pdf_target.stat().st_size,
            "image_bytes": image_target.stat().st_size,
            "stitches": pattern["total_stitches"],
            "colors": len(pattern["threads"]),
        }
    return results


def replace_text_fields(row: dict, base_id: str, design: dict, suffix: str, pattern: dict, revision: int):
    cfg = bg.TECHS[suffix]
    code = f"{base_id}-{suffix}"
    title_en = design["title_en"]
    title_es = design["title_es"]
    display = cfg["display"]
    total = int(pattern["total_stitches"])
    colors = len(pattern["threads"])
    w, h = cfg["w"], cfg["h"]
    unit = cfg["unit_label"]
    count_label = cfg["count_label"]
    tech_es = TECH_ES[suffix]
    title_product_en = f"{title_en} {display} Pattern PDF"
    title_product_es = f"{TITLE_ES[suffix]}: {title_es}"
    slug = f"{design['slug']}-{cfg['technique']}-pattern"

    short_en = (
        f"Downloadable {title_en} {display} pattern PDF from the Baby & Nursery collection. "
        f"{w} × {h} {unit}; {total:,} {count_label.lower()}; {colors} coordinated colours; "
        f"beginner friendly. Pattern code: {code}."
    )
    short_es = (
        f"Patrón PDF descargable de {title_es.lower()} para {tech_es}. "
        f"{w} × {h}; {total:,} celdas ocupadas; {colors} colores coordinados; "
        f"apto para principiantes. Código: {code}."
    )
    desc_en = (
        f"<p><strong>{title_product_en}</strong> is a downloadable digital pattern from the Baby & Nursery collection.</p>"
        f"<p><strong>Digital product only:</strong> no finished item or physical materials are included.</p>"
        f"<h3>Pattern details</h3><ul><li>Pattern code: {code}</li>"
        f"<li>Grid: {w} × {h} {unit}</li><li>{count_label}: {total:,}</li>"
        f"<li>Colours: {colors} coordinated collection colours</li>"
        f"<li>Technique: {cfg['stitch_type']}</li><li>Skill level: Beginner friendly</li></ul>"
        f"<h3>What you receive</h3><ul><li>17-page PDF pattern</li><li>Finished-design preview</li>"
        f"<li>Colour key with counts</li><li>Full-colour chart overview</li>"
        f"<li>Black-and-white symbol chart</li><li>Enlarged chart sections</li>"
        f"<li>Print-and-make guide</li></ul>"
        f"<p>Personal use only. The pattern and PDF may not be redistributed or resold.</p>"
    )
    desc_es = (
        f"<p><strong>{title_product_es}</strong> es un patrón digital descargable de la colección Bebé e Infantil.</p>"
        f"<p><strong>Solo producto digital:</strong> no se incluye la pieza terminada ni materiales físicos.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {code}</li><li>Cuadrícula: {w} × {h}</li>"
        f"<li>Celdas ocupadas: {total:,}</li><li>Colores: {colors} colores coordinados</li>"
        f"<li>Técnica: {tech_es}</li><li>Nivel: apto para principiantes</li></ul>"
        f"<h3>Qué recibirás</h3><ul><li>PDF de 17 páginas</li><li>Vista previa del diseño</li>"
        f"<li>Clave de colores</li><li>Gráfico general a color</li><li>Gráfico con símbolos</li>"
        f"<li>Secciones ampliadas</li><li>Guía para realizar el proyecto</li></ul>"
        f"<p>Solo para uso personal.</p>"
    )

    tags = [
        title_en.lower(),
        "baby nursery",
        "nursery pattern",
        "digital pattern",
        "beginner pattern",
        *TECH_TAGS[suffix],
    ]

    row.update(
        {
            "code": code,
            "sku": f"DRIELO-{code}",
            "title": title_product_en,
            "title_en": title_product_en,
            "title_es": title_product_es,
            "slug": slug,
            "collection": "baby-nursery",
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
            "gallery": [],
            "download": f"files/Drielo_{code}.pdf",
            "featured_image": f"assets/{code}-product.webp",
            "gallery_revision": revision,
            "seo_title": f"{title_product_en} | Drielo",
            "seo_title_en": f"{title_product_en} | Drielo",
            "seo_title_es": f"{title_product_es} | Drielo",
            "meta_description": short_en[:155],
            "meta_description_en": short_en[:155],
            "meta_description_es": short_es[:155],
            "etsy_title_en": title_product_en,
            "etsy_title_es": title_product_es,
            "etsy_description_en": short_en,
            "etsy_description_es": short_es,
            "tags": tags,
            "etsy_tags_en": tags[:13],
            "etsy_tags_es": [title_es.lower(), "bebé", "infantil", "patrón digital", "descarga pdf", tech_es, "principiantes"],
            "design_id": code,
            "base_design_id": base_id,
            "technique_code": suffix,
            "technique": cfg["technique"],
            "size_attribute_label": cfg["size_label"],
            "colour_attribute_label": cfg["colour_label"],
            "type_attribute_label": "Technique",
            "count_attribute_label": count_label,
        }
    )
    row["filters"] = {
        "technique": [cfg["technique"]],
        "theme": ["baby-nursery"],
        "style": ["cute", "soft", "nursery"],
        "project": [cfg["project"]],
        "orientation": ["portrait"],
        "difficulty": ["beginner"],
        "color-family": ["pastel"],
        "season": [],
    }
    return row


def update_catalog(base_id: str, design: dict):
    catalog = read_json(CATALOG_PATH)
    rows = catalog.setdefault("products", [])
    by_code = {p.get("code"): p for p in rows}
    templates = {s: deepcopy(by_code[f"I0001-{s}"]) for s in SUFFIXES}
    revision = 202609240000 + int(base_id[1:])

    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        pattern = read_json(PATTERNS / code / "pattern.json")
        row = by_code.get(code)
        if row is None:
            row = templates[suffix]
            rows.append(row)
            by_code[code] = row
        replace_text_fields(row, base_id, design, suffix, pattern, revision)

    rows.sort(key=lambda x: x.get("code", ""))
    write_json(CATALOG_PATH, catalog)
    return revision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_id", help="Base design id, e.g. I0002")
    args = ap.parse_args()
    base_id = args.design_id.strip().upper()
    if not base_id.startswith("I") or len(base_id) != 5:
        raise SystemExit("Expected base design id like I0002")
    if base_id == "I0001":
        raise SystemExit("I0001 is the approved reference and is not part of the automatic queue")

    design = design_record(base_id)
    collection = read_json(COLLECTION_PATH)

    bbox = rebuild_from_master(base_id, design, collection)
    results = render_design(base_id, design, collection)
    revision = update_catalog(base_id, design)

    summary = {
        "design_id": base_id,
        "title": design["title_en"],
        "source_asset": design["source_asset"],
        "reference_asset": f"collections/baby-nursery/reference-masters/{base_id}-{design['slug']}-reference.png",
        "source_bbox": bbox,
        "gallery_revision": revision,
        "products": {f"{base_id}-{s}": results[s] for s in SUFFIXES},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"AUTO_DESIGN_READY={base_id}")


if __name__ == "__main__":
    main()
