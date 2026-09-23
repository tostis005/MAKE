#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_DIR = SYSTEM / "collections" / "baby-nursery"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
OUTPUT = SYSTEM / "output-multitech"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def teddy_labels() -> Image.Image:
    """Canonical I0001 motif at the Pop Art master CS grid: 100 x 120."""
    im = Image.new("L", (100, 120), 0)
    d = ImageDraw.Draw(im)

    outline = 1
    fur = 2
    light = 3
    face = 4
    blush = 5
    bow = 6
    bow_dark = 7
    white = 8

    # Dark silhouette.
    d.ellipse((14, 9, 39, 34), fill=outline)
    d.ellipse((61, 9, 86, 34), fill=outline)
    d.ellipse((21, 8, 79, 62), fill=outline)
    d.ellipse((27, 53, 73, 104), fill=outline)
    d.ellipse((12, 58, 39, 95), fill=outline)
    d.ellipse((61, 58, 88, 95), fill=outline)
    d.ellipse((19, 88, 45, 117), fill=outline)
    d.ellipse((55, 88, 81, 117), fill=outline)

    # Main fur.
    d.ellipse((17, 12, 36, 31), fill=fur)
    d.ellipse((64, 12, 83, 31), fill=fur)
    d.ellipse((24, 11, 76, 59), fill=fur)
    d.ellipse((30, 55, 70, 101), fill=fur)
    d.ellipse((15, 61, 37, 92), fill=fur)
    d.ellipse((63, 61, 85, 92), fill=fur)
    d.ellipse((22, 91, 43, 115), fill=fur)
    d.ellipse((57, 91, 78, 115), fill=fur)

    # Inner ears, muzzle, belly and paws.
    d.ellipse((20, 15, 33, 28), fill=light)
    d.ellipse((67, 15, 80, 28), fill=light)
    d.ellipse((35, 34, 65, 54), fill=light)
    d.ellipse((38, 64, 62, 94), fill=light)
    d.ellipse((22, 82, 34, 91), fill=light)
    d.ellipse((66, 82, 78, 91), fill=light)
    d.ellipse((26, 104, 40, 114), fill=light)
    d.ellipse((60, 104, 74, 114), fill=light)

    # Face.
    d.ellipse((36, 29, 41, 35), fill=face)
    d.ellipse((59, 29, 64, 35), fill=face)
    d.point((38, 31), fill=white)
    d.point((61, 31), fill=white)
    d.ellipse((46, 40, 54, 46), fill=face)
    d.arc((40, 42, 50, 53), start=10, end=92, fill=outline, width=2)
    d.arc((50, 42, 60, 53), start=88, end=170, fill=outline, width=2)
    d.ellipse((31, 39, 36, 44), fill=blush)
    d.ellipse((64, 39, 69, 44), fill=blush)

    # Bow tie.
    d.polygon([(37, 54), (47, 59), (47, 68), (36, 72), (33, 63)], fill=bow)
    d.polygon([(63, 54), (53, 59), (53, 68), (64, 72), (67, 63)], fill=bow)
    d.ellipse((46, 59, 54, 68), fill=bow_dark)

    # Tiny decorative stitches inside belly to give the nursery motif a handmade feel.
    d.arc((43, 72, 57, 86), start=200, end=340, fill=light, width=1)
    return im


def pattern_from_labels(labels: Image.Image, collection):
    label_to_dmc = {
        1: "801",   # Dark Coffee Brown
        2: "437",   # Light Tan
        3: "842",   # Very Light Beige Brown
        4: "3799",  # Very Dark Pewter Gray
        5: "3713",  # Very Light Salmon
        6: "3325",  # Light Baby Blue
        7: "3760",  # Medium Wedgewood
        8: "3865",  # Winter White
    }
    symbols = {1:"A", 2:"B", 3:"C", 4:"D", 5:"E", 6:"F", 7:"G", 8:"H"}
    palette = {str(p["dmc"]): p for p in collection["palette"]}
    px = labels.load()
    matrix = []
    counts = Counter()
    for y in range(labels.height):
        row = []
        for x in range(labels.width):
            lab = int(px[x, y])
            if lab == 0:
                row.append(None)
            else:
                sym = symbols[lab]
                row.append(sym)
                counts[sym] += 1
        matrix.append(row)
    threads = []
    for lab in range(1, 9):
        sym = symbols[lab]
        if not counts[sym]:
            continue
        p = palette[label_to_dmc[lab]]
        threads.append({
            "symbol": sym,
            "dmc": str(p["dmc"]),
            "color": str(p["hex"]).upper(),
            "name": p.get("name", f"DMC {p['dmc']}"),
            "stitches": counts[sym],
        })
    return matrix, threads


