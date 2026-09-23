#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_DIR = SYSTEM / "collections" / "baby-nursery"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

CODES = ("I0001-CS","I0001-C2C","I0001-TC","I0001-LH")
SUFFIXES = ("CS","C2C","TC","LH")
REVISION = 2026092402

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def update_catalog_row(row, suffix, pattern):
    cfg = bg.TECHS[suffix]
    total = int(pattern["total_stitches"])
    colors = len(pattern["threads"])
    row["stitches"] = total
    row["grid"] = f"{cfg['w']} × {cfg['h']} {cfg['unit_label']}"
    row["colours"] = colors
    row["color_count"] = colors
    row["grid_width"] = cfg["w"]
    row["grid_height"] = cfg["h"]
    row["gallery_revision"] = REVISION
    row["featured_image"] = f"assets/I0001-{suffix}-product.webp"
    row["download"] = f"files/Drielo_I0001-{suffix}.pdf"
    row["gallery"] = []

    display = cfg["display"]
    code = f"I0001-{suffix}"
    count_label = cfg["count_label"]
    short_en = (
        f"Downloadable Teddy Bear {display} pattern PDF from the Baby & Nursery collection. "
        f"{cfg['w']} × {cfg['h']} {cfg['unit_label']}; {total:,} {count_label.lower()}; "
        f"{colors} coordinated colours; beginner friendly. Pattern code: {code}."
    )
    short_es = (
        f"Patrón PDF descargable de osito de peluche para {display}. "
        f"{cfg['w']} × {cfg['h']}; {total:,} celdas ocupadas; {colors} colores coordinados; "
        f"apto para principiantes. Código: {code}."
    )
    row["short_description"] = short_en
    row["short_description_en"] = short_en
    row["short_description_es"] = short_es
    row["meta_description"] = short_en[:155]
    row["meta_description_en"] = short_en[:155]
    row["meta_description_es"] = short_es[:155]

    row["description"] = (
        f"<p><strong>{row['title']}</strong> is a downloadable digital pattern from the Baby & Nursery collection.</p>"
        f"<p><strong>Digital product only:</strong> no finished item or physical materials are included.</p>"
        f"<h3>Pattern details</h3><ul><li>Pattern code: {code}</li>"
        f"<li>Grid: {cfg['w']} × {cfg['h']} {cfg['unit_label']}</li>"
        f"<li>{count_label}: {total:,}</li><li>Colours: {colors} coordinated collection colours</li>"
        f"<li>Technique: {cfg['stitch_type']}</li><li>Skill level: Beginner friendly</li></ul>"
        f"<h3>What you receive</h3><ul><li>17-page PDF pattern</li><li>Finished-design preview</li>"
        f"<li>Colour key with counts</li><li>Full-colour chart overview</li><li>Black-and-white symbol chart</li>"
        f"<li>Enlarged chart sections</li><li>Print-and-make guide</li></ul>"
        f"<p>Personal use only. The pattern and PDF may not be redistributed or resold.</p>"
    )
    row["description_en"] = row["description"]
    row["description_es"] = (
        f"<p><strong>{row.get('title_es','Patrón de osito')}</strong> es un patrón digital descargable de la colección Bebé e Infantil.</p>"
        f"<p><strong>Solo producto digital:</strong> no se incluye la pieza terminada ni materiales físicos.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {code}</li><li>Cuadrícula: {cfg['w']} × {cfg['h']}</li>"
        f"<li>Celdas ocupadas: {total:,}</li><li>Colores: {colors} colores coordinados</li>"
        f"<li>Técnica: {cfg['stitch_type']}</li><li>Nivel: apto para principiantes</li></ul>"
        f"<h3>Qué recibirás</h3><ul><li>PDF de 17 páginas</li><li>Vista previa del diseño</li>"
        f"<li>Clave de colores</li><li>Gráfico general a color</li><li>Gráfico con símbolos</li>"
        f"<li>Secciones ampliadas</li><li>Guía para realizar el proyecto</li></ul>"
        f"<p>Solo para uso personal.</p>"
    )
    return row

def main():
    collection = read_json(COLLECTION_DIR / "collection.json")
    layouts = collection["mockup_spec"]["technique_layouts"]

    expected_pages = {
        "CS": "collections/baby-nursery/assets/cover-cross-stitch.jpg",
        "C2C": "collections/baby-nursery/assets/cover-crochet.jpg",
        "TC": "collections/baby-nursery/assets/cover-c2c-crochet.jpg",
        "LH": "collections/baby-nursery/assets/cover-rug.jpg",
    }
    for suffix in SUFFIXES:
        product = read_json(SYSTEM / "products" / f"I0001-{suffix}" / "product.json")
        if product.get("page_1_asset") != expected_pages[suffix]:
            raise RuntimeError(f"{suffix}: incorrect page_1_asset: {product.get('page_1_asset')}")

    # Convert collection covers to the fixed filenames expected by the renderer.
    temp_assets = Path("/tmp/drielo-baby-i0001-assets")
    if temp_assets.exists():
        shutil.rmtree(temp_assets)
    temp_assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bg.ENGINE_ASSETS / "floral.png", temp_assets / "floral.png")
    cover_map = {
        "cover-cross-stitch.jpg": "cover-cross-stitch.webp",
        "cover-crochet.jpg": "cover-crochet.webp",
        "cover-c2c-crochet.jpg": "cover-c2c-crochet.webp",
        "cover-rug.jpg": "cover-rug.webp",
    }
    for src, dst in cover_map.items():
        Image.open(COLLECTION_DIR / "assets" / src).convert("RGB").save(
            temp_assets / dst, "WEBP", quality=94, method=6
        )
    bg.ENGINE_ASSETS = temp_assets

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)

    patterns = {}
    for suffix in SUFFIXES:
        code = f"I0001-{suffix}"
        pattern = read_json(SYSTEM / "patterns" / code / "pattern.json")
        patterns[suffix] = pattern

        data = bg.pattern_data(code, "Teddy Bear", suffix, pattern["matrix"], pattern["threads"])
        data["collection"] = "Baby & Nursery"
        data["collection_id"] = "baby-nursery"
        data["cover_overlay"] = layouts[suffix]["cover_overlay"]
        data["cover_stage_scale"] = layouts[suffix]["cover_stage_scale"]

        result = bg.render_one((code, suffix, data))
        shutil.copy2(result["pdf"], STORE_FILES / f"Drielo_{code}.pdf")
        shutil.copy2(result["image"], STORE_ASSETS / f"{code}-product.webp")
        print(json.dumps({
            "code": code,
            "pdf_bytes": result["pdf_bytes"],
            "image_bytes": result["image_bytes"],
            "stitches": pattern["total_stitches"],
            "colors": len(pattern["threads"]),
            "page_1_asset": expected_pages[suffix],
        }))

    catalog = read_json(CATALOG_PATH)
    by_code = {p.get("code"): p for p in catalog.get("products", [])}
    for suffix in SUFFIXES:
        code = f"I0001-{suffix}"
        if code not in by_code:
            raise RuntimeError(f"Catalog missing {code}")
        update_catalog_row(by_code[code], suffix, patterns[suffix])

    write_json(CATALOG_PATH, catalog)
    print("I0001_RENDERED=4")
    print(f"GALLERY_REVISION={REVISION}")

if __name__ == "__main__":
    main()
