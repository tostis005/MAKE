#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
CID = "pop-art-25"
SYSTEM = ROOT / "content" / "pattern-system"
CDIR = SYSTEM / "collections" / CID
ZIP_PATH = ROOT / "tmp" / "pop-art-60-upload" / "pop_art_60_png_100x120_exact30.zip"
SOURCE_GMAIL_MESSAGE_ID = "1a0e2264a0410f68"
REWORK = CDIR / "rework-60"
INPUT = REWORK / "input"
MARKER = REWORK / "processed.json"
SOURCES = CDIR / "sources"
PRODUCTS_DIR = SYSTEM / "products"
PATTERNS_DIR = SYSTEM / "patterns"
CATALOG = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
APPROVED_BACKGROUND = STORE_ASSETS / "pop-art-25-collection-cover.webp"
APPROVED_BACKGROUND_SOURCE_COMMIT = "58e89fb2e14a02eca6ee7a3700a17cc099d21fed"

DESIGN_TITLES = [
    ("Glam Blonde Icon", "Icono rubia glam"),
    ("Elegant Bubble Gum Brunette", "Morena elegante con chicle"),
    ("Rockabilly Singer Portrait", "Retrato de cantante rockabilly"),
    ("Floral Crown Artist", "Artista con corona floral"),
    ("Wild-Haired Scientist", "Científico de cabello alborotado"),
    ("Crowned Royal Portrait", "Retrato real con corona"),
    ("Lightning Glam Rocker", "Rocker glam con rayo"),
    ("Round Glasses Musician", "Músico con gafas redondas"),
    ("Moustached Stage Singer", "Cantante de escenario con bigote"),
    ("Curly-Haired Pop Performer", "Artista pop de cabello rizado"),
    ("Bowler Hat Comedian", "Comediante con bombín"),
    ("Classic Renaissance Lady", "Dama clásica renacentista"),
    ("Elegant Sunglasses Lady", "Dama elegante con gafas"),
    ("Rebel Movie Star", "Estrella rebelde de cine"),
    ("Heart Glasses Blonde", "Rubia con gafas de corazón"),
    ("Pearl Earring Girl", "Joven con pendiente de perla"),
    ("Bubble Gum Blonde", "Rubia con chicle"),
    ("Surreal Moustache Artist", "Artista surrealista con bigote"),
    ("Royal Tiara Lady", "Dama real con tiara"),
    ("Smiling Elder Statesman", "Estadista sonriente"),
    ("Floral Crown Profile", "Perfil con corona floral"),
    ("Riveter Heroine", "Heroína obrera"),
    ("Reggae Singer", "Cantante de reggae"),
    ("Surprised Blonde", "Rubia sorprendida"),
    ("Headscarf Sunglasses Lady", "Dama con pañuelo y gafas"),
    ("White-Haired Pop Artist", "Artista pop de cabello blanco"),
    ("Rockabilly Profile", "Perfil rockabilly"),
    ("Blue-Haired Comic Lady", "Dama comic de cabello azul"),
    ("Apple Face Surreal Gentleman", "Caballero surrealista de la manzana"),
    ("Dark-Haired Glamour Lady", "Dama glam de cabello oscuro"),
    ("Liberty Pop Icon", "Icono pop de la libertad"),
    ("Heart Glasses Cat", "Gato con gafas de corazón"),
    ("Shh Bob Hair Lady", "Dama bob haciendo silencio"),
    ("Red-Bearded Painter with Sunflowers", "Pintor pelirrojo con girasoles"),
    ("Crying Blonde Comic", "Rubia comic llorando"),
    ("Elegant Profile Lady", "Dama elegante de perfil"),
    ("Bubble Gum Blonde Portrait", "Retrato de rubia con chicle"),
    ("Sunglasses Rebel Man", "Hombre rebelde con gafas"),
    ("Egyptian Queen", "Reina egipcia"),
    ("Western Cowboy", "Vaquero del oeste"),
    ("Heart Sunglasses Glam Blonde", "Rubia glam con gafas de corazón"),
    ("Round Glasses Rocker", "Rocker con gafas redondas"),
    ("Sunglasses Bulldog", "Bulldog con gafas"),
    ("Winking Blonde", "Rubia guiñando un ojo"),
    ("Polka Scarf Cat-Eye Lady", "Dama con pañuelo de lunares"),
    ("Comic Superhero", "Superhéroe comic"),
    ("Warrior Heroine", "Heroína guerrera"),
    ("Young Rockabilly Man", "Joven rockabilly"),
    ("Hibiscus Glamour Lady", "Dama glam con hibisco"),
    ("Oversized Sunglasses Fashion Lady", "Dama fashion con gafas grandes"),
    ("Red-Haired Crying Comic", "Pelirroja comic llorando"),
    ("Bubble Gum Blonde Profile", "Perfil rubio con chicle"),
    ("Afro Sunglasses Lady", "Dama afro con gafas"),
    ("Punk Rocker", "Rocker punk"),
    ("Royal Blonde with Tiara", "Rubia real con tiara"),
    ("Bearded Hat and Glasses Man", "Hombre barbudo con sombrero y gafas"),
    ("POP Comic Burst", "Explosión comic POP"),
    ("Tropical Flower Glamour Lady", "Dama glam con flor tropical"),
    ("Pop Art Tiger", "Tigre Pop Art"),
    ("Pink Pop Lips", "Labios pop rosas"),
]

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

