#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
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
from generate_reference_master import generate_reference_master  # noqa: E402

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


def threads_from_matrix(matrix, palette):
    counts = Counter(v for row in matrix for v in row if v)
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
    return threads


def cleanup_isolated_external_white(matrix, white_symbol, max_component_cells=12, neighborhood=8):
    if not matrix or not matrix[0] or not white_symbol:
        return matrix, {"removed_components": 0, "removed_cells": 0}

    out = [row[:] for row in matrix]
    h, w = len(out), len(out[0])
    if neighborhood == 4:
        offsets = [(-1,0),(1,0),(0,-1),(0,1)]
    else:
        offsets = [(dy,dx) for dy in (-1,0,1) for dx in (-1,0,1) if not (dy == 0 and dx == 0)]

    seen = set()
    removed_components = 0
    removed_cells = 0

    for y in range(h):
        for x in range(w):
            if out[y][x] != white_symbol or (y, x) in seen:
                continue

            stack = [(y, x)]
            seen.add((y, x))
            component = []
            touches_nonwhite = False

            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))
                for dy, dx in offsets:
                    yy, xx = cy + dy, cx + dx
                    if yy < 0 or yy >= h or xx < 0 or xx >= w:
                        continue
                    value = out[yy][xx]
                    if value == white_symbol and (yy, xx) not in seen:
                        seen.add((yy, xx))
                        stack.append((yy, xx))
                    elif value is not None and value != white_symbol:
                        touches_nonwhite = True

            # Exterior antialias/fleck pixels are small white islands floating in
            # transparent canvas. Intentional motif whites touch another motif
            # colour/outline or form a larger region, so they are preserved.
            if len(component) <= max_component_cells and not touches_nonwhite:
                for cy, cx in component:
                    out[cy][cx] = None
                removed_components += 1
                removed_cells += len(component)

    return out, {
        "removed_components": removed_components,
        "removed_cells": removed_cells,
        "max_component_cells": max_component_cells,
        "neighborhood": neighborhood,
    }


def _distance_to_transparency(matrix, y, x, max_depth=3):
    if matrix[y][x] is None:
        return 0
    h, w = len(matrix), len(matrix[0])
    for radius in range(1, max_depth + 1):
        y0, y1 = max(0, y - radius), min(h - 1, y + radius)
        x0, x1 = max(0, x - radius), min(w - 1, x + radius)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                if max(abs(yy - y), abs(xx - x)) != radius:
                    continue
                if yy < 0 or yy >= h or xx < 0 or xx >= w:
                    return radius
                if matrix[yy][xx] is None:
                    return radius
        if y - radius < 0 or y + radius >= h or x - radius < 0 or x + radius >= w:
            return radius
    return max_depth + 1


def _nearest_fill_symbol(matrix, y, x, outline_symbol, max_radius=6):
    h, w = len(matrix), len(matrix[0])
    candidates = []
    for radius in range(1, max_radius + 1):
        for yy in range(max(0, y - radius), min(h, y + radius + 1)):
            for xx in range(max(0, x - radius), min(w, x + radius + 1)):
                if max(abs(yy - y), abs(xx - x)) != radius:
                    continue
                v = matrix[yy][xx]
                if v is not None and v != outline_symbol:
                    candidates.append(v)
        if candidates:
            return Counter(candidates).most_common(1)[0][0]
    return outline_symbol


