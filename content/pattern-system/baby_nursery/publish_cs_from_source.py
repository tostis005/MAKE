#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "baby-nursery"
COL_DIR = SYSTEM / "collections" / COLLECTION_ID
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
PALETTE_PATH = COL_DIR / "palette30.json"
DMC_PATH = SYSTEM / "data" / "dmc-colors.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
MAPPED_DIR = COL_DIR / "mapped-designs"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

WIDTH = 100
HEIGHT = 120
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") + list("!@#$%&*+=?^~:;/\\")
ALPHA_THRESHOLD = 128

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def nearest(colour, rows, key):
    r,g,b = colour
    return min(rows, key=lambda p: (
        2*(r-p[key][0])**2 + 4*(g-p[key][1])**2 + 3*(b-p[key][2])**2
    ))

def dmc_table():
    out=[]
    seen=set()
    for row in read_json(DMC_PATH):
        code=str(row.get("floss","")).strip()
        if not code or code in seen:
            continue
        try:
            rgb=(int(row["r"]),int(row["g"]),int(row["b"]))
        except Exception:
            continue
        out.append({
            "dmc":code,
            "name":str(row.get("description") or f"DMC {code}"),
            "rgb":rgb,
            "hex":"#%02X%02X%02X" % rgb,
        })
        seen.add(code)
    if len(out)<400:
        raise RuntimeError("DMC table incomplete")
    return out

def design_record(base_id: str):
    doc=read_json(DESIGNS_PATH)
    row=next((x for x in doc.get("designs",[]) if x.get("base_design_id")==base_id),None)
    if not row:
        raise RuntimeError(f"Unknown Baby Nursery design {base_id}")
    if row.get("variants") != [f"{base_id}-CS"]:
        raise RuntimeError(f"{base_id}: Baby Nursery must be cross-stitch only")
    return row

