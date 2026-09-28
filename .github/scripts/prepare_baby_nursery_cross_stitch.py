#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections" / "baby-nursery"
MANIFEST_PATH = SOURCE_ROOT / "source-manifest.json"
COL_DIR = SYSTEM / "collections" / "baby-nursery"
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
QUEUE_PATH = SYSTEM / "baby_nursery" / "publish_queue.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"

WIDTH = 100
HEIGHT = 120

TITLE_MAP = {
    "teddy-bear": ("Teddy Bear", "Osito de peluche"),
    "bunny": ("Bunny", "Conejito"),
    "elephant": ("Elephant", "Elefante"),
    "giraffe": ("Giraffe", "Jirafa"),
    "lion": ("Lion", "León"),
    "zebra": ("Zebra", "Cebra"),
    "hippo": ("Hippo", "Hipopótamo"),
    "panda": ("Panda", "Panda"),
    "koala": ("Koala", "Koala"),
    "fox": ("Fox", "Zorro"),
    "cottage": ("Cottage", "Casita"),
    "swing-tree": ("Tree Swing", "Árbol con columpio"),
    "flower-bouquet": ("Flower Bouquet", "Ramo de flores"),
    "sunflower": ("Sunflower", "Girasol"),
    "mushroom": ("Mushroom", "Seta"),
    "ladybug": ("Ladybug", "Mariquita"),
    "bee": ("Bee", "Abeja"),
    "butterfly": ("Butterfly", "Mariposa"),
    "snail": ("Snail", "Caracol"),
    "castle": ("Castle", "Castillo"),
    "whale": ("Whale", "Ballena"),
    "dolphin": ("Dolphin", "Delfín"),
    "octopus": ("Octopus", "Pulpo"),
    "clownfish": ("Clownfish", "Pez payaso"),
    "seahorse": ("Seahorse", "Caballito de mar"),
    "long-neck-dinosaur": ("Long-Neck Dinosaur", "Dinosaurio de cuello largo"),
    "triceratops": ("Triceratops", "Triceratops"),
    "t-rex": ("T-Rex", "T-Rex"),
    "stegosaurus": ("Stegosaurus", "Estegosaurio"),
    "baby-dragon": ("Baby Dragon", "Dragón bebé"),
    "deer": ("Deer", "Ciervo"),
    "squirrel": ("Squirrel", "Ardilla"),
    "hedgehog": ("Hedgehog", "Erizo"),
    "raccoon": ("Raccoon", "Mapache"),
    "owl": ("Owl", "Búho"),
    "penguin": ("Penguin", "Pingüino"),
    "seal": ("Seal", "Foca"),
    "frog-prince": ("Frog Prince", "Príncipe rana"),
    "axolotl": ("Axolotl", "Ajolote"),
    "turtle": ("Turtle", "Tortuga"),
    "unicorn": ("Unicorn", "Unicornio"),
    "floral-unicorn": ("Floral Unicorn", "Unicornio floral"),
    "rainbow-clouds": ("Rainbow with Clouds", "Arcoíris con nubes"),
    "sun": ("Sun", "Sol"),
    "moon": ("Moon", "Luna"),
    "star": ("Star", "Estrella"),
    "hanging-cloud": ("Hanging Cloud", "Nube colgante"),
    "hot-air-balloon": ("Hot Air Balloon", "Globo aerostático"),
    "kite": ("Kite", "Cometa"),
    "rocket": ("Rocket", "Cohete"),
    "airplane": ("Airplane", "Avión"),
    "train": ("Toy Train", "Tren de juguete"),
    "car": ("Toy Car", "Coche de juguete"),
    "sailboat": ("Sailboat", "Velero"),
    "baby-blocks": ("Baby Blocks", "Bloques infantiles"),
    "rocking-horse": ("Rocking Horse", "Caballito balancín"),
    "rattle": ("Rattle", "Sonajero"),
    "rubber-duck": ("Rubber Duck", "Patito de goma"),
    "baby-bottle": ("Baby Bottle", "Biberón"),
    "crown": ("Crown", "Corona"),
}

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

manifest = read_json(MANIFEST_PATH)
items = manifest.get("products") or []
if len(items) != 60:
    raise SystemExit(f"Expected 60 Baby Nursery source products, got {len(items)}")

