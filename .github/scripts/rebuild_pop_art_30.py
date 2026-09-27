#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path.cwd()
SYSTEM = ROOT / "content" / "pattern-system"
CID = "pop-art-25"
CDIR = SYSTEM / "collections" / CID
STAGED = CDIR / "rework-30" / "sources"
SOURCES = CDIR / "sources"
PRODUCTS_DIR = SYSTEM / "products"
PATTERNS_DIR = SYSTEM / "patterns"
CATALOG = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
DMC_PATH = SYSTEM / "data" / "dmc-colors.json"
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")

DESIGNS = [
    ("P0001","Albert Einstein Tongue Out","Albert Einstein sacando la lengua","albert-einstein-tongue-out"),
    ("P0002","Apple Man Portrait","Retrato del hombre de la manzana","apple-man-portrait"),
    ("P0003","Audrey Hepburn Bubble Gum","Audrey Hepburn con chicle","audrey-hepburn-bubble-gum"),
    ("P0004","Audrey Hepburn Profile","Audrey Hepburn de perfil","audrey-hepburn-profile"),
    ("P0005","Audrey Hepburn Sunglasses","Audrey Hepburn con gafas","audrey-hepburn-sunglasses"),
    ("P0006","Charlie Chaplin Portrait","Retrato de Charlie Chaplin","charlie-chaplin-portrait"),
    ("P0007","Frida Kahlo Floral Crown","Frida Kahlo con corona floral","frida-kahlo-floral-crown"),
    ("P0008","Girl with a Pearl Earring Bubble Gum","La joven de la perla con chicle","girl-pearl-earring-bubble-gum"),
    ("P0009","Girl with a Pearl Earring","La joven de la perla","girl-with-a-pearl-earring"),
    ("P0010","Girl with a Pearl Earring Sunglasses","La joven de la perla con gafas","girl-pearl-earring-sunglasses"),
    ("P0011","Marilyn Monroe Blowing Kiss","Marilyn Monroe lanzando un beso","marilyn-monroe-blowing-kiss"),
    ("P0012","Marilyn Monroe Bubble Gum","Marilyn Monroe con chicle","marilyn-monroe-bubble-gum"),
    ("P0013","Marilyn Monroe Sunglasses","Marilyn Monroe con gafas","marilyn-monroe-sunglasses"),
    ("P0014","Marilyn Monroe Surprise","Marilyn Monroe sorprendida","marilyn-monroe-surprise"),
    ("P0015","Marilyn Monroe Wink","Marilyn Monroe guiñando un ojo","marilyn-monroe-wink"),
    ("P0016","Mona Lisa Portrait","Retrato de la Mona Lisa","mona-lisa-portrait"),
    ("P0017","Salvador Dalí Portrait","Retrato de Salvador Dalí","salvador-dali-portrait"),
    ("P0018","Van Gogh with Sunflower","Van Gogh con girasol","van-gogh-sunflower"),
    ("P0019","Vincent van Gogh Portrait","Retrato de Vincent van Gogh","vincent-van-gogh-portrait"),
    ("P0020","James Dean Portrait","Retrato de James Dean","james-dean-portrait"),
    ("P0021","David Bowie Portrait","Retrato de David Bowie","david-bowie-portrait"),
    ("P0022","Princess Diana Bubble Gum","Princesa Diana con chicle","princess-diana-bubble-gum"),
    ("P0023","Princess Diana Portrait","Retrato de la princesa Diana","princess-diana-portrait"),
    ("P0024","Michael Jackson Portrait","Retrato de Michael Jackson","michael-jackson-portrait"),
    ("P0025","Nelson Mandela Portrait","Retrato de Nelson Mandela","nelson-mandela-portrait"),
    ("P0026","Freddie Mercury Portrait","Retrato de Freddie Mercury","freddie-mercury-portrait"),
]

