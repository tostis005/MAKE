#!/usr/bin/env python3
from __future__ import annotations

import base64
import colorsys
import json
import shutil
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "baby-nursery"
CHUNKS = SYSTEM / "baby_nursery" / "source_chunks"
OUT_SRC = COL / "source-designs"
PAT = SYSTEM / "patterns"
PROD = SYSTEM / "products"

DESIGNS = [
    ("I0001","Teddy Bear","Osito de peluche","teddy-bear"),
    ("I0002","Baby Elephant","Elefantito","baby-elephant"),
    ("I0003","Giraffe","Jirafa","giraffe"),
    ("I0004","Crescent Moon","Luna creciente","crescent-moon"),
    ("I0005","Smiling Cloud","Nube sonriente","smiling-cloud"),
    ("I0006","Bunny with Heart","Conejito con corazón","bunny-heart"),
    ("I0007","Rainbow with Clouds","Arcoíris con nubes","rainbow-clouds"),
    ("I0008","Cute Dinosaur","Dinosaurio infantil","cute-dinosaur"),
    ("I0009","Hot Air Balloon","Globo aerostático","hot-air-balloon"),
    ("I0010","Toy Sailboat","Velero infantil","toy-sailboat"),
    ("I0011","Unicorn","Unicornio","unicorn"),
    ("I0012","Baby Bottle","Biberón","baby-bottle"),
    ("I0013","Pacifier","Chupete","pacifier"),
    ("I0014","Baby Stroller","Cochecito de bebé","baby-stroller"),
    ("I0015","Rocking Horse","Caballito balancín","rocking-horse"),
    ("I0016","Teddy Bear Baby Onesie","Body de bebé con osito","teddy-bear-onesie"),
    ("I0017","Rubber Duck","Patito de goma","rubber-duck"),
    ("I0018","ABC Blocks","Bloques ABC","abc-blocks"),
    ("I0019","Nursery Mobile","Móvil de cuna","nursery-mobile"),
    ("I0020","Smiling Star","Estrella sonriente","smiling-star"),
    ("I0021","Sleeping Owl","Búho dormido","sleeping-owl"),
    ("I0022","Floral Baby Bib","Babero floral","floral-baby-bib"),
    ("I0023","Plush Lamb","Corderito de peluche","plush-lamb"),
    ("I0024","Toy Train","Tren de juguete","toy-train"),
    ("I0025","Stacking Rings","Anillas apilables","stacking-rings"),
    ("I0026","Baby Crib","Cuna de bebé","baby-crib"),
    ("I0027","Pink Floral Baby Onesie","Body rosa floral de bebé","pink-floral-onesie"),
    ("I0028","Rocket","Cohete","rocket"),
    ("I0029","Kite","Cometa","kite"),
    ("I0030","Fairytale Castle","Castillo de cuento","fairytale-castle"),
]

PALETTE = [
    {"dmc":"3865","name":"Winter White","hex":"#F5ECDF"},
    {"dmc":"842","name":"Very Light Beige Brown","hex":"#D8C0A6"},
    {"dmc":"437","name":"Light Tan","hex":"#C19671"},
    {"dmc":"434","name":"Light Brown","hex":"#986C4B"},
    {"dmc":"801","name":"Dark Coffee Brown","hex":"#664B37"},
    {"dmc":"3799","name":"Very Dark Pewter Gray","hex":"#404040"},
    {"dmc":"415","name":"Pearl Gray","hex":"#AEB3B9"},
    {"dmc":"3752","name":"Very Light Antique Blue","hex":"#A8BED2"},
    {"dmc":"3325","name":"Light Baby Blue","hex":"#86B1D0"},
    {"dmc":"3760","name":"Medium Wedgewood","hex":"#558EBD"},
    {"dmc":"3813","name":"Light Blue Green","hex":"#A4BFB0"},
    {"dmc":"522","name":"Fern Green","hex":"#829879"},
    {"dmc":"3051","name":"Dark Green Gray","hex":"#627650"},
    {"dmc":"744","name":"Pale Yellow","hex":"#F5CB79"},
    {"dmc":"3824","name":"Light Apricot","hex":"#F3B98E"},
    {"dmc":"761","name":"Light Salmon","hex":"#FC9F8B"},
    {"dmc":"3713","name":"Very Light Salmon","hex":"#FBB4B9"},
    {"dmc":"3733","name":"DMC 3733","hex":"#D16F81"},
    {"dmc":"211","name":"Light Lavender","hex":"#C6A2C6"},
    {"dmc":"3042","name":"Light Antique Violet","hex":"#BBA7C7"},
    {"dmc":"598","name":"Light Turquoise","hex":"#8EB8BC"},
    {"dmc":"3013","name":"Light Khaki Green","hex":"#BDBF9F"},
    {"dmc":"453","name":"DMC 453","hex":"#D3C1BE"},
    {"dmc":"3727","name":"Light Antique Mauve","hex":"#D1B5B3"},
]

SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
TECH = {
    "CS":  {"w":100,"h":120,"technique":"cross-stitch","template":"cross-stitch.html",
            "page":"collections/baby-nursery/assets/cover-cross-stitch.jpg"},
    "C2C": {"w":60,"h":72,"technique":"c2c-crochet","template":"c2c-crochet.html",
            "page":"collections/baby-nursery/assets/cover-c2c-crochet.jpg"},
    "TC":  {"w":80,"h":96,"technique":"tapestry-crochet","template":"crochet.html",
            "page":"collections/baby-nursery/assets/cover-crochet.jpg"},
    "LH":  {"w":60,"h":72,"technique":"latch-hook","template":"rug.html",
            "page":"collections/baby-nursery/assets/cover-rug.jpg"},
}

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def rgb(hexv):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def visual_props(hexv):
    r,g,b = (v/255.0 for v in rgb(hexv))
    _,s,v = colorsys.rgb_to_hsv(r,g,b)
    return s,v

def load_master_bytes():
    combined = OUT_SRC / "source-matrix.b64"
    if combined.is_file():
        encoded = combined.read_text(encoding="ascii").strip()
    else:
        parts = sorted(CHUNKS.glob("part*.txt"))
        if len(parts) != 6:
            raise RuntimeError(f"Expected 6 source chunks, found {len(parts)}")
        encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
        OUT_SRC.mkdir(parents=True, exist_ok=True)
        combined.write_text(encoded + "\n", encoding="ascii")
    raw = zlib.decompress(base64.b64decode(encoded))
    expected = 30 * 100 * 120
    if len(raw) != expected:
        raise RuntimeError(f"Source matrix bytes {len(raw)} != {expected}")
    return raw

def downsample(mat, new_w, new_h):
    h,w = mat.shape
    props = {i:visual_props(PALETTE[i]["hex"]) for i in range(len(PALETTE))}
    out = np.full((new_h,new_w), 255, dtype=np.uint8)
    for yy in range(new_h):
        ya = int(yy*h/new_h)
        yb = max(ya+1, int((yy+1)*h/new_h))
        for xx in range(new_w):
            xa = int(xx*w/new_w)
            xb = max(xa+1, int((xx+1)*w/new_w))
            vals = [int(v) for v in mat[ya:min(h,yb), xa:min(w,xb)].ravel() if int(v) != 255]
            if not vals:
                continue
            counts = Counter(vals)
            area = len(vals)
            def vote(i):
                sat,val = props.get(i,(0.0,0.5))
                return counts[i] + area*(1.65*sat + 0.42*(1.0-val))
            out[yy,xx] = max(counts, key=vote)
    return out

def matrix_and_threads(mat):
    counts = Counter(int(v) for v in mat.ravel() if int(v) != 255)
    used = sorted(counts)
    sym = {idx:SYMBOLS[idx] for idx in used}
    matrix = [[None if int(v)==255 else sym[int(v)] for v in row] for row in mat]
    threads = []
    for idx in used:
        p = PALETTE[idx]
        threads.append({
            "symbol":sym[idx],
            "dmc":str(p["dmc"]),
            "color":p["hex"].upper(),
            "name":p["name"],
            "stitches":counts[idx],
        })
    return matrix, threads, sum(counts.values())

def save_source_png(mat, path, scale=8):
    h,w = mat.shape
    arr = np.zeros((h,w,4), dtype=np.uint8)
    for idx,p in enumerate(PALETTE):
        rr,gg,bb = rgb(p["hex"])
        mask = mat == idx
        arr[mask,0] = rr
        arr[mask,1] = gg
        arr[mask,2] = bb
        arr[mask,3] = 255
    im = Image.fromarray(arr, "RGBA").resize((w*scale,h*scale), Image.Resampling.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)