def build_pattern(base_id: str, design: dict):
    source_rel=design["source_asset"]
    source=(SYSTEM/source_rel).resolve()
    if not source.is_file():
        raise RuntimeError(f"Missing source {source}")

    with Image.open(source) as im:
        rgba=im.convert("RGBA")
        if rgba.size!=(WIDTH,HEIGHT):
            raise RuntimeError(f"{base_id}: source must be 100x120, got {rgba.size}")
        pixels=list(rgba.getdata())

    paldoc=read_json(PALETTE_PATH)
    source_palette=[tuple(map(int,c)) for c in paldoc["colors"]]
    if len(source_palette)!=30:
        raise RuntimeError(f"Expected 30 shared source colours, got {len(source_palette)}")
    palette_rows=[{"index":i,"rgb":c} for i,c in enumerate(source_palette)]

    dmc=dmc_table()
    mapped_palette=[]
    for i,c in enumerate(source_palette):
        match=nearest(c,dmc,"rgb")
        mapped_palette.append({
            "source_index":i,
            "source_rgb":c,
            "dmc":match["dmc"],
            "name":match["name"],
            "rgb":match["rgb"],
            "hex":match["hex"],
        })

    dmc_order=[]
    by_dmc={}
    for p in mapped_palette:
        if p["dmc"] not in by_dmc:
            by_dmc[p["dmc"]]=p
            dmc_order.append(p["dmc"])
    if len(dmc_order)>len(SYMBOLS):
        raise RuntimeError(f"{base_id}: too many DMC colours")
    symbol_for={code:SYMBOLS[i] for i,code in enumerate(dmc_order)}

    matrix=[]
    mapped_pixels=[]
    counts=Counter()
    visible=0
    for y in range(HEIGHT):
        row=[]
        for x in range(WIDTH):
            r,g,b,a=pixels[y*WIDTH+x]
            if a<ALPHA_THRESHOLD:
                row.append(None)
                mapped_pixels.append((0,0,0,0))
                continue
            src_match=nearest((r,g,b),palette_rows,"rgb")
            mp=mapped_palette[src_match["index"]]
            sym=symbol_for[mp["dmc"]]
            row.append(sym)
            counts[sym]+=1
            visible+=1
            mr,mg,mb=mp["rgb"]
            mapped_pixels.append((mr,mg,mb,255))
        matrix.append(row)

    if visible<=0:
        raise RuntimeError(f"{base_id}: source produced no stitches")

    threads=[]
    for code in dmc_order:
        sym=symbol_for[code]
        if counts[sym]<=0:
            continue
        p=by_dmc[code]
        threads.append({
            "symbol":sym,
            "dmc":code,
            "color":p["hex"],
            "name":p["name"],
            "stitches":counts[sym],
        })

    mapped_rel=f"collections/baby-nursery/mapped-designs/{base_id}-{design['slug']}-dmc.png"
    mapped_path=SYSTEM/mapped_rel
    mapped_path.parent.mkdir(parents=True,exist_ok=True)
    out=Image.new("RGBA",(WIDTH,HEIGHT))
    out.putdata(mapped_pixels)
    out.save(mapped_path,"PNG",optimize=True)

    code=f"{base_id}-CS"
    pattern_path=PATTERNS/code/"pattern.json"
    pattern=read_json(pattern_path) if pattern_path.is_file() else {}
    pattern.update({
        "code":code,
        "base_design_id":base_id,
        "technique_code":"CS",
        "collection":COLLECTION_ID,
        "palette_mode":"shared-30-source-colours-to-dmc",
        "status":"ready",
        "source_asset":source_rel,
        "mapped_asset":mapped_rel,
        "alpha_threshold":ALPHA_THRESHOLD,
        "stitch_width":WIDTH,
        "stitch_height":HEIGHT,
        "total_stitches":visible,
        "threads":threads,
        "matrix":matrix,
    })
    write_json(pattern_path,pattern)

    product_path=PRODUCTS/code/"product.json"
    product=read_json(product_path) if product_path.is_file() else {}
    product.update({
        "code":code,
        "base_design_id":base_id,
        "technique_code":"CS",
        "collection":COLLECTION_ID,
        "title":design["product_title_en"],
        "title_en":design["product_title_en"],
        "title_es":design["product_title_es"],
        "design_title_en":design["title_en"],
        "design_title_es":design["title_es"],
        "design_slug":design["slug"],
        "technique":"cross-stitch",
        "pattern_file":f"patterns/{code}/pattern.json",
        "template":"cross-stitch.html",
        "website":"www.drielo.com",
        "status":"active",
        "render_ready":True,
        "renderer":"multitech",
        "source_artwork":source_rel,
        "mapped_artwork":mapped_rel,
        "page_1_asset":"collections/baby-nursery/assets/cover-cross-stitch.jpg",
        "palette_mode":"shared-30-source-colours-to-dmc",
    })
    write_json(product_path,product)

    return {
        "matrix":matrix,
        "threads":threads,
        "total_stitches":visible,
        "mapped_rel":mapped_rel,
        "mapped_path":mapped_path,
        "source_rel":source_rel,
    }

def prepare_renderer_assets(collection: dict):
    temp=Path("/tmp/drielo-baby-cs-assets")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True,exist_ok=True)
    floral=bg.ENGINE_ASSETS/"floral.png"
    if floral.is_file():
        shutil.copy2(floral,temp/"floral.png")
    src_rel=collection["mockup_spec"]["technique_assets"]["CS"]
    src=SYSTEM/src_rel
    if not src.is_file():
        raise RuntimeError(f"Missing Baby Nursery cross-stitch cover: {src}")
    Image.open(src).convert("RGB").save(temp/"cover-cross-stitch.webp","WEBP",quality=94,method=6)
    bg.ENGINE_ASSETS=temp