TECH = {
    "CS":  {"technique":"cross-stitch","display_en":"Cross Stitch","display_es":"punto de cruz","w":100,"h":120,"unit":"stitches","unit_es":"puntos","count_en":"Total stitches","count_es":"Puntadas","stitch_en":"Full cross stitch","stitch_es":"Punto de cruz completo","project":"wall-art","price":2.99,"categories":["cross-stitch-patterns","portraits","pop-art"],"cover":"multitech/assets/cover-cross-stitch.webp"},
    "C2C": {"technique":"c2c-crochet","display_en":"C2C Crochet","display_es":"crochet C2C","w":60,"h":72,"unit":"blocks","unit_es":"bloques","count_en":"Filled blocks","count_es":"Bloques","stitch_en":"Corner-to-corner blocks","stitch_es":"Bloques de crochet C2C","project":"blanket","price":2.49,"categories":["c2c-crochet-patterns","c2c-crochet-portraits","c2c-crochet-pop-art"],"cover":"multitech/assets/cover-crochet.webp"},
    "TC":  {"technique":"tapestry-crochet","display_en":"Tapestry Crochet","display_es":"crochet tapestry","w":80,"h":96,"unit":"crochet stitches","unit_es":"puntos de crochet","count_en":"Colourwork stitches","count_es":"Puntos","stitch_en":"Tapestry crochet colourwork","stitch_es":"Crochet tapestry en color","project":"tapestry","price":2.49,"categories":["tapestry-crochet-patterns","tapestry-crochet-portraits","tapestry-crochet-pop-art"],"cover":"multitech/assets/cover-c2c-crochet.webp"},
    "LH":  {"technique":"latch-hook","display_en":"Latch Hook Rug","display_es":"alfombra latch hook","w":60,"h":72,"unit":"knots","unit_es":"nudos","count_en":"Filled knots","count_es":"Nudos","stitch_en":"Latch hook / rug knots","stitch_es":"Nudos latch hook / alfombra","project":"rug","price":2.49,"categories":["latch-hook-rug-patterns","latch-hook-rug-portraits","latch-hook-rug-pop-art"],"cover":"multitech/assets/cover-rug.webp"},
}

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def load_palette_rgb():
    manifest = json.loads((STAGED / "manifest.json").read_text(encoding="utf-8"))
    colors = [tuple(int(v) for v in rgb) for rgb in manifest["palette_rgb"]]
    if len(colors) != 30 or len(set(colors)) != 30:
        raise RuntimeError(f"Expected exactly 30 staged RGB colours, got {len(set(colors))}")
    return colors

def build_palette(colors):
    dmc = json.loads(DMC_PATH.read_text(encoding="utf-8"))
    rows = []
    seen = set()
    for row in dmc:
        floss = str(row.get("floss","")).strip()
        if not floss or floss in seen:
            continue
        try:
            rgb = (int(row["r"]), int(row["g"]), int(row["b"]))
        except Exception:
            continue
        if any(v < 0 or v > 255 for v in rgb):
            continue
        rows.append((floss, row.get("description") or f"DMC {floss}", rgb))
        seen.add(floss)

    used = set()
    palette = []
    for col in colors:
        def dist(item):
            r,g,b = col
            dr,dg,db = item[2]
            return 2*(r-dr)**2 + 4*(g-dg)**2 + 3*(b-db)**2
        choice = next(x for x in sorted(rows, key=dist) if x[0] not in used)
        used.add(choice[0])
        palette.append({
            "dmc": choice[0],
            "hex": "#%02X%02X%02X" % col,
            "name": choice[1],
        })
    if len({p["dmc"] for p in palette}) != 30:
        raise RuntimeError("DMC mapping is not unique")
    return palette

def source_matrix(path: Path, palette):
    im = Image.open(path).convert("RGB")
    if im.size != (100,120):
        raise RuntimeError(f"{path}: expected 100x120, got {im.size}")
    by_rgb = {
        tuple(int(p["hex"][i:i+2],16) for i in (1,3,5)): SYMBOLS[n]
        for n,p in enumerate(palette)
    }
    counts = Counter()
    matrix = []
    for y in range(120):
        row = []
        for x in range(100):
            c = im.getpixel((x,y))
            if c not in by_rgb:
                raise RuntimeError(f"{path}: unexpected RGB {c}")
            s = by_rgb[c]
            row.append(s)
            counts[s] += 1
        matrix.append(row)
    threads = []
    for n,p in enumerate(palette):
        s = SYMBOLS[n]
        if counts[s]:
            threads.append({
                "symbol":s,
                "dmc":str(p["dmc"]),
                "color":p["hex"],
                "name":p["name"],
                "stitches":counts[s],
            })
    return matrix,threads

