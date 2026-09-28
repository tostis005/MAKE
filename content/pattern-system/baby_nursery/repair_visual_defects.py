#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from statistics import mean

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections" / "baby-nursery"
PRODUCTS = SOURCE_ROOT / "products"
MANIFEST = SOURCE_ROOT / "source-manifest.json"
PALETTE = SOURCE_ROOT / "palette50_dmc.json"
QA = SOURCE_ROOT / "qa_report.json"
DESIGNS = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "designs.json"
REPORT = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "repair-report-2026-09-28.json"

# Visual audit of all 60 source PNGs + all 60 live WooCommerce featured images.
# These five have unrelated disconnected fragments outside the intended artwork.
REPAIR_IDS = {"I0022", "I0027", "I0028", "I0030", "I0044"}


def comps(mask, w, h):
    seen=set(); out=[]
    for y in range(h):
        for x in range(w):
            if not mask[y*w+x] or (x,y) in seen:
                continue
            q=deque([(x,y)]); seen.add((x,y)); pts=[]
            while q:
                px,py=q.popleft(); pts.append((px,py))
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if dx==0 and dy==0: continue
                        nx,ny=px+dx,py+dy
                        if 0<=nx<w and 0<=ny<h and mask[ny*w+nx] and (nx,ny) not in seen:
                            seen.add((nx,ny)); q.append((nx,ny))
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            out.append({"points":pts,"size":len(pts),"bbox":[min(xs),min(ys),max(xs)+1,max(ys)+1]})
    out.sort(key=lambda x:x["size"],reverse=True)
    return out


def analyse_rgba(rgba):
    w,h=rgba.size
    pix=list(rgba.getdata())
    mask=[a>=128 for _,_,_,a in pix]
    cs=comps(mask,w,h)
    xs=[i%w for i,v in enumerate(mask) if v]
    ys=[i//w for i,v in enumerate(mask) if v]
    bbox=[min(xs),min(ys),max(xs)+1,max(ys)+1] if xs else None
    margins={
        "left":bbox[0],"top":bbox[1],"right":w-bbox[2],"bottom":h-bbox[3]
    } if bbox else {}
    colors={(r,g,b) for r,g,b,a in pix if a==255}
    semis=sum(1 for *_,a in pix if a not in (0,255))
    white=sum(1 for r,g,b,a in pix if a==255 and (r,g,b)==(255,255,255))
    return cs,bbox,margins,colors,semis,white


def main():
    designs=json.loads(DESIGNS.read_text(encoding="utf-8"))
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    palette=json.loads(PALETTE.read_text(encoding="utf-8"))
    qa=json.loads(QA.read_text(encoding="utf-8"))

    by_design={d["base_design_id"]:d for d in designs["designs"]}
    by_manifest={p["id"]:p for p in manifest["products"]}
    rgb_to_dmc={tuple(x["rgb"]):str(x["dmc"]) for x in palette["colors"]}

    report=[]
    for base in sorted(REPAIR_IDS):
        d=by_design[base]
        path=PRODUCTS/f"{base}-{d['slug']}.png"
        with Image.open(path) as im:
            rgba=im.convert("RGBA")
        if rgba.size!=(100,120):
            raise SystemExit(f"{base}: wrong source size {rgba.size}")
        before,bbox,margins,colors,semis,white=analyse_rgba(rgba)
        if len(before)<2:
            raise SystemExit(f"{base}: expected a disconnected corrupt fragment, got {len(before)} components")
        if semis or white:
            raise SystemExit(f"{base}: invalid alpha/white source before repair")

        main_component=set(before[0]["points"])
        removed=[c for c in before[1:]]
        px=rgba.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                if px[x,y][3]>=128 and (x,y) not in main_component:
                    px[x,y]=(0,0,0,0)

        after,abbox,amargins,acolors,semis,white=analyse_rgba(rgba)
        if len(after)!=1:
            raise SystemExit(f"{base}: repair did not produce a single component")
        if semis or white:
            raise SystemExit(f"{base}: invalid alpha/white after repair")
        unknown=acolors-set(rgb_to_dmc)
        if unknown:
            raise SystemExit(f"{base}: repaired source has colors outside DMC50: {sorted(unknown)[:5]}")
        if min(amargins.values())<5:
            raise SystemExit(f"{base}: repaired art too close to edge: {amargins}")

        rgba.save(path,"PNG",optimize=False)

        codes=sorted({rgb_to_dmc[c] for c in acolors},key=lambda x:(len(x),x))
        m=by_manifest[base]
        m["color_count"]=len(acolors)
        m["dmc_codes"]=codes
        d["source_colour_count"]=len(acolors)

        report.append({
            "id":base,
            "title_en":d["title_en"],
            "file":path.name,
            "before_components":[{"size":c["size"],"bbox":c["bbox"]} for c in before],
            "removed_components":[{"size":c["size"],"bbox":c["bbox"]} for c in removed],
            "removed_pixels":sum(c["size"] for c in removed),
            "after_components":1,
            "after_bbox":abbox,
            "after_margins":amargins,
            "after_color_count":len(acolors),
            "after_dmc_codes":codes,
        })

    # Rebuild QA metrics for all 60 canonical sources so metadata matches bytes.
    qa_rows=[]
    all_colors=set(); semi_total=0; white_total=0
    for idx,d in enumerate(designs["designs"],start=1):
        base=d["base_design_id"]
        path=PRODUCTS/f"{base}-{d['slug']}.png"
        with Image.open(path) as im:
            rgba=im.convert("RGBA")
        cs,bbox,margins,colors,semis,white=analyse_rgba(rgba)
        all_colors.update(colors); semi_total+=semis; white_total+=white
        old=(qa.get("files") or [{}]*60)[idx-1]
        qa_rows.append({
            "filename":old.get("filename",f"infantil_{idx:03d}_{d['slug'].replace('-','_')}.png"),
            "colors_used":len(colors),
            "margins":margins,
        })
    counts=[x["colors_used"] for x in qa_rows]
    qa.update({
        "files_checked":60,
        "global_palette_colors":50,
        "global_palette_colors_used":len(all_colors),
        "per_design_color_min":min(counts),
        "per_design_color_max":max(counts),
        "per_design_color_average":round(mean(counts),2),
        "minimum_canvas_margin_px":min(min(x["margins"].values()) for x in qa_rows),
        "semi_transparent_pixels":semi_total,
        "opaque_pure_white_pixels":white_total,
        "files":qa_rows,
    })

    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    DESIGNS.write_text(json.dumps(designs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps({
        "collection":"baby-nursery",
        "audit_scope":"60 source PNGs + 60 live WooCommerce featured images",
        "source_repairs":report,
        "refresh_without_source_change":["I0021","I0026"],
        "rebuild_ids":["I0021","I0022","I0026","I0027","I0028","I0030","I0044"],
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print(json.dumps({"repaired":report,"rebuild_ids":["I0021","I0022","I0026","I0027","I0028","I0030","I0044"]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
