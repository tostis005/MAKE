#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
import zipfile
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "content/products/catalog.json"
PATTERN_ROOT = ROOT / "content/pattern-system/patterns"
ASSETS = ROOT / "content/products/assets"
FILES = ROOT / "content/products/files"

DESIGNS = {
    "N0001": ("Christmas Tree", "Árbol de Navidad", "christmas tree"),
    "N0002": ("Santa Claus", "Papá Noel", "santa cross stitch"),
    "N0003": ("Snowman", "Muñeco de Nieve", "snowman pattern"),
    "N0004": ("Reindeer", "Reno", "reindeer pattern"),
    "N0005": ("Christmas Stocking", "Calcetín de Navidad", "xmas stocking"),
    "N0006": ("Gingerbread House", "Casa de Jengibre", "gingerbread house"),
    "N0007": ("Gingerbread Man", "Muñeco de Jengibre", "gingerbread man"),
    "N0008": ("Christmas Wreath", "Corona de Navidad", "christmas wreath"),
    "N0009": ("Candy Cane Mug", "Taza con Bastón de Caramelo", "christmas mug"),
    "N0010": ("Nutcracker", "Cascanueces", "nutcracker pattern"),
    "N0011": ("Christmas Bauble", "Bola de Navidad", "xmas ornament"),
    "N0012": ("Christmas Gnome", "Gnomo de Navidad", "christmas gnome"),
    "N0013": ("Poinsettia", "Flor de Pascua", "poinsettia pattern"),
    "N0014": ("Robin on Holly", "Petirrojo sobre Acebo", "christmas robin"),
    "N0015": ("Snow Globe", "Bola de Nieve", "snow globe pattern"),
}

BASE_TAGS = [
    "mini cross stitch",
    "christmas pattern",
    "xmas cross stitch",
    "easy cross stitch",
    "beginner pattern",
    "cross stitch pdf",
    "instant download",
    "small cross stitch",
    "christmas ornament",
    "counted cross stitch",
    "holiday embroidery",
    "digital pattern",
]

def readj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def writej(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def font(size: int, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def motif_bbox(pattern: dict):
    matrix = pattern["matrix"]
    xs, ys = [], []
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            if v is not None:
                xs.append(x); ys.append(y)
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))

def title_en(name: str):
    # Etsy-style keyword-rich title, under 140 chars.
    t = f"Mini {name} Cross Stitch Pattern PDF, Easy Beginner Christmas Ornament, Small Counted Cross Stitch, Instant Download"
    return t[:140].rstrip(" ,")

def title_es(name: str):
    t = f"Patrón Mini de {name} en Punto de Cruz PDF, Navidad Fácil para Principiantes, Descarga Digital"
    return t[:140].rstrip(" ,")

def etsy_description_en(name, w, h, stitches, colors):
    inch_w, inch_h = w / 14.0, h / 14.0
    cm_w, cm_h = inch_w * 2.54, inch_h * 2.54
    return f"""🎄 MINI CHRISTMAS CROSS STITCH PATTERN — DIGITAL PDF

A small, cheerful {name.lower()} counted cross stitch pattern designed for quick holiday stitching. The simple shapes, full cross stitches and compact size make it beginner-friendly while still being fun for experienced stitchers who want a relaxing Christmas project.

PATTERN DETAILS
• Design size: {w} W × {h} H stitches
• 14-count Aida finished size: approx. {inch_w:.1f} × {inch_h:.1f} in / {cm_w:.1f} × {cm_h:.1f} cm
• Full cross stitches only
• {colors} DMC colours
• Approx. {stitches:,} stitches
• Skill level: Easy / Beginner-Friendly
• Mini design — great for quick projects and small hoops

YOUR PDF INCLUDES
• Full-colour chart with symbols
• Black-and-white symbol chart
• DMC colour key and stitch information
• Finished design preview for reference
• Printable pages plus screen/tablet-friendly chart pages

PERFECT FOR
• Christmas ornaments
• Mini framed embroidery
• Gift tags and greeting cards
• Handmade holiday gifts
• Quick weekend stitching
• Beginner cross stitch projects

IMPORTANT
This listing is for a DIGITAL CROSS STITCH PATTERN only. No fabric, floss, hoop, needle or other physical materials are included. Your files are available as an instant digital download after purchase.

The chart is centred on a consistent 100 × 120 printable grid, with the mini motif itself contained within the approved 50 × 60 design area. Transparent cells remain blank Aida.

For personal use only. Please do not resell, redistribute or share the digital pattern files.

Happy stitching! 🎁"""