def product_source(code, suffix):
    cfg = bg.TECHS[suffix]
    page_assets = {
        "CS": "collections/baby-nursery/assets/cover-cross-stitch.jpg",
        "C2C": "collections/baby-nursery/assets/cover-c2c-crochet.jpg",
        "TC": "collections/baby-nursery/assets/cover-crochet.jpg",
        "LH": "collections/baby-nursery/assets/cover-rug.jpg",
    }
    return {
        "code": code,
        "base_design_id": "I0001",
        "technique_code": suffix,
        "collection": "baby-nursery",
        "title": "Teddy Bear",
        "title_en": "Teddy Bear",
        "title_es": "Osito de peluche",
        "design_slug": "teddy-bear",
        "technique": cfg["technique"],
        "pattern_file": f"patterns/{code}/pattern.json",
        "template": cfg["template"],
        "website": "www.drielo.com",
        "status": "active",
        "render_ready": True,
        "source_artwork": "generated-in-repo:baby-nursery/I0001-teddy-bear-v1",
        "page_1_asset": page_assets[suffix],
    }


def ensure_categories(catalog):
    wanted = [
        {"name":"Baby & Nursery","slug":"cross-stitch-baby-nursery","parent":"cross-stitch-patterns","name_en":"Baby & Nursery","name_es":"Bebé e Infantil"},
        {"name":"Baby & Nursery","slug":"c2c-crochet-baby-nursery","parent":"c2c-crochet-patterns","name_en":"Baby & Nursery","name_es":"Bebé e Infantil"},
        {"name":"Baby & Nursery","slug":"tapestry-crochet-baby-nursery","parent":"tapestry-crochet-patterns","name_en":"Baby & Nursery","name_es":"Bebé e Infantil"},
        {"name":"Baby & Nursery","slug":"latch-hook-rug-baby-nursery","parent":"latch-hook-rug-patterns","name_en":"Baby & Nursery","name_es":"Bebé e Infantil"},
    ]
    by_slug = {x["slug"]: x for x in catalog.get("categories", [])}
    for x in wanted:
        by_slug[x["slug"]] = x
    catalog["categories"] = list(by_slug.values())


def collection_row(collection):
    return {
        "id": "baby-nursery",
        "name": "Baby & Nursery",
        "slug": "baby-nursery",
        "description": "Gentle baby and nursery motifs in a coordinated soft palette, available across cross stitch, C2C crochet, tapestry crochet and latch-hook patterns.",
        "palette_hex": [p["hex"] for p in collection["palette"]],
        "thread_codes": [str(p["dmc"]) for p in collection["palette"]],
        "cover_asset": "assets/I0001-CS-product.webp",
        "name_es": "Bebé e Infantil",
        "name_en": "Baby & Nursery",
        "description_es": "Motivos de bebé e infantiles en una paleta suave y coordinada, disponibles para punto de cruz, crochet C2C, tapestry crochet y latch hook.",
        "description_en": "Gentle baby and nursery motifs in a coordinated soft palette, available across cross stitch, C2C crochet, tapestry crochet and latch-hook patterns.",
        "techniques": ["cross-stitch", "c2c-crochet", "tapestry-crochet", "latch-hook"],
    }