def render(base_id: str, design: dict, built: dict):
    code=f"{base_id}-CS"
    collection=read_json(COLLECTION_PATH)
    prepare_renderer_assets(collection)
    cfg=bg.TECHS["CS"]
    data=bg.pattern_data(code,design["title_en"],"CS",built["matrix"],built["threads"])
    data["collection"]=collection.get("name_en","Baby & Nursery")
    data["collection_id"]=COLLECTION_ID
    layout=collection["mockup_spec"]["technique_layouts"]["CS"]
    data["cover_overlay"]=layout["cover_overlay"]
    data["cover_stage_scale"]=layout["cover_stage_scale"]
    result=bg.render_one((code,"CS",data))

    STORE_ASSETS.mkdir(parents=True,exist_ok=True)
    STORE_FILES.mkdir(parents=True,exist_ok=True)
    pdf=STORE_FILES/f"Drielo_{code}.pdf"
    image=STORE_ASSETS/f"{code}-product.webp"
    shutil.copy2(result["pdf"],pdf)
    shutil.copy2(result["image"],image)
    gallery=[]
    sources=result.get("gallery",[])
    if len(sources)!=3:
        raise RuntimeError(f"{code}: expected 3 gallery previews, got {len(sources)}")
    for n,src in enumerate(sources,start=2):
        dst=STORE_ASSETS/f"{code}-gallery-{n}.webp"
        shutil.copy2(src,dst)
        gallery.append(dst)
    if not pdf.is_file() or pdf.stat().st_size<100000 or pdf.read_bytes()[:4]!=b"%PDF":
        raise RuntimeError(f"{code}: invalid PDF")
    if not image.is_file() or image.stat().st_size<30000:
        raise RuntimeError(f"{code}: invalid product image")
    return {"pdf":pdf,"image":image,"gallery":gallery}

