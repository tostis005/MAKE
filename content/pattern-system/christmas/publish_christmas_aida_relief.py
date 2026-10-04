#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
SYSTEM=ROOT/"content"/"pattern-system"
COL=ROOT/"content"/"source-images"/"collections"/"christmas"
PRODUCTS_DIR=COL/"products"
BG=COL/"background"/"christmas-collection-background.png"
PAL=COL/"palette20_rgb.json"
DMC=SYSTEM/"data"/"dmc-colors.json"
PATTERN_ROOT=SYSTEM/"patterns"
PRODUCT_ROOT=SYSTEM/"products"
CAT=ROOT/"content"/"products"/"catalog.json"
STORE_ASSETS=ROOT/"content"/"products"/"assets"
STORE_FILES=ROOT/"content"/"products"/"files"

sys.path.insert(0,str((SYSTEM/"multitech").resolve()))
import bulk_generate as bg

GRID_W,GRID_H=100,120
SRC_W,SRC_H=50,60
OFF_X,OFF_Y=25,30
FRAME=(438,212,685,822)
SYMBOLS=list("ABCDEFGHJKLMNPQRSTUV")

DESIGNS={
    "N0001":("christmas-tree","Christmas Tree","Árbol de Navidad"),
    "N0002":("snowman","Snowman","Muñeco de Nieve"),
    "N0003":("santa-face","Santa Face","Cara de Papá Noel"),
    "N0004":("reindeer","Reindeer","Reno"),
    "N0005":("christmas-stocking","Christmas Stocking","Calcetín de Navidad"),
    "N0006":("gingerbread-house","Gingerbread House","Casa de Jengibre"),
    "N0007":("christmas-wreath","Christmas Wreath","Corona de Navidad"),
    "N0008":("candy-cane-mug","Candy Cane Mug","Taza con Bastón de Caramelo"),
    "N0009":("nutcracker","Nutcracker","Cascanueces"),
    "N0010":("ornament-bauble","Christmas Bauble","Bola de Navidad"),
    "N0011":("christmas-gnome","Christmas Gnome","Gnomo de Navidad"),
    "N0012":("poinsettia","Poinsettia","Flor de Pascua"),
    "N0013":("robin-on-holly","Robin on Holly","Petirrojo sobre Acebo"),
    "N0014":("polar-bear-with-scarf","Polar Bear with Scarf","Oso Polar con Bufanda"),
    "N0015":("holiday-church","Christmas Chapel","Capilla de Navidad"),
}

