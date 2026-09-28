#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections" / "baby-nursery"
PRODUCTS = SOURCE_ROOT / "products"
MANIFEST = SOURCE_ROOT / "source-manifest.json"
PALETTE = SOURCE_ROOT / "palette50_dmc.json"
QA = SOURCE_ROOT / "qa_report.json"
DESIGNS = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "designs.json"
REPORT = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "layout-normalization-2026-09-28.json"

TARGET_IDS = (
    "I0021", # Whale
    "I0025", # Seahorse
    "I0026", # Long-Neck Dinosaur
    "I0027", # Triceratops
    "I0029", # Stegosaurus
    "I0043", # Rainbow with Clouds
    "I0044", # Sun
    "I0057", # Rattle
)
MAX_ART_W = 80
MAX_ART_H = 100


def bbox_and_margins(rgba: Image.Image):
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError("empty artwork")
    l,t,r,b=bbox
    return bbox, {
        "left": l,
        "top": t,
        "right": rgba.width-r,
        "bottom": rgba.height-b,
    }


def normalize(rgba: Image.Image):
    bbox,before=bbox_and_margins(rgba)
    crop=rgba.crop(bbox)
    w,h=crop.size
    scale=min(1.0, MAX_ART_W/w, MAX_ART_H/h)
    nw=max(1,round(w*scale))
    nh=max(1,round(h*scale))
    if (nw,nh)!=(w,h):
        crop=crop.resize((nw,nh),Image.Resampling.NEAREST)

    canvas=Image.new("RGBA",(100,120),(0,0,0,0))
    x=(100-nw)//2
    y=(120-nh)//2
    canvas.alpha_composite(crop,(x,y))
    abox,after=bbox_and_margins(canvas)
    return canvas, {
        "before_bbox": list(bbox),
        "before_margins": before,
        "source_art_size": [w,h],
        "scale": scale,
        "new_art_size": [nw,nh],
        "after_bbox": list(abox),
        "after_margins": after,
    }


def analyse(path: Path):
    with Image.open(path) as im:
        rgba=im.convert("RGBA")
    bbox,m=bbox_and_margins(rgba)
    colors={(r,g,b) for r,g,b,a in rgba.getdata() if a==255}
    semis=sum(1 for r,g,b,a in rgba.getdata() if a not in (0,255))
    white=sum(1 for r,g,b,a in rgba.getdata() if a==255 and (r,g,b)==(255,255,255))
    return rgba,bbox,m,colors,semis,white


def main():
    designs=json.loads(DESIGNS.read_text(encoding="utf-8"))
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    palette=json.loads(PALETTE.read_text(encoding="utf-8"))
    qa=json.loads(QA.read_text(encoding="utf-8"))

    by_design={d["base_design_id"]:d for d in designs["designs"]}
    by_manifest={p["id"]:p for p in manifest["products"]}
    rgb_to_dmc={tuple(x["rgb"]):str(x["dmc"]) for x in palette["colors"]}

    report=[]
    for base in TARGET_IDS:
        d=by_design[base]
        path=PRODUCTS/f"{base}-{d['slug']}.png"
        rgba,_,_,before_colors,semis,white=analyse(path)
        if rgba.size!=(100,120):
            raise SystemExit(f"{base}: expected 100x120, got {rgba.size}")
        if semis or white:
            raise SystemExit(f"{base}: invalid alpha/opaque white before normalization")

        normalized,metrics=normalize(rgba)
        after_colors={(r,g,b) for r,g,b,a in normalized.getdata() if a==255}
        unknown=after_colors-set(rgb_to_dmc)
        if unknown:
            raise SystemExit(f"{base}: normalization introduced colors outside DMC50: {sorted(unknown)[:5]}")
        if not after_colors:
            raise SystemExit(f"{base}: empty after normalization")

        _,after_m=bbox_and_margins(normalized)
        if min(after_m["left"],after_m["right"]) < 10:
            raise SystemExit(f"{base}: horizontal safe margin failed {after_m}")
        if min(after_m["top"],after_m["bottom"]) < 10:
            raise SystemExit(f"{base}: vertical safe margin failed {after_m}")
        if abs(after_m["left"]-after_m["right"])>1:
            raise SystemExit(f"{base}: not horizontally centered {after_m}")
        if abs(after_m["top"]-after_m["bottom"])>1:
            raise SystemExit(f"{base}: not vertically centered {after_m}")

        normalized.save(path,"PNG",optimize=False)

        codes=sorted({rgb_to_dmc[c] for c in after_colors},key=lambda x:(len(x),x))
        by_manifest[base]["color_count"]=len(after_colors)
        by_manifest[base]["dmc_codes"]=codes
        d["source_colour_count"]=len(after_colors)

        report.append({
            "id":base,
            "title_en":d["title_en"],
            "title_es":d["title_es"],
            "file":path.name,
            **metrics,
            "before_color_count":len(before_colors),
            "after_color_count":len(after_colors),
            "dmc_codes":codes,
        })

    # Rebuild QA metadata for all 60 sources.
    qa_rows=[]
    all_colors=set(); semi_total=0; white_total=0
    for idx,d in enumerate(designs["designs"],start=1):
        base=d["base_design_id"]
        path=PRODUCTS/f"{base}-{d['slug']}.png"
        rgba,bbox,margins,colors,semis,white=analyse(path)
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
        "per_design_color_average":round(sum(counts)/len(counts),2),
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
        "policy":{
            "canvas":[100,120],
            "max_art_width":MAX_ART_W,
            "max_art_height":MAX_ART_H,
            "minimum_horizontal_margin":10,
            "minimum_vertical_margin":10,
            "centering":"alpha-bounding-box centered to within 1 px",
            "upscale":False,
            "resampling":"nearest-neighbour",
        },
        "items":report,
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print(json.dumps({"normalized":report},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
