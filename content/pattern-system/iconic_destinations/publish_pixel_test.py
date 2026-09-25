#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "iconic-destinations"
COL_DIR = SYSTEM / "collections" / COLLECTION_ID
COLLECTION_PATH = COL_DIR / "collection.json"
SOURCE = COL_DIR / "approved-pixel-designs" / "D0001-paris-eiffel-tower.png"
PATTERN_PATH = SYSTEM / "patterns" / "D0001-CS" / "pattern.json"
PRODUCT_PATH = SYSTEM / "products" / "D0001-CS" / "product.json"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
MOCKUP = COL_DIR / "assets" / "iconic-room.jpg"

sys.path.insert(0, str((SYSTEM / "pixel_importer").resolve()))
import import_pixel_sheet as pixel  # noqa: E402

sys.path.insert(0, str((SYSTEM / "renderer").resolve()))
import render as renderer  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configure_collection_mockup():
    if not MOCKUP.is_file():
        raise FileNotFoundError(f"Missing collection mockup: {MOCKUP}")

    collection = read_json(COLLECTION_PATH)
    collection["mockup_spec"] = {
        "asset": "assets/iconic-room.jpg",
        "technique_assets": {"CS": "assets/iconic-room.jpg"},
        "status": "pixel-test-positioning",
        "generation": {
            "purpose": "Iconic Destinations reusable cross-stitch lifestyle mockup.",
            "frame_requirement": "Keep the central wooden frame empty; renderer inserts the exact vector stitch pattern.",
            "post_generation_measurement": "First positioning test; artwork shifted about 2 mm upward for review."
        },
        "frame": {
            "enabled": True,
            "source_px": {"width": 256, "height": 256},
            "area_px": {
                "x": 70,
                "y": 29,
                "width": 119,
                "height": 143
            },
            "padding_ratio": 0.010,
            "stitch_offset_x_ratio": 0.0,
            "stitch_offset_y_ratio": -0.014,
            "fabric": {
                "color": "#F7F3EA",
                "kind": "aida",
                "count_visual_reference": 14
            }
        }
    }
    write_json(COLLECTION_PATH, collection)


def build_exact_d0001():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    image = pixel.read_image(SOURCE)
    if image.size != (100, 120):
        raise RuntimeError(f"D0001 exact source must be 100x120, got {image.size}")

    pattern = pixel.build_exact_pattern(image, "D0001-CS", "Paris Eiffel Tower")
    pixel.validate_exact_roundtrip(image, pattern)
    pattern.update({
        "base_design_id": "D0001",
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "palette_mode": "per-design",
        "status": "ready",
        "source_mode": "pixel-exact",
        "source_asset": "collections/iconic-destinations/approved-pixel-designs/D0001-paris-eiffel-tower.png",
        "pixel_to_stitch": "1:1",
        "colour_mapping": "exact-rgb-no-quantization",
    })
    write_json(PATTERN_PATH, pattern)

    product = read_json(PRODUCT_PATH)
    product.update({
        "code": "D0001-CS",
        "base_design_id": "D0001",
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "title": "Paris Eiffel Tower",
        "title_en": "Paris Eiffel Tower",
        "title_es": "París — Torre Eiffel",
        "design_slug": "paris-eiffel-tower",
        "technique": "cross-stitch",
        "pattern_file": "patterns/D0001-CS/pattern.json",
        "website": "www.drielo.com",
        "status": "ready",
        "render_ready": True,
        "renderer": "standard",
        "source_artwork": pattern["source_asset"],
        "palette_mode": "per-design",
        "source_mode": "pixel-exact",
    })
    write_json(PRODUCT_PATH, product)
    return pattern