def product_row(suffix, pattern):
    code = f"I0001-{suffix}"
    cfg = bg.TECHS[suffix]
    total = pattern["total_stitches"]
    colors = len(pattern["threads"])
    technique_en = {
        "CS":"Cross Stitch",
        "C2C":"C2C Crochet",
        "TC":"Tapestry Crochet",
        "LH":"Latch Hook Rug",
    }[suffix]
    technique_es = {
        "CS":"punto de cruz",
        "C2C":"crochet C2C",
        "TC":"tapestry crochet",
        "LH":"alfombra latch hook",
    }[suffix]
    title_en = {
        "CS":"Teddy Bear Cross Stitch Pattern PDF",
        "C2C":"Teddy Bear C2C Crochet Pattern PDF",
        "TC":"Teddy Bear Tapestry Crochet Pattern PDF",
        "LH":"Teddy Bear Latch Hook Rug Pattern PDF",
    }[suffix]
    title_es = {
        "CS":"Patrón PDF de punto de cruz: osito de peluche",
        "C2C":"Patrón PDF de crochet C2C: osito de peluche",
        "TC":"Patrón PDF de tapestry crochet: osito de peluche",
        "LH":"Patrón PDF de alfombra latch hook: osito de peluche",
    }[suffix]
    unit = cfg["unit_label"]
    count_label = cfg["count_label"]
    grid = f"{cfg['w']} × {cfg['h']} {unit}"
    short_en = f"Downloadable Teddy Bear {technique_en} pattern PDF from the Baby & Nursery collection. {grid}; {total:,} {count_label.lower()}; {colors} coordinated colours; beginner friendly. Pattern code: {code}."
    short_es = f"Patrón PDF descargable de osito de peluche para {technique_es}. {cfg['w']} × {cfg['h']}; {total:,} celdas ocupadas; {colors} colores coordinados; apto para principiantes. Código: {code}."

    if suffix == "CS":
        sizes_en = [
            f"14 ct: {cfg['w']/14:.2f} × {cfg['h']/14:.2f} in ({cfg['w']/14*2.54:.1f} × {cfg['h']/14*2.54:.1f} cm)",
            f"16 ct: {cfg['w']/16:.2f} × {cfg['h']/16:.2f} in ({cfg['w']/16*2.54:.1f} × {cfg['h']/16*2.54:.1f} cm)",
            f"18 ct: {cfg['w']/18:.2f} × {cfg['h']/18:.2f} in ({cfg['w']/18*2.54:.1f} × {cfg['h']/18*2.54:.1f} cm)",
        ]
    else:
        cm = {"C2C":2.0, "TC":0.55, "LH":0.8}[suffix]
        sizes_en = [f"Example finished size: {cfg['w']*cm:.1f} × {cfg['h']*cm:.1f} cm ({cfg['w']*cm/2.54:.1f} × {cfg['h']*cm/2.54:.1f} in)"]

    desc_en = (
        f"<p><strong>{title_en}</strong> is a downloadable digital pattern from the Baby & Nursery collection.</p>"
        f"<p><strong>Digital product only:</strong> no finished item or physical materials are included.</p>"
        f"<h3>Pattern details</h3><ul><li>Pattern code: {code}</li><li>Grid: {grid}</li>"
        f"<li>{count_label}: {total:,}</li><li>Colours: {colors} coordinated collection colours</li>"
        f"<li>Technique: {cfg['stitch_type']}</li><li>Skill level: Beginner friendly</li></ul>"
        f"<h3>Finished size</h3><ul>{''.join('<li>'+x+'</li>' for x in sizes_en)}</ul>"
        f"<h3>What you receive</h3><ul><li>17-page PDF pattern</li><li>Finished-design preview and pattern facts</li>"
        f"<li>Colour key with counts</li><li>Full-colour chart overview</li><li>Black-and-white symbol chart</li>"
        f"<li>Enlarged chart sections</li><li>Print-and-make guide</li></ul>"
        f"<p>Your PDF is available after payment. Personal use only; the pattern and PDF may not be redistributed or resold.</p>"
    )
    desc_es = (
        f"<p><strong>{title_es}</strong> es un patrón digital descargable de la colección Bebé e Infantil.</p>"
        f"<p><strong>Solo producto digital:</strong> no se incluye la pieza terminada ni materiales físicos.</p>"
        f"<h3>Detalles del patrón</h3><ul><li>Código: {code}</li><li>Cuadrícula: {cfg['w']} × {cfg['h']}</li>"
        f"<li>Celdas ocupadas: {total:,}</li><li>Colores: {colors} colores coordinados</li>"
        f"<li>Técnica: {cfg['stitch_type']}</li><li>Nivel: apto para principiantes</li></ul>"
        f"<h3>Qué recibirás</h3><ul><li>Patrón PDF de 17 páginas</li><li>Vista previa y datos del patrón</li>"
        f"<li>Clave de colores</li><li>Gráfico general a color</li><li>Gráfico con símbolos</li>"
        f"<li>Secciones ampliadas</li><li>Guía para imprimir y realizar el proyecto</li></ul>"
        f"<p>Tu PDF estará disponible después del pago. Solo para uso personal; el patrón y el PDF no pueden redistribuirse ni revenderse.</p>"
    )

    cat_child = {
        "CS":"cross-stitch-baby-nursery",
        "C2C":"c2c-crochet-baby-nursery",
        "TC":"tapestry-crochet-baby-nursery",
        "LH":"latch-hook-rug-baby-nursery",
    }[suffix]
    project = {"CS":"wall-art","C2C":"blanket","TC":"tapestry","LH":"rug"}[suffix]
    slug = {
        "CS":"teddy-bear-cross-stitch-pattern",
        "C2C":"teddy-bear-c2c-crochet-pattern",
        "TC":"teddy-bear-tapestry-crochet-pattern",
        "LH":"teddy-bear-latch-hook-rug-pattern",
    }[suffix]

    tags_en = {
        "CS":["teddy bear","baby cross stitch","nursery pattern","cross stitch pdf","counted cross stitch","digital pattern","beginner pattern","dmc pattern"],
        "C2C":["teddy bear","baby crochet","nursery pattern","c2c crochet","crochet graph","digital pattern","baby blanket","beginner crochet"],
        "TC":["teddy bear","baby crochet","nursery pattern","tapestry crochet","crochet chart","colorwork crochet","digital pattern","wall hanging"],
        "LH":["teddy bear","nursery rug","latch hook","rug pattern pdf","baby room decor","digital pattern","rug making","beginner rug"],
    }[suffix]
    tags_es = ["osito de peluche","bebé","infantil","patrón digital","descarga pdf","decoración bebé","principiantes"]

    return {
        "code": code,
        "sku": f"DRIELO-{code}",
        "title": title_en,
        "slug": slug,
        "price": 4.99,
        "collection": "baby-nursery",
        "stitches": total,
        "grid": grid,
        "colours": colors,
        "skill": "Beginner friendly",
        "stitch_type": cfg["stitch_type"],
        "short_description": short_en,
        "description": desc_en,
        "categories": [cfg["category"][0], cat_child],
        "tags": tags_en,
        "gallery": [],
        "download": f"files/Drielo_{code}.pdf",
        "seo_title": f"{title_en} | Drielo",
        "meta_description": short_en[:155],
        "gallery_revision": 2026092301,
        "title_en": title_en,
        "title_es": title_es,
        "short_description_en": short_en,
        "short_description_es": short_es,
        "description_en": desc_en,
        "description_es": desc_es,
        "seo_title_en": f"{title_en} | Drielo",
        "seo_title_es": f"{title_es} | Drielo",
        "meta_description_en": short_en[:155],
        "meta_description_es": short_es[:155],
        "purchase_note_en": "Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
        "purchase_note_es": "Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        "skill_en": "Beginner friendly",
        "skill_es": "Apto para principiantes",
        "stitch_type_en": cfg["stitch_type"],
        "stitch_type_es": technique_es,
        "etsy_title_en": title_en,
        "etsy_title_es": title_es,
        "etsy_description_en": short_en,
        "etsy_description_es": short_es,
        "etsy_tags_en": tags_en[:13],
        "etsy_tags_es": tags_es[:13],
        "filters": {
            "technique": [cfg["technique"]],
            "theme": ["baby-nursery", "animals"],
            "style": ["cute", "soft", "nursery"],
            "project": [project],
            "orientation": ["portrait"],
            "difficulty": ["beginner"],
            "color-family": ["neutral", "warm", "pastel"],
            "season": [],
        },
        "design_id": code,
        "base_design_id": "I0001",
        "technique_code": suffix,
        "grid_width": cfg["w"],
        "grid_height": cfg["h"],
        "color_count": colors,
        "technique": cfg["technique"],
        "size_attribute_label": cfg["size_label"],
        "colour_attribute_label": cfg["colour_label"],
        "type_attribute_label": "Technique",
        "count_attribute_label": count_label,
        "featured_image": f"assets/{code}-product.webp",
    }


