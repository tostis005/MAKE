#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import zlib
import shutil
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
SYSTEM=ROOT/"content"/"pattern-system"
COL_DIR=SYSTEM/"collections"/"pop-art-25"
DESIGNS_PATH=COL_DIR/"designs.json"
COLLECTION_PATH=COL_DIR/"collection.json"
SOURCE_DIR=COL_DIR/"sources"
REFERENCE_DIR=COL_DIR/"reference-masters"
PATTERNS=SYSTEM/"patterns"
PRODUCTS=SYSTEM/"products"
CATALOG_PATH=ROOT/"content"/"products"/"catalog.json"
STORE_ASSETS=ROOT/"content"/"products"/"assets"
STORE_FILES=ROOT/"content"/"products"/"files"

sys.path.insert(0,str((SYSTEM/"multitech").resolve()))
import bulk_generate as bg  # noqa: E402

SUFFIXES=("CS","C2C","TC","LH")
SYMBOLS=list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
TECH_META={
 "CS":{"display_en":"Cross Stitch","display_es":"Punto de cruz","stitch_es":"Punto de cruz completo"},
 "C2C":{"display_en":"C2C Crochet","display_es":"Crochet C2C","stitch_es":"Bloques de crochet C2C"},
 "TC":{"display_en":"Tapestry Crochet","display_es":"Crochet tapestry","stitch_es":"Crochet tapestry en color"},
 "LH":{"display_en":"Latch Hook Rug","display_es":"Alfombra latch hook","stitch_es":"Nudos latch hook / alfombra"},
}