def etsy_description_es(name, w, h, stitches, colors):
    inch_w, inch_h = w / 14.0, h / 14.0
    cm_w, cm_h = inch_w * 2.54, inch_h * 2.54
    return f"""🎄 PATRÓN MINI DE PUNTO DE CRUZ NAVIDEÑO — PDF DIGITAL

Patrón contado de {name.lower()} pensado para proyectos navideños rápidos. Sus formas sencillas, el uso exclusivo de punto de cruz completo y su tamaño compacto hacen que sea apto para principiantes y agradable también para bordadores con experiencia.

DETALLES DEL PATRÓN
• Tamaño del motivo: {w} ancho × {h} alto puntadas
• En Aida 14: aprox. {inch_w:.1f} × {inch_h:.1f} pulgadas / {cm_w:.1f} × {cm_h:.1f} cm
• Solo punto de cruz completo
• {colors} colores DMC
• Aprox. {stitches:,} puntadas
• Nivel: Fácil / Apto para principiantes
• Diseño mini ideal para proyectos rápidos

EL PDF INCLUYE
• Diagrama a color con símbolos
• Diagrama en blanco y negro con símbolos
• Clave de colores DMC e información de puntadas
• Vista previa del diseño terminado
• Páginas imprimibles y páginas cómodas para pantalla/tablet

IDEAL PARA
• Adornos de Navidad
• Mini bastidores o cuadros
• Etiquetas de regalo y tarjetas
• Regalos hechos a mano
• Proyectos rápidos
• Principiantes

IMPORTANTE
Este anuncio es únicamente para un PATRÓN DIGITAL. No incluye tela, hilos, bastidor, aguja ni materiales físicos. Los archivos estarán disponibles como descarga digital después de la compra.

El diagrama se presenta centrado en una cuadrícula imprimible de 100 × 120, mientras que el motivo mini está contenido dentro del área de diseño aprobada de 50 × 60. Las celdas transparentes quedan como Aida en blanco.

Solo para uso personal. No se permite revender, redistribuir ni compartir los archivos digitales."""

def woocommerce_description(en_text: str):
    lines = en_text.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.isupper() or s.endswith("DETAILS") or s in {"YOUR PDF INCLUDES", "PERFECT FOR", "IMPORTANT"}:
            out.append(f"<h3>{s}</h3>")
        elif s.startswith("•"):
            out.append(f"<p>{s}</p>")
        else:
            out.append(f"<p>{s}</p>")
    return "".join(out)