def readj(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def writej(p:Path,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def dmc_table():
    rows=[]; seen=set()
    for r in readj(DMC):
        code=str(r.get("floss","")).strip()
        if not code or code in seen:
            continue
        try:
            rgb=(int(r["r"]),int(r["g"]),int(r["b"]))
        except Exception:
            continue
        rows.append({"dmc":code,"name":str(r.get("description") or f"DMC {code}"),"rgb":rgb})
        seen.add(code)
    if len(rows)<400:
        raise RuntimeError("DMC table incomplete")
    return rows

def nearest(rgb,rows):
    r,g,b=rgb
    return min(rows,key=lambda p:2*(r-p["rgb"][0])**2+4*(g-p["rgb"][1])**2+3*(b-p["rgb"][2])**2)

def build_pattern(base_id:str):
    if base_id not in DESIGNS:
        raise RuntimeError(f"Unknown Christmas design {base_id}")
    slug,title_en,title_es=DESIGNS[base_id]
    code=f"{base_id}-CS"
    source=PRODUCTS_DIR/f"{base_id}-{slug}.png"

    src=Image.open(source).convert("RGBA")
    if src.size!=(SRC_W,SRC_H):
        raise RuntimeError(f"{source.name}: expected 50x60, got {src.size}")

    palette=[tuple(x) for x in readj(PAL)["palette_rgb"]]
    if len(palette)!=20 or len(set(palette))!=20:
        raise RuntimeError("Christmas palette must contain exactly 20 distinct RGB colours")
    symbol_for={c:SYMBOLS[i] for i,c in enumerate(palette)}
    dmc=dmc_table()

    matrix=[[None]*GRID_W for _ in range(GRID_H)]
    counts=Counter()
    opaque=0
    for sy in range(SRC_H):
        for sx in range(SRC_W):
            r,g,b,a=src.getpixel((sx,sy))
            if a<128:
                continue
            c=(r,g,b)
            if c not in symbol_for:
                raise RuntimeError(f"{source.name}: pixel {(sx,sy)} colour {c} outside shared palette")
            sym=symbol_for[c]
            matrix[OFF_Y+sy][OFF_X+sx]=sym
            counts[sym]+=1
            opaque+=1

    if opaque<=0 or opaque>=SRC_W*SRC_H:
        raise RuntimeError(f"{base_id}: invalid transparent motif stitch count {opaque}")

    threads=[]
    for c in palette:
        sym=symbol_for[c]
        if counts[sym]<=0:
            continue
        dm=nearest(c,dmc)
        threads.append({
            "symbol":sym,
            "dmc":dm["dmc"],
            "name":dm["name"],
            # Keep the exact approved shared-palette RGB for rendering.
            "color":"#%02X%02X%02X"%c,
            "source_rgb":list(c),
            "source_hex":"#%02X%02X%02X"%c,
            "stitches":counts[sym],
        })

    # Guardrail: transparency becomes blank Aida and nothing else.
    for y in range(GRID_H):
        for x in range(GRID_W):
            inside=OFF_X<=x<OFF_X+SRC_W and OFF_Y<=y<OFF_Y+SRC_H
            if not inside:
                if matrix[y][x] is not None:
                    raise RuntimeError(f"{base_id}: nonblank cell outside 50x60 motif at {(x,y)}")
                continue
            r,g,b,a=src.getpixel((x-OFF_X,y-OFF_Y))
            expected=None if a<128 else symbol_for[(r,g,b)]
            if matrix[y][x]!=expected:
                raise RuntimeError(f"{base_id}: pixel/matrix mismatch at {(x,y)}")

    pattern={
        "code":code,
        "base_design_id":base_id,
        "technique_code":"CS",
        "collection":"christmas",
        "status":"ready",
        "algorithm":"pixel-exact-alpha-1px-1stitch-aida-relief-v4",
        "source_asset":f"source-images/collections/christmas/products/{source.name}",
        "palette_mode":"shared-exact-20-rgb",
        "shared_palette_rgb":[list(c) for c in palette],
        "source_width":SRC_W,
        "source_height":SRC_H,
        "stitch_width":GRID_W,
        "stitch_height":GRID_H,
        "source_offset":{"x":OFF_X,"y":OFF_Y},
        "total_stitches":opaque,
        "threads":threads,
        "matrix":matrix,
    }
    writej(PATTERN_ROOT/code/"pattern.json",pattern)

    product=readj(PRODUCT_ROOT/code/"product.json") if (PRODUCT_ROOT/code/"product.json").is_file() else {}
    product.update({
        "code":code,
        "base_design_id":base_id,
        "technique_code":"CS",
        "collection":"christmas",
        "title":f"{title_en} Mini Cross Stitch Pattern PDF",
        "title_en":f"{title_en} Mini Cross Stitch Pattern PDF",
        "title_es":f"Patrón Mini de {title_es} en Punto de Cruz PDF",
        "design_slug":slug,
        "technique":"cross-stitch",
        "pattern_file":f"patterns/{code}/pattern.json",
        "template":"cross-stitch.html",
        "website":"www.drielo.com",
        "status":"active",
        "render_ready":True,
        "renderer":"multitech-aida-relief-v4",
        "source_artwork":f"source-images/collections/christmas/products/{source.name}",
        "palette_mode":"shared-exact-20-rgb",
    })
    writej(PRODUCT_ROOT/code/"product.json",product)
    return src,pattern,slug,title_en,title_es

def render(base_id:str,pattern:dict,title_en:str):
    code=f"{base_id}-CS"
    if not BG.is_file():
        raise RuntimeError(f"Missing Christmas background: {BG}")
    with Image.open(BG) as check:
        if check.size!=(1536,1536):
            raise RuntimeError(f"Christmas background must be 1536x1536, got {check.size}")

    data=bg.pattern_data(code,title_en,"CS",pattern["matrix"],pattern["threads"])
    data.update({
        "collection":"Christmas",
        "collection_id":"christmas",
        "title":title_en,
        "subtitle":"Mini pixel-exact Christmas cross-stitch pattern",
        "stitch_width":GRID_W,
        "stitch_height":GRID_H,
        "total_stitches":pattern["total_stitches"],
        "threads":pattern["threads"],
        "matrix":pattern["matrix"],
        "cover_image_path":str(BG.resolve()),
        "cover_overlay":{
            "left":round(FRAME[0]/1536*100,4),
            "top":round(FRAME[1]/1536*100,4),
            "width":round(FRAME[2]/1536*100,4),
            "height":round(FRAME[3]/1536*100,4),
            "opacity":0.96,
            "safe_inset_pct":0.0,
        },
        "cover_stage_scale":bg.TECHS["CS"]["cover_stage_scale"],
        "finished_subtitle":"Exact 100 × 120 Aida preview",
        "finished_caption":"Each opaque source pixel becomes one full cross stitch; transparent pixels remain blank Aida.",
        "preview_label":"Finished cross-stitch preview",
    })
    result=bg.render_one((code,"CS",data))

    STORE_ASSETS.mkdir(parents=True,exist_ok=True)
    STORE_FILES.mkdir(parents=True,exist_ok=True)

    pdf=STORE_FILES/f"Drielo_{code}.pdf"
    shutil.copy2(result["pdf"],pdf)

    x,y,w,h=FRAME
    background=Image.open(BG).convert("RGB")
    preview=Image.open(result["design_preview"]).convert("RGB")
    rendered=preview.resize((w,h),Image.Resampling.LANCZOS)
    background.paste(rendered,(x,y))
    hero=STORE_ASSETS/f"{code}-product.webp"
    background.save(hero,"WEBP",quality=94,method=6)

    galleries=[]
    for n,src in enumerate(result.get("gallery",[]),start=2):
        dst=STORE_ASSETS/f"{code}-gallery-{n}.webp"
        shutil.copy2(src,dst)
        galleries.append(dst)
    if len(galleries)!=3:
        raise RuntimeError(f"{code}: expected 3 gallery assets, got {len(galleries)}")

    design_dst=STORE_ASSETS/f"{code}-design.webp"
    shutil.copy2(result["design_preview"],design_dst)

    if not pdf.is_file() or pdf.read_bytes()[:4]!=b"%PDF" or pdf.stat().st_size<100000:
        raise RuntimeError(f"{code}: invalid PDF")
    with Image.open(hero) as im:
        if im.size!=(1536,1536):
            raise RuntimeError(f"{code}: hero wrong size {im.size}")

def update_catalog(base_id:str,pattern:dict,slug:str,title_en:str,title_es:str):
    code=f"{base_id}-CS"
    cat=readj(CAT)
    products=cat.setdefault("products",[])
    row=next((p for p in products if p.get("sku")==f"DRIELO-{code}" or p.get("code")==code),None)
    if row is None:
        row={"code":code,"sku":f"DRIELO-{code}","price":2.99}
        products.append(row)

    colours=len(pattern["threads"])
    total=pattern["total_stitches"]
    short_en=(f"Mini {title_en.lower()} cross-stitch PDF rendered with Drielo's pixel-by-pixel Aida/X engine. "
              f"Transparent cells remain blank Aida; {total:,} full cross stitches and {colours} colours.")
    short_es=(f"Mini patrón PDF de {title_es.lower()} renderizado con el motor píxel a píxel de Aida y cruces de Drielo. "
              f"Las celdas transparentes quedan como Aida en blanco; {total:,} puntadas completas y {colours} colores.")

    row.update({
        "code":code,
        "sku":f"DRIELO-{code}",
        "price":row.get("price",2.99),
        "categories":["cross-stitch-patterns","cross-stitch-christmas"],
        "title":f"{title_en} Mini Cross Stitch Pattern PDF",
        "title_en":f"{title_en} Mini Cross Stitch Pattern PDF",
        "title_es":f"Patrón Mini de {title_es} en Punto de Cruz PDF",
        "slug":f"{slug}-mini-cross-stitch-pattern",
        "collection":"christmas",
        "stitches":total,
        "grid":"100 × 120 stitches",
        "colours":colours,
        "color_count":colours,
        "grid_width":100,
        "grid_height":120,
        "motif_width":50,
        "motif_height":60,
        "skill":"Beginner friendly",
        "skill_en":"Beginner friendly",
        "skill_es":"Apto para principiantes",
        "stitch_type":"Full cross stitch",
        "stitch_type_en":"Full cross stitch",
        "stitch_type_es":"Punto de cruz completo",
        "short_description":short_en,
        "short_description_en":short_en,
        "short_description_es":short_es,
        "description":(
            f"<p><strong>{title_en} Mini Cross Stitch Pattern PDF</strong></p>"
            f"<p>The transparent 50 × 60 source is read pixel by pixel and centered inside a 100 × 120 matrix. "
            f"Every opaque pixel becomes one full X stitch and every transparent pixel remains blank Aida. "
            f"The PDF, finished preview and WooCommerce hero use the same Aida-relief-v4 stitch engine.</p>"
            f"<p>{total:,} stitches · {colours} colours.</p>"
        ),
        "description_en":(
            f"<p><strong>{title_en} Mini Cross Stitch Pattern PDF</strong></p>"
            f"<p>The transparent 50 × 60 source is read pixel by pixel and centered inside a 100 × 120 matrix. "
            f"Every opaque pixel becomes one full X stitch and every transparent pixel remains blank Aida. "
            f"The PDF, finished preview and WooCommerce hero use the same Aida-relief-v4 stitch engine.</p>"
            f"<p>{total:,} stitches · {colours} colours.</p>"
        ),
        "description_es":(
            f"<p><strong>Patrón Mini de {title_es} en Punto de Cruz PDF</strong></p>"
            f"<p>La fuente transparente de 50 × 60 se lee píxel a píxel y se centra dentro de una matriz de 100 × 120. "
            f"Cada píxel opaco se convierte en una cruz completa y cada píxel transparente queda como Aida en blanco. "
            f"El PDF, la vista terminada y la imagen de WooCommerce usan el mismo motor Aida-relief-v4.</p>"
            f"<p>{total:,} puntadas · {colours} colores.</p>"
        ),
        "gallery":[f"assets/{code}-gallery-{i}.webp" for i in (2,3,4)],
        "gallery_preview_pages":{"facts":3,"colour_a1":8,"symbol_a1":12},
        "download":f"files/Drielo_{code}.pdf",
        "featured_image":f"assets/{code}-product.webp",
        "seo_title":f"{title_en} Mini Cross Stitch Pattern PDF | Drielo",
        "seo_title_en":f"{title_en} Mini Cross Stitch Pattern PDF | Drielo",
        "seo_title_es":f"Patrón Mini de {title_es} en Punto de Cruz PDF | Drielo",
        "meta_description":short_en[:155],
        "meta_description_en":short_en[:155],
        "meta_description_es":short_es[:155],
        "tags":[slug.replace("-"," "), "christmas cross stitch","mini cross stitch","cross stitch pdf","counted cross stitch","digital pattern"],
        "design_id":code,
        "base_design_id":base_id,
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
            "season":["christmas"],
        },
    })
    cat["retired_products"]=[x for x in cat.get("retired_products",[]) if x!=f"DRIELO-{code}"]
    writej(CAT,cat)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("design_id")
    args=ap.parse_args()
    base_id=args.design_id.strip().upper()
    src,pattern,slug,title_en,title_es=build_pattern(base_id)
    render(base_id,pattern,title_en)
    update_catalog(base_id,pattern,slug,title_en,title_es)
    print(json.dumps({
        "code":f"{base_id}-CS",
        "renderer":"aida-relief-v4",
        "source":"50x60 transparent",
        "grid":"100x120",
        "offset":[25,30],
        "stitches":pattern["total_stitches"],
        "blank_cells":12000-pattern["total_stitches"],
        "colours":len(pattern["threads"]),
    },ensure_ascii=False))

if __name__=="__main__":
    main()
