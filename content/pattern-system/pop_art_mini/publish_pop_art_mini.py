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
COL_SRC=ROOT/"content"/"source-images"/"collections"/"pop-art-mini"
PRODUCTS_SRC=COL_SRC/"products"
MANIFEST=COL_SRC/"manifest.json"
PALETTE_FILE=COL_SRC/"palette30_rgb.json"
DMC=SYSTEM/"data"/"dmc-colors.json"
PATTERN_ROOT=SYSTEM/"patterns"
PRODUCT_ROOT=SYSTEM/"products"
CAT=ROOT/"content"/"products"/"catalog.json"
STORE_ASSETS=ROOT/"content"/"products"/"assets"
STORE_FILES=ROOT/"content"/"products"/"files"
POP_ART_BG=ROOT/"content"/"products"/"assets"/"pop-art-25-collection-cover.webp"
COLLECTION_COVER=STORE_ASSETS/"pop-art-mini-collection-cover.webp"

sys.path.insert(0,str((SYSTEM/"multitech").resolve()))
import bulk_generate as bg

GRID_W,GRID_H=100,120
SRC_W,SRC_H=50,60
OFF_X,OFF_Y=25,30
SYMBOLS=list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")

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

def nearest_unique_dmc(colors):
    rows=dmc_table(); used=set(); out={}
    for c in colors:
        def score(row):
            r,g,b=c; dr,dg,db=row["rgb"]
            return 2*(r-dr)**2+4*(g-dg)**2+3*(b-db)**2
        choice=next(row for row in sorted(rows,key=score) if row["dmc"] not in used)
        used.add(choice["dmc"])
        out[c]=choice
    return out

def manifest_by_code():
    m=readj(MANIFEST)
    return {d["code"]:d for d in m["designs"]}

def build_pattern(code:str,palette,dmc_map,meta):
    src=Image.open(PRODUCTS_SRC/meta["file"]).convert("RGBA")
    if src.size!=(SRC_W,SRC_H):
        raise RuntimeError(f"{code}: expected 50x60, got {src.size}")
    symbols={c:SYMBOLS[i] for i,c in enumerate(palette)}
    matrix=[[None]*GRID_W for _ in range(GRID_H)]
    counts=Counter()
    for sy in range(SRC_H):
        for sx in range(SRC_W):
            r,g,b,a=src.getpixel((sx,sy))
            if a<128:
                continue
            c=(r,g,b)
            if c not in symbols:
                raise RuntimeError(f"{code}: pixel {(sx,sy)} {c} outside shared palette")
            sym=symbols[c]
            matrix[OFF_Y+sy][OFF_X+sx]=sym
            counts[sym]+=1

    threads=[]
    for c in palette:
        sym=symbols[c]
        if counts[sym] <= 0:
            continue
        dm=dmc_map[c]
        threads.append({
            "symbol":sym,
            "dmc":dm["dmc"],
            "name":dm["name"],
            "color":"#%02X%02X%02X"%c,
            "source_rgb":list(c),
            "stitches":counts[sym],
        })
    total=sum(counts.values())
    if total<=0 or total>=3000:
        raise RuntimeError(f"{code}: invalid motif stitch count {total}")

    pattern={
        "code":f"{code}-CS",
        "base_design_id":code,
        "technique_code":"CS",
        "collection":"pop-art-mini",
        "status":"ready",
        "algorithm":"pixel-exact-alpha-1px-1stitch-aida-relief-v4",
        "source_asset":f"source-images/collections/pop-art-mini/products/{meta['file']}",
        "palette_mode":"shared-exact-30-rgb",
        "shared_palette_rgb":[list(c) for c in palette],
        "source_width":50,"source_height":60,
        "stitch_width":100,"stitch_height":120,
        "source_offset":{"x":25,"y":30},
        "total_stitches":total,
        "threads":threads,
        "matrix":matrix,
    }
    writej(PATTERN_ROOT/f"{code}-CS"/"pattern.json",pattern)
    writej(PRODUCT_ROOT/f"{code}-CS"/"product.json",{
        "code":f"{code}-CS",
        "base_design_id":code,
        "technique_code":"CS",
        "collection":"pop-art-mini",
        "title":f"{meta['title_en']} Mini Cross Stitch Pattern PDF",
        "title_en":f"{meta['title_en']} Mini Cross Stitch Pattern PDF",
        "title_es":f"{meta['title_es']} - patrón mini de punto de cruz PDF",
        "technique":"cross-stitch",
        "pattern_file":f"patterns/{code}-CS/pattern.json",
        "template":"cross-stitch.html",
        "website":"www.drielo.com",
        "status":"active",
        "render_ready":True,
        "renderer":"multitech-aida-relief-v4",
        "source_artwork":f"source-images/collections/pop-art-mini/products/{meta['file']}",
        "palette_mode":"shared-exact-30-rgb",
    })
    return pattern

