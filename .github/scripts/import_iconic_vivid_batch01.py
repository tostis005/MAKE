#!/usr/bin/env python3
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "iconic-destinations"
ZIP_REL = "collections/iconic-destinations/assets/iconic-batch-01-vivid-q50.zip"
ZIP_PATH = SYSTEM / ZIP_REL
INPUT = COL / "input-pngs-q50"
DESIGNS = COL / "designs.json"
QUEUE = SYSTEM / "iconic_destinations" / "publish_queue.json"

BATCH = [
    ("D0031","D0031-paris-eiffel-tower.png","destino_04_01.png"),
    ("D0032","D0032-london-big-ben.png","destino_04_02.png"),
    ("D0033","D0033-rome-colosseum.png","destino_04_03.png"),
    ("D0034","D0034-new-york-statue-liberty.png","destino_04_04.png"),
    ("D0035","D0035-taj-mahal.png","destino_04_05.png"),
    ("D0036","D0036-great-wall-china.png","destino_04_06.png"),
    ("D0037","D0037-rio-christ-redeemer.png","destino_04_07.png"),
    ("D0038","D0038-pyramids-giza.png","destino_04_08.png"),
    ("D0039","D0039-sydney-opera-house.png","destino_04_09.png"),
    ("D0046","D0046-cape-town-table-mountain.png","destino_05_06.png"),
]

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    if not ZIP_PATH.exists():
        raise SystemExit(f"Missing vivid ZIP: {ZIP_PATH}")
    INPUT.mkdir(parents=True, exist_ok=True)

    expected_members = [m for _,m,_ in BATCH]
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        all_names = zf.namelist()
        names = [n for n in all_names if n.lower().endswith(".png")]
        if names != expected_members:
            raise SystemExit(f"ZIP PNG members mismatch: {names}")
        for base, member, input_name in BATCH:
            raw = zf.read(member)
            target = INPUT / input_name
            target.write_bytes(raw)
            with Image.open(target) as im:
                rgb = im.convert("RGB")
                colours = len(set(rgb.getdata()))
                if rgb.size != (100,120):
                    raise SystemExit(f"{base}: expected 100x120, got {rgb.size}")
                if colours != 50:
                    raise SystemExit(f"{base}: expected exactly 50 colours, got {colours}")
            if target.read_bytes() != raw:
                raise SystemExit(f"{base}: extracted bytes differ from ZIP")
            print(f"VIVID_SOURCE_OK {base} 100x120 50-colours")

    designs_doc = read_json(DESIGNS)
    designs_doc["source_policy"] = "individual-pngs-from-approved-clean-batch-zips-only"
    by_id = {d["base_design_id"]: d for d in designs_doc["designs"]}
    for base, member, input_name in BATCH:
        rel = f"collections/iconic-destinations/input-pngs-q50/{input_name}"
        d = by_id[base]
        d.update({
            "input_png": rel,
            "source_asset": rel,
            "source_zip": ZIP_REL,
            "source_zip_member": member,
            "artwork_status": "approved-vivid-premium-zip-png-100x120-q50",
            "palette_mode": "per-design",
            "palette_status": "ready-for-direct-png-dmc-map",
            "source_colour_count": 50,
            "source_style": "vivid-premium-realistic-cross-stitch",
            "target_master_grid": {"width":100,"height":120,"max_long_side_stitches":120},
            "target_chart_pages": 4,
        })
        for k in ("source_reference_file","source_reference_license","source_pdf","source_pdf_page",
                  "reference_board","planned_source_asset","preview_mosaic","mosaic_source",
                  "mosaic_crop","board_source"):
            d.pop(k, None)
    write_json(DESIGNS, designs_doc)

    queue = read_json(QUEUE)
    active = {b for b,_,_ in BATCH}
    queue["mode"] = "direct-zip-png-vivid-batch-v5"
    queue["active_batch"] = "batch-01-vivid-premium"
    queue["auto_continue"] = True
    queue["source_zip"] = ZIP_REL
    queue["notes"] = [
        "Batch 01 source is the approved vivid premium ZIP committed to GitHub.",
        "Every source PNG is exactly 100x120 pixels and uses exactly 50 colours.",
        "ZIP member and extracted input PNG are byte-identical.",
        "These files replace all prior conceptual/procedural batch-01 artwork."
    ]
    for row in queue["items"]:
        if row["base_design_id"] in active:
            base, member, input_name = next(x for x in BATCH if x[0] == row["base_design_id"])
            row.update({
                "input_png": f"collections/iconic-destinations/input-pngs-q50/{input_name}",
                "source_zip": ZIP_REL,
                "source_zip_member": member,
                "status": "pending",
                "attempts": 0,
                "last_run": None,
                "last_error": None,
            })
            row.pop("published_at", None)
            row.pop("product_id", None)
        elif row.get("status") in ("pending","failed"):
            row["status"] = "held"
    write_json(QUEUE, queue)
    print("VIVID_BATCH01_IMPORTED count=10 pending=10 held=50")

if __name__ == "__main__":
    main()
