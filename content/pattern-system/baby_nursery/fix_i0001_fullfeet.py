#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
SRC = SYSTEM / "patterns"
OUT_IMG = SYSTEM / "collections" / "baby-nursery" / "source-designs" / "I0001-teddy-bear.png"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

SUFFIXES = ("CS","C2C","TC","LH")
GRID = {"CS":(100,120),"C2C":(60,72),"TC":(80,96),"LH":(60,72)}

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def sym_for_dmc(threads, dmc):
    for t in threads:
        if str(t.get("dmc")) == str(dmc):
            return t["symbol"]
    raise RuntimeError(f"Missing DMC {dmc}")

def set_if_lower(matrix, x, y, sym):
    if 0 <= y < len(matrix) and 0 <= x < len(matrix[0]):
        matrix[y][x] = sym

def inside_ellipse(x, y, x0, y0, x1, y1):
    cx=(x0+x1)/2.0; cy=(y0+y1)/2.0
    rx=(x1-x0)/2.0; ry=(y1-y0)/2.0
    if rx <= 0 or ry <= 0:
        return False
    return ((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 1.0

def paint_ellipse(matrix, box, sym, only_y_from=None):
    x0,y0,x1,y1=box
    for y in range(max(0,y0), min(len(matrix),y1+1)):
        if only_y_from is not None and y < only_y_from:
            continue
        for x in range(max(0,x0), min(len(matrix[0]),x1+1)):
            if inside_ellipse(x,y,x0,y0,x1,y1):
                matrix[y][x]=sym

def recount(matrix, threads):
    counts=Counter(v for row in matrix for v in row if v)
    out=[]
    for t in threads:
        n=counts.get(t["symbol"],0)
        if n:
            nt=dict(t)
            nt["stitches"]=n
            out.append(nt)
    return out, sum(counts.values())

def save_source_png(matrix, threads, path):
    color={t["symbol"]:t["color"] for t in threads}
    h=len(matrix); w=len(matrix[0])
    im=Image.new("RGBA",(w,h),(0,0,0,0))
    pix=im.load()
    for y,row in enumerate(matrix):
        for x,s in enumerate(row):
            if not s:
                continue
            hx=color[s].lstrip("#")
            pix[x,y]=(int(hx[0:2],16),int(hx[2:4],16),int(hx[4:6],16),255)
    path.parent.mkdir(parents=True,exist_ok=True)
    im.resize((800,960),Image.Resampling.NEAREST).save(path,optimize=True)

def main():
    cs_path=SRC/"I0001-CS"/"pattern.json"
    cs=read_json(cs_path)
    matrix=[list(row) for row in cs["matrix"]]
    threads=cs["threads"]

    # Keep the approved face/body/bow exactly as-is. Only rebuild the lower
    # silhouette so both seated paws are closed, rounded and fully visible.
    brown=sym_for_dmc(threads,"434")
    dark=sym_for_dmc(threads,"801")
    beige=sym_for_dmc(threads,"842")
    tan=sym_for_dmc(threads,"437")

    # Remove the old hard, flat lower edge while retaining everything above it.
    for y in range(102,120):
        for x in range(100):
            matrix[y][x]=None

    # Round the central belly downward instead of ending in a horizontal crop.
    paint_ellipse(matrix,(32,86,67,111),brown,only_y_from=98)
    paint_ellipse(matrix,(40,90,59,106),tan,only_y_from=99)

    # Left full paw: brown exterior, pale pad ring, dark centre.
    paint_ellipse(matrix,(3,82,41,114),brown,only_y_from=96)
    paint_ellipse(matrix,(7,86,37,112),beige,only_y_from=97)
    paint_ellipse(matrix,(12,90,33,109),dark,only_y_from=98)

    # Right full paw.
    paint_ellipse(matrix,(58,82,96,114),brown,only_y_from=96)
    paint_ellipse(matrix,(62,86,92,112),beige,only_y_from=97)
    paint_ellipse(matrix,(67,90,88,109),dark,only_y_from=98)

    # A few outer-brown cells bridge the legs into the new rounded paws, avoiding
    # the visual impression of detached circles after downsampling.
    for y in range(96,104):
        for x in range(28,35):
            matrix[y][x]=brown
        for x in range(65,72):
            matrix[y][x]=brown

    cs_threads,total=recount(matrix,threads)
    cs["matrix"]=matrix
    cs["threads"]=cs_threads
    cs["total_stitches"]=total
    cs["source_asset"]="collections/baby-nursery/source-designs/I0001-teddy-bear.png"
    write_json(cs_path,cs)

    # Rebuild all other techniques from corrected CS source using the same
    # chroma-preserving downsample logic used by Pop Art.
    for suffix in ("C2C","TC","LH"):
        w,h=GRID[suffix]
        m,t=bg.downsample(matrix,cs_threads,w,h)
        t,total2=recount(m,t)
        p=read_json(SRC/f"I0001-{suffix}"/"pattern.json")
        p["matrix"]=m
        p["threads"]=t
        p["total_stitches"]=total2
        p["stitch_width"]=w
        p["stitch_height"]=h
        p["source_asset"]="collections/baby-nursery/source-designs/I0001-teddy-bear.png"
        write_json(SRC/f"I0001-{suffix}"/"pattern.json",p)

    save_source_png(matrix,cs_threads,OUT_IMG)

    # Guardrail: source must end with a transparent margin, not a crop.
    alpha=Image.open(OUT_IMG).convert("RGBA").getchannel("A")
    bbox=alpha.getbbox()
    if not bbox:
        raise RuntimeError("Corrected source image is empty")
    if bbox[3] >= 952:
        raise RuntimeError(f"Corrected feet still touch the bottom edge: bbox={bbox}")

    print("I0001_FULL_FEET_SOURCE",OUT_IMG)
    print("I0001_CS_STITCHES",total)
    print("I0001_SOURCE_BBOX",bbox)

if __name__=="__main__":
    main()