def update_catalog(base_id: str, design: dict, built: dict):
    code=f"{base_id}-CS"
    catalog=read_json(CATALOG_PATH)
    collection=read_json(COLLECTION_PATH)
    rows=catalog.setdefault("products",[])
    rows[:]=[p for p in rows if not (p.get("collection")==COLLECTION_ID and p.get("code")!=code)]

    colours=len(built["threads"])
    total=built["total_stitches"]
    title_en=design["product_title_en"]
    title_es=design["product_title_es"]
    short_en=f"Downloadable {design['title_en']} cross-stitch pattern PDF from the Baby & Nursery collection. Exact 100 × 120 grid with transparent canvas areas left unstitched; {total:,} full cross stitches and {colours} DMC colours. Code: {code}."
    short_es=f"Patrón PDF descargable de {design['title_es'].lower()} para punto de cruz. Cuadrícula exacta de 100 × 120 con las zonas transparentes sin bordar; {total:,} cruces completas y {colours} colores DMC. Código: {code}."
    desc_en=(
        f"<p><strong>{title_en}</strong> is a digital counted cross-stitch pattern from the Baby & Nursery collection.</p>"
        f"<p>The approved artwork uses a 100 × 120 source grid. Transparent pixels remain blank Aida canvas and visible pixels become full cross stitches.</p>"
        f"<h3>Pattern details</h3><ul><li>Code: {code}</li><li>Grid: 100 × 120 stitches</li>"
        f"<li>Full cross stitches: {total:,}</li><li>DMC colours: {colours}</li><li>Skill level: Beginner friendly</li></ul>"
        f"<p>Includes a printable PDF with colour key, charts and enlarged working sections. Digital product only.</p>"
    )
    desc_es=(
        f"<p><strong>{title_es}</strong> es un patrón digital de punto de cruz de la colección Bebé e Infantil.</p>"
        f"<p>El diseño aprobado utiliza una cuadrícula fuente de 100 × 120. Los píxeles transparentes quedan como lienzo Aida sin bordar y los píxeles visibles se convierten en cruces completas.</p>"
        f"<h3>Detalles</h3><ul><li>Código: {code}</li><li>Cuadrícula: 100 × 120</li>"
        f"<li>Puntadas: {total:,}</li><li>Colores DMC: {colours}</li><li>Nivel: apto para principiantes</li></ul>"
        f"<p>Incluye PDF imprimible con clave de colores, gráficos y secciones ampliadas. Producto digital.</p>"
    )
    row={
        "code":code,
        "sku":f"DRIELO-{code}",
        "price":2.99,
        "categories":["cross-stitch-patterns","cross-stitch-baby-nursery"],
        "purchase_note_en":"Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
        "purchase_note_es":"Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        "title":title_en,
        "title_en":title_en,
        "title_es":title_es,
        "slug":f"{design['slug']}-cross-stitch-pattern",
        "collection":COLLECTION_ID,
        "stitches":total,
        "grid":"100 × 120 stitches",
        "colours":colours,
        "color_count":colours,
        "grid_width":100,
        "grid_height":120,
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
        "gallery":[f"assets/{code}-gallery-{i}.webp" for i in (2,3,4)],
        "gallery_preview_pages":{"facts":3,"colour_a1":8,"symbol_a1":12},
        "download":f"files/Drielo_{code}.pdf",
        "featured_image":f"assets/{code}-product.webp",
        "seo_title":f"{title_en} | Drielo",
        "seo_title_en":f"{title_en} | Drielo",
        "seo_title_es":f"{title_es} | Drielo",
        "meta_description":short_en[:155],
        "meta_description_en":short_en[:155],
        "meta_description_es":short_es[:155],
        "tags":[design["title_en"].lower(),"baby nursery","cross stitch pdf","counted cross stitch","dmc pattern","digital pattern"],
        "etsy_tags_en":[design["title_en"].lower(),"baby nursery","cross stitch pdf","counted cross stitch","dmc pattern","digital pattern"],
        "etsy_tags_es":[design["title_es"].lower(),"bebé","infantil","punto de cruz","patrón digital","descarga pdf"],
        "design_id":code,
        "base_design_id":base_id,
        "technique_code":"CS",
        "technique":"cross-stitch",
        "size_attribute_label":"Pattern size",
        "colour_attribute_label":"DMC colours",
        "type_attribute_label":"Technique",
        "count_attribute_label":"Total stitches",
        "filters":{
            "technique":["cross-stitch"],
            "theme":["baby-nursery"],
            "style":["cute","soft","nursery"],
            "project":["wall-art"],
            "orientation":["portrait"],
            "difficulty":["beginner"],
            "color-family":["multicolor"],
            "season":[],
        },
    }
    idx=next((i for i,p in enumerate(rows) if p.get("code")==code),None)
    if idx is None:
        rows.append(row)
    else:
        rows[idx]=row
    catalog["retired_products"]=[x for x in catalog.get("retired_products",[]) if x!=row["sku"]]

    coll=next((c for c in catalog.get("collections",[]) if c.get("slug")==COLLECTION_ID),None)
    if coll is None:
        coll={"id":COLLECTION_ID,"slug":COLLECTION_ID}
        catalog.setdefault("collections",[]).append(coll)
    coll.update({
        "id":COLLECTION_ID,
        "slug":COLLECTION_ID,
        "name":"Baby & Nursery",
        "name_en":"Baby & Nursery",
        "name_es":"Bebé e Infantil",
        "description":collection["description"],
        "description_en":collection["description"],
        "description_es":collection["description_es"],
        "techniques":["cross-stitch"],
        "cover_asset":f"assets/{code}-product.webp",
        "visible":bool(collection.get("visible",False)),
        "palette_mode":"shared-30-source-colours-to-dmc",
    })
    write_json(CATALOG_PATH,catalog)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("design_id")
    args=ap.parse_args()
    base_id=args.design_id.strip().upper()
    if not base_id.startswith("I") or len(base_id)!=5:
        raise SystemExit("Expected I#### design id")
    design=design_record(base_id)
    built=build_pattern(base_id,design)
    rendered=render(base_id,design,built)
    update_catalog(base_id,design,built)
    print(json.dumps({
        "design_id":base_id,
        "code":f"{base_id}-CS",
        "title":design["title_en"],
        "stitches":built["total_stitches"],
        "dmc_colours":len(built["threads"]),
        "pdf_bytes":rendered["pdf"].stat().st_size,
        "image_bytes":rendered["image"].stat().st_size,
    },ensure_ascii=False))
    print(f"BABY_CS_READY={base_id}")

if __name__=="__main__":
    main()