def product_json(base,en,es,slug,suffix):
    cfg = TECH[suffix]
    return {
        "code": f"{base}-{suffix}",
        "base_design_id": base,
        "technique_code": suffix,
        "collection": CID,
        "title": en,
        "title_en": en,
        "title_es": es,
        "design_slug": slug,
        "technique": cfg["technique"],
        "pattern_file": f"patterns/{base}-{suffix}/pattern.json",
        "template": {"CS":"cross-stitch.html","C2C":"c2c-crochet.html","TC":"crochet.html","LH":"rug.html"}[suffix],
        "website":"www.drielo.com",
        "status":"ready",
        "render_ready":True,
        "renderer":"multitech",
        "source_artwork":f"collections/{CID}/sources/{base}.png",
        "page_1_asset":cfg["cover"],
        "palette_mode":"strict",
        "palette_size":30,
        "transparent_source":False,
    }

def pattern_json(base,suffix,matrix,threads):
    cfg = TECH[suffix]
    return {
        "code":f"{base}-{suffix}",
        "base_design_id":base,
        "technique_code":suffix,
        "collection":CID,
        "palette_collection":CID,
        "status":"ready",
        "source_asset":f"content/pattern-system/collections/{CID}/sources/{base}.png",
        "stitch_width":cfg["w"],
        "stitch_height":cfg["h"],
        "total_stitches":sum(t["stitches"] for t in threads),
        "color_count":len(threads),
        "palette_size":30,
        "transparent_background":False,
        "threads":threads,
        "matrix":matrix,
    }

