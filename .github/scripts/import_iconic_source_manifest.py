#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "iconic-destinations"
SOURCE_DIR = COL / "source-images"
MANIFEST_PATH = SOURCE_DIR / "manifest.json"
SCHEMA_REL = "collections/source-images-manifest.schema.json"
SOURCE_MANIFEST_REL = "collections/iconic-destinations/source-images/manifest.json"
ZIP_REL = "collections/iconic-destinations/assets/iconic-current-manifest-source-q50.zip"
ZIP_PATH = SYSTEM / ZIP_REL
INPUT_DIR = COL / "input-pngs-q50" / "current"
DESIGNS_PATH = COL / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PATTERNS = SYSTEM / "patterns"
PRODUCTS = SYSTEM / "products"

WIDTH = 100
HEIGHT = 120
COLOURS = 50


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_manifest():
    doc = read_json(MANIFEST_PATH)
    collection = doc.get("collection") or {}
    spec = doc.get("image_spec") or {}
    items = doc.get("items") or []

    if collection.get("slug") != "iconic-destinations":
        raise SystemExit("Manifest collection slug must be iconic-destinations")
    if len(items) != 100:
        raise SystemExit(f"Expected 100 manifest items, got {len(items)}")
    if spec.get("format") != "PNG" or spec.get("width") != WIDTH or spec.get("height") != HEIGHT:
        raise SystemExit(f"Invalid manifest image spec: {spec}")
    if spec.get("color_count") != COLOURS:
        raise SystemExit(f"Manifest must require exactly {COLOURS} colours")
    if spec.get("palette_mode") != "independent_per_image":
        raise SystemExit("Manifest palette_mode must be independent_per_image")
    if spec.get("dithering") is not False:
        raise SystemExit("Manifest dithering must be false")

    ids, filenames, slugs = set(), set(), set()
    validated = []
    for index, item in enumerate(items, start=1):
        for key in (
            "id", "filename", "slug",
            "title_en", "title_es",
            "product_title_en", "product_title_es",
        ):
            if not str(item.get(key) or "").strip():
                raise SystemExit(f"Manifest item {index} missing {key}")

        base = str(item["id"])
        filename = str(item["filename"])
        slug = str(item["slug"])
        if not re.fullmatch(r"D\d{4}", base):
            raise SystemExit(f"Invalid base id: {base}")
        if not filename.startswith(base + "-") or not filename.endswith(".png"):
            raise SystemExit(f"{base}: invalid filename {filename}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise SystemExit(f"{base}: invalid slug {slug}")
        if base in ids or filename in filenames or slug in slugs:
            raise SystemExit(f"Duplicate manifest identity: {base} / {filename} / {slug}")
        ids.add(base)
        filenames.add(filename)
        slugs.add(slug)

        source = SOURCE_DIR / filename
        if not source.is_file():
            raise SystemExit(f"{base}: missing canonical source image {source}")
        with Image.open(source) as im:
            rgb = im.convert("RGB")
            colour_count = len(set(rgb.getdata()))
            if im.format != "PNG" or rgb.size != (WIDTH, HEIGHT) or colour_count != COLOURS:
                raise SystemExit(
                    f"{base}: invalid source image format={im.format} size={rgb.size} colours={colour_count}"
                )
        if item.get("width") != WIDTH or item.get("height") != HEIGHT:
            raise SystemExit(f"{base}: manifest dimensions disagree with image")
        if item.get("color_count") != COLOURS:
            raise SystemExit(f"{base}: manifest colour count must be {COLOURS}")
        validated.append(item)

    return doc, validated


manifest, items = validate_manifest()

# Build a deterministic approved transport ZIP from the manifest-listed canonical files.
ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for item in items:
        source = SOURCE_DIR / item["filename"]
        zf.write(source, arcname=item["filename"])
    zf.write(MANIFEST_PATH, arcname="manifest.json")

# Staging is generated strictly from the manifest; stale files are not eligible.
if INPUT_DIR.exists():
    shutil.rmtree(INPUT_DIR)
INPUT_DIR.mkdir(parents=True, exist_ok=True)

design_rows = []
queue_rows = []
for order, item in enumerate(items, start=1):
    base = item["id"]
    code = f"{base}-CS"
    source = SOURCE_DIR / item["filename"]
    input_rel = f"collections/iconic-destinations/input-pngs-q50/current/{item['filename']}"
    target = SYSTEM / input_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if target.read_bytes() != source.read_bytes():
        raise SystemExit(f"{base}: staging PNG differs from canonical source image")

    row = {
        "order": order,
        "base_design_id": base,
        "title_en": item["title_en"],
        "title_es": item["title_es"],
        "product_title_en": item["product_title_en"],
        "product_title_es": item["product_title_es"],
        "slug": item["slug"],
        "variants": [code],
        "artwork_status": "approved-manifest-individual-png-100x120",
        "source_asset": input_rel,
        "input_png": input_rel,
        "palette_mode": "per-design",
        "palette_status": "ready-for-direct-png-dmc-map",
        "target_master_grid": {
            "width": WIDTH,
            "height": HEIGHT,
            "max_long_side_stitches": HEIGHT,
        },
        "target_chart_pages": 4,
        "source_colour_count": COLOURS,
        "dmc_colour_count": None,
        "source_manifest": SOURCE_MANIFEST_REL,
        "source_manifest_item": base,
        "source_zip": ZIP_REL,
        "source_zip_member": item["filename"],
        "source_style": "audited-vivid-premium-cross-stitch",
    }
    design_rows.append(row)

    queue_rows.append({
        "base_design_id": base,
        "title_en": item["title_en"],
        "title_es": item["title_es"],
        "product_title_en": item["product_title_en"],
        "product_title_es": item["product_title_es"],
        "slug": item["slug"],
        "input_png": input_rel,
        "status": "pending",
        "attempts": 0,
        "last_run": None,
        "last_error": None,
        "source_manifest": SOURCE_MANIFEST_REL,
        "source_manifest_item": base,
        "source_zip": ZIP_REL,
        "source_zip_member": item["filename"],
    })

    write_json(PATTERNS / code / "pattern.json", {
        "code": code,
        "base_design_id": base,
        "technique_code": "CS",
        "collection": "iconic-destinations",
        "palette_mode": "per-design",
        "status": "awaiting-source-artwork",
        "source_asset": None,
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
        "collection": "iconic-destinations",
        "title": item["product_title_en"],
        "title_en": item["product_title_en"],
        "title_es": item["product_title_es"],
        "design_title_en": item["title_en"],
        "design_title_es": item["title_es"],
        "design_slug": item["slug"],
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
        "source_manifest": SOURCE_MANIFEST_REL,
    })

designs = {
    "collection": "iconic-destinations",
    "code_prefix": "D",
    "count": len(design_rows),
    "source_policy": "individual-pngs-from-approved-clean-batch-zips-only",
    "identity_policy": "manifest-is-source-of-truth-no-title-inference",
    "source_manifest": SOURCE_MANIFEST_REL,
    "source_manifest_schema": SCHEMA_REL,
    "designs": design_rows,
}
write_json(DESIGNS_PATH, designs)

queue = {
    "collection": "iconic-destinations",
    "mode": "direct-zip-png-manifest-v1",
    "active_batch": "manifest-current-100-audited",
    "auto_continue": True,
    "max_attempts_per_design": 3,
    "source_zip": ZIP_REL,
    "source_manifest": SOURCE_MANIFEST_REL,
    "items": queue_rows,
    "notes": [
        "Identity, filename, slug and web titles come only from source-images/manifest.json.",
        "The transport ZIP is generated from the 100 canonical manifest-listed PNGs.",
        "Every source image is exactly 100x120 pixels and exactly 50 colours.",
        "Every staging PNG is byte-identical to its canonical source image.",
        "No title, slug or product identity may be inferred from filename order or image content.",
    ],
}
write_json(QUEUE_PATH, queue)

print(
    "ICONIC_MANIFEST_IMPORT_PREPARED "
    f"designs={len(design_rows)} source_manifest={SOURCE_MANIFEST_REL} "
    f"size={WIDTH}x{HEIGHT} colours={COLOURS}"
)