def render(code,pattern,meta):
    data=bg.pattern_data(f"{code}-CS",meta["title_en"],"CS",pattern["matrix"],pattern["threads"])
    data.update({
        "collection":"Pop Art Mini",
        "collection_id":"pop-art-mini",
        "title":meta["title_en"],
        "subtitle":"Mini pixel-exact Pop Art cross-stitch pattern",
        "stitch_width":100,
        "stitch_height":120,
        "total_stitches":pattern["total_stitches"],
        "threads":pattern["threads"],
        "matrix":pattern["matrix"],
        "finished_subtitle":"Exact 100 × 120 Aida preview",
        "finished_caption":"Each opaque 50 × 60 source pixel becomes one full cross stitch; transparent pixels remain blank Aida.",
        "preview_label":"Finished cross-stitch preview",
        "cover_image_path":str(POP_ART_BG.resolve()),
        "cover_overlay":bg.TECHS["CS"]["cover_overlay"],
        "cover_stage_scale":bg.TECHS["CS"]["cover_stage_scale"],
    })
    result=bg.render_one((f"{code}-CS","CS",data))
    STORE_ASSETS.mkdir(parents=True,exist_ok=True)
    STORE_FILES.mkdir(parents=True,exist_ok=True)
    shutil.copy2(result["pdf"],STORE_FILES/Path(result["pdf"]).name)
    shutil.copy2(result["image"],STORE_ASSETS/Path(result["image"]).name)
    shutil.copy2(result["design_preview"],STORE_ASSETS/Path(result["design_preview"]).name)
    galleries=[]
    for item in result["gallery"]:
        src=Path(item)
        shutil.copy2(src,STORE_ASSETS/src.name)
        galleries.append(f"assets/{src.name}")
    return galleries

