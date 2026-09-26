#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "iconic-destinations"
ASSETS = COL / "assets"
INPUT = COL / "input-pngs-q50"
DESIGNS = COL / "designs.json"
QUEUE = SYSTEM / "iconic_destinations" / "publish_queue.json"

W, H = 100, 120
ZIP_REL = "collections/iconic-destinations/assets/iconic-batch-01-clean-q50.zip"
ZIP_PATH = SYSTEM / ZIP_REL

# All sources below are Wikimedia Commons photographs released under CC0.
# Focal points are normalized (x,y) and preserve the landmark during the 5:6 crop.
BATCH = [
    dict(base="D0031", slug="paris-eiffel-tower", member="D0031-paris-eiffel-tower.png",
         input="destino_04_01.png", file="The Eiffel Tower in Paris.jpg", focal=(0.50,0.53)),
    dict(base="D0032", slug="london-big-ben", member="D0032-london-big-ben.png",
         input="destino_04_02.png", file="Big Ben Dec 2025.jpg", focal=(0.52,0.48)),
    dict(base="D0033", slug="rome-colosseum", member="D0033-rome-colosseum.png",
         input="destino_04_03.png", file="Colosseum, Rome.jpg", focal=(0.52,0.58)),
    dict(base="D0034", slug="new-york-statue-liberty", member="D0034-new-york-statue-liberty.png",
         input="destino_04_04.png", file="Statue of Liberty 2011.jpg", focal=(0.50,0.50)),
    dict(base="D0035", slug="taj-mahal", member="D0035-taj-mahal.png",
         input="destino_04_05.png", file="Taj-Mahal CC0.jpg", focal=(0.50,0.52)),
    dict(base="D0036", slug="great-wall-china", member="D0036-great-wall-china.png",
         input="destino_04_06.png", file="Great Wall of China at Jinshanling 1.jpg", focal=(0.53,0.55)),
    dict(base="D0037", slug="rio-christ-redeemer", member="D0037-rio-christ-redeemer.png",
         input="destino_04_07.png", file="Christ the Redeemer on Corcovado Mountain, Rio de Janeiro, Brazil.jpg", focal=(0.50,0.45)),
    dict(base="D0038", slug="pyramids-giza", member="D0038-pyramids-giza.png",
         input="destino_04_08.png", file="Pyramids of Giza Egypt.png", focal=(0.50,0.55)),
    dict(base="D0039", slug="sydney-opera-house", member="D0039-sydney-opera-house.png",
         input="destino_04_09.png", file="Sydney Opera House, Sydney, Australia (Unsplash fLEw4UdS0D0).jpg", focal=(0.46,0.56)),
    dict(base="D0046", slug="cape-town-table-mountain", member="D0046-cape-town-table-mountain.png",
         input="destino_05_06.png", file="Cape Town - Table Mountain seen from Waterfront (1).jpg", focal=(0.50,0.50)),
]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def commons_url(filename: str) -> str:
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename, safe="") + "?width=1800"