def main():
    collection = read_json(COLLECTION_DIR / "collection.json")
    labels = teddy_labels()
    matrix_cs, threads_cs = pattern_from_labels(labels, collection)

    technique_data = {"CS": (matrix_cs, threads_cs)}
    for suffix in ("C2C", "TC", "LH"):
        cfg = bg.TECHS[suffix]
        technique_data[suffix] = bg.downsample(matrix_cs, threads_cs, cfg["w"], cfg["h"])

    patterns = {}
    for suffix in ("CS", "C2C", "TC", "LH"):
        code = f"I0001-{suffix}"
        matrix, threads = technique_data[suffix]
        cfg = bg.TECHS[suffix]
        total = sum(1 for row in matrix for v in row if v)
        pattern = {
            "code": code,
            "base_design_id": "I0001",
            "technique_code": suffix,
            "collection": "baby-nursery",
            "palette_collection": "baby-nursery",
            "status": "ready",
            "source_asset": "generated-in-repo:baby-nursery/I0001-teddy-bear-v1",
            "stitch_width": cfg["w"],
            "stitch_height": cfg["h"],
            "total_stitches": total,
            "threads": threads,
            "matrix": matrix,
        }
        write_json(SYSTEM / "patterns" / code / "pattern.json", pattern)
        write_json(SYSTEM / "products" / code / "product.json", product_source(code, suffix))
        patterns[suffix] = pattern

    # Use the approved Baby & Nursery backgrounds, but keep Pop Art's exact
    # cover_overlay and cover_stage_scale values from bg.TECHS.
    temp_assets = Path("/tmp/drielo-baby-i0001-assets")
    temp_assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bg.ENGINE_ASSETS / "floral.png", temp_assets / "floral.png")
    cover_map = {
        "cover-cross-stitch.jpg": "cover-cross-stitch.webp",
        "cover-c2c-crochet.jpg": "cover-c2c-crochet.webp",
        "cover-crochet.jpg": "cover-crochet.webp",
        "cover-rug.jpg": "cover-rug.webp",
    }
    for src, dst in cover_map.items():
        Image.open(COLLECTION_DIR / "assets" / src).convert("RGB").save(temp_assets / dst, "WEBP", quality=94, method=6)
    bg.ENGINE_ASSETS = temp_assets

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for suffix in ("CS", "C2C", "TC", "LH"):
        code = f"I0001-{suffix}"
        pattern = patterns[suffix]
        data = bg.pattern_data(code, "Teddy Bear", suffix, pattern["matrix"], pattern["threads"])
        data["collection"] = "Baby & Nursery"
        data["collection_id"] = "baby-nursery"
        # IMPORTANT: do not modify data['cover_overlay'] or data['cover_stage_scale'].
        # They are the exact approved Pop Art placements requested for this collection.
        result = bg.render_one((code, suffix, data))
        shutil.copy2(result["pdf"], STORE_FILES / f"Drielo_{code}.pdf")
        shutil.copy2(result["image"], STORE_ASSETS / f"{code}-product.webp")
        print(json.dumps({"built": code, "pdf_bytes": result["pdf_bytes"], "image_bytes": result["image_bytes"]}))

    designs_path = COLLECTION_DIR / "designs.json"
    designs = read_json(designs_path)
    for item in designs.get("designs", []):
        if item.get("base_design_id") == "I0001":
            item["artwork_status"] = "canonical-pattern-ready"
            item["source_asset"] = "generated-in-repo:baby-nursery/I0001-teddy-bear-v1"
    write_json(designs_path, designs)

    catalog = read_json(CATALOG_PATH)
    ensure_categories(catalog)
    catalog["collections"] = [c for c in catalog.get("collections", []) if c.get("slug") != "baby-nursery"]
    catalog["collections"].append(collection_row(collection))

    codes = {f"I0001-{s}" for s in ("CS","C2C","TC","LH")}
    catalog["products"] = [p for p in catalog.get("products", []) if p.get("code") not in codes]
    for suffix in ("CS","C2C","TC","LH"):
        catalog["products"].append(product_row(suffix, patterns[suffix]))
    order = {"CS":0,"C2C":1,"TC":2,"LH":3}
    catalog["products"].sort(key=lambda p: (
        p.get("base_design_id", str(p.get("code","")).split("-")[0]),
        order.get(p.get("technique_code","CS"), 9),
    ))
    write_json(CATALOG_PATH, catalog)

    print("I0001_READY=4")


if __name__ == "__main__":
    main()
