#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
COLLECTION = HERE.parent
REFERENCE_LIBRARY = COLLECTION / "reference-library"
MANIFEST = REFERENCE_LIBRARY / "manifest.json"
COLLECTION_JSON = COLLECTION / "collection.json"
DESIGNS_JSON = COLLECTION / "designs.json"

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWX"
TRANSPARENT = "."

def load_archive():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    names = manifest.get("canonical_archive_parts") or []
    if not names:
        raise SystemExit("Animals reference manifest has no canonical_archive_parts")
    encoded = "".join((REFERENCE_LIBRARY / name).read_text(encoding="ascii").strip() for name in names)
    compressed = base64.b64decode(encoded)
    raw = zlib.decompress(compressed)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest.get("decoded_sha256"):
        raise SystemExit(f"Canonical archive SHA256 mismatch: {digest}")
    data = json.loads(raw.decode("utf-8"))
    return data, raw

def validate(data, collection, designs):
    palette = collection["palette"]
    if len(palette) != 24:
        raise SystemExit(f"Animals palette must contain exactly 24 colours, found {len(palette)}")
    if data["palette_order"] != [str(p["dmc"]) for p in palette]:
        raise SystemExit("Archive palette order does not match collection.json")
    if data["grid"] != {"width": 100, "height": 120, "transparent": "."}:
        raise SystemExit("Unexpected canonical grid definition")
    if len(data["designs"]) != 30 or len(designs["designs"]) != 30:
        raise SystemExit("Animals collection must contain exactly 30 designs")
    allowed = set(CHARS + TRANSPARENT)
    for item in data["designs"]:
        rows = item["rows"]
        if len(rows) != 120 or any(len(row) != 100 for row in rows):
            raise SystemExit(f"{item['base_design_id']}: malformed 100x120 matrix")
        bad = set("".join(rows)) - allowed
        if bad:
            raise SystemExit(f"{item['base_design_id']}: unknown matrix symbols {sorted(bad)}")
        xs=[]; ys=[]
        for y,row in enumerate(rows):
            for x,c in enumerate(row):
                if c != TRANSPARENT:
                    xs.append(x); ys.append(y)
        if not xs:
            raise SystemExit(f"{item['base_design_id']}: empty matrix")
        if min(xs) < 6 or max(xs) > 93 or min(ys) < 6 or max(ys) > 113:
            raise SystemExit(f"{item['base_design_id']}: motif violates 6-cell safe margin")

def render_source(rows, palette):
    rgb = [tuple(int(p["hex"][i:i+2], 16) for i in (1,3,5)) for p in palette]
    img = Image.new("RGBA", (100,120), (0,0,0,0))
    px = img.load()
    for y,row in enumerate(rows):
        for x,c in enumerate(row):
            if c == TRANSPARENT:
                continue
            idx = CHARS.index(c)
            r,g,b = rgb[idx]
            px[x,y] = (r,g,b,255)
    return img

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    data, raw = load_archive()
    collection = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))
    designs = json.loads(DESIGNS_JSON.read_text(encoding="utf-8"))
    validate(data, collection, designs)
    palette = collection["palette"]
    by_id = {d["base_design_id"]: d for d in designs["designs"]}

    source_dir = COLLECTION / "source-designs"
    master_dir = COLLECTION / "reference-masters"
    sheet_dir = COLLECTION / "reference-sheets"
    for d in (source_dir, master_dir, sheet_dir):
        d.mkdir(parents=True, exist_ok=True)

    source_manifest=[]
    master_manifest=[]
    rendered=[]
    for item in data["designs"]:
        did=item["base_design_id"]
        meta=by_id[did]
        src=render_source(item["rows"],palette)
        source_path=source_dir / f"{did}-{meta['slug']}.png"
        src.save(source_path,optimize=True)
        master=src.resize((800,960),Image.Resampling.NEAREST)
        master_path=master_dir / f"{did}-{meta['slug']}-reference.png"
        master.save(master_path,optimize=True)
        source_manifest.append({"base_design_id":did,"slug":meta["slug"],"asset":f"collections/animals/source-designs/{source_path.name}","sha256":sha256(source_path)})
        master_manifest.append({"base_design_id":did,"slug":meta["slug"],"asset":f"collections/animals/reference-masters/{master_path.name}","sha256":sha256(master_path)})
        rendered.append(master)

    sheet_manifest=[]
    for s in range(5):
        sheet=Image.new("RGBA",(1200,960),(0,0,0,0))
        ids=[]
        for j in range(6):
            idx=s*6+j
            im=rendered[idx].resize((400,480),Image.Resampling.NEAREST)
            sheet.alpha_composite(im,((j%3)*400,(j//3)*480))
            ids.append(designs["designs"][idx]["base_design_id"])
        path=sheet_dir/f"animals-reference-sheet-{s+1:02d}.png"
        sheet.save(path,optimize=True)
        sheet_manifest.append({"sheet":s+1,"asset":f"collections/animals/reference-sheets/{path.name}","design_ids":ids,"sha256":sha256(path)})

    (source_dir/"manifest.json").write_text(json.dumps({"collection":"animals","source":"canonical matrix archive","master_grid":{"width":100,"height":120},"palette":"Animals 24-colour collection palette only","transparent_background":True,"designs":source_manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (master_dir/"manifest.json").write_text(json.dumps({"collection":"animals","source":"deterministic 8x render of canonical 100x120 matrices","canvas":{"width":800,"height":960},"transparent_background":True,"designs":master_manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (sheet_dir/"manifest.json").write_text(json.dumps({"collection":"animals","layout":"3x2","sheet_count":5,"transparent_background":True,"sheets":sheet_manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"collection":"animals","designs":len(rendered),"archive_decoded_sha256":hashlib.sha256(raw).hexdigest(),"source_dir":str(source_dir),"master_dir":str(master_dir),"sheet_dir":str(sheet_dir)},indent=2))

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--write",action="store_true",help="Kept for workflow readability; generation always writes outputs.")
    ap.parse_args()
    build()
