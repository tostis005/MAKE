#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
SYSTEM=ROOT/"content"/"pattern-system"
SRC=ROOT/"content"/"source-images"/"collections"/"christmas"/"products"/"N0001-christmas-tree.png"
BG=ROOT/"content"/"source-images"/"collections"/"christmas"/"background"/"christmas-collection-background.png"
PAL=ROOT/"content"/"source-images"/"collections"/"christmas"/"palette20_rgb.json"
DMC=SYSTEM/"data"/"dmc-colors.json"
PAT=SYSTEM/"patterns"/"N0001-CS"/"pattern.json"
PROD=SYSTEM/"products"/"N0001-CS"/"product.json"
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
CODE="N0001-CS"

def readj(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def writej(p:Path,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def dmc_table():
    rows=[]
    seen=set()
    for r in readj(DMC):
        code=str(r.get("floss","")).strip()
        if not code or code in seen:
            continue
        try:
            rgb=(int(r["r"]),int(r["g"]),int(r["b"]))
        except Exception:
            continue
        rows.append({
            "dmc":code,
            "name":str(r.get("description") or f"DMC {code}"),
            "rgb":rgb,
            "hex":"#%02X%02X%02X"%rgb,
        })
        seen.add(code)
    if len(rows)<400:
        raise RuntimeError("DMC table incomplete")
    return rows

def nearest(rgb,rows):
    r,g,b=rgb
    return min(rows,key=lambda p:2*(r-p["rgb"][0])**2+4*(g-p["rgb"][1])**2+3*(b-p["rgb"][2])**2)

def build_pattern():
    src=Image.open(SRC).convert("RGBA")
    if src.size!=(SRC_W,SRC_H):
        raise RuntimeError(f"Expected 50x60 source, got {src.size}")
    palette=[tuple(x) for x in readj(PAL)["palette_rgb"]]
    if len(palette)!=20 or len(set(palette))!=20:
        raise RuntimeError("Christmas palette must be exactly 20 colours")
    symbol_for={c:SYMBOLS[i] for i,c in enumerate(palette)}
    dmc=dmc_table()

    matrix=[[None]*GRID_W for _ in range(GRID_H)]
    counts=Counter()
    used=[]
    seen=set()
    opaque=0
    for sy in range(SRC_H):
        for sx in range(SRC_W):
            r,g,b,a=src.getpixel((sx,sy))
            if a<128:
                continue
            c=(r,g,b)
            if c not in symbol_for:
                raise RuntimeError(f"Pixel {(sx,sy)} has colour outside shared palette: {c}")
            sym=symbol_for[c]
            matrix[OFF_Y+sy][OFF_X+sx]=sym
            counts[sym]+=1
            opaque+=1
            if c not in seen:
                seen.add(c); used.append(c)

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
            # IMPORTANT: renderer colour is the exact approved source RGB.
            # DMC is metadata/mapping; no second recolouring is applied.
            "color":"#%02X%02X%02X"%c,
            "source_rgb":list(c),
            "source_hex":"#%02X%02X%02X"%c,
            "stitches":counts[sym],
        })

    # Hard pixel-to-matrix verification.
    for y in range(GRID_H):
        for x in range(GRID_W):
            inside=OFF_X<=x<OFF_X+SRC_W and OFF_Y<=y<OFF_Y+SRC_H
            if not inside:
                if matrix[y][x] is not None:
                    raise RuntimeError(f"Nonblank matrix outside motif at {(x,y)}")
                continue
            r,g,b,a=src.getpixel((x-OFF_X,y-OFF_Y))
            expected=None if a<128 else symbol_for[(r,g,b)]
            if matrix[y][x]!=expected:
                raise RuntimeError(f"Pixel/matrix mismatch at {(x,y)}")

    pattern={
        "code":CODE,
        "base_design_id":"N0001",
        "technique_code":"CS",
        "collection":"christmas",
        "status":"ready",
        "algorithm":"pixel-exact-alpha-1px-1stitch-aida-relief-v4",
        "source_asset":"source-images/collections/christmas/products/N0001-christmas-tree.png",
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
    writej(PAT,pattern)

    product=readj(PROD) if PROD.is_file() else {}
    product.update({
        "code":CODE,
        "base_design_id":"N0001",
        "technique_code":"CS",
        "collection":"christmas",
        "title":"Christmas Tree Mini Cross Stitch Pattern PDF",
        "title_en":"Christmas Tree Mini Cross Stitch Pattern PDF",
        "title_es":"Patrón Mini de Árbol de Navidad en Punto de Cruz PDF",
        "technique":"cross-stitch",
        "pattern_file":"patterns/N0001-CS/pattern.json",
        "template":"cross-stitch.html",
        "website":"www.drielo.com",
        "status":"active",
        "render_ready":True,
        "renderer":"multitech-aida-relief-v4",
        "source_artwork":"source-images/collections/christmas/products/N0001-christmas-tree.png",
        "palette_mode":"shared-exact-20-rgb",
    })
    writej(PROD,product)
    return src,pattern

def render(pattern):
    if not BG.is_file():
        raise RuntimeError(f"Missing Christmas background: {BG}")
    if Image.open(BG).size!=(1536,1536):
        raise RuntimeError("Christmas background must remain 1536x1536")

    # Use the SAME production stitch renderer as the established pixel-by-pixel
    # collections. It paints organic full-cross X stitches and renders blank
    # matrix cells as the Aida-relief fabric.
    data=bg.pattern_data(CODE,"Christmas Tree","CS",pattern["matrix"],pattern["threads"])
    data.update({
        "collection":"Christmas",
        "collection_id":"christmas",
        "title":"Christmas Tree",
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
    result=bg.render_one((CODE,"CS",data))

    STORE_ASSETS.mkdir(parents=True,exist_ok=True)
    STORE_FILES.mkdir(parents=True,exist_ok=True)

    # PDF is now generated by the same aida-relief-v4 renderer, not the old
    # coloured-square one-page approximation.
    pdf=STORE_FILES/f"Drielo_{CODE}.pdf"
    shutil.copy2(result["pdf"],pdf)

    # WooCommerce hero: exact 1536x1536 lifestyle background with the renderer's
    # finished Aida/X preview pasted only inside the measured frame opening.
    x,y,w,h=FRAME
    background=Image.open(BG).convert("RGB")
    preview=Image.open(result["design_preview"]).convert("RGB")
    rendered=preview.resize((w,h),Image.Resampling.LANCZOS)
    background.paste(rendered,(x,y))
    hero=STORE_ASSETS/f"{CODE}-product.webp"
    background.save(hero,"WEBP",quality=94,method=6)

    galleries=[]
    for n,src in enumerate(result.get("gallery",[]),start=2):
        dst=STORE_ASSETS/f"{CODE}-gallery-{n}.webp"
        shutil.copy2(src,dst)
        galleries.append(dst)
    if len(galleries)!=3:
        raise RuntimeError(f"Expected 3 gallery images, got {len(galleries)}")

    design_dst=STORE_ASSETS/f"{CODE}-design.webp"
    shutil.copy2(result["design_preview"],design_dst)

    if not pdf.is_file() or pdf.read_bytes()[:4]!=b"%PDF" or pdf.stat().st_size<100000:
        raise RuntimeError("Invalid renderer PDF")
    with Image.open(hero) as im:
        if im.size!=(1536,1536):
            raise RuntimeError(f"Hero wrong size: {im.size}")
    return pdf,hero,galleries,design_dst

def update_catalog(pattern):
    cat=readj(CAT)
    products=cat.setdefault("products",[])
    row=next((p for p in products if p.get("sku")=="DRIELO-N0001-CS" or p.get("code")==CODE),None)
    if row is None:
        row={"code":CODE,"sku":"DRIELO-N0001-CS","price":2.99}
        products.append(row)
    colours=len(pattern["threads"])
    total=pattern["total_stitches"]
    short_en=(f"Mini Christmas tree cross-stitch PDF rendered with the same pixel-by-pixel Aida/X algorithm used by Drielo's established patterns. "
              f"Transparent cells remain blank Aida; {total:,} full cross stitches and {colours} colours.")
    short_es=(f"Mini patrón PDF de árbol de Navidad renderizado con el mismo algoritmo píxel a píxel de Aida y cruces usado en los patrones de Drielo. "
              f"Las celdas transparentes quedan como Aida en blanco; {total:,} puntadas completas y {colours} colores.")
    row.update({
        "code":CODE,
        "sku":"DRIELO-N0001-CS",
        "price":row.get("price",2.99),
        "categories":["cross-stitch-patterns","cross-stitch-christmas"],
        "title":"Christmas Tree Mini Cross Stitch Pattern PDF",
        "title_en":"Christmas Tree Mini Cross Stitch Pattern PDF",
        "title_es":"Patrón Mini de Árbol de Navidad en Punto de Cruz PDF",
        "slug":"christmas-tree-mini-cross-stitch-pattern",
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
            f"<p><strong>Christmas Tree Mini Cross Stitch Pattern PDF</strong></p>"
            f"<p>The transparent 50 × 60 source is read pixel by pixel and centered inside a 100 × 120 matrix. "
            f"Every opaque pixel becomes one full X stitch and every transparent pixel remains blank Aida. "
            f"The PDF, finished preview and WooCommerce hero are rendered with the same Aida-relief-v4 stitch engine.</p>"
            f"<p>{total:,} stitches · {colours} colours.</p>"
        ),
        "description_en":(
            f"<p><strong>Christmas Tree Mini Cross Stitch Pattern PDF</strong></p>"
            f"<p>The transparent 50 × 60 source is read pixel by pixel and centered inside a 100 × 120 matrix. "
            f"Every opaque pixel becomes one full X stitch and every transparent pixel remains blank Aida. "
            f"The PDF, finished preview and WooCommerce hero are rendered with the same Aida-relief-v4 stitch engine.</p>"
            f"<p>{total:,} stitches · {colours} colours.</p>"
        ),
        "description_es":(
            f"<p><strong>Patrón Mini de Árbol de Navidad en Punto de Cruz PDF</strong></p>"
            f"<p>La fuente transparente de 50 × 60 se lee píxel a píxel y se centra dentro de una matriz de 100 × 120. "
            f"Cada píxel opaco se convierte en una cruz completa y cada píxel transparente queda como Aida en blanco. "
            f"El PDF, la vista terminada y la imagen de WooCommerce se renderizan con el mismo motor Aida-relief-v4.</p>"
            f"<p>{total:,} puntadas · {colours} colores.</p>"
        ),
        "gallery":[f"assets/{CODE}-gallery-{i}.webp" for i in (2,3,4)],
        "gallery_preview_pages":{"facts":3,"colour_a1":8,"symbol_a1":12},
        "download":f"files/Drielo_{CODE}.pdf",
        "featured_image":f"assets/{CODE}-product.webp",
        "seo_title":"Christmas Tree Mini Cross Stitch Pattern PDF | Drielo",
        "seo_title_en":"Christmas Tree Mini Cross Stitch Pattern PDF | Drielo",
        "seo_title_es":"Patrón Mini de Árbol de Navidad en Punto de Cruz PDF | Drielo",
        "meta_description":short_en[:155],
        "meta_description_en":short_en[:155],
        "meta_description_es":short_es[:155],
        "tags":["christmas tree","christmas cross stitch","mini cross stitch","cross stitch pdf","counted cross stitch","digital pattern"],
        "design_id":CODE,
        "base_design_id":"N0001",
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
    cat["retired_products"]=[x for x in cat.get("retired_products",[]) if x!="DRIELO-N0001-CS"]
    writej(CAT,cat)

def main():
    _,pattern=build_pattern()
    pdf,hero,galleries,design=render(pattern)
    update_catalog(pattern)
    print(json.dumps({
        "code":CODE,
        "renderer":"aida-relief-v4",
        "source":"50x60 transparent",
        "grid":"100x120",
        "offset":[25,30],
        "stitches":pattern["total_stitches"],
        "colours":len(pattern["threads"]),
        "pdf":str(pdf),
        "hero":str(hero),
        "gallery":[str(x) for x in galleries],
        "design_preview":str(design),
    },ensure_ascii=False))

if __name__=="__main__":
    main()
