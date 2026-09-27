#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "iconic-destinations"
ZIP_REL = "collections/iconic-destinations/assets/iconic-batch-02-90-q50.zip"
ZIP_PATH = SYSTEM / ZIP_REL
INPUT_DIR = COL / "input-pngs-q50" / "batch-02"
DESIGNS_PATH = COL / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"

NAMES = [
"Meteora Monasteries","Lake Bled","Petra Treasury","Angkor Wat","Mont Saint-Michel",
"Hallstatt Lakeside Village","Neuschwanstein Castle","Cinque Terre Village","Bruges Canals","Bagan Temples and Balloons",
"Salar de Uyuni","Ha Long Bay","Pamukkale Terraces","Kotor Bay","Moraine Lake",
"Plitvice Lakes","Giant's Causeway","Cappadocia Balloons","Ait Ben Haddou","Registan Samarkand",
"Hawa Mahal Jaipur","Sheikh Zayed Grand Mosque","Jodhpur Blue City","Rila Monastery","Dubrovnik Old Town",
"Cesky Krumlov","Pena Palace Sintra","Sighisoara Old Town","Rothenburg ob der Tauber","Colmar Canals",
"Bryce Canyon","Antelope Canyon","Monument Valley","Na Pali Coast Kauai","Bora Bora Lagoon",
"Faroe Islands Village","Lofoten Islands","Iceland Black Church Aurora","Geirangerfjord","Torres del Paine",
"Mount Kilimanjaro","Victoria Falls","Chefchaouen Blue City","Lalibela Rock Churches","Zanzibar Stone Town",
"Namib Desert","Avenue of the Baobabs","Blyde River Canyon","Le Morne Mauritius","Great Mosque of Djenne",
"Fushimi Inari Kyoto","Himeji Castle","Jeju Seongsan Ilchulbong","Kathmandu Durbar Square","Luang Prabang Temple",
"Borobudur Temple","Jiufen Old Street","Hong Kong Victoria Harbour","Palawan Lagoons","Gyeongbokgung Palace",
"Yosemite Valley","Horseshoe Bend","Sedona Red Rocks","Chateau Frontenac Quebec","Havana Old Town",
"Cartagena Walled City","Chichen Itza","Tikal Mayan Temples","Easter Island Moai","Golden Gate Bridge",
"Positano Amalfi Coast","Alberobello Trulli","Sete Cidades Azores","Bergen Bryggen","Tallinn Old Town",
"Prague Charles Bridge","Budapest Parliament","Lauterbrunnen Valley","Mostar Old Bridge","Portofino Harbor",
"Wadi Rum","Athens Acropolis","Jerusalem Old City","Machu Picchu","Iguazu Falls",
"Perito Moreno Glacier","Saint Basil Cathedral","Alhambra Granada","Persepolis","Istanbul Blue Mosque",
]

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

if len(NAMES) != 90:
    raise SystemExit("Expected 90 product names")

expected = [f"iconic_{i:03d}.png" for i in range(1, 91)]
INPUT_DIR.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(ZIP_PATH, "r") as zf:
    pngs = [n for n in zf.namelist() if n.lower().endswith(".png")]
    if pngs != expected:
        raise SystemExit(f"ZIP PNG members mismatch: {pngs[:5]} ... count={len(pngs)}")
    for i, member in enumerate(expected, start=1):
        raw = zf.read(member)
        with Image.open(io.BytesIO(raw)) as im:
            rgb = im.convert("RGB")
            colours = len(set(rgb.getdata()))
            if im.format != "PNG" or rgb.size != (100, 120) or colours != 50:
                raise SystemExit(f"{member}: format={im.format} size={rgb.size} colours={colours}")
        out = INPUT_DIR / member
        out.write_bytes(raw)
        if out.read_bytes() != raw:
            raise SystemExit(f"{member}: extracted bytes changed")

designs = read_json(DESIGNS_PATH)
designs["source_policy"] = "individual-pngs-from-approved-clean-batch-zips-only"
existing = {x["base_design_id"]: x for x in designs["designs"]}