def load_existing_source_master(path):
    im = Image.open(path).convert("RGBA").resize((100,120), Image.Resampling.NEAREST)
    arr = np.array(im)
    lut = {rgb(p["hex"]): i for i,p in enumerate(PALETTE)}
    out = np.full((120,100),255,dtype=np.uint8)
    for y in range(120):
        for x in range(100):
            r,g,b,a = [int(v) for v in arr[y,x]]
            if a < 128:
                continue
            key=(r,g,b)
            if key not in lut:
                raise RuntimeError(f"Existing source uses colour outside Baby Nursery palette: {key}")
            out[y,x]=lut[key]
    return out


def main():
    raw = load_master_bytes()
    masters = []
    off = 0
    for _ in DESIGNS:
        masters.append(np.frombuffer(raw[off:off+12000], dtype=np.uint8).reshape((120,100)).copy())
        off += 12000

    for (base,en,es,slug), master in zip(DESIGNS, masters):
        src_rel = f"collections/baby-nursery/source-designs/{base}-{slug}.png"
        src_path = SYSTEM / src_rel
        # I0001 has an approved full-feet correction. Preserve that canonical
        # source on collection-wide rebuilds instead of restoring the older
        # cropped source matrix.
        if base == "I0001" and src_path.is_file():
            master = load_existing_source_master(src_path)
        save_source_png(master, src_path)
        for suffix in ("CS","C2C","TC","LH"):
            cfg = TECH[suffix]
            mat = master if suffix == "CS" else downsample(master, cfg["w"], cfg["h"])
            matrix,threads,total = matrix_and_threads(mat)
            code = f"{base}-{suffix}"
            write_json(PAT/code/"pattern.json", {
                "code":code,
                "base_design_id":base,
                "technique_code":suffix,
                "collection":"baby-nursery",
                "palette_collection":"baby-nursery",
                "status":"ready",
                "source_asset":src_rel,
                "stitch_width":cfg["w"],
                "stitch_height":cfg["h"],
                "total_stitches":total,
                "threads":threads,
                "matrix":matrix,
            })
            write_json(PROD/code/"product.json", {
                "code":code,
                "base_design_id":base,
                "technique_code":suffix,
                "collection":"baby-nursery",
                "title":en,
                "title_en":en,
                "title_es":es,
                "design_slug":slug,
                "technique":cfg["technique"],
                "pattern_file":f"patterns/{code}/pattern.json",
                "template":cfg["template"],
                "website":"www.drielo.com",
                "status":"active",
                "render_ready":True,
                "source_artwork":src_rel,
                "page_1_asset":cfg["page"],
            })

    designs_path = COL / "designs.json"
    doc = json.loads(designs_path.read_text(encoding="utf-8"))
    lookup = {d[0]:d for d in DESIGNS}
    for item in doc.get("designs", []):
        base,en,es,slug = lookup[item["base_design_id"]]
        item["artwork_status"] = "canonical-pattern-ready"
        item["source_asset"] = f"collections/baby-nursery/source-designs/{base}-{slug}.png"
    write_json(designs_path, doc)

    col_path = COL / "collection.json"
    col = json.loads(col_path.read_text(encoding="utf-8"))
    col["mockup_spec"]["technique_assets"]["C2C"] = "collections/baby-nursery/assets/cover-c2c-crochet.jpg"
    col["mockup_spec"]["technique_assets"]["TC"] = "collections/baby-nursery/assets/cover-crochet.jpg"
    col["mockup_spec"]["crochet_asset_mapping_note"] = "Canonical mapping: C2C uses cover-c2c-crochet.jpg; tapestry crochet (TC) uses cover-crochet.jpg. Keep this mapping for future executions."
    write_json(col_path, col)

    write_json(OUT_SRC/"manifest.json", {
        "collection":"baby-nursery",
        "source":"approved transparent HD nursery sprite sheets",
        "palette":"Baby & Nursery collection palette only",
        "transparent_background":True,
        "master_grid":{"width":100,"height":120},
        "techniques":{k:{"width":v["w"],"height":v["h"]} for k,v in TECH.items()},
        "designs":[
            {"base_design_id":base,"slug":slug,
             "source_asset":f"collections/baby-nursery/source-designs/{base}-{slug}.png"}
            for base,en,es,slug in DESIGNS
        ],
    })

    if CHUNKS.exists():
        shutil.rmtree(CHUNKS)

    print("GENERATED_DESIGNS=30")
    print("GENERATED_PATTERN_JSONS=120")
    print("GENERATED_PRODUCT_JSONS=120")
    print("GENERATED_SOURCE_PNGS=30")

if __name__ == "__main__":
    main()
