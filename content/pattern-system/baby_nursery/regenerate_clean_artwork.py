#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections" / "baby-nursery"
PRODUCTS = SOURCE_ROOT / "products"
PALETTE = SOURCE_ROOT / "palette50_dmc.json"
MANIFEST = SOURCE_ROOT / "source-manifest.json"
QA = SOURCE_ROOT / "qa_report.json"
DESIGNS = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "designs.json"
REPORT = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "clean-redraw-2026-09-28.json"

TARGETS = {
    "I0021": "I0021-whale.png",
    "I0026": "I0026-long-neck-dinosaur.png",
    "I0027": "I0027-triceratops.png",
    "I0029": "I0029-stegosaurus.png",
    "I0043": "I0043-rainbow-clouds.png",
}

def load_palette():
    p=json.loads(PALETTE.read_text(encoding="utf-8"))
    return {str(x["dmc"]): tuple(x["rgb"])+(255,) for x in p["colors"]}

C = load_palette()

def blank():
    return Image.new("RGBA",(100,120),(0,0,0,0))

def whale():
    im=blank(); d=ImageDraw.Draw(im)
    outline=C["939"]; blue=C["322"]; light=C["3755"]; belly=C["3752"]; black=C["310"]; blush=C["3706"]
    # tail on left, body fully inside safe area
    d.polygon([(12,59),(22,52),(27,58),(25,63),(28,68),(22,74),(12,67),(17,63)],fill=outline)
    d.polygon([(15,59),(22,55),(24,59),(22,63),(25,67),(22,71),(15,67),(20,63)],fill=blue)
    d.ellipse((22,42,81,78),fill=outline)
    d.ellipse((25,45,78,75),fill=blue)
    d.ellipse((42,58,72,74),fill=belly)
    d.polygon([(43,62),(55,68),(46,73),(39,68)],fill=outline)
    d.polygon([(44,63),(52,68),(46,71),(41,68)],fill=light)
    d.ellipse((65,53,68,56),fill=black)
    d.arc((64,56,72,63),0,150,fill=outline,width=1)
    d.ellipse((70,60,73,63),fill=blush)
    # water spout
    d.line((58,43,58,36),fill=light,width=2)
    d.line((58,37,54,33),fill=light,width=2)
    d.line((59,37,63,33),fill=light,width=2)
    return im

def long_neck():
    im=blank(); d=ImageDraw.Draw(im)
    outline=C["934"]; green=C["470"]; dark=C["905"]; light=C["703"]; beige=C["738"]; black=C["310"]
    # long tapered tail left
    d.polygon([(14,69),(27,62),(39,61),(39,74),(27,75)],fill=outline)
    d.polygon([(17,69),(28,64),(38,64),(38,71),(27,72)],fill=green)
    # body
    d.ellipse((29,52,73,82),fill=outline); d.ellipse((32,55,70,79),fill=green)
    # neck and head
    d.rounded_rectangle((56,28,68,62),radius=5,fill=outline)
    d.rounded_rectangle((59,30,65,60),radius=3,fill=green)
    d.ellipse((54,20,76,39),fill=outline); d.ellipse((57,23,73,36),fill=green)
    # snout
    d.ellipse((66,27,77,36),fill=outline); d.ellipse((67,28,74,34),fill=beige)
    # legs
    for x in (36,58):
        d.rounded_rectangle((x,74,x+8,95),radius=3,fill=outline)
        d.rounded_rectangle((x+2,76,x+6,92),radius=2,fill=green)
    # spots
    for box in [(40,58,46,64),(49,66,55,72),(61,46,65,51)]:
        d.ellipse(box,fill=dark)
    d.ellipse((64,27,67,30),fill=black)
    d.arc((67,31,73,36),10,130,fill=outline,width=1)
    return im

def triceratops():
    im=blank(); d=ImageDraw.Draw(im)
    outline=C["938"]; orange=C["741"]; shade=C["922"]; cream=C["738"]; black=C["310"]; cheek=C["351"]
    # tail left, deliberately tapered
    d.polygon([(13,67),(26,60),(36,61),(37,72),(25,73)],fill=outline)
    d.polygon([(16,67),(27,63),(35,63),(35,69),(26,70)],fill=orange)
    # body
    d.ellipse((28,51,71,80),fill=outline); d.ellipse((31,54,68,77),fill=orange)
    # frill + head on right
    d.polygon([(64,47),(74,43),(83,48),(87,58),(82,68),(71,69),(64,61)],fill=outline)
    d.polygon([(67,49),(74,46),(80,50),(83,58),(79,65),(71,66),(67,60)],fill=shade)
    d.ellipse((68,52,84,69),fill=outline); d.ellipse((70,54,81,66),fill=orange)
    # horns
    d.polygon([(76,51),(80,43),(82,52)],fill=cream)
    d.polygon([(81,58),(89,55),(82,61)],fill=cream)
    # legs
    for x in (36,57):
        d.rounded_rectangle((x,73,x+8,94),radius=3,fill=outline)
        d.rounded_rectangle((x+2,75,x+6,91),radius=2,fill=orange)
    d.ellipse((76,57,79,60),fill=black)
    d.ellipse((78,62,81,65),fill=cheek)
    return im