def update_catalog(pattern):
    catalog = read_json(CATALOG_PATH)
    existing_iconic = [
        row for row in catalog.get("products", [])
        if row.get("collection") == COLLECTION_ID
    ]
    retired = set(catalog.get("retired_products", []))
    retired.update(
        row.get("sku") for row in existing_iconic
        if row.get("sku")
    )

    template = next(
        (row for row in existing_iconic if row.get("code") == "D0001-CS"),
        None,
    )
    if template is None:
        raise RuntimeError("D0001-CS catalog row not found")

    colours = len(pattern["threads"])
    row = dict(template)
    row.update({
        "code": "D0001-CS",
        "sku": "DRIELO-D0001-CS",
        "price": 2.99,
        "title": "Paris Eiffel Tower Cross Stitch Pattern PDF",
        "title_en": "Paris Eiffel Tower Cross Stitch Pattern PDF",
        "title_es": "Patrón PDF de punto de cruz: París — Torre Eiffel",
        "slug": "paris-eiffel-tower-cross-stitch-pattern",
        "collection": COLLECTION_ID,
        "stitches": 12000,
        "grid": "100 × 120 stitches",
        "colours": colours,
        "color_count": colours,
        "grid_width": 100,
        "grid_height": 120,
        "skill": "Intermediate",
        "skill_en": "Intermediate",
        "skill_es": "Intermedio",
        "stitch_type": "Full cross stitch",
        "stitch_type_en": "Full cross stitch",
        "stitch_type_es": "Punto de cruz completo",
        "short_description": (
            f"Downloadable Paris Eiffel Tower cross-stitch pattern. "
            f"Exact 100 × 120 pixel-to-stitch chart; {colours} exact source colours; "
            "one source pixel equals one full cross stitch. Code: D0001-CS."
        ),
        "short_description_en": (
            f"Downloadable Paris Eiffel Tower cross-stitch pattern. "
            f"Exact 100 × 120 pixel-to-stitch chart; {colours} exact source colours; "
            "one source pixel equals one full cross stitch. Code: D0001-CS."
        ),
        "short_description_es": (
            f"Patrón descargable de la Torre Eiffel de París. "
            f"Gráfico exacto 100 × 120; {colours} colores exactos de la imagen; "
            "cada píxel equivale a una puntada completa. Código: D0001-CS."
        ),
        "description": (
            "<p><strong>Paris Eiffel Tower Cross Stitch Pattern PDF</strong>.</p>"
            "<p>Pixel-by-pixel edition: every source pixel is one full cross stitch. "
            "The pattern is generated without resizing, colour reduction, smoothing or DMC remapping.</p>"
            f"<ul><li>Grid: 100 × 120 stitches</li><li>Total stitches: 12,000</li>"
            f"<li>Exact source colours: {colours}</li></ul>"
            "<p>The PDF includes the finished preview, exact colour key, colour charts and black-and-white symbol charts.</p>"
        ),
        "description_en": (
            "<p><strong>Paris Eiffel Tower Cross Stitch Pattern PDF</strong>.</p>"
            "<p>Pixel-by-pixel edition: every source pixel is one full cross stitch. "
            "The pattern is generated without resizing, colour reduction, smoothing or DMC remapping.</p>"
            f"<ul><li>Grid: 100 × 120 stitches</li><li>Total stitches: 12,000</li>"
            f"<li>Exact source colours: {colours}</li></ul>"
            "<p>The PDF includes the finished preview, exact colour key, colour charts and black-and-white symbol charts.</p>"
        ),
        "description_es": (
            "<p><strong>París — Torre Eiffel: patrón PDF de punto de cruz</strong>.</p>"
            "<p>Edición píxel a píxel: cada píxel de la imagen fuente corresponde exactamente a una puntada completa. "
            "No se redimensiona, reduce, suaviza ni remapea la paleta.</p>"
            f"<ul><li>Cuadrícula: 100 × 120</li><li>Puntadas: 12.000</li>"
            f"<li>Colores exactos: {colours}</li></ul>"
            "<p>El PDF incluye vista previa, clave de colores exactos, gráficos a color y gráficos en blanco y negro con símbolos.</p>"
        ),
        "download": "files/Drielo_D0001-CS.pdf",
        "featured_image": "assets/D0001-CS-product.webp",
        "gallery": [],
        "gallery_revision": 20260925,
        "design_id": "D0001-CS",
        "base_design_id": "D0001",
        "technique_code": "CS",
        "technique": "cross-stitch",
        "size_attribute_label": "Pattern size",
        "colour_attribute_label": "Exact colours",
        "type_attribute_label": "Technique",
        "count_attribute_label": "Total stitches",
    })

    catalog["products"] = [
        p for p in catalog.get("products", [])
        if p.get("collection") != COLLECTION_ID
    ]
    catalog["products"].append(row)
    catalog["retired_products"] = sorted(retired)

    coll = next(
        c for c in catalog.get("collections", [])
        if c.get("slug") == COLLECTION_ID
    )
    coll["cover_asset"] = "assets/D0001-CS-product.webp"
    coll["palette_mode"] = "per-design"
    coll["show_collection_palette"] = False
    coll["palette_hex"] = []
    coll["thread_codes"] = []
    coll["techniques"] = ["cross-stitch"]

    write_json(CATALOG_PATH, catalog)
    return [r.get("sku") for r in existing_iconic if r.get("sku")]


def render_and_stage():
    pdf = renderer.render("D0001-CS", fix=False)
    output = SYSTEM / "output" / "D0001-CS"
    image = output / "D0001-CS-product.webp"
    if not image.is_file():
        raise RuntimeError("Featured product image was not rendered")

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image, STORE_ASSETS / image.name)
    shutil.copy2(pdf, STORE_FILES / pdf.name)

    if pdf.stat().st_size < 10000 or pdf.read_bytes()[:4] != b"%PDF":
        raise RuntimeError("Invalid D0001 PDF")
    if image.stat().st_size < 10000:
        raise RuntimeError("Invalid D0001 featured image")
    return pdf, image


def main():
    configure_collection_mockup()
    pattern = build_exact_d0001()
    retired = update_catalog(pattern)
    pdf, image = render_and_stage()

    source = pixel.read_image(SOURCE)
    saved = read_json(PATTERN_PATH)
    pixel.validate_exact_roundtrip(source, saved)

    print(json.dumps({
        "product": "D0001-CS",
        "grid": [100, 120],
        "stitches": 12000,
        "exact_colours": len(pattern["threads"]),
        "retire_from_live_collection": retired,
        "mockup": str(MOCKUP),
        "frame_test": {
            "area_px": [70, 29, 119, 143],
            "stitch_offset_y_ratio": -0.014,
            "intent": "approximately 2 mm upward"
        },
        "pdf": str(pdf),
        "featured_image": str(image),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
