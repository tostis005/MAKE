#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "content/source-images/collections/christmas/products/N0001-christmas-tree.png"
BG = ROOT / "content/source-images/collections/christmas/background/christmas-collection-background.png"
PALETTE = ROOT / "content/source-images/collections/christmas/palette20_rgb.json"
DMC = ROOT / "content/pattern-system/data/dmc-colors.json"

ASSETS = ROOT / "content/products/assets"
FILES = ROOT / "content/products/files"
PATTERNS = ROOT / "content/pattern-system/patterns/N0001-CS"
PRODUCTS = ROOT / "content/pattern-system/products/N0001-CS"
CATALOG = ROOT / "content/products/catalog.json"

CODE = "N0001-CS"
SKU = "DRIELO-N0001-CS"
GRID_W, GRID_H = 100, 120
MOTIF_W, MOTIF_H = 50, 60
OFF_X, OFF_Y = (GRID_W - MOTIF_W)//2, (GRID_H - MOTIF_H)//2

# Exact measured 5:6 Aida opening used by the existing Drielo 100x120 product mockups.
FRAME_X, FRAME_Y, FRAME_W, FRAME_H = 438, 212, 685, 822

SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") + list("!@#$%&*+=?^~:;/\\")
TITLE_EN = "Christmas Tree Mini Cross Stitch Pattern PDF"
TITLE_ES = "Patrón Mini de Árbol de Navidad en Punto de Cruz PDF"

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def font(size: int, bold: bool=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def nearest_dmc(rgb, dmc_rows):
    r,g,b = rgb
    return min(dmc_rows, key=lambda p: 2*(r-p["rgb"][0])**2 + 4*(g-p["rgb"][1])**2 + 3*(b-p["rgb"][2])**2)

def load_dmc():
    rows=[]
    seen=set()
    for row in read_json(DMC):
        code=str(row.get("floss","")).strip()
        if not code or code in seen:
            continue
        try:
            rgb=(int(row["r"]),int(row["g"]),int(row["b"]))
        except Exception:
            continue
        rows.append({
            "dmc":code,
            "name":str(row.get("description") or f"DMC {code}"),
            "rgb":rgb,
            "hex":"#%02X%02X%02X" % rgb,
        })
        seen.add(code)
    return rows

def build_pattern(src: Image.Image):
    colors = list(dict.fromkeys(src.getdata()))
    if len(colors) > 20:
        raise RuntimeError(f"Expected <=20 source colours, got {len(colors)}")
    dmc_rows = load_dmc()
    mapped = {c: nearest_dmc(c, dmc_rows) for c in colors}

    # One symbol per exact source colour so the 50x60 mini stays faithful.
    symbol_for = {c: SYMBOLS[i] for i,c in enumerate(colors)}
    counts=Counter()
    matrix=[[None for _ in range(GRID_W)] for _ in range(GRID_H)]
    for y in range(MOTIF_H):
        for x in range(MOTIF_W):
            c=src.getpixel((x,y))
            sym=symbol_for[c]
            matrix[OFF_Y+y][OFF_X+x]=sym
            counts[sym]+=1

    threads=[]
    for c in colors:
        sym=symbol_for[c]
        d=mapped[c]
        threads.append({
            "symbol":sym,
            "dmc":d["dmc"],
            "name":d["name"],
            "source_rgb":list(c),
            "color":"#%02X%02X%02X" % c,
            "mapped_dmc_color":d["hex"],
            "stitches":counts[sym],
        })

    pattern={
        "code":CODE,
        "base_design_id":"N0001",
        "technique_code":"CS",
        "collection":"christmas",
        "status":"ready",
        "source_asset":"source-images/collections/christmas/products/N0001-christmas-tree.png",
        "palette_mode":"shared-20-source-colours",
        "source_motif_width":MOTIF_W,
        "source_motif_height":MOTIF_H,
        "stitch_width":GRID_W,
        "stitch_height":GRID_H,
        "motif_offset":{"x":OFF_X,"y":OFF_Y},
        "total_stitches":MOTIF_W*MOTIF_H,
        "threads":threads,
        "matrix":matrix,
    }
    return pattern

def render_hero(src: Image.Image):
    bg=Image.open(BG).convert("RGB")
    if bg.size != (1536,1536):
        raise RuntimeError(f"Christmas background must be 1536x1536, got {bg.size}")

    draw=ImageDraw.Draw(bg)
    cell_w=FRAME_W/GRID_W
    cell_h=FRAME_H/GRID_H

    # Draw the 50x60 motif as real X stitches at the center of the virtual 100x120 canvas.
    # The outer 25 columns / 30 rows on each side remain untouched Aida.
    for sy in range(MOTIF_H):
        for sx in range(MOTIF_W):
            gx=OFF_X+sx
            gy=OFF_Y+sy
            c=src.getpixel((sx,sy))
            x0=FRAME_X + gx*cell_w
            y0=FRAME_Y + gy*cell_h
            x1=FRAME_X + (gx+1)*cell_w
            y1=FRAME_Y + (gy+1)*cell_h
            pad=max(0.8, min(cell_w,cell_h)*0.16)
            width=max(2, int(round(min(cell_w,cell_h)*0.36)))
            draw.line((x0+pad,y0+pad,x1-pad,y1-pad), fill=c, width=width)
            draw.line((x1-pad,y0+pad,x0+pad,y1-pad), fill=c, width=width)

    ASSETS.mkdir(parents=True, exist_ok=True)
    out=ASSETS/f"{CODE}-product.webp"
    bg.save(out, "WEBP", quality=95, method=6)
    return out

def render_pdf(src: Image.Image, pattern: dict):
    # One-page A4 300dpi pattern. Full 100x120 chart is shown; the 50x60 motif
    # stays centered with blank grid all around it.
    W,H=2480,3508
    page=Image.new("RGB",(W,H),"white")
    d=ImageDraw.Draw(page)
    f_title=font(62,True)
    f_sub=font(34,False)
    f_cell=font(12,True)
    f_legend=font(24,False)
    f_legend_b=font(26,True)

    d.text((140,90), "Christmas Tree Mini Cross Stitch Pattern", font=f_title, fill=(30,30,30))
    d.text((140,175), "100 × 120 chart · centered 50 × 60 stitched motif · 3,000 stitches", font=f_sub, fill=(70,70,70))

    cell=16
    chart_w=GRID_W*cell
    chart_h=GRID_H*cell
    ox=(W-chart_w)//2
    oy=285

    # Filled central 50x60 motif; blank outer cells stay white.
    for y in range(GRID_H):
        for x in range(GRID_W):
            x0=ox+x*cell; y0=oy+y*cell
            sym=pattern["matrix"][y][x]
            if sym is not None:
                sx=x-OFF_X; sy=y-OFF_Y
                c=src.getpixel((sx,sy))
                d.rectangle((x0,y0,x0+cell-1,y0+cell-1), fill=c)
                lum=0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
                txt=(20,20,20) if lum>145 else (255,255,255)
                bbox=d.textbbox((0,0),sym,font=f_cell)
                tw=bbox[2]-bbox[0]; th=bbox[3]-bbox[1]
                d.text((x0+(cell-tw)/2,y0+(cell-th)/2-1),sym,font=f_cell,fill=txt)

    for x in range(GRID_W+1):
        xx=ox+x*cell
        width=3 if x%10==0 else 1
        fill=(80,80,80) if x%10==0 else (190,190,190)
        d.line((xx,oy,xx,oy+chart_h),fill=fill,width=width)
    for y in range(GRID_H+1):
        yy=oy+y*cell
        width=3 if y%10==0 else 1
        fill=(80,80,80) if y%10==0 else (190,190,190)
        d.line((ox,yy,ox+chart_w,yy),fill=fill,width=width)

    legend_y=oy+chart_h+70
    d.text((140,legend_y),"Colour key",font=f_legend_b,fill=(30,30,30))
    legend_y+=55
    cols=2
    col_w=1100
    row_h=56
    for i,t in enumerate(pattern["threads"]):
        col=i%cols
        row=i//cols
        x=140+col*col_w
        y=legend_y+row*row_h
        c=tuple(t["source_rgb"])
        d.rectangle((x,y+5,x+34,y+39),fill=c,outline=(80,80,80),width=1)
        label=f'{t["symbol"]}   DMC {t["dmc"]}   {t["name"]}   · {t["stitches"]} stitches'
        d.text((x+50,y),label,font=f_legend,fill=(40,40,40))

    footer_y=H-150
    d.text((140,footer_y),"Digital counted cross-stitch pattern · Drielo",font=f_sub,fill=(80,80,80))

    FILES.mkdir(parents=True, exist_ok=True)
    out=FILES/f"Drielo_{CODE}.pdf"
    page.save(out,"PDF",resolution=300.0,quality=95)
    return out

def update_catalog(pattern: dict):
    catalog=read_json(CATALOG)

    # Add/refresh Christmas subcategory under the existing cross-stitch root.
    cats=catalog.setdefault("categories",[])
    child={
        "slug":"cross-stitch-christmas",
        "name":"Christmas Cross Stitch",
        "name_en":"Christmas Cross Stitch",
        "name_es":"Punto de cruz de Navidad",
        "parent":"cross-stitch-patterns",
    }
    idx=next((i for i,c in enumerate(cats) if c.get("slug")==child["slug"]),None)
    if idx is None: cats.append(child)
    else: cats[idx].update(child)

    palette_doc=read_json(PALETTE)
    palette_hex=["#%02X%02X%02X" % tuple(c) for c in palette_doc["palette_rgb"]]
    thread_codes=[str(t["dmc"]) for t in pattern["threads"]]

    collections=catalog.setdefault("collections",[])
    collection={
        "id":"christmas",
        "slug":"christmas",
        "name":"Christmas",
        "name_en":"Christmas",
        "name_es":"Navidad",
        "description":"Mini Christmas cross-stitch patterns designed as quick, beginner-friendly seasonal projects.",
        "description_en":"Mini Christmas cross-stitch patterns designed as quick, beginner-friendly seasonal projects.",
        "description_es":"Mini patrones navideños de punto de cruz pensados como proyectos rápidos y aptos para principiantes.",
        "techniques":["cross-stitch"],
        "cover_asset":f"assets/{CODE}-product.webp",
        "visible":True,
        "force_visibility_sync":True,
        "palette_mode":"shared",
        "show_collection_palette":True,
        "palette_hex":palette_hex,
        "thread_codes":thread_codes,
    }
    idx=next((i for i,c in enumerate(collections) if c.get("slug")=="christmas"),None)
    if idx is None: collections.append(collection)
    else: collections[idx].update(collection)

    colours=len(pattern["threads"])
    total=pattern["total_stitches"]
    short_en=f"Mini Christmas tree cross-stitch PDF. A 50 × 60 full-coverage motif is centered on a 100 × 120 chart, leaving generous blank canvas around it. {total:,} stitches and {colours} colours."
    short_es=f"Mini patrón PDF de árbol de Navidad. El motivo de 50 × 60 queda centrado en una cuadrícula de 100 × 120, dejando bastante lienzo en blanco alrededor. {total:,} puntadas y {colours} colores."
    desc_en=(
        f"<p><strong>{TITLE_EN}</strong> is a digital counted cross-stitch pattern from the Christmas Minis collection.</p>"
        "<p>The artwork itself is 50 × 60 stitches and is centered inside a 100 × 120 chart. "
        "The extra area stays blank, so the storefront mockup keeps the same physical scale as Drielo's existing 100 × 120 patterns.</p>"
        f"<h3>Pattern details</h3><ul><li>Code: {CODE}</li><li>Chart: 100 × 120 stitches</li>"
        f"<li>Stitched motif: 50 × 60 stitches</li><li>Total stitched cells: {total:,}</li>"
        f"<li>Colours: {colours}</li><li>PDF: 1 page</li><li>Skill level: Beginner friendly</li></ul>"
        "<p>Digital product only.</p>"
    )
    desc_es=(
        f"<p><strong>{TITLE_ES}</strong> es un patrón digital contado de la colección Christmas Minis.</p>"
        "<p>El dibujo ocupa 50 × 60 puntos y está centrado dentro de una cuadrícula de 100 × 120. "
        "La zona adicional queda en blanco para conservar en el mockup la misma escala física que los patrones Drielo de 100 × 120.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {CODE}</li><li>Cuadrícula: 100 × 120</li>"
        f"<li>Motivo bordado: 50 × 60</li><li>Puntadas: {total:,}</li>"
        f"<li>Colores: {colours}</li><li>PDF: 1 página</li><li>Nivel: apto para principiantes</li></ul>"
        "<p>Producto exclusivamente digital.</p>"
    )

    row={
        "code":CODE,
        "sku":SKU,
        "price":2.99,
        "categories":["cross-stitch-patterns","cross-stitch-christmas"],
        "purchase_note_en":"Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
        "purchase_note_es":"Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        "title":TITLE_EN,
        "title_en":TITLE_EN,
        "title_es":TITLE_ES,
        "slug":"christmas-tree-mini-cross-stitch-pattern",
        "collection":"christmas",
        "stitches":total,
        "grid":"100 × 120 stitches",
        "colours":colours,
        "color_count":colours,
        "grid_width":GRID_W,
        "grid_height":GRID_H,
        "motif_width":MOTIF_W,
        "motif_height":MOTIF_H,
        "skill":"Beginner friendly",
        "skill_en":"Beginner friendly",
        "skill_es":"Apto para principiantes",
        "stitch_type":"Full cross stitch",
        "stitch_type_en":"Full cross stitch",
        "stitch_type_es":"Punto de cruz completo",
        "short_description":short_en,
        "short_description_en":short_en,
        "short_description_es":short_es,
        "description":desc_en,
        "description_en":desc_en,
        "description_es":desc_es,
        "gallery":[],
        "download":f"files/Drielo_{CODE}.pdf",
        "featured_image":f"assets/{CODE}-product.webp",
        "seo_title":f"{TITLE_EN} | Drielo",
        "seo_title_en":f"{TITLE_EN} | Drielo",
        "seo_title_es":f"{TITLE_ES} | Drielo",
        "meta_description":short_en[:155],
        "meta_description_en":short_en[:155],
        "meta_description_es":short_es[:155],
        "tags":["christmas tree","christmas cross stitch","mini cross stitch","cross stitch pdf","counted cross stitch","digital pattern"],
        "etsy_tags_en":["christmas tree","christmas cross stitch","mini cross stitch","cross stitch pdf","counted cross stitch","digital pattern"],
        "etsy_tags_es":["árbol de navidad","punto de cruz navidad","mini punto de cruz","patrón pdf","punto de cruz","patrón digital"],
        "design_id":CODE,
        "base_design_id":"N0001",
        "technique_code":"CS",
        "technique":"cross-stitch",
        "size_attribute_label":"Pattern size",
        "colour_attribute_label":"Colours",
        "type_attribute_label":"Technique",
        "count_attribute_label":"Total stitches",
        "filters":{
            "technique":["cross-stitch"],
            "theme":["holidays-seasons"],
            "style":["cute"],
            "project":["wall-art"],
            "orientation":["portrait"],
            "difficulty":["beginner"],
            "color-family":["multicolor"],
            "season":["christmas"],
        },
    }
    products=catalog.setdefault("products",[])
    idx=next((i for i,p in enumerate(products) if p.get("code")==CODE or p.get("sku")==SKU),None)
    if idx is None: products.append(row)
    else: products[idx]=row

    catalog["retired_products"]=[x for x in catalog.get("retired_products",[]) if x!=SKU]
    write_json(CATALOG,catalog)
    return row, collection

def main():
    src=Image.open(SRC).convert("RGB")
    if src.size != (50,60):
        raise RuntimeError(f"N0001 source must be exactly 50x60, got {src.size}")
    if len(set(src.getdata())) > 20:
        raise RuntimeError("N0001 uses more than the shared 20-colour maximum")

    pattern=build_pattern(src)
    write_json(PATTERNS/"pattern.json",pattern)
    write_json(PRODUCTS/"product.json",{
        "code":CODE,
        "base_design_id":"N0001",
        "technique_code":"CS",
        "collection":"christmas",
        "title":TITLE_EN,
        "title_en":TITLE_EN,
        "title_es":TITLE_ES,
        "technique":"cross-stitch",
        "pattern_file":"patterns/N0001-CS/pattern.json",
        "template":"single-page-100x120-centered-mini",
        "status":"active",
        "render_ready":True,
        "source_artwork":"source-images/collections/christmas/products/N0001-christmas-tree.png",
        "page_1_asset":"source-images/collections/christmas/background/christmas-collection-background.png",
    })

    hero=render_hero(src)
    pdf=render_pdf(src,pattern)
    row,collection=update_catalog(pattern)

    print(json.dumps({
        "code":CODE,
        "source_size":list(src.size),
        "virtual_canvas":[GRID_W,GRID_H],
        "motif_offset":[OFF_X,OFF_Y],
        "total_stitches":pattern["total_stitches"],
        "source_colours":len(pattern["threads"]),
        "hero":str(hero.relative_to(ROOT)),
        "hero_bytes":hero.stat().st_size,
        "pdf":str(pdf.relative_to(ROOT)),
        "pdf_bytes":pdf.stat().st_size,
    },ensure_ascii=False))

if __name__=="__main__":
    main()