def make_bundle_images():
    previews = []
    for i in range(1, 16):
        p = ASSETS / f"N{i:04d}-CS-design.webp"
        if not p.is_file():
            raise SystemExit(f"Missing design preview: {p}")
        previews.append(Image.open(p).convert("RGB"))

    bg = (248, 245, 239)
    card = (255, 255, 255)
    textc = (35, 35, 35)

    def render_grid(indices, out_path, title, subtitle, cols):
        W, H = 2000, 1600
        canvas = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(canvas)
        d.text((100, 70), title, font=font(64, True), fill=textc)
        d.text((100, 150), subtitle, font=font(32), fill=(80, 80, 80))
        top = 240
        rows = math.ceil(len(indices)/cols)
        gap = 28
        cell_w = (W - 200 - gap*(cols-1)) // cols
        cell_h = (H - top - 100 - gap*(rows-1)) // rows
        for pos, idx in enumerate(indices):
            r, c = divmod(pos, cols)
            x = 100 + c*(cell_w+gap)
            y = top + r*(cell_h+gap)
            d.rounded_rectangle((x,y,x+cell_w,y+cell_h), radius=24, fill=card)
            im = previews[idx]
            target_w = cell_w - 30
            target_h = cell_h - 30
            scale = min(target_w/im.width, target_h/im.height)
            thumb = im.resize((max(1,int(im.width*scale)), max(1,int(im.height*scale))), Image.Resampling.LANCZOS)
            px = x + (cell_w-thumb.width)//2
            py = y + (cell_h-thumb.height)//2
            canvas.paste(thumb,(px,py))
        canvas.save(out_path, "WEBP", quality=94, method=6)

    render_grid(
        list(range(15)),
        ASSETS / "XMAS15-CS-product.webp",
        "15 Mini Christmas Cross Stitch Patterns",
        "Beginner-Friendly PDF Bundle • Full Cross Stitch • Instant Download",
        5
    )
    render_grid(list(range(0,5)), ASSETS/"XMAS15-CS-gallery-2.webp", "Christmas Minis 1–5", "Tree • Santa • Snowman • Reindeer • Stocking", 5)
    render_grid(list(range(5,10)), ASSETS/"XMAS15-CS-gallery-3.webp", "Christmas Minis 6–10", "Gingerbread House • Gingerbread Man • Wreath • Mug • Nutcracker", 5)
    render_grid(list(range(10,15)), ASSETS/"XMAS15-CS-gallery-4.webp", "Christmas Minis 11–15", "Bauble • Gnome • Poinsettia • Robin • Snow Globe", 5)