def fetch_photo(filename: str) -> Image.Image:
    req = urllib.request.Request(
        commons_url(filename),
        headers={"User-Agent":"DrieloPatternBuilder/1.0 (GitHub Actions; photoreal cross-stitch source build)"}
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read()
    if len(raw) < 20_000:
        raise RuntimeError(f"{filename}: suspiciously small download ({len(raw)} bytes)")
    return Image.open(io.BytesIO(raw)).convert("RGB")

def crop_5x6(im: Image.Image, focal: tuple[float,float]) -> Image.Image:
    target_ratio = W / H
    sw, sh = im.size
    source_ratio = sw / sh
    fx, fy = focal
    if source_ratio > target_ratio:
        crop_h = sh
        crop_w = int(round(sh * target_ratio))
    else:
        crop_w = sw
        crop_h = int(round(sw / target_ratio))
    cx = fx * sw
    cy = fy * sh
    left = max(0, min(sw - crop_w, int(round(cx - crop_w/2))))
    top = max(0, min(sh - crop_h, int(round(cy - crop_h/2))))
    return im.crop((left, top, left+crop_w, top+crop_h))

def make_pattern_source(im: Image.Image, focal: tuple[float,float]) -> Image.Image:
    im = crop_5x6(im, focal)
    # Mild photographic enhancement before reduction: retain local contrast and texture
    # without producing the cartoon/pixel-art look of the previous generator.
    im = ImageOps.autocontrast(im, cutoff=0.4)
    im = ImageEnhance.Color(im).enhance(1.05)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Sharpness(im).enhance(1.15)
    im = im.resize((W,H), Image.Resampling.LANCZOS)
    # Median-cut palette keeps broad photographic shading while guaranteeing that
    # every stitch/pixel is one exact palette colour. No alpha/gradients remain.
    q = im.quantize(colors=50, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    rgb = q.convert("RGB")
    colours = len(set(rgb.getdata()))
    if not (45 <= colours <= 50):
        raise RuntimeError(f"photographic quantization produced {colours} colours, expected ~50")
    # Save indexed PNG to make the palette explicit.
    return q

def main():
    INPUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    tmp = COL / "_photoreal_batch01"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    source_manifest = []
    generated = {}
    for row in BATCH:
        photo = fetch_photo(row["file"])
        out = make_pattern_source(photo, row["focal"])
        path = tmp / row["member"]
        out.save(path, format="PNG", optimize=True)
        with Image.open(path) as chk:
            rgb = chk.convert("RGB")
            colours = len(set(rgb.getdata()))
            if rgb.size != (W,H) or not (45 <= colours <= 50):
                raise RuntimeError(f"{row['base']}: invalid PNG {rgb.size=} {colours=}")
        generated[row["base"]] = path
        source_manifest.append({
            "base_design_id": row["base"],
            "source": row["file"],
            "source_url": commons_url(row["file"]),
            "license": "CC0 1.0",
            "focal": list(row["focal"]),
            "output": row["member"],
            "width": W,
            "height": H,
            "colour_count": colours,
        })
        print(f"PHOTO_SOURCE_OK {row['base']} size=100x120 colours={colours} source={row['file']}")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for row in BATCH:
            zf.write(generated[row["base"]], row["member"])

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        if set(zf.namelist()) != {x["member"] for x in BATCH}:
            raise RuntimeError("ZIP member set mismatch")
        for row in BATCH:
            raw = zf.read(row["member"])
            target = INPUT / row["input"]
            target.write_bytes(raw)
            if target.read_bytes() != raw:
                raise RuntimeError(f"{row['base']}: extracted input differs from ZIP member")

    (ASSETS / "iconic-batch-01-photoreal-sources.json").write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
    )

    designs_doc = load_json(DESIGNS)
    designs_doc["source_policy"] = "individual-pngs-from-approved-clean-batch-zips-only"
    by_id = {x["base_design_id"]: x for x in designs_doc["designs"]}
    for row in BATCH:
        d = by_id[row["base"]]
        rel = f"collections/iconic-destinations/input-pngs-q50/{row['input']}"
        with Image.open(INPUT / row["input"]) as im:
            colour_count = len(set(im.convert("RGB").getdata()))
        d.update({
            "input_png": rel,
            "source_asset": rel,
            "source_zip": ZIP_REL,
            "source_zip_member": row["member"],
            "artwork_status": "approved-photoreal-cc0-zip-png-100x120",
            "palette_mode": "per-design",
            "palette_status": "ready-for-direct-png-dmc-map",
            "source_colour_count": colour_count,
            "source_style": "photographic-hyperreal-within-grid",
            "source_reference_file": row["file"],
            "source_reference_license": "CC0-1.0",
            "target_master_grid": {"width":100,"height":120,"max_long_side_stitches":120},
            "target_chart_pages": 4,
        })
        for k in ("reference_board","planned_source_asset","preview_mosaic","mosaic_source","mosaic_crop","board_source","source_pdf","source_pdf_page"):
            d.pop(k, None)
    save_json(DESIGNS, designs_doc)

    queue = load_json(QUEUE)
    active = {x["base"] for x in BATCH}
    queue["mode"] = "direct-zip-png-clean-batches-v4"
    queue["auto_continue"] = True
    queue["active_batch"] = "batch-01-photoreal"
    queue["source_zip"] = ZIP_REL
    queue["notes"] = [
        "Batch 01 is rebuilt from CC0 photographic landmark sources, not procedural pixel art.",
        "Each final source PNG is exactly 100x120 and uses approximately 50 discrete colours.",
        "The ZIP member is the authoritative product artwork source and byte identity is validated before publishing.",
        "Mosaic, PDF-page and board-crop artwork sources remain forbidden.",
    ]
    for qrow in queue["items"]:
        if qrow["base_design_id"] in active:
            row = next(x for x in BATCH if x["base"] == qrow["base_design_id"])
            qrow.update({
                "input_png": f"collections/iconic-destinations/input-pngs-q50/{row['input']}",
                "source_zip": ZIP_REL,
                "source_zip_member": row["member"],
                "status": "pending",
                "attempts": 0,
                "last_run": None,
                "last_error": None,
            })
        elif qrow.get("status") in ("pending","failed"):
            qrow["status"] = "held"
    save_json(QUEUE, queue)

    shutil.rmtree(tmp, ignore_errors=True)
    print("PHOTOREAL_BATCH01_READY count=10 grid=100x120 max_colours=50")

if __name__ == "__main__":
    main()
