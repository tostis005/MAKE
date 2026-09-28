#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "content" / "source-images" / "collections" / "baby-nursery" / "products"
DESIGNS = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "designs.json"
OUT = ROOT / "tmp" / "baby-nursery-visual-audit"
PRODUCT_ASSETS = ROOT / "content" / "products" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 5
TILE_W = 560
TILE_H = 690
COLS = 5
ROWS = 2


def components(mask, w, h):
    seen=set()
    out=[]
    for y in range(h):
        for x in range(w):
            if not mask[y*w+x] or (x,y) in seen:
                continue
            q=deque([(x,y)])
            seen.add((x,y))
            pts=[]
            while q:
                px,py=q.popleft()
                pts.append((px,py))
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if dx==0 and dy==0:
                            continue
                        nx,ny=px+dx,py+dy
                        if 0<=nx<w and 0<=ny<h and mask[ny*w+nx] and (nx,ny) not in seen:
                            seen.add((nx,ny)); q.append((nx,ny))
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            out.append({"size":len(pts),"bbox":[min(xs),min(ys),max(xs)+1,max(ys)+1]})
    out.sort(key=lambda c:c["size"], reverse=True)
    return out


def checker(w,h,cell=10):
    im=Image.new("RGB",(w,h),"white")
    d=ImageDraw.Draw(im)
    for y in range(0,h,cell):
        for x in range(0,w,cell):
            if ((x//cell)+(y//cell))%2:
                d.rectangle([x,y,x+cell-1,y+cell-1],fill=(235,235,235))
    return im


def compose_preview(src, scale=SCALE):
    rgba=src.convert("RGBA").resize((src.width*scale,src.height*scale),Image.Resampling.NEAREST)
    bg=checker(rgba.width,rgba.height,max(5,scale*2))
    bg.paste(rgba.convert("RGB"),mask=rgba.getchannel("A"))
    return bg


def analyse(path):
    with Image.open(path) as im:
        rgba=im.convert("RGBA")
    w,h=rgba.size
    pix=list(rgba.getdata())
    mask=[a>=128 for _,_,_,a in pix]
    xs=[i%w for i,v in enumerate(mask) if v]
    ys=[i//w for i,v in enumerate(mask) if v]
    bbox=[min(xs),min(ys),max(xs)+1,max(ys)+1] if xs else None
    margins={
        "left": bbox[0] if bbox else None,
        "top": bbox[1] if bbox else None,
        "right": w-bbox[2] if bbox else None,
        "bottom": h-bbox[3] if bbox else None,
    } if bbox else {}
    comps=components(mask,w,h)
    main=comps[0]["size"] if comps else 0
    residual=sum(c["size"] for c in comps[1:] if c["size"] <= max(12, int(main*0.015)))
    large_extra=[c for c in comps[1:] if c["size"] > max(12,int(main*0.015))]
    min_margin=min(margins.values()) if margins else 0
    flags=[]
    if min_margin <= 4:
        flags.append("near-edge")
    if residual >= 10:
        flags.append("small-islands")
    if len(large_extra) >= 1:
        flags.append("multiple-components")
    return {
        "size":[w,h],
        "bbox":bbox,
        "margins":margins,
        "opaque_pixels":sum(mask),
        "component_count":len(comps),
        "components":comps[:12],
        "small_residual_pixels":residual,
        "flags":flags,
    }


def main():
    doc=json.loads(DESIGNS.read_text(encoding="utf-8"))
    rows=[]
    for d in doc["designs"]:
        base=d["base_design_id"]
        p=SOURCE/f"{base}-{d['slug']}.png"
        if not p.is_file():
            raise SystemExit(f"Missing {p}")
        a=analyse(p)
        a.update({"id":base,"title_en":d["title_en"],"title_es":d["title_es"],"slug":d["slug"],"file":p.name})
        rows.append(a)

    (OUT/"audit.json").write_text(json.dumps({"count":len(rows),"items":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    font=ImageFont.load_default()
    for sidx in range(0,len(rows),10):
        subset=rows[sidx:sidx+10]
        sheet=Image.new("RGB",(COLS*TILE_W,ROWS*TILE_H),(248,248,248))
        draw=ImageDraw.Draw(sheet)
        for idx,row in enumerate(subset):
            col=idx%COLS; rr=idx//COLS
            x0=col*TILE_W; y0=rr*TILE_H
            p=SOURCE/row["file"]
            with Image.open(p) as im:
                prev=compose_preview(im)
            px=x0+(TILE_W-prev.width)//2
            py=y0+55
            sheet.paste(prev,(px,py))
            flags=", ".join(row["flags"]) or "OK"
            draw.text((x0+12,y0+10),f"{row['id']}  {row['title_en']}",fill="black",font=font)
            draw.text((x0+12,y0+28),f"components={row['component_count']} residual={row['small_residual_pixels']}  {flags}",fill="black",font=font)
            draw.rectangle([x0,y0,x0+TILE_W-1,y0+TILE_H-1],outline=(180,180,180))
        sheet.save(OUT/f"sheet_{sidx//10+1:02d}_{subset[0]['id']}_{subset[-1]['id']}.png")

    # Large pixel-grid inspection for the three user-reported failures.
    focus_ids=["I0021","I0022","I0026"]
    focus=Image.new("RGB",(3*1080,1420),(250,250,250))
    fd=ImageDraw.Draw(focus)
    for j,base in enumerate(focus_ids):
        row=next(x for x in rows if x["id"]==base)
        with Image.open(SOURCE/row["file"]) as im:
            rgba=im.convert("RGBA").resize((1000,1200),Image.Resampling.NEAREST)
        bg=checker(1000,1200,20)
        bg.paste(rgba.convert("RGB"),mask=rgba.getchannel("A"))
        ox=j*1080+40; oy=120
        focus.paste(bg,(ox,oy))
        fd.text((j*1080+40,30),f"{row['id']} {row['title_en']} | flags={','.join(row['flags']) or 'OK'} | comps={row['component_count']}",fill="black",font=font)
        # grid every original pixel
        for gx in range(0,1001,10):
            fd.line((ox+gx,oy,ox+gx,oy+1200),fill=(210,210,210),width=1)
        for gy in range(0,1201,10):
            fd.line((ox,oy+gy,ox+1000,oy+gy),fill=(210,210,210),width=1)
    focus.save(OUT/"focus_I0021_I0022_I0026.png")

    # Audit the actual ecommerce hero frame for every published product asset.
    hero_rows=[]
    for row in rows:
        hero=PRODUCT_ASSETS/f"{row['id']}-CS-product.webp"
        hero_rows.append({**row,"hero_exists":hero.is_file()})
    for sidx in range(0,len(hero_rows),10):
        subset=hero_rows[sidx:sidx+10]
        sheet=Image.new("RGB",(COLS*TILE_W,ROWS*TILE_H),(248,248,248))
        draw=ImageDraw.Draw(sheet)
        for idx,row in enumerate(subset):
            col=idx%COLS; rr=idx//COLS
            x0=col*TILE_W; y0=rr*TILE_H
            hero=PRODUCT_ASSETS/f"{row['id']}-CS-product.webp"
            if hero.is_file():
                with Image.open(hero) as im:
                    rgb=im.convert("RGB")
                    if rgb.size==(1536,1536):
                        crop=rgb.crop((438,212,1123,1034))
                    else:
                        crop=rgb
                    prev=crop.resize((500,600),Image.Resampling.LANCZOS)
                sheet.paste(prev,(x0+30,y0+55))
            else:
                draw.text((x0+30,y0+300),"MISSING HERO",fill="red",font=font)
            draw.text((x0+12,y0+10),f"{row['id']}  {row['title_en']}",fill="black",font=font)
            draw.text((x0+12,y0+28),f"hero={'yes' if hero.is_file() else 'NO'}",fill="black",font=font)
            draw.rectangle([x0,y0,x0+TILE_W-1,y0+TILE_H-1],outline=(180,180,180))
        sheet.save(OUT/f"hero_sheet_{sidx//10+1:02d}_{subset[0]['id']}_{subset[-1]['id']}.png")

    hero_focus=Image.new("RGB",(3*1080,1420),(250,250,250))
    hfd=ImageDraw.Draw(hero_focus)
    for j,base in enumerate(focus_ids):
        row=next(x for x in rows if x["id"]==base)
        hero=PRODUCT_ASSETS/f"{base}-CS-product.webp"
        if hero.is_file():
            with Image.open(hero) as im:
                rgb=im.convert("RGB")
                crop=rgb.crop((438,212,1123,1034)) if rgb.size==(1536,1536) else rgb
                prev=crop.resize((1000,1200),Image.Resampling.LANCZOS)
            hero_focus.paste(prev,(j*1080+40,120))
        hfd.text((j*1080+40,30),f"{base} {row['title_en']} hero",fill="black",font=font)
    hero_focus.save(OUT/"hero_focus_I0021_I0022_I0026.png")

    print(json.dumps({
        "audited":len(rows),
        "flagged":[{"id":x["id"],"title":x["title_en"],"flags":x["flags"],"components":x["component_count"],"residual":x["small_residual_pixels"],"margins":x["margins"]} for x in rows if x["flags"]],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