def read_json(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path:Path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def rgb(hexv:str):
    h=hexv.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def nearest_palette_index(col,palette_rgb):
    r,g,b=col
    return min(range(len(palette_rgb)),key=lambda i:
        2*(r-palette_rgb[i][0])**2+4*(g-palette_rgb[i][1])**2+3*(b-palette_rgb[i][2])**2)

def design_record(base_id:str):
    for item in read_json(DESIGNS_PATH)["designs"]:
        if item["code"]==base_id:
            return item
    raise RuntimeError(f"Unknown Pop Art design: {base_id}")

def validate_master(base_id:str,image:Image.Image):
    if image.size!=(800,960):
        raise RuntimeError(f"{base_id}: source master must be 800x960, got {image.size}")
    alpha=image.getchannel("A")
    amin,amax=alpha.getextrema()
    bbox=alpha.getbbox()
    if amin!=0 or amax==0 or not bbox:
        raise RuntimeError(f"{base_id}: source master must have a real transparent background")
    x0,y0,x1,y1=bbox
    margins={"left":x0,"top":y0,"right":800-x1,"bottom":960-y1}
    if min(margins.values())<24:
        raise RuntimeError(f"{base_id}: artwork too close to canvas edge: bbox={bbox} margins={margins}")
    return bbox,margins

def _load_encoded_matrix(base_id:str):
    override_path=SYSTEM/"pop_art_25"/"source_overrides.json"
    if override_path.is_file():
        override=read_json(override_path).get(base_id)
        if override:
            if isinstance(override,dict) and override.get("zlib_b64"):
                raw=zlib.decompress(base64.b64decode(override["zlib_b64"])).decode("utf-8")
                rows=raw.splitlines()
            else:
                rows=list(override)
            if len(rows)!=120 or any(len(row)!=100 for row in rows):
                raise RuntimeError(f"{base_id}: malformed source override in {override_path}")
            print(f"SOURCE_OVERRIDE {base_id} {override_path}")
            return rows

    for path in sorted((SYSTEM/"pop_art_25").glob("source_matrices_*.json")):
        doc=read_json(path)
        encoded=doc.get(base_id)
        if not encoded:
            continue
        raw=zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
        rows=raw.splitlines()
        if len(rows)!=120 or any(len(row)!=100 for row in rows):
            raise RuntimeError(f"{base_id}: malformed encoded source matrix in {path}")
        return rows
    raise RuntimeError(f"{base_id}: no encoded source matrix found")


def _rows_from_existing_source(base_id:str,collection:dict):
    src=SOURCE_DIR/f"{base_id}.png"
    if not src.is_file():
        raise RuntimeError(f"{base_id}: encoded source is invalid and fallback PNG is missing")
    im=Image.open(src).convert("RGBA")
    im=_fit_transparent_master(im,32) if im.size!=(800,960) else im
    palette=collection["palette"]
    palette_rgb=[rgb(p["hex"]) for p in palette]
    exact={col:i for i,col in enumerate(palette_rgb)}
    px=im.load()
    rows=[]
    for gy in range(120):
        chars=[]
        for gx in range(100):
            samples=[]
            for yy in range(gy*8,gy*8+8):
                for xx in range(gx*8,gx*8+8):
                    r,g,b,a=px[xx,yy]
                    if a>=128:
                        samples.append((r,g,b))
            if len(samples)<8:
                chars.append(".")
                continue
            col=Counter(samples).most_common(1)[0][0]
            i=exact.get(col)
            if i is None:
                i=nearest_palette_index(col,palette_rgb)
            chars.append(SYMBOLS[i])
        rows.append("".join(chars))
    if not any(ch!="." for row in rows for ch in row):
        raise RuntimeError(f"{base_id}: fallback PNG produced an empty matrix")
    print(f"SOURCE_FALLBACK_PNG {base_id} {src}")
    return rows


def _clean_exterior_white_noise(rows:list[str],collection:dict):
    """Remove only small exterior white/near-white artifacts.

    Large white areas (shirts, hair, etc.) and white details enclosed by or
    strongly attached to coloured stitches are preserved. The canvas itself is
    already white, so detached/weakly-attached white pixels around the portrait
    should remain transparent.
    """
    grid=[list(r) for r in rows]
    h=len(grid); w=len(grid[0]) if h else 0
    white=set()
    for i,p in enumerate(collection["palette"]):
        if str(p.get("dmc","")).upper() in {"B5200","3865"}:
            white.add(SYMBOLS[i])
    if not white:
        return rows,0

    seen=[[False]*w for _ in range(h)]
    removed=0
    dirs=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    for sy in range(h):
        for sx in range(w):
            if seen[sy][sx] or grid[sy][sx] not in white:
                continue
            stack=[(sy,sx)]
            seen[sy][sx]=True
            comp=[]
            boundary=set()
            enclosed=0
            while stack:
                y,x=stack.pop()
                comp.append((y,x))
                for dy,dx in dirs:
                    ny,nx=y+dy,x+dx
                    if 0<=ny<h and 0<=nx<w:
                        v=grid[ny][nx]
                        if v in white and not seen[ny][nx]:
                            seen[ny][nx]=True
                            stack.append((ny,nx))
                        elif v!="." and v not in white:
                            boundary.add((ny,nx))

                # Intentional white details inside the subject tend to be
                # enclosed by coloured stitches on at least one axis.
                left=any(grid[y][xx]!="." and grid[y][xx] not in white for xx in range(max(0,x-4),x))
                right=any(grid[y][xx]!="." and grid[y][xx] not in white for xx in range(x+1,min(w,x+5)))
                up=any(grid[yy][x]!="." and grid[yy][x] not in white for yy in range(max(0,y-4),y))
                down=any(grid[yy][x]!="." and grid[yy][x] not in white for yy in range(y+1,min(h,y+5)))
                if (left and right) or (up and down):
                    enclosed+=1

            n=len(comp)
            # Preserve substantial white regions and well-integrated details.
            keep = n>=20 or len(boundary)>=2 or enclosed>=max(1,n//3)
            if not keep:
                for y,x in comp:
                    grid[y][x]="."
                removed+=n

    return ["".join(r) for r in grid],removed


def _fit_transparent_master(image:Image.Image,min_margin:int=32):
    image=image.convert("RGBA")
    bbox=image.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("empty transparent source")
    crop=image.crop(bbox)
    max_w=800-2*min_margin
    max_h=960-2*min_margin
    scale=min(max_w/crop.width,max_h/crop.height,1.0 if image.size==(800,960) else 99.0)
    new_w=max(1,int(round(crop.width*scale)))
    new_h=max(1,int(round(crop.height*scale)))
    resized=crop.resize((new_w,new_h),Image.Resampling.NEAREST)
    canvas=Image.new("RGBA",(800,960),(0,0,0,0))
    x=(800-new_w)//2
    y=(960-new_h)//2
    canvas.alpha_composite(resized,(x,y))
    return canvas

def ensure_source_png(base_id:str,collection:dict):
    if base_id in {"P0001","P0012"}:
        if os.environ.get("DRIELO_ALLOW_PROTECTED")!="1":
            raise RuntimeError(f"{base_id}: protected approved design requires an explicit protected rebuild")
        src=SOURCE_DIR/f"{base_id}.png"
        if not src.is_file():
            raise RuntimeError(f"{base_id}: approved protected source PNG is missing")
        approved=Image.open(src).convert("RGBA")
        if approved.size != (800,960):
            if approved.width*6 != approved.height*5:
                raise RuntimeError(f"{base_id}: protected source has unexpected aspect ratio {approved.size}")
            approved=approved.resize((800,960),Image.Resampling.NEAREST)
            print(f"PROTECTED_SOURCE_NORMALIZED {base_id} -> {approved.size}")
        # Preserve the approved artwork itself, but fit it into the same safe
        # transparent margins used by the current collection workflow.
        approved=_fit_transparent_master(approved,32)
        approved.save(src,"PNG",optimize=True)
        bbox,margins=validate_master(base_id,approved)
        print(f"PROTECTED_SOURCE_REUSED {base_id} {src} bbox={bbox} margins={margins}")
        return src

    # Always rebuild branch-generated sources from the canonical matrix/override.
    # Explicit per-design overrides are authoritative and must fail closed:
    # a malformed override must never silently reuse an older PNG.
    override_path=SYSTEM/"pop_art_25"/"source_overrides.json"
    explicit_override=False
    if override_path.is_file():
        explicit_override=bool(read_json(override_path).get(base_id))

    if explicit_override:
        rows=_load_encoded_matrix(base_id)
        print(f"SOURCE_OVERRIDE_REQUIRED {base_id}")
    else:
        try:
            rows=_load_encoded_matrix(base_id)
        except Exception as exc:
            print(f"SOURCE_MATRIX_FALLBACK {base_id}: {type(exc).__name__}: {exc}")
            rows=_rows_from_existing_source(base_id,collection)
    rows,removed=_clean_exterior_white_noise(rows,collection)
    if removed:
        print(f"EXTERIOR_WHITE_CLEANUP {base_id} removed={removed}")

    palette=collection["palette"]
    if len(palette)!=25:
        raise RuntimeError("Pop Art master palette must contain exactly 25 colours")
    by_symbol={SYMBOLS[i]:rgb(p["hex"]) for i,p in enumerate(palette)}
    im=Image.new("RGBA",(800,960),(0,0,0,0))
    px=im.load()
    for gy,row in enumerate(rows):
        for gx,sym in enumerate(row):
            if sym==".":
                continue
            if sym not in by_symbol:
                raise RuntimeError(f"{base_id}: unknown matrix symbol {sym!r}")
            r,g,b=by_symbol[sym]
            for yy in range(gy*8,gy*8+8):
                for xx in range(gx*8,gx*8+8):
                    px[xx,yy]=(r,g,b,255)

    im=_fit_transparent_master(im,32)
    SOURCE_DIR.mkdir(parents=True,exist_ok=True)
    src=SOURCE_DIR/f"{base_id}.png"
    im.save(src,"PNG",optimize=True)
    print(f"SOURCE_REBUILT {base_id} {src} bbox={im.getchannel('A').getbbox()}")
    return src


def make_reference(base_id:str,design:dict,collection:dict):
    src=ensure_source_png(base_id,collection)
    im=Image.open(src).convert("RGBA")
    bbox,margins=validate_master(base_id,im)
    REFERENCE_DIR.mkdir(parents=True,exist_ok=True)
    ref=REFERENCE_DIR/f"{base_id}-{design['slug']}-reference.png"
    im.save(ref,"PNG",optimize=True)
    persisted=Image.open(ref).convert("RGBA")
    bbox2,_=validate_master(base_id,persisted)
    if bbox2!=bbox:
        raise RuntimeError(f"{base_id}: reference geometry changed")
    print(f"REFERENCE_OK {base_id} bbox={bbox} margins={margins}")
    return ref,bbox

def build_patterns(base_id:str,design:dict,collection:dict):
    ref,bbox=make_reference(base_id,design,collection)
    im=Image.open(ref).convert("RGBA")
    palette=collection["palette"]
    if len(palette)!=25:
        raise RuntimeError("Pop Art master palette must contain exactly 25 colours")
    palette_rgb=[rgb(p["hex"]) for p in palette]
    exact={c:i for i,c in enumerate(palette_rgb)}
    pix=im.load()
    matrix=[]
    counts=Counter()
    for gy in range(120):
        row=[]
        for gx in range(100):
            samples=[]
            x0,y0=gx*8,gy*8
            for yy in range(y0,y0+8):
                for xx in range(x0,x0+8):
                    r,g,b,a=pix[xx,yy]
                    if a>=128:
                        samples.append((r,g,b))
            if len(samples)<8:
                row.append(None)
                continue
            col=Counter(samples).most_common(1)[0][0]
            idx=exact.get(col)
            if idx is None:
                idx=nearest_palette_index(col,palette_rgb)
            sym=SYMBOLS[idx]
            row.append(sym)
            counts[sym]+=1
        matrix.append(row)
    if not counts:
        raise RuntimeError(f"{base_id}: empty cross-stitch matrix")

    threads=[]
    for i,p in enumerate(palette):
        sym=SYMBOLS[i]
        if counts[sym]:
            threads.append({"symbol":sym,"dmc":str(p["dmc"]),"color":p["hex"].upper(),
                            "name":p.get("name",f"DMC {p['dmc']}"),"stitches":counts[sym]})

    mats={"CS":(matrix,threads)}
    for suffix in ("C2C","TC","LH"):
        cfg=bg.TECHS[suffix]
        mats[suffix]=bg.downsample(matrix,threads,cfg["w"],cfg["h"])

    page_assets=collection["mockup_spec"]["technique_assets"]
    for suffix in SUFFIXES:
        code=f"{base_id}-{suffix}"
        cfg=bg.TECHS[suffix]
        mat,th=mats[suffix]
        ppath=PATTERNS/code/"pattern.json"
        prodpath=PRODUCTS/code/"product.json"
        pattern=read_json(ppath)
        pattern.update({
            "code":code,"base_design_id":base_id,"technique_code":suffix,
            "collection":"pop-art-25","palette_collection":"pop-art-25","status":"ready",
            "source_asset":f"content/pattern-system/collections/pop-art-25/sources/{base_id}.png",
            "reference_asset":f"content/pattern-system/collections/pop-art-25/reference-masters/{ref.name}",
            "stitch_width":cfg["w"],"stitch_height":cfg["h"],
            "total_stitches":sum(1 for r in mat for v in r if v),
            "threads":th,"matrix":mat,
        })
        write_json(ppath,pattern)
        product=read_json(prodpath)
        product.update({
            "collection":"pop-art-25","source_artwork":f"collections/pop-art-25/sources/{base_id}.png",
            "reference_artwork":f"collections/pop-art-25/reference-masters/{ref.name}",
            "page_1_asset":page_assets[suffix],"render_ready":True,"status":"active",
            "palette_mode":"strict","palette_size":25,"transparent_source":True,
        })
        write_json(prodpath,product)
    return bbox

def prepare_renderer_assets(collection:dict):
    tmp=Path("/tmp/drielo-pop-art-auto-assets")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    shutil.copy2(bg.ENGINE_ASSETS/"floral.png",tmp/"floral.png")
    targets={
        "CS":"cover-cross-stitch.webp",
        "C2C":"cover-crochet.webp",
        "TC":"cover-c2c-crochet.webp",
        "LH":"cover-rug.webp",
    }
    for suffix,target in targets.items():
        rel=collection["mockup_spec"]["technique_assets"][suffix]
        src=(COL_DIR/rel).resolve()
        if not src.is_file():
            raise RuntimeError(f"{suffix}: configured Pop Art cover missing: {rel} -> {src}")
        Image.open(src).convert("RGB").save(tmp/target,"WEBP",quality=94,method=6)
    bg.ENGINE_ASSETS=tmp

def render_design(base_id:str,design:dict,collection:dict):
    STORE_ASSETS.mkdir(parents=True,exist_ok=True)
    STORE_FILES.mkdir(parents=True,exist_ok=True)
    prepare_renderer_assets(collection)
    results={}
    for suffix in SUFFIXES:
        code=f"{base_id}-{suffix}"
        pattern=read_json(PATTERNS/code/"pattern.json")
        data=bg.pattern_data(code,design["title_en"],suffix,pattern["matrix"],pattern["threads"])
        data["collection"]=collection["name_en"]
        data["collection_id"]="pop-art-25"
        result=bg.render_one((code,suffix,data))
        pdf=STORE_FILES/f"Drielo_{code}.pdf"
        image=STORE_ASSETS/f"{code}-product.webp"
        gallery=[STORE_ASSETS/f"{code}-gallery-{i}.webp" for i in (2,3,4)]
        shutil.copy2(result["pdf"],pdf)
        shutil.copy2(result["image"],image)
        if len(result.get("gallery",[])) != 3:
            raise RuntimeError(f"{code}: renderer did not return the three required gallery previews")
        for src,dst in zip(result["gallery"],gallery):
            shutil.copy2(src,dst)
        if pdf.stat().st_size<100000 or pdf.read_bytes()[:4]!=b"%PDF":
            raise RuntimeError(f"{code}: invalid PDF")
        if image.stat().st_size<50000:
            raise RuntimeError(f"{code}: invalid product image")
        for g in gallery:
            if not g.is_file() or g.stat().st_size<30000:
                raise RuntimeError(f"{code}: invalid gallery preview {g.name}")
        results[suffix]={"pdf_bytes":pdf.stat().st_size,"image_bytes":image.stat().st_size,
                         "gallery_bytes":[g.stat().st_size for g in gallery],
                         "stitches":pattern["total_stitches"],"colors":len(pattern["threads"])}
    return results

def update_catalog(base_id:str,design:dict):
    catalog=read_json(CATALOG_PATH)
    rows=catalog.setdefault("products",[])
    by={p.get("code"):p for p in rows}
    templates={s:deepcopy(by[f"P0001-{s}"]) for s in SUFFIXES}
    revision=int(os.environ.get("DRIELO_GALLERY_REVISION",202609240000+int(base_id[1:])))
    for suffix in SUFFIXES:
        code=f"{base_id}-{suffix}"
        pattern=read_json(PATTERNS/code/"pattern.json")
        cfg=bg.TECHS[suffix]
        meta=TECH_META[suffix]
        row=by.get(code)
        if row is None:
            row=templates[suffix]
            rows.append(row)
            by[code]=row
        total=int(pattern["total_stitches"])
        colors=len(pattern["threads"])
        title_en=f"{design['title_en']} {meta['display_en']} Pattern PDF"
        title_es=f"Patrón PDF de {meta['display_es'].lower()}: {design['title_es']}"
        short_en=(f"Downloadable {design['title_en']} {meta['display_en']} pattern PDF. "
                  f"{cfg['w']} × {cfg['h']} {cfg['unit_label']}; {total:,} positions; "
                  f"{colors} colours selected exclusively from the fixed 25-colour Pop Art palette; "
                  f"beginner friendly. Pattern code: {code}.")
        short_es=(f"Patrón PDF descargable de {meta['display_es']}: {design['title_es']}. "
                  f"{cfg['w']} × {cfg['h']}; {total:,} posiciones; {colors} colores seleccionados "
                  f"exclusivamente de la paleta fija Pop Art de 25 colores; apto para principiantes. Código: {code}.")
        desc_en=(f"<p><strong>{title_en}</strong> is a downloadable digital pattern from Drielo’s Pop Art collection.</p>"
                 f"<p><strong>Pattern code:</strong> {code}</p>"
                 f"<p>This design uses only colours from the collection’s fixed 25-colour master palette.</p>"
                 f"<h3>Pattern details</h3><ul><li>Chart: {cfg['w']} × {cfg['h']} {cfg['unit_label']}</li>"
                 f"<li>{cfg['count_label']}: {total:,}</li><li>Colours used: {colors} from the fixed 25-colour palette</li>"
                 f"<li>Technique: {cfg['stitch_type']}</li><li>Beginner friendly</li></ul>"
                 f"<h3>What you receive</h3><p>A complete printable PDF with finished preview, pattern facts, "
                 f"colour key, charts, symbols, enlarged sections and working guide.</p><p>Digital product only. Personal use only.</p>")
        desc_es=(f"<p><strong>{title_es}</strong> es un patrón digital descargable de la colección Pop Art de Drielo.</p>"
                 f"<p><strong>Código:</strong> {code}</p><p>Este diseño utiliza únicamente colores de la paleta maestra fija de 25 colores.</p>"
                 f"<h3>Detalles</h3><ul><li>Gráfico: {cfg['w']} × {cfg['h']}</li><li>Posiciones: {total:,}</li>"
                 f"<li>Colores usados: {colors} de la paleta fija de 25 colores</li><li>Técnica: {meta['stitch_es']}</li>"
                 f"<li>Apto para principiantes</li></ul><h3>Qué recibirás</h3><p>PDF completo e imprimible con vista previa, "
                 f"datos del patrón, clave de colores, gráficos, símbolos, secciones ampliadas y guía de trabajo.</p>"
                 f"<p>Producto digital. Solo para uso personal.</p>")
        tags=[cfg["technique"],"digital pattern","pop art portrait","portrait pattern",
              "instant download","beginner pattern","colorwork chart",design["slug"][:20]]
        row.update({
            "code":code,"sku":f"DRIELO-{code}","base_design_id":base_id,"design_id":code,
            "technique_code":suffix,"technique":cfg["technique"],"title":title_en,"title_en":title_en,
            "title_es":title_es,"slug":f"{design['slug']}-{cfg['technique']}-pattern","price":4.99,
            "collection":"pop-art-25","stitches":total,"grid":f"{cfg['w']} × {cfg['h']} {cfg['unit_label']}",
            "colours":colors,"color_count":colors,"grid_width":cfg["w"],"grid_height":cfg["h"],
            "skill":"Beginner friendly","skill_en":"Beginner friendly","skill_es":"Apto para principiantes",
            "stitch_type":cfg["stitch_type"],"stitch_type_en":cfg["stitch_type"],"stitch_type_es":meta["stitch_es"],
            "short_description":short_en,"short_description_en":short_en,"short_description_es":short_es,
            "description":desc_en,"description_en":desc_en,"description_es":desc_es,
            "gallery":[
                f"assets/{code}-gallery-2.webp",
                f"assets/{code}-gallery-3.webp",
                f"assets/{code}-gallery-4.webp",
            ],
            "gallery_preview_pages":{"facts":3,"colour_a1":8,"symbol_a1":12},
            "featured_image":f"assets/{code}-product.webp","download":f"files/Drielo_{code}.pdf",
            "gallery_revision":revision,"tags":tags,"etsy_tags_en":tags,"etsy_tags_es":tags,
            "seo_title":f"{title_en} | Drielo","seo_title_en":f"{title_en} | Drielo","seo_title_es":f"{title_es} | Drielo",
            "meta_description":short_en[:155],"meta_description_en":short_en[:155],"meta_description_es":short_es[:155],
            "purchase_note_en":"Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.",
            "purchase_note_es":"Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.",
        })
        row["filters"]={
            "technique":[cfg["technique"]],"theme":["people-portraits"],"style":["pop-art","colorful"],
            "project":[cfg["project"]],"orientation":["portrait"],"difficulty":["beginner"],
            "color-family":["multicolor"],"season":[]
        }
        row.pop("previous_skus",None)

    rows.sort(key=lambda x:x.get("code",""))
    write_json(CATALOG_PATH,catalog)

    designs_doc=read_json(DESIGNS_PATH)
    for item in designs_doc["designs"]:
        if item["code"]==base_id:
            item["status"]="ready"
            item["source_artwork"]=f"sources/{base_id}.png"
            item["transparent_background"]=True
    write_json(DESIGNS_PATH,designs_doc)
    return revision

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("design_id")
    args=ap.parse_args()
    base=args.design_id.strip().upper()
    if not base.startswith("P") or len(base)!=5:
        raise SystemExit("Expected design id like P0002")
    if base in {"P0001","P0012"} and os.environ.get("DRIELO_ALLOW_PROTECTED")!="1":
        raise SystemExit(f"{base} is protected and requires an explicit protected rebuild")
    design=design_record(base)
    collection=read_json(COLLECTION_PATH)
    bbox=build_patterns(base,design,collection)
    results=render_design(base,design,collection)
    revision=update_catalog(base,design)
    print(json.dumps({"design_id":base,"title":design["title_en"],"bbox":bbox,
                      "gallery_revision":revision,"products":results},ensure_ascii=False,indent=2))
    print(f"AUTO_DESIGN_READY={base}")

if __name__=="__main__":
    main()