def stegosaurus():
    im=blank(); d=ImageDraw.Draw(im)
    outline=C["939"]; blue=C["3755"]; dark=C["322"]; plate=C["922"]; cream=C["738"]; black=C["310"]
    # tapered tail left
    d.polygon([(12,68),(27,60),(39,61),(39,73),(27,74)],fill=outline)
    d.polygon([(15,68),(28,63),(37,63),(37,70),(27,71)],fill=blue)
    # body
    d.ellipse((30,51,72,80),fill=outline); d.ellipse((33,54,69,77),fill=blue)
    # head/neck right
    d.rounded_rectangle((65,60,78,73),radius=5,fill=outline)
    d.rounded_rectangle((68,62,76,70),radius=3,fill=blue)
    d.ellipse((72,59,84,71),fill=outline); d.ellipse((74,61,81,68),fill=blue)
    # dorsal plates
    plates=[(32,56,36,44,41,56),(40,53,45,40,50,55),(49,53,54,39,59,55),(58,56,63,44,68,58)]
    for pts in plates:
        d.polygon([(pts[0],pts[1]),(pts[2],pts[3]),(pts[4],pts[5])],fill=outline)
        cx=(pts[0]+pts[2]+pts[4])//3
        cy=(pts[1]+pts[3]+pts[5])//3
        d.ellipse((cx-1,cy-1,cx+1,cy+1),fill=plate)
    # legs
    for x in (37,58):
        d.rounded_rectangle((x,73,x+8,94),radius=3,fill=outline)
        d.rounded_rectangle((x+2,75,x+6,91),radius=2,fill=blue)
    d.ellipse((78,63,81,66),fill=black)
    d.ellipse((49,61,54,66),fill=dark)
    d.ellipse((58,67,63,72),fill=dark)
    d.line((16,66,13,62),fill=cream,width=2)
    return im

def rainbow():
    im=blank(); d=ImageDraw.Draw(im)
    navy=C["939"]
    # rainbow, built from full arcs with generous side margins
    arcs=[
        ("350",(19,28,81,90),7),
        ("741",(24,33,76,85),7),
        ("726",(29,38,71,80),7),
        ("470",(34,43,66,75),7),
        ("322",(39,48,61,70),7),
    ]
    for code,box,width in arcs:
        d.arc(box,180,360,fill=navy,width=width+2)
        d.arc(box,180,360,fill=C[code],width=width)
    # remove everything below the rainbow baseline center except cloud regions
    d.rectangle((10,61,90,90),fill=(0,0,0,0))
    # redraw lower arc ends to meet clouds naturally
    for code,box,width in arcs[:4]:
        d.arc(box,180,360,fill=C[code],width=width)
    # clouds left/right, complete and symmetric
    cloud=C["762"]; shadow=C["3752"]
    for x in (14,62):
        d.ellipse((x+6,64,x+26,81),fill=navy)
        d.ellipse((x,70,x+18,85),fill=navy)
        d.ellipse((x+15,70,x+34,85),fill=navy)
        d.rectangle((x+7,73,x+27,85),fill=navy)
        d.ellipse((x+7,66,x+25,80),fill=cloud)
        d.ellipse((x+2,72,x+16,82),fill=cloud)
        d.ellipse((x+17,72,x+31,82),fill=cloud)
        d.rectangle((x+8,73,x+25,82),fill=cloud)
        d.line((x+8,82,x+25,82),fill=shadow,width=1)
    return im

DRAWERS={"I0021":whale,"I0026":long_neck,"I0027":triceratops,"I0029":stegosaurus,"I0043":rainbow}

def bbox_margins(im):
    bbox=im.getchannel("A").getbbox()
    if not bbox: raise RuntimeError("empty image")
    l,t,r,b=bbox
    return list(bbox),{"left":l,"top":t,"right":100-r,"bottom":120-b}

def main():
    palette=json.loads(PALETTE.read_text(encoding="utf-8"))
    rgb_to_dmc={tuple(x["rgb"]):str(x["dmc"]) for x in palette["colors"]}
    designs=json.loads(DESIGNS.read_text(encoding="utf-8"))
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    qa=json.loads(QA.read_text(encoding="utf-8"))
    by_design={d["base_design_id"]:d for d in designs["designs"]}
    by_manifest={p["id"]:p for p in manifest["products"]}

    rows=[]
    for base,filename in TARGETS.items():
        im=DRAWERS[base]()
        bbox,m=bbox_margins(im)
        if min(m.values())<10:
            raise SystemExit(f"{base}: unsafe margin {m}")
        colors={(r,g,b) for r,g,b,a in im.getdata() if a==255}
        unknown=colors-set(rgb_to_dmc)
        if unknown:
            raise SystemExit(f"{base}: non-DMC colors {unknown}")
        path=PRODUCTS/filename
        im.save(path,"PNG",optimize=False)
        codes=sorted({rgb_to_dmc[c] for c in colors},key=lambda x:(len(x),x))
        by_manifest[base]["color_count"]=len(colors)
        by_manifest[base]["dmc_codes"]=codes
        by_design[base]["source_colour_count"]=len(colors)
        qa["files"][int(base[1:])-1]["colors_used"]=len(colors)
        qa["files"][int(base[1:])-1]["margins"]=m
        rows.append({"id":base,"file":filename,"bbox":bbox,"margins":m,"colors":len(colors),"dmc_codes":codes})
        print("REDRAW_OK",base,bbox,m)

    qa["minimum_canvas_margin_px"]=min(min(x["margins"].values()) for x in qa["files"])
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    DESIGNS.write_text(json.dumps(designs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps({
        "version":"full-redraw-v1",
        "method":"drawn from scratch; no geometry copied from prior damaged PNGs",
        "canvas":[100,120],
        "targets":rows,
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