def make_bundle_zip():
    FILES.mkdir(parents=True, exist_ok=True)
    readme = """DRIELO — 15 Mini Christmas Cross Stitch Patterns

This bundle contains 15 individual PDF cross stitch patterns.
Each PDF includes colour charts, black-and-white symbol charts, DMC colour information and finished-design previews.

Digital patterns only. No physical materials are included.
Personal use only. Please do not resell, redistribute or share the digital files.
"""
    gs = shutil.which("gs")
    if not gs:
        raise SystemExit("Ghostscript is required to build Etsy-safe bundle files")

    tmpdir = Path(tempfile.mkdtemp(prefix="drielo_etsy_bundle_"))
    compressed = {}
    try:
        profiles = [
            (120, 120, 300),
            (100, 100, 240),
            (85, 85, 200),
            (72, 72, 180),
        ]
        for i in range(1,16):
            src = FILES / f"Drielo_N{i:04d}-CS.pdf"
            if not src.is_file():
                raise SystemExit(f"Missing PDF: {src}")
            best = None
            for n,(cr,gr,mr) in enumerate(profiles, start=1):
                out = tmpdir / f"N{i:04d}-compressed-{n}.pdf"
                cmd = [
                    gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                    "-dNOPAUSE", "-dQUIET", "-dBATCH",
                    "-dDetectDuplicateImages=true",
                    "-dCompressFonts=true",
                    "-dSubsetFonts=true",
                    "-dDownsampleColorImages=true",
                    "-dDownsampleGrayImages=true",
                    "-dDownsampleMonoImages=true",
                    f"-dColorImageResolution={cr}",
                    f"-dGrayImageResolution={gr}",
                    f"-dMonoImageResolution={mr}",
                    f"-sOutputFile={out}", str(src)
                ]
                subprocess.run(cmd, check=True)
                if best is None or out.stat().st_size < best.stat().st_size:
                    best = out
                if out.stat().st_size <= 6_000_000:
                    break
            if best is None:
                raise SystemExit(f"Could not compress {src}")
            compressed[i] = best

        outs = []
        groups = [(1,3),(4,6),(7,9),(10,12),(13,15)]
        for part,(start_i,end_i) in enumerate(groups, start=1):
            out = FILES / f"Drielo_XMAS15-CS_Part{part}.zip"
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                zf.writestr("README.txt", readme)
                for i in range(start_i,end_i+1):
                    zf.write(compressed[i], arcname=f"Drielo_N{i:04d}-CS.pdf")
            if out.stat().st_size > 19_500_000:
                raise SystemExit(f"Etsy ZIP part too large after compression: {out} {out.stat().st_size}")
            outs.append(out)
        return outs
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    cat = readj(CATALOG)
    products = cat.setdefault("products", [])
    by_code = {p.get("code"): p for p in products}

    for base, (name_en, name_es, tag) in DESIGNS.items():
        code = f"{base}-CS"
        row = by_code.get(code)
        if row is None:
            raise SystemExit(f"Catalog product missing: {code}")
        pat = readj(PATTERN_ROOT / code / "pattern.json")
        x0,y0,x1,y1 = motif_bbox(pat)
        w = x1-x0+1
        h = y1-y0+1
        stitches = int(pat.get("total_stitches", 0))
        colors = len(pat.get("threads", []))
        desc_en = etsy_description_en(name_en,w,h,stitches,colors)
        desc_es = etsy_description_es(name_es,w,h,stitches,colors)
        tags = (BASE_TAGS + [tag])[:13]

        row.update({
            "title": f"{name_en} Mini Cross Stitch Pattern PDF",
            "title_en": f"{name_en} Mini Cross Stitch Pattern PDF",
            "title_es": f"Patrón Mini de {name_es} en Punto de Cruz PDF",
            "etsy_title_en": title_en(name_en),
            "etsy_title_es": title_es(name_es),
            "etsy_description_en": desc_en,
            "etsy_description_es": desc_es,
            "etsy_tags_en": tags,
            "etsy_tags_es": [
                "punto de cruz mini","patron navidad","punto de cruz pdf","facil principiantes",
                "descarga digital","punto de cruz facil","adorno navidad","patron digital",
                "bordado navidad","punto de cruz","mini navidad","patron facil", tag[:20]
            ][:13],
            "short_description_en": f"Mini {name_en.lower()} counted cross stitch PDF. {w} × {h} stitches, {colors} DMC colours, full cross stitches only, beginner-friendly and designed for quick Christmas projects.",
            "short_description_es": f"Patrón mini de {name_es.lower()} en punto de cruz. {w} × {h} puntadas, {colors} colores DMC, solo punto de cruz completo y apto para principiantes.",
            "description_en": woocommerce_description(desc_en),
            "description_es": woocommerce_description(desc_es),
            "skill": "Beginner friendly",
            "skill_en": "Beginner friendly",
            "skill_es": "Apto para principiantes",
            "stitch_type": "Full cross stitch only",
            "stitch_type_en": "Full cross stitch only",
            "stitch_type_es": "Solo punto de cruz completo",
            "grid": f"{w} × {h} stitch motif (centred on 100 × 120 chart)",
            "grid_width": w,
            "grid_height": h,
            "colours": colors,
            "color_count": colors,
            "stitches": stitches,
            "seo_title": title_en(name_en),
            "seo_title_en": title_en(name_en),
            "seo_title_es": title_es(name_es),
            "meta_description_en": f"Mini {name_en.lower()} cross stitch PDF for Christmas. Beginner-friendly, full cross stitches only, colour + black-and-white charts, DMC key and instant download."[:155],
            "meta_description_es": f"Patrón mini de {name_es.lower()} para Navidad. Apto para principiantes, diagrama a color y en blanco y negro, clave DMC y descarga digital."[:155],
            "gallery_revision": "etsy-christmas-v1",
        })

    make_bundle_images()
    bundle_parts = make_bundle_zip()

    bundle_desc_en = """🎄 15 MINI CHRISTMAS CROSS STITCH PATTERNS — DIGITAL PDF BUNDLE

Get the complete Drielo Christmas mini collection in one bundle: 15 separate counted cross stitch patterns designed for quick, cheerful holiday stitching.

INCLUDED DESIGNS
• Christmas Tree
• Santa Claus
• Snowman
• Reindeer
• Christmas Stocking
• Gingerbread House
• Gingerbread Man
• Christmas Wreath
• Candy Cane Mug
• Nutcracker
• Christmas Bauble
• Christmas Gnome
• Poinsettia
• Robin on Holly
• Snow Globe

WHAT YOU RECEIVE
• 15 individual PDF cross stitch patterns supplied across five ZIP downloads
• Full-colour charts with symbols
• Black-and-white symbol charts
• DMC colour keys and stitch information
• Finished-design previews
• Printable and screen/tablet-friendly pages

COLLECTION DETAILS
• Mini patterns designed within a 50 × 60 stitch motif area
• Full cross stitches only
• Beginner-friendly / easy
• Shared coordinated Christmas palette
• Great for ornaments, gift tags, greeting cards, mini frames and handmade gifts

IMPORTANT
This is a DIGITAL DOWNLOAD only. No fabric, floss, hoop, needle or physical materials are included.
For personal use only. Please do not resell, redistribute or share the digital files.

A simple way to get the complete Christmas set and stitch the whole collection at your own pace. 🎁"""

    bundle_desc_es = """🎄 15 PATRONES MINI DE PUNTO DE CRUZ DE NAVIDAD — BUNDLE DIGITAL

Colección completa Drielo de Navidad con 15 patrones individuales pensados para proyectos rápidos y fáciles.

INCLUYE 15 DISEÑOS
Árbol de Navidad, Papá Noel, muñeco de nieve, reno, calcetín, casa de jengibre, muñeco de jengibre, corona, taza con bastón de caramelo, cascanueces, bola de Navidad, gnomo, flor de Pascua, petirrojo y bola de nieve.

RECIBIRÁS
• 15 PDFs individuales dentro de un archivo ZIP
• Diagramas a color con símbolos
• Diagramas en blanco y negro con símbolos
• Claves de colores DMC e información de puntadas
• Vistas previas de los diseños terminados
• Páginas imprimibles y cómodas para pantalla/tablet

DETALLES
• Diseños mini dentro de un área de motivo de 50 × 60
• Solo punto de cruz completo
• Fácil / apto para principiantes
• Paleta navideña coordinada
• Ideal para adornos, tarjetas, etiquetas de regalo, mini cuadros y regalos hechos a mano

IMPORTANTE
Producto DIGITAL. No incluye materiales físicos.
Solo para uso personal. No se permite revender, redistribuir ni compartir los archivos."""

    bundle = by_code.get("XMAS15-CS")
    if bundle is None:
        bundle = {}
        products.append(bundle)

    bundle.update({
        "code":"XMAS15-CS",
        "sku":"DRIELO-XMAS15-CS",
        "price":9.99,
        "fixed_price":True,
        "categories":["cross-stitch-patterns","cross-stitch-christmas"],
        "title":"15 Mini Christmas Cross Stitch Patterns Bundle PDF",
        "title_en":"15 Mini Christmas Cross Stitch Patterns Bundle PDF",
        "title_es":"Bundle de 15 Patrones Mini de Navidad en Punto de Cruz PDF",
        "etsy_title_en":"15 Mini Christmas Cross Stitch Patterns Bundle PDF, Easy Beginner Xmas Ornaments, Instant Digital Download",
        "etsy_title_es":"Bundle 15 Patrones Mini de Navidad Punto de Cruz PDF, Fácil Principiantes, Descarga Digital",
        "etsy_description_en":bundle_desc_en,
        "etsy_description_es":bundle_desc_es,
        "etsy_tags_en":[
            "christmas bundle","mini cross stitch","christmas pattern","xmas cross stitch",
            "beginner pattern","cross stitch pdf","instant download","easy cross stitch",
            "christmas ornament","counted cross stitch","holiday embroidery","digital pattern","15 patterns"
        ],
        "etsy_tags_es":[
            "bundle navidad","punto de cruz mini","patron navidad","punto de cruz pdf",
            "principiantes","descarga digital","punto de cruz facil","adorno navidad",
            "bordado navidad","patron digital","15 patrones","navidad mini","punto de cruz"
        ],
        "slug":"15-mini-christmas-cross-stitch-patterns-bundle",
        "collection":"christmas",
        "stitches":0,
        "grid":"15 mini patterns · each within a 50 × 60 stitch motif area",
        "colours":20,
        "color_count":20,
        "grid_width":50,
        "grid_height":60,
        "skill":"Beginner friendly",
        "skill_en":"Beginner friendly",
        "skill_es":"Apto para principiantes",
        "stitch_type":"Full cross stitch only",
        "stitch_type_en":"Full cross stitch only",
        "stitch_type_es":"Solo punto de cruz completo",
        "short_description_en":"Complete bundle of 15 mini Christmas counted cross stitch PDFs. Beginner-friendly, full cross stitches only, colour + black-and-white charts, DMC keys and instant download.",
        "short_description_es":"Bundle completo de 15 patrones mini de Navidad en PDF. Apto para principiantes, solo punto de cruz completo, diagramas a color y en blanco y negro y claves DMC.",
        "description_en":woocommerce_description(bundle_desc_en),
        "description_es":woocommerce_description(bundle_desc_es),
        "gallery":[
            "assets/XMAS15-CS-gallery-2.webp",
            "assets/XMAS15-CS-gallery-3.webp",
            "assets/XMAS15-CS-gallery-4.webp"
        ],
        "download":"files/Drielo_XMAS15-CS_Part1.zip",
        "downloads":[
            "files/Drielo_XMAS15-CS_Part1.zip",
            "files/Drielo_XMAS15-CS_Part2.zip",
            "files/Drielo_XMAS15-CS_Part3.zip",
            "files/Drielo_XMAS15-CS_Part4.zip",
            "files/Drielo_XMAS15-CS_Part5.zip"
        ],
        "featured_image":"assets/XMAS15-CS-product.webp",
        "seo_title":"15 Mini Christmas Cross Stitch Patterns Bundle PDF | Drielo",
        "seo_title_en":"15 Mini Christmas Cross Stitch Patterns Bundle PDF | Drielo",
        "seo_title_es":"Bundle de 15 Patrones Mini de Navidad en Punto de Cruz PDF | Drielo",
        "meta_description":"15 mini Christmas cross stitch PDF patterns in one bundle. Beginner-friendly, full cross stitches only, colour and black-and-white charts, DMC keys.",
        "meta_description_en":"15 mini Christmas cross stitch PDF patterns in one bundle. Beginner-friendly, full cross stitches only, colour and black-and-white charts, DMC keys.",
        "meta_description_es":"15 patrones mini de Navidad en punto de cruz PDF. Apto para principiantes, diagramas a color y blanco y negro y claves DMC.",
        "tags":["christmas bundle","mini cross stitch","christmas pattern","xmas cross stitch","beginner pattern","cross stitch pdf"],
        "design_id":"XMAS15-CS",
        "base_design_id":"XMAS15",
        "technique_code":"CS",
        "technique":"cross-stitch",
        "filters":{
            "technique":["cross-stitch"],
            "theme":["holidays-seasons"],
            "style":["cute"],
            "project":["wall-art"],
            "orientation":["portrait"],
            "difficulty":["beginner"],
            "color-family":["multicolor"],
            "season":["christmas"]
        },
        "gallery_revision":"etsy-christmas-v1"
    })

    writej(CATALOG, cat)
    print("ETSY_CHRISTMAS_METADATA_READY products=15 bundle=1 bundle_price=9.99")

if __name__ == "__main__":
    main()