def normalize_external_outline(matrix, outline_symbol, cleanup_depth=2, neighborhood=8):
    if not matrix or not matrix[0]:
        return matrix, {"changed": 0, "boundary_cells": 0, "extra_outline_removed": 0}

    original = [row[:] for row in matrix]
    h, w = len(original), len(original[0])
    occupied = [[original[y][x] is not None for x in range(w)] for y in range(h)]

    if neighborhood == 4:
        offsets = [(-1,0),(1,0),(0,-1),(0,1)]
    else:
        offsets = [(dy,dx) for dy in (-1,0,1) for dx in (-1,0,1) if not (dy == 0 and dx == 0)]

    boundary = set()
    for y in range(h):
        for x in range(w):
            if not occupied[y][x]:
                continue
            for dy, dx in offsets:
                yy, xx = y + dy, x + dx
                if yy < 0 or yy >= h or xx < 0 or xx >= w or not occupied[yy][xx]:
                    boundary.add((y, x))
                    break

    # Only clean dark cells that are actually connected to the exterior outline.
    # This preserves eyes, mouths and other black interior details even when they
    # happen to sit close to an outer edge.
    dark_boundary = {(y, x) for (y, x) in boundary if original[y][x] == outline_symbol}
    connected_outer_dark = set(dark_boundary)
    frontier = set(dark_boundary)
    dark_offsets = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if not (dy == 0 and dx == 0)]
    for _ in range(max(0, cleanup_depth)):
        nxt = set()
        for y, x in frontier:
            for dy, dx in dark_offsets:
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and original[yy][xx] == outline_symbol:
                    if (yy, xx) not in connected_outer_dark:
                        nxt.add((yy, xx))
        connected_outer_dark.update(nxt)
        frontier = nxt
        if not frontier:
            break

    cleaned = [row[:] for row in original]
    removed = 0
    for y, x in sorted(connected_outer_dark - boundary):
        dist = _distance_to_transparency(original, y, x, max_depth=max(3, cleanup_depth))
        if dist <= cleanup_depth:
            fill = _nearest_fill_symbol(original, y, x, outline_symbol)
            if fill != outline_symbol:
                cleaned[y][x] = fill
                removed += 1

    changed = removed
    for y, x in boundary:
        if cleaned[y][x] != outline_symbol:
            cleaned[y][x] = outline_symbol
            changed += 1

    # Guardrail: every exterior cell must be outline. Also reject a second
    # connected outline layer, while leaving isolated interior black details alone.
    for y, x in boundary:
        if cleaned[y][x] != outline_symbol:
            raise RuntimeError(f"External outline normalization failed at {x},{y}")

    # Only the original exterior contour band is subject to thickness cleanup.
    # After repainting the boundary, it may legitimately touch a black eye/detail
    # near an edge; that must not be mistaken for a second contour layer.
    remaining_original_extras = [
        (y, x)
        for (y, x) in (connected_outer_dark - boundary)
        if cleaned[y][x] == outline_symbol
        and _distance_to_transparency(cleaned, y, x, max_depth=max(3, cleanup_depth)) <= cleanup_depth
    ]
    if remaining_original_extras:
        # One last, wider fill search handles narrow feet/tips where the nearest
        # interior colour is several cells away.
        for y, x in remaining_original_extras:
            fill = _nearest_fill_symbol(cleaned, y, x, outline_symbol, max_radius=12)
            if fill != outline_symbol:
                cleaned[y][x] = fill
                removed += 1
                changed += 1

    stubborn = [
        (y, x)
        for (y, x) in remaining_original_extras
        if cleaned[y][x] == outline_symbol
    ]
    if stubborn:
        raise RuntimeError(
            f"External outline cleanup could not resolve {len(stubborn)} original extra cells: {stubborn[:8]}"
        )

    return cleaned, {
        "changed": changed,
        "boundary_cells": len(boundary),
        "extra_outline_removed": removed,
        "thickness_cells": 1,
        "neighborhood": neighborhood,
    }


def design_record(base_id: str):
    designs = read_json(DESIGNS_PATH)["designs"]
    for item in designs:
        if item["base_design_id"] == base_id:
            return item
    raise RuntimeError(f"Unknown Baby & Nursery design: {base_id}")


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
    return bbox, margins