def update_catalog(code,pattern,meta,galleries,palette,dmc_map):
    cat=readj(CAT)
    # collection cover is a separate copy of the approved Pop Art background
    STORE_ASSETS.mkdir(parents=True,exist_ok=True)
    if not POP_ART_BG.is_file():
        raise RuntimeError(f"Missing Pop Art background {POP_ART_BG}")
    shutil.copy2(POP_ART_BG,COLLECTION_COVER)

    collections=cat.setdefault("collections",[])
    collection=next((c for c in collections if c.get("slug")=="pop-art-mini"),None)
    if collection is None:
        collection={"id":"pop-art-mini","slug":"pop-art-mini"}
        collections.append(collection)
    collection.update({
        "id":"pop-art-mini",
        "slug":"pop-art-mini",
        "name":"Pop Art Mini",
        "name_en":"Pop Art Mini",
        "name_es":"Pop Art Mini",
        "description":"Mini Pop Art portrait cross-stitch patterns built from transparent 50 × 60 pixel sources and one strict shared 30-colour palette.",
        "description_en":"Mini Pop Art portrait cross-stitch patterns built from transparent 50 × 60 pixel sources and one strict shared 30-colour palette.",
        "description_es":"Mini retratos Pop Art para punto de cruz creados desde fuentes transparentes de 50 × 60 píxeles y una paleta estricta compartida de 30 colores.",
        "palette_mode":"shared",
        "show_collection_palette":True,
        "palette_hex":["#%02X%02X%02X"%c for c in palette],
        "thread_codes":[str(dmc_map[c]["dmc"]) for c in palette],
        "cover_asset":"assets/pop-art-mini-collection-cover.webp",
        "techniques":["cross-stitch"],
        "visible":True,
        "force_visibility_sync":True,
    })

    products=cat.setdefault("products",[])
    sku=f"DRIELO-{code}-CS"
    row=next((p for p in products if p.get("sku")==sku or p.get("code")==f"{code}-CS"),None)
    if row is None:
        row={"code":f"{code}-CS","sku":sku,"price":2.99}
        products.append(row)
    total=pattern["total_stitches"]; colours=len(pattern["threads"])
    short_en=(f"{meta['title_en']} mini cross-stitch PDF from a transparent 50 × 60 pixel source, centered on a 100 × 120 chart. "
              f"{total:,} full cross stitches and {colours} colours from the shared 30-colour Pop Art Mini palette.")
    short_es=(f"{meta['title_es']}: patrón mini PDF creado desde una fuente transparente de 50 × 60 y centrado en una cuadrícula de 100 × 120. "
              f"{total:,} puntadas completas y {colours} colores de la paleta compartida de 30 colores Pop Art Mini.")
    row.update({
        "code":f"{code}-CS",
        "sku":sku,
        "price":row.get("price",2.99),
        "categories":["cross-stitch-patterns","portraits","pop-art"],
        "title":f"{meta['title_en']} Mini Cross Stitch Pattern PDF",
        "title_en":f"{meta['title_en']} Mini Cross Stitch Pattern PDF",
        "title_es":f"{meta['title_es']} - patrón mini de punto de cruz PDF",
        "slug":f"{meta['slug']}-mini-cross-stitch-pattern",
        "collection":"pop-art-mini",
        "stitches":total,
        "grid":"100 × 120 stitches",
        "colours":colours,
        "color_count":colours,
        "grid_width":100,"grid_height":120,
        "motif_width":50,"motif_height":60,
        "skill":"Beginner friendly",
        "skill_en":"Beginner friendly",
        "skill_es":"Apto para principiantes",
        "stitch_type":"Full cross stitch",
        "stitch_type_en":"Full cross stitch",
        "stitch_type_es":"Punto de cruz completo",
        "short_description":short_en,
        "short_description_en":short_en,
        "short_description_es":short_es,
        "description":f"<p><strong>{meta['title_en']} Mini Cross Stitch Pattern PDF</strong></p><p>Pixel-exact mini pattern: every opaque pixel from the transparent 50 × 60 source becomes one full cross stitch. Transparent pixels remain blank Aida. The motif is centered inside a 100 × 120 chart.</p><p>{total:,} stitches · {colours} colours · shared 30-colour Pop Art Mini palette.</p>",
        "description_en":f"<p><strong>{meta['title_en']} Mini Cross Stitch Pattern PDF</strong></p><p>Pixel-exact mini pattern: every opaque pixel from the transparent 50 × 60 source becomes one full cross stitch. Transparent pixels remain blank Aida. The motif is centered inside a 100 × 120 chart.</p><p>{total:,} stitches · {colours} colours · shared 30-colour Pop Art Mini palette.</p>",
        "description_es":f"<p><strong>{meta['title_es']} - patrón mini de punto de cruz PDF</strong></p><p>Patrón mini exacto píxel a píxel: cada píxel opaco de la fuente transparente 50 × 60 se convierte en una cruz completa. Los píxeles transparentes quedan como Aida en blanco. El motivo se centra dentro de una cuadrícula de 100 × 120.</p><p>{total:,} puntadas · {colours} colores · paleta compartida Pop Art Mini de 30 colores.</p>",
        "gallery":galleries,
        "gallery_preview_pages":{"facts":3,"colour_a1":8,"symbol_a1":12},
        "download":f"files/Drielo_{code}-CS.pdf",
        "featured_image":f"assets/{code}-CS-product.webp",
        "seo_title":f"{meta['title_en']} Mini Cross Stitch Pattern PDF | Drielo",
        "seo_title_en":f"{meta['title_en']} Mini Cross Stitch Pattern PDF | Drielo",
        "seo_title_es":f"{meta['title_es']} - patrón mini de punto de cruz PDF | Drielo",
        "meta_description":short_en[:155],
        "meta_description_en":short_en[:155],
        "meta_description_es":short_es[:155],
        "tags":["pop art","portrait cross stitch","mini cross stitch","cross stitch pdf","counted cross stitch","digital pattern"],
        "design_id":f"{code}-CS",
        "base_design_id":code,
        "technique_code":"CS",
        "technique":"cross-stitch",
        "filters":{
            "technique":["cross-stitch"],
            "theme":["people-portraits"],
            "style":["pop-art"],
            "project":["wall-art"],
            "orientation":["portrait"],
            "difficulty":["beginner"],
            "color-family":["multicolor"],
            "season":[],
        },
    })
    cat["retired_products"]=[x for x in cat.get("retired_products",[]) if x!=sku]
    writej(CAT,cat)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("codes",nargs="+")
    args=ap.parse_args()
    metas=manifest_by_code()
    palette=[tuple(x) for x in readj(PALETTE_FILE)["palette_rgb"]]
    if len(palette)!=30 or len(set(palette))!=30:
        raise RuntimeError("Pop Art Mini palette must be exactly 30 colours")
    dmc_map=nearest_unique_dmc(palette)
    for code in args.codes:
        if code not in metas:
            raise RuntimeError(f"Unknown Pop Art Mini code {code}")
        pattern=build_pattern(code,palette,dmc_map,metas[code])
        galleries=render(code,pattern,metas[code])
        update_catalog(code,pattern,metas[code],galleries,palette,dmc_map)
        print(json.dumps({
            "code":f"{code}-CS",
            "source":"50x60 transparent",
            "grid":"100x120",
            "offset":[25,30],
            "stitches":pattern["total_stitches"],
            "blank_cells":12000-pattern["total_stitches"],
            "colours":len(pattern["threads"]),
            "renderer":"aida-relief-v4",
        },ensure_ascii=False))

if __name__=="__main__":
    main()