def row_for(base,en,es,slug,suffix,data):
    cfg = TECH[suffix]
    code = f"{base}-{suffix}"
    total = data["total_stitches"]
    colors = len(data["threads"])
    title = f"{en} {cfg['display_en']} Pattern PDF"
    title_es = f"Patrón PDF de {cfg['display_es']}: {es}"
    grid = f"{cfg['w']} × {cfg['h']} {cfg['unit']}"
    short = (
        f"Downloadable {en} {cfg['display_en']} pattern PDF. {grid}; "
        f"{total:,} positions; {colors} colours from the shared 30-colour Pop Art palette; "
        f"beginner friendly. Pattern code: {code}."
    )
    short_es = (
        f"Patrón PDF descargable de {cfg['display_es']}: {es}. "
        f"{cfg['w']} × {cfg['h']} {cfg['unit_es']}; {total:,} posiciones; "
        f"{colors} colores de la paleta Pop Art compartida de 30 colores; "
        f"apto para principiantes. Código: {code}."
    )
    desc = (
        f"<p><strong>{title}</strong> is a downloadable digital pattern from Drielo’s Pop Art collection.</p>"
        f"<p><strong>Pattern code:</strong> {code}</p>"
        f"<p>Every design in this collection is built from the same coordinated 30-colour master palette.</p>"
        f"<h3>Pattern details</h3><ul><li>Chart: {grid}</li><li>{cfg['count_en']}: {total:,}</li>"
        f"<li>Colours used: {colors} from the shared 30-colour palette</li>"
        f"<li>Technique: {cfg['stitch_en']}</li><li>Beginner friendly</li></ul>"
        f"<h3>What you receive</h3><p>A complete printable PDF with finished preview, pattern facts, colour key, charts, symbols, enlarged sections and working guide.</p>"
        f"<p>Digital product only. Personal use only.</p>"
    )
    desc_es = (
        f"<p><strong>{title_es}</strong> es un patrón digital descargable de la colección Pop Art de Drielo.</p>"
        f"<p><strong>Código:</strong> {code}</p>"
        f"<p>Todos los diseños de esta colección se construyen con la misma paleta maestra coordinada de 30 colores.</p>"
        f"<h3>Detalles</h3><ul><li>Gráfico: {cfg['w']} × {cfg['h']} {cfg['unit_es']}</li>"
        f"<li>{cfg['count_es']}: {total:,}</li><li>Colores usados: {colors} de la paleta compartida de 30 colores</li>"
        f"<li>Técnica: {cfg['stitch_es']}</li><li>Apto para principiantes</li></ul>"
        f"<h3>Qué recibirás</h3><p>PDF completo e imprimible con vista previa, datos del patrón, clave de colores, gráficos, símbolos, secciones ampliadas y guía de trabajo.</p>"
        f"<p>Producto digital. Solo para uso personal.</p>"
    )
    tagtech = {"CS":"cross stitch","C2C":"c2c crochet","TC":"tapestry crochet","LH":"latch hook"}[suffix]
    tags = [tagtech,"digital pattern","pop art portrait","portrait pattern","instant download","beginner pattern","colorwork chart",slug[:20]]
    return {
        "code":code,
        "sku":f"DRIELO-{code}",
        "base_design_id":base,
        "design_id":code,
        "technique_code":suffix,
        "technique":cfg["technique"],
        "title":title,
        "title_en":title,
        "title_es":title_es,
        "slug":f"{slug}-{cfg['technique']}-pattern",
        "price":cfg["price"],
        "collection":CID,
        "stitches":total,
        "grid":grid,
        "colours":colors,
        "color_count":colors,
        "grid_width":cfg["w"],
        "grid_height":cfg["h"],
        "skill":"Beginner friendly",
        "skill_en":"Beginner friendly",
        "skill_es":"Apto para principiantes",
        "stitch_type":cfg["stitch_en"],
        "stitch_type_en":cfg["stitch_en"],
        "stitch_type_es":cfg["stitch_es"],
        "short_description":short,
        "short_description_en":short,
        "short_description_es":short_es,
        "description":desc,
        "description_en":desc,
        "description_es":desc_es,
        "categories":cfg["categories"],
        "tags":tags,
        "etsy_tags_en":tags,
        "etsy_tags_es":tags,
        "gallery":[],
        "featured_image":f"assets/{code}-product.webp",
        "download":f"files/Drielo_{code}.pdf",
        "gallery_revision":2026092701,
        "seo_title":f"{en} {cfg['display_en']} Pattern PDF | Drielo",
        "seo_title_en":f"{en} {cfg['display_en']} Pattern PDF | Drielo",
        "seo_title_es":f"{es} - patrón {cfg['display_es']} PDF | Drielo",
        "meta_description":f"{en} {cfg['display_en']} PDF {code}: {cfg['w']} × {cfg['h']}, {colors} colours from a shared 30-colour palette.",
        "meta_description_en":f"{en} {cfg['display_en']} PDF {code}: {cfg['w']} × {cfg['h']}, {colors} colours from a shared 30-colour palette.",
        "meta_description_es":f"{es}, patrón {cfg['display_es']} PDF {code}: {cfg['w']} × {cfg['h']}, {colors} colores de una paleta compartida de 30 colores.",
        "purchase_note_en":"Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
        "purchase_note_es":"Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        "size_attribute_label":"Pattern size",
        "colour_attribute_label":"DMC colours" if suffix=="CS" else "Yarn colours",
        "type_attribute_label":"Technique",
        "count_attribute_label":cfg["count_en"],
        "filters":{
            "technique":[cfg["technique"]],
            "theme":["people-portraits"],
            "style":["pop-art","colorful"],
            "project":[cfg["project"]],
            "orientation":["portrait"],
            "difficulty":["beginner"],
            "color-family":["multicolor"],
            "season":[],
        },
    }