DESIGNS = [
    (f"P{1000+i:04d}", en, es, f"pop-art-{i:02d}-{slugify(en)}")
    for i, (en, es) in enumerate(DESIGN_TITLES, start=1)
]

EXPECTED_CODES = {f"P{1000+i:04d}-CS" for i in range(1, 61)}

def zip_sha() -> str:
    if not ZIP_PATH.is_file():
        raise SystemExit(f"Missing source ZIP: {ZIP_PATH}")
    h = hashlib.sha256()
    with ZIP_PATH.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def background_sha() -> str:
    if not APPROVED_BACKGROUND.is_file():
        raise SystemExit(f"Missing approved Pop Art background: {APPROVED_BACKGROUND}")
    h = hashlib.sha256()
    with APPROVED_BACKGROUND.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def catalogue_has_current_generation() -> bool:
    if not CATALOG.is_file():
        return False
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except Exception:
        return False
    codes = {p.get("code") for p in data.get("products", []) if p.get("collection") == CID}
    if codes != EXPECTED_CODES:
        return False
    for p in data.get("products", []):
        if p.get("code") not in EXPECTED_CODES:
            continue
        if not (ROOT / "content" / "products" / p.get("featured_image", "")).is_file():
            return False
        for rel in p.get("gallery", []):
            if not (ROOT / "content" / "products" / rel).is_file():
                return False
    return True