for i, name in enumerate(NAMES, start=1):
    n = 60 + i
    base = f"D{n:04d}"
    member = f"iconic_{i:03d}.png"
    slug = f"batch02-{n:04d}-{slugify(name)}"
    input_rel = f"collections/iconic-destinations/input-pngs-q50/batch-02/{member}"
    row = {
        "order": n,
        "base_design_id": base,
        "title_en": name,
        "title_es": name,
        "slug": slug,
        "variants": [f"{base}-CS"],
        "artwork_status": "approved-zip-individual-png-100x120",
        "source_asset": input_rel,
        "palette_mode": "per-design",
        "palette_status": "ready-for-direct-png-dmc-map",
        "target_master_grid": {"width": 100, "height": 120, "max_long_side_stitches": 120},
        "target_chart_pages": 4,
        "source_colour_count": 50,
        "dmc_colour_count": None,
        "input_png": input_rel,
        "source_zip": ZIP_REL,
        "source_zip_member": member,
        "source_style": "vivid-premium-realistic-cross-stitch",
    }
    existing[base] = row

designs["designs"] = sorted(existing.values(), key=lambda x: int(x["base_design_id"][1:]))
designs["count"] = len(designs["designs"])
write_json(DESIGNS_PATH, designs)

queue = read_json(QUEUE_PATH)
qexisting = {x["base_design_id"]: x for x in queue["items"]}
for i, name in enumerate(NAMES, start=1):
    n = 60 + i
    base = f"D{n:04d}"
    member = f"iconic_{i:03d}.png"
    slug = f"batch02-{n:04d}-{slugify(name)}"
    input_rel = f"collections/iconic-destinations/input-pngs-q50/batch-02/{member}"
    qexisting[base] = {
        "base_design_id": base,
        "title_en": name,
        "title_es": name,
        "slug": slug,
        "input_png": input_rel,
        "status": "pending",
        "attempts": 0,
        "last_run": None,
        "last_error": None,
        "source_zip": ZIP_REL,
        "source_zip_member": member,
    }

queue["items"] = sorted(qexisting.values(), key=lambda x: int(x["base_design_id"][1:]))
queue["mode"] = "direct-zip-png-batch02-90-v1"
queue["active_batch"] = "batch-02-90-approved"
queue["auto_continue"] = True
queue["max_attempts_per_design"] = 3
queue["source_zip"] = ZIP_REL
queue["notes"] = [
    "Batch 02 contains 90 user-approved vivid destination PNGs.",
    "Every source PNG is exactly 100x120 pixels and uses exactly 50 colours.",
    "Every extracted PNG is byte-identical to its approved Gmail ZIP member.",
    "D0061-D0150 are the only newly pending designs in this batch.",
]
write_json(QUEUE_PATH, queue)

for i, name in enumerate(NAMES, start=1):
    n = 60 + i
    base = f"D{n:04d}"
    code = f"{base}-CS"
    slug = f"batch02-{n:04d}-{slugify(name)}"
    ppath = PATTERNS / code / "pattern.json"
    prodpath = PRODUCTS / code / "product.json"
    write_json(ppath, {
        "code": code,
        "base_design_id": base,
        "technique_code": "CS",
        "collection": "iconic-destinations",
        "palette_mode": "per-design",
        "status": "awaiting-source-artwork",
        "source_asset": None,
        "stitch_width": 100,
        "stitch_height": 120,
        "total_stitches": 0,
        "threads": [],
        "matrix": [],
    })
    write_json(prodpath, {
        "code": code,
        "base_design_id": base,
        "technique_code": "CS",
        "collection": "iconic-destinations",
        "title": name,
        "title_en": name,
        "title_es": name,
        "design_slug": slug,
        "technique": "cross-stitch",
        "pattern_file": f"patterns/{code}/pattern.json",
        "template": "cross-stitch.html",
        "website": "www.drielo.com",
        "status": "draft",
        "render_ready": False,
        "renderer": "multitech",
        "source_artwork": None,
        "page_1_asset": None,
        "palette_mode": "per-design",
    })

print("BATCH02_IMPORTED designs=90 ids=D0061-D0150 png=100x120 colours=50")