def prepare_reference_master(base_id: str, design: dict):
    # The user's two approved reference sheets are the only design source.
    # Reconstruct the 800x960 master from the canonical archived matrix on every
    # execution, overwriting any older generated/invented source PNG.
    canonical = generate_reference_master(base_id)
    if canonical["slug"] != design["slug"]:
        raise RuntimeError(f"{base_id}: canonical slug mismatch")

    source_rel = canonical["source_asset"]
    if source_rel != design["source_asset"]:
        raise RuntimeError(
            f"{base_id}: canonical source {source_rel} != designs.json source {design['source_asset']}"
        )

    ref_rel = canonical["reference_asset"]
    ref_path = SYSTEM / ref_rel
    image = Image.open(ref_path).convert("RGBA")
    bbox, margins = validate_reference_master(base_id, image)
    if tuple(canonical["bbox"]) != tuple(bbox):
        raise RuntimeError(f"{base_id}: canonical/reference bbox mismatch")

    print(
        f"REFERENCE_MASTER_OK {base_id} path={ref_rel} bbox={bbox} "
        f"margins={margins} source=user-approved-reference-sheet"
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

    white_rule = collection.get("pattern_rules", {}).get("external_white_cleanup", {})
    white_symbol = None
    if white_rule.get("enabled", False):
        white_dmc = str(white_rule.get("dmc", "3865"))
        try:
            white_index = next(i for i, p in enumerate(palette) if str(p["dmc"]) == white_dmc)
        except StopIteration:
            raise RuntimeError(f"{base_id}: white cleanup DMC {white_dmc} not found in collection palette")
        white_symbol = SYMBOLS[white_index]
        matrix, white_stats_cs = cleanup_isolated_external_white(
            matrix,
            white_symbol,
            max_component_cells=int(white_rule.get("max_isolated_component_cells", 12)),
            neighborhood=int(white_rule.get("neighborhood", 8)),
        )
    else:
        white_stats_cs = {"removed_components": 0, "removed_cells": 0}

    outline_rule = collection.get("pattern_rules", {}).get("external_outline", {})
    if outline_rule.get("enabled", False):
        outline_dmc = str(outline_rule.get("dmc", "3799"))
        try:
            outline_index = next(i for i, p in enumerate(palette) if str(p["dmc"]) == outline_dmc)
        except StopIteration:
            raise RuntimeError(f"{base_id}: outline DMC {outline_dmc} not found in collection palette")
        outline_symbol = SYMBOLS[outline_index]
        matrix, outline_stats_cs = normalize_external_outline(
            matrix,
            outline_symbol,
            cleanup_depth=int(outline_rule.get("cleanup_depth_cells", 2)),
            neighborhood=int(outline_rule.get("neighborhood", 8)),
        )
    else:
        outline_symbol = None
        outline_stats_cs = {"changed": 0, "boundary_cells": 0, "extra_outline_removed": 0}

    threads = threads_from_matrix(matrix, palette)
    matrices = {"CS": (matrix, threads, outline_stats_cs, white_stats_cs)}

    for suffix in ("C2C", "TC", "LH"):
        cfg = bg.TECHS[suffix]
        m, _ = bg.downsample(matrix, threads, cfg["w"], cfg["h"])
        if white_symbol:
            m, white_stats = cleanup_isolated_external_white(
                m,
                white_symbol,
                max_component_cells=int(white_rule.get("max_isolated_component_cells", 12)),
                neighborhood=int(white_rule.get("neighborhood", 8)),
            )
        else:
            white_stats = {"removed_components": 0, "removed_cells": 0}
        if outline_symbol:
            m, stats = normalize_external_outline(
                m,
                outline_symbol,
                cleanup_depth=int(outline_rule.get("cleanup_depth_cells", 2)),
                neighborhood=int(outline_rule.get("neighborhood", 8)),
            )
        else:
            stats = {"changed": 0, "boundary_cells": 0, "extra_outline_removed": 0}
        matrices[suffix] = (m, threads_from_matrix(m, palette), stats, white_stats)

    page_assets = collection["mockup_spec"]["technique_assets"]
    for suffix in SUFFIXES:
        code = f"{base_id}-{suffix}"
        cfg = bg.TECHS[suffix]
        mat, th, outline_stats, white_stats = matrices[suffix]
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
                "outline_policy": {
                    "enabled": bool(outline_symbol),
                    "dmc": str(outline_rule.get("dmc", "3799")) if outline_symbol else None,
                    "thickness_cells": 1 if outline_symbol else None,
                    "neighborhood": int(outline_rule.get("neighborhood", 8)) if outline_symbol else None,
                    "stats": outline_stats,
                },
                "external_white_cleanup": {
                    "enabled": bool(white_symbol),
                    "dmc": str(white_rule.get("dmc", "3865")) if white_symbol else None,
                    "max_isolated_component_cells": int(white_rule.get("max_isolated_component_cells", 12)) if white_symbol else None,
                    "neighborhood": int(white_rule.get("neighborhood", 8)) if white_symbol else None,
                    "stats": white_stats,
                },
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
    revision = int(os.environ.get("DRIELO_GALLERY_REVISION", 202609242000 + int(base_id[1:])))

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