designs = []
queue_items = []
for order, item in enumerate(items, start=1):
    base = str(item["id"])
    slug = str(item["slug"])
    filename = str(item["filename"])
    if not re.fullmatch(r"I\d{4}", base):
        raise SystemExit(f"Invalid id: {base}")
    if order != int(base[1:]):
        raise SystemExit(f"Unexpected order for {base}")
    source = SOURCE_ROOT / "products" / filename
    if not source.is_file():
        raise SystemExit(f"Missing source: {source}")
    if item.get("width") != WIDTH or item.get("height") != HEIGHT:
        raise SystemExit(f"{base}: manifest size mismatch")
    title_en, title_es = TITLE_MAP.get(slug, (slug.replace("-", " ").title(), slug.replace("-", " ").title()))
    code = f"{base}-CS"
    source_rel = f"../source-images/collections/baby-nursery/products/{filename}"
    designs.append({
        "order": order,
        "base_design_id": base,
        "title_en": title_en,
        "title_es": title_es,
        "product_title_en": f"{title_en} Cross Stitch Pattern PDF",
        "product_title_es": f"Patrón PDF de punto de cruz: {title_es}",
        "slug": slug,
        "variants": [code],
        "artwork_status": "approved-source-png-100x120",
        "source_asset": source_rel,
        "input_png": source_rel,
        "palette_mode": "shared-30-source-colours-to-dmc",
        "source_manifest": "../source-images/collections/baby-nursery/source-manifest.json",
    })
    queue_items.append({
        "order": order,
        "base_design_id": base,
        "title_en": title_en,
        "title_es": title_es,
        "slug": slug,
        "input_png": source_rel,
        "status": "pending",
        "attempts": 0,
        "last_run": None,
        "last_error": None,
    })
    write_json(PATTERNS / code / "pattern.json", {
        "code": code,
        "base_design_id": base,
        "technique_code": "CS",
        "collection": "baby-nursery",
        "palette_mode": "shared-30-source-colours-to-dmc",
        "status": "awaiting-source-artwork",
        "source_asset": source_rel,
        "stitch_width": WIDTH,
        "stitch_height": HEIGHT,
        "total_stitches": 0,
        "threads": [],
        "matrix": [],
    })
    write_json(PRODUCTS / code / "product.json", {
        "code": code,
        "base_design_id": base,
        "technique_code": "CS",
        "collection": "baby-nursery",
        "title": f"{title_en} Cross Stitch Pattern PDF",
        "title_en": f"{title_en} Cross Stitch Pattern PDF",
        "title_es": f"Patrón PDF de punto de cruz: {title_es}",
        "design_title_en": title_en,
        "design_title_es": title_es,
        "design_slug": slug,
        "technique": "cross-stitch",
        "pattern_file": f"patterns/{code}/pattern.json",
        "template": "cross-stitch.html",
        "website": "www.drielo.com",
        "status": "draft",
        "render_ready": False,
        "renderer": "multitech",
        "source_artwork": source_rel,
        "page_1_asset": "collections/baby-nursery/assets/cover-cross-stitch.jpg",
        "palette_mode": "shared-30-source-colours-to-dmc",
    })

write_json(DESIGNS_PATH, {
    "collection": "baby-nursery",
    "code_prefix": "I",
    "count": 60,
    "source_policy": "canonical-100x120-transparent-pngs",
    "technique_policy": "cross-stitch-only",
    "designs": designs,
})

write_json(QUEUE_PATH, {
    "collection": "baby-nursery",
    "mode": "cross-stitch-only-manual-preview",
    "auto_continue": False,
    "max_attempts_per_design": 3,
    "items": queue_items,
    "notes": [
        "All Baby Nursery products are cross-stitch only.",
        "Publication is manual until the first approved product is visually reviewed.",
        "Transparent source pixels are treated as empty canvas and are not stitches.",
        "All visible pixels are mapped through the shared 30-colour source palette and then to DMC.",
    ],
})

collection = read_json(COLLECTION_PATH)
collection["design_count"] = 60
collection["techniques"] = ["cross-stitch"]
collection["description"] = "Baby and nursery motifs prepared exclusively as 100 × 120 cross-stitch patterns from approved transparent pixel sources."
collection["description_es"] = "Motivos infantiles preparados exclusivamente como patrones de punto de cruz de 100 × 120 a partir de fuentes transparentes aprobadas."
collection["source_palette"] = "palette30.json"
collection["source_palette_mode"] = "shared-30-colours"
collection["transparent_pixels_are_stitches"] = False
write_json(COLLECTION_PATH, collection)

catalog = read_json(CATALOG_PATH)
catalog["products"] = [p for p in catalog.get("products", []) if p.get("collection") != "baby-nursery"]
coll = next((c for c in catalog.get("collections", []) if c.get("slug") == "baby-nursery"), None)
if coll is not None:
    coll["techniques"] = ["cross-stitch"]
    coll["visible"] = bool(collection.get("visible", False))
    coll["palette_mode"] = "shared-30-source-colours-to-dmc"
write_json(CATALOG_PATH, catalog)

print("BABY_NURSERY_CS_PREPARED designs=60 technique=cross-stitch auto_continue=false")