def needs_rebuild() -> bool:
    digest = zip_sha()
    if not MARKER.is_file():
        return True
    try:
        marker = json.loads(MARKER.read_text(encoding="utf-8"))
    except Exception:
        return True
    # Rebuild whenever either the 60-design source ZIP or the approved Pop Art
    # room/background image changes. This prevents product renders from silently
    # reusing an older generic background.
    return (
        marker.get("zip_sha256") != digest
        or marker.get("background_sha256") != background_sha()
        or not catalogue_has_current_generation()
    )

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def extract_and_verify():
    from PIL import Image

    if INPUT.exists():
        shutil.rmtree(INPUT)
    INPUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        safe = []
        for info in zf.infolist():
            name = Path(info.filename).name
            if name != info.filename or not name:
                continue
            if name == "manifest.json" or re.fullmatch(r"pop_art_\d{2}\.png", name) or name == "pop_art_60_mosaico_1000x720_exact30.png":
                safe.append(info)
        zf.extractall(INPUT, members=safe)

    files = [INPUT / f"pop_art_{i:02d}.png" for i in range(1, 61)]
    missing = [p.name for p in files if not p.is_file()]
    if missing:
        raise RuntimeError(f"Missing PNGs in ZIP: {missing}")

    colours = set()
    for p in files:
        im = Image.open(p).convert("RGB")
        if im.size != (100, 120):
            raise RuntimeError(f"{p.name}: expected 100x120, got {im.size}")
        colours.update(im.getdata())
    if len(colours) != 30:
        raise RuntimeError(f"ZIP has {len(colours)} RGB colours; expected exactly 30")

    manifest_path = INPUT / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("ZIP has no manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("design_count", 0)) != 60:
        raise RuntimeError("Manifest design_count is not 60")
    if int(manifest.get("shared_palette_size", 0)) != 30:
        raise RuntimeError("Manifest shared_palette_size is not 30")

    return files, colours, manifest

def clean_old_pop_art():
    # Remove old source generation and obsolete generated pattern-system records.
    shutil.rmtree(CDIR / "rework-30", ignore_errors=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    for p in SOURCES.glob("P*.png"):
        p.unlink()

    def old_or_new_base(name: str) -> bool:
        m = re.match(r"P(\d{4})", name)
        if not m:
            return False
        n = int(m.group(1))
        return 1 <= n <= 26 or 1001 <= n <= 1060

    for parent in (PRODUCTS_DIR, PATTERNS_DIR):
        if not parent.exists():
            continue
        for p in list(parent.iterdir()):
            if p.is_dir() and old_or_new_base(p.name):
                shutil.rmtree(p)

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    for p in list(STORE_ASSETS.iterdir()):
        if p.is_file() and old_or_new_base(p.name):
            p.unlink()

    STORE_FILES.mkdir(parents=True, exist_ok=True)
    for p in list(STORE_FILES.glob("Drielo_P*.pdf")):
        m = re.match(r"Drielo_P(\d{4})", p.name)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 26 or 1001 <= n <= 1060:
                p.unlink()

def make_cover(mosaic_path: Path):
    from PIL import Image, ImageOps
    with Image.open(mosaic_path) as im:
        im = im.convert("RGB")
        # Storefront cover: preserve full mosaic, with a small clean border.
        canvas = Image.new("RGB", (1200, 864), "white")
        fitted = ImageOps.contain(im, (1160, 824), Image.Resampling.NEAREST)
        canvas.paste(fitted, ((1200-fitted.width)//2, (864-fitted.height)//2))
        canvas.save(STORE_ASSETS / "pop-art-25-collection-cover.webp", "WEBP", quality=92, method=6)

def main() -> None:
    if not needs_rebuild():
        print("POP_ART_60_ALREADY_CURRENT")
        return

    from PIL import Image

    files, colours, manifest = extract_and_verify()
    digest = zip_sha()
    clean_old_pop_art()

    base = load_module("drielo_pop30_base", ROOT / ".github" / "scripts" / "rebuild_pop_art_30.py")
    base.STAGED = INPUT
    base.SOURCES = SOURCES
    base.DESIGNS = DESIGNS

    palette_rgb = [tuple(int(v) for v in row) for row in manifest["palette_rgb"]]
    if len(palette_rgb) != 30 or set(palette_rgb) != colours:
        raise RuntimeError("Manifest palette does not exactly match PNG RGB union")
    palette = base.build_palette(palette_rgb)

    # Promote the exact Gmail/GitHub ZIP tiles to the official collection sources.
    for i, (code, _en, _es, _slug) in enumerate(DESIGNS, start=1):
        shutil.copy2(INPUT / f"pop_art_{i:02d}.png", SOURCES / f"{code}.png")

    collection = {
        "id": CID,
        "name": "Retratos Pop Art",
        "name_en": "Pop Art Portraits",
        "name_es": "Retratos Pop Art",
        "slug": CID,
        "code_prefix": "P",
        "description": "60 vivid Pop Art portrait designs built from one verified shared palette of exactly 30 colours.",
        "description_en": "60 vivid Pop Art portrait designs built from one verified shared palette of exactly 30 colours.",
        "description_es": "60 retratos Pop Art vibrantes construidos con una única paleta compartida verificada de exactamente 30 colores.",
        "palette_mode": "shared",
        "show_collection_palette": True,
        "palette": palette,
        "design_count": 60,
        "techniques": ["cross-stitch"],
        "mockup_spec": {
            "asset": "../../../products/assets/pop-art-25-collection-cover.webp",
            "technique_assets": {"CS": "../../../products/assets/pop-art-25-collection-cover.webp"},
            "frame": {"enabled": False},
            "approved_background_source_commit": APPROVED_BACKGROUND_SOURCE_COMMIT,
        },
        "preview_rules": {
            "palette_mode": "strict",
            "allowed_palette_size": 30,
            "gradients": False,
            "extra_colours": False,
            "transparent_background": False,
        },
    }
    write_json(CDIR / "collection.json", collection)

    write_json(CDIR / "designs.json", {
        "collection": CID,
        "palette_size": 30,
        "transparent_background": False,
        "designs": [{
            "code": code,
            "title_en": en,
            "title_es": es,
            "slug": slug,
            "status": "ready",
            "source_artwork": f"sources/{code}.png",
            "transparent_background": False,
            "variants": [f"{code}-CS"],
        } for code, en, es, slug in DESIGNS],
    })

    bulk = load_module("drielo_bulk60", SYSTEM / "multitech" / "bulk_generate.py")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    # Retire every currently published Pop Art SKU so the new generation is created
    # as a genuinely new product family instead of reusing the old product records.
    old_rows = [p for p in catalog.get("products", []) if p.get("collection") == CID]
    retired = set(catalog.get("retired_products", []))
    retired.update(str(p.get("sku", "")).strip() for p in old_rows if p.get("sku"))
    retired.update(f"DRIELO-P{i:04d}" for i in range(1, 27))
    catalog["retired_products"] = sorted(x for x in retired if x)

    catalog["products"] = [p for p in catalog.get("products", []) if p.get("collection") != CID]

    existing_collection = next((dict(c) for c in catalog.get("collections", []) if c.get("slug") == CID), {})
    existing_collection.update({
        "id": CID,
        "name": "Retratos Pop Art",
        "slug": CID,
        "name_en": "Pop Art Portraits",
        "name_es": "Retratos Pop Art",
        "description": collection["description_en"],
        "description_en": collection["description_en"],
        "description_es": collection["description_es"],
        "palette_mode": "shared",
        "show_collection_palette": True,
        "palette_hex": [p["hex"] for p in palette],
        "thread_codes": [p["dmc"] for p in palette],
        "cover_asset": "assets/pop-art-25-collection-cover.webp",
        "techniques": ["cross-stitch"],
        "visible": True,
        "force_visibility_sync": True,
    })
    catalog["collections"] = [c for c in catalog.get("collections", []) if c.get("slug") != CID]
    catalog["collections"].append(existing_collection)

    new_rows = []
    tasks = []
    for code, en, es, slug in DESIGNS:
        matrix, threads = base.source_matrix(SOURCES / f"{code}.png", palette)
        pattern = base.pattern_json(code, "CS", matrix, threads)
        product = base.product_json(code, en, es, slug, "CS")
        write_json(PATTERNS_DIR / f"{code}-CS" / "pattern.json", pattern)
        write_json(PRODUCTS_DIR / f"{code}-CS" / "product.json", product)

        data = bulk.pattern_data(f"{code}-CS", en, "CS", matrix, threads)
        data["collection"] = "Retratos Pop Art"
        data["collection_id"] = CID
        # Use the last explicitly approved Pop Art room/background image for
        # every product/PDF cover instead of the generic multitech cover.
        data["cover_image_path"] = str(APPROVED_BACKGROUND)
        tasks.append((f"{code}-CS", "CS", data))

        row = base.row_for(code, en, es, slug, "CS", data)
        row["gallery_revision"] = 2026092704
        new_rows.append(row)

    if {r["code"] for r in new_rows} != EXPECTED_CODES:
        raise RuntimeError("Did not prepare exactly 60 new Pop Art cross-stitch products")

    # Keep the approved Pop Art background untouched. The previous rebuild
    # incorrectly replaced it with the 60-design mosaic; the mosaic is only a
    # validation artefact and must never become the product background.
    if not APPROVED_BACKGROUND.is_file():
        raise RuntimeError(f"Approved Pop Art background missing: {APPROVED_BACKGROUND}")

    bulk.OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(bulk.render_one, task): task[0] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print("BUILT", result["code"], result["pdf_bytes"], result["image_bytes"], flush=True)

    by_code = {r["code"]: r for r in results}
    if set(by_code) != EXPECTED_CODES:
        raise RuntimeError(f"Rendered {len(by_code)} products, expected 60")

    rows_by_code = {r["code"]: r for r in new_rows}
    for code, result in by_code.items():
        shutil.copy2(result["pdf"], STORE_FILES / Path(result["pdf"]).name)
        shutil.copy2(result["image"], STORE_ASSETS / Path(result["image"]).name)
        shutil.copy2(result["design_preview"], STORE_ASSETS / Path(result["design_preview"]).name)
        gallery_assets = [f"assets/{Path(result['design_preview']).name}"]
        for item in result["gallery"]:
            src = Path(item)
            shutil.copy2(src, STORE_ASSETS / src.name)
            gallery_assets.append(f"assets/{src.name}")
        rows_by_code[code]["gallery"] = gallery_assets

    catalog["products"].extend(new_rows)
    catalog["products"].sort(key=lambda p: (p.get("collection", ""), p.get("code", "")))
    write_json(CATALOG, catalog)

    # Final source QA.
    union = set()
    for code, *_rest in DESIGNS:
        im = Image.open(SOURCES / f"{code}.png").convert("RGB")
        if im.size != (100, 120):
            raise RuntimeError(f"{code}: wrong official source size {im.size}")
        union.update(im.getdata())
    if len(union) != 30:
        raise RuntimeError(f"Official sources use {len(union)} RGB colours, expected 30")

    pop_rows = [p for p in catalog["products"] if p.get("collection") == CID]
    if len(pop_rows) != 60 or {p["code"] for p in pop_rows} != EXPECTED_CODES:
        raise RuntimeError("Catalogue does not contain exactly the new 60 Pop Art products")
    for row in pop_rows:
        if not (STORE_ASSETS / f"{row['code']}-product.webp").is_file():
            raise RuntimeError(f"Missing featured image for {row['code']}")
        if not (STORE_FILES / f"Drielo_{row['code']}.pdf").is_file():
            raise RuntimeError(f"Missing PDF for {row['code']}")
        if len(row.get("gallery", [])) != 4:
            raise RuntimeError(f"Expected 4 gallery images for {row['code']}")

    write_json(MARKER, {
        "zip_sha256": digest,
        "background_sha256": background_sha(),
        "background_source_commit": APPROVED_BACKGROUND_SOURCE_COMMIT,
        "background_asset": "content/products/assets/pop-art-25-collection-cover.webp",
        "gmail_message_id": SOURCE_GMAIL_MESSAGE_ID,
        "github_source": "tmp/pop-art-60-upload/pop_art_60_png_100x120_exact30.zip",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "design_count": 60,
        "product_count": 60,
        "tile_size": [100, 120],
        "shared_palette_size": 30,
        "deployed": False,
        "codes": sorted(EXPECTED_CODES),
    })

    print(json.dumps({
        "collection": CID,
        "designs": 60,
        "products": 60,
        "technique": "cross-stitch",
        "source_size": "100x120",
        "shared_palette": 30,
        "zip_sha256": digest,
    }, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--needs-rebuild", action="store_true")
    args = parser.parse_args()
    if args.needs_rebuild:
        raise SystemExit(0 if needs_rebuild() else 1)
    main()