def main():
    if len(SYMBOLS) < 30:
        raise RuntimeError("Not enough chart symbols for 30 colours")
    staged_pngs = sorted(STAGED.glob("P*.png"))
    if len(staged_pngs) != 26:
        raise RuntimeError(f"Expected 26 staged PNGs, got {len(staged_pngs)}")

    colors = load_palette_rgb()
    palette = build_palette(colors)

    SOURCES.mkdir(parents=True, exist_ok=True)
    for p in staged_pngs:
        shutil.copy2(p, SOURCES / p.name)

    collection = {
        "id":CID,
        "name":"Pop Art",
        "name_en":"Pop Art",
        "name_es":"Pop Art",
        "slug":CID,
        "code_prefix":"P",
        "description":"26 vivid Pop Art portrait designs sharing one coordinated 30-colour palette across four grid-based craft techniques.",
        "description_en":"26 vivid Pop Art portrait designs sharing one coordinated 30-colour palette across four grid-based craft techniques.",
        "description_es":"26 diseños Pop Art vibrantes que comparten una única paleta coordinada de 30 colores en cuatro técnicas basadas en cuadrícula.",
        "palette_mode":"shared",
        "show_collection_palette":True,
        "palette":palette,
        "design_count":26,
        "techniques":["cross-stitch","c2c-crochet","tapestry-crochet","latch-hook"],
        "mockup_spec":{
            "asset":"../../multitech/assets/cover-cross-stitch.webp",
            "technique_assets":{
                "CS":"../../multitech/assets/cover-cross-stitch.webp",
                "C2C":"../../multitech/assets/cover-crochet.webp",
                "TC":"../../multitech/assets/cover-c2c-crochet.webp",
                "LH":"../../multitech/assets/cover-rug.webp",
            },
            "frame":{"enabled":False},
        },
        "preview_rules":{
            "palette_mode":"strict",
            "allowed_palette_size":30,
            "gradients":False,
            "extra_colours":False,
            "transparent_background":False,
        },
    }
    write_json(CDIR / "collection.json", collection)

    write_json(CDIR / "designs.json", {
        "collection":CID,
        "palette_size":30,
        "transparent_background":False,
        "designs":[{
            "code":base,
            "title_en":en,
            "title_es":es,
            "slug":slug,
            "status":"ready",
            "source_artwork":f"sources/{base}.png",
            "transparent_background":False,
            "variants":[f"{base}-{s}" for s in ("CS","C2C","TC","LH")],
        } for base,en,es,slug in DESIGNS],
    })

    modpath = SYSTEM / "multitech" / "bulk_generate.py"
    spec = importlib.util.spec_from_file_location("drielo_bulk", modpath)
    bulk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bulk)

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    retired = set(catalog.get("retired_products", []))
    retired.update({"DRIELO-P0001","DRIELO-P0012"})
    catalog["retired_products"] = sorted(retired)
    new_rows = []
    tasks = []

    for base,en,es,slug in DESIGNS:
        matrix_cs,threads_cs = source_matrix(SOURCES / f"{base}.png", palette)
        variants = {"CS":(matrix_cs,threads_cs)}
        for suffix in ("C2C","TC","LH"):
            cfg = TECH[suffix]
            variants[suffix] = bulk.downsample(matrix_cs, threads_cs, cfg["w"], cfg["h"])

        for suffix in ("CS","C2C","TC","LH"):
            matrix,threads = variants[suffix]
            code = f"{base}-{suffix}"
            write_json(PATTERNS_DIR / code / "pattern.json", pattern_json(base,suffix,matrix,threads))
            write_json(PRODUCTS_DIR / code / "product.json", product_json(base,en,es,slug,suffix))
            data = bulk.pattern_data(code,en,suffix,matrix,threads)
            data["collection"] = "Pop Art"
            data["collection_id"] = CID
            tasks.append((code,suffix,data))
            new_rows.append(row_for(base,en,es,slug,suffix,data))

    expected = {f"P{i:04d}-{s}" for i in range(1,27) for s in ("CS","C2C","TC","LH")}
    if {r["code"] for r in new_rows} != expected:
        raise RuntimeError("Did not prepare exactly 104 Pop Art variants")

    catalog["collections"] = [
        c for c in catalog.get("collections",[]) if c.get("slug") != CID
    ] + [{
        "id":CID,
        "name":"Pop Art",
        "slug":CID,
        "name_en":"Pop Art",
        "name_es":"Pop Art",
        "description":collection["description_en"],
        "description_en":collection["description_en"],
        "description_es":collection["description_es"],
        "palette_mode":"shared",
        "show_collection_palette":True,
        "palette_hex":[p["hex"] for p in palette],
        "thread_codes":[p["dmc"] for p in palette],
        "cover_asset":"assets/pop-art-25-collection-cover.webp",
        "techniques":collection["techniques"],
        "visible":True,
        "force_visibility_sync":True,
    }]

    def base_of(row):
        return row.get("base_design_id") or re.sub(r"-.*$","",str(row.get("code","")))

    pop_bases = {x[0] for x in DESIGNS}
    catalog["products"] = [
        p for p in catalog.get("products",[])
        if not (base_of(p) in pop_bases or p.get("collection") == CID)
    ]
    catalog["products"].extend(new_rows)

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    bulk.OUTPUT.mkdir(parents=True, exist_ok=True)

    results = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(bulk.render_one, task):task[0] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print("BUILT", result["code"], result["pdf_bytes"], result["image_bytes"], flush=True)

    by_code = {r["code"]:r for r in results}
    if set(by_code) != expected:
        raise RuntimeError(f"Rendered {len(by_code)} variants, expected 104")

    rows_by_code = {r["code"]:r for r in new_rows}
    for code,result in by_code.items():
        shutil.copy2(result["pdf"], STORE_FILES / Path(result["pdf"]).name)
        shutil.copy2(result["image"], STORE_ASSETS / Path(result["image"]).name)
        shutil.copy2(result["design_preview"], STORE_ASSETS / Path(result["design_preview"]).name)
        gallery_assets = []
        design_name = Path(result["design_preview"]).name
        gallery_assets.append(f"assets/{design_name}")
        for item in result["gallery"]:
            src = Path(item)
            shutil.copy2(src, STORE_ASSETS / src.name)
            gallery_assets.append(f"assets/{src.name}")
        rows_by_code[code]["gallery"] = gallery_assets

    catalog["products"].sort(key=lambda p:(
        base_of(p),
        {"CS":0,"C2C":1,"TC":2,"LH":3}.get(p.get("technique_code",""),9),
        p.get("code",""),
    ))
    write_json(CATALOG, catalog)

    # Final QA: source files are exact, palette is globally 30 colours, all product files exist.
    seen = set()
    for base,_,_,_ in DESIGNS:
        im = Image.open(SOURCES / f"{base}.png").convert("RGB")
        if im.size != (100,120):
            raise RuntimeError(f"{base}: wrong source size {im.size}")
        seen.update(im.getdata())
    if len(seen) != 30:
        raise RuntimeError(f"Official sources use {len(seen)} RGB colours, expected 30")
    if {("#%02X%02X%02X" % c) for c in seen} != {p["hex"] for p in palette}:
        raise RuntimeError("Collection palette does not exactly match source RGB set")

    pop_rows = [p for p in catalog["products"] if p.get("collection") == CID]
    if len(pop_rows) != 104:
        raise RuntimeError(f"Catalog has {len(pop_rows)} Pop Art products, expected 104")
    for row in pop_rows:
        code = row["code"]
        if not (STORE_ASSETS / f"{code}-product.webp").is_file():
            raise RuntimeError(f"Missing featured image for {code}")
        if not (STORE_FILES / f"Drielo_{code}.pdf").is_file():
            raise RuntimeError(f"Missing PDF for {code}")
        if len(row.get("gallery",[])) != 4:
            raise RuntimeError(f"Expected 4 gallery images for {code}")

    print(json.dumps({
        "collection":CID,
        "designs":26,
        "variants":104,
        "source_size":"100x120",
        "shared_palette":30,
        "rendered":len(results),
    }, indent=2))

if __name__ == "__main__":
    main()
