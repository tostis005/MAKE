#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import re
import shutil
import zlib
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path.cwd()
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "pop-art-25"
COLLECTION_DIR = SYSTEM / "collections" / COLLECTION_ID
PRODUCTS_DIR = SYSTEM / "products"
PATTERNS_DIR = SYSTEM / "patterns"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
DATA_DIR = ROOT / ".github" / "data" / "pop-art-resto-24"
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
TECH_ORDER = ("CS", "C2C", "TC", "LH")

DESIGNS = [
    ("P0002","Apple Man Portrait","Retrato del hombre de la manzana","apple-man-portrait"),
    ("P0003","Audrey Hepburn Bubble Gum","Audrey Hepburn con chicle","audrey-hepburn-bubble-gum"),
    ("P0004","Audrey Hepburn Profile","Audrey Hepburn de perfil","audrey-hepburn-profile"),
    ("P0005","Audrey Hepburn Sunglasses","Audrey Hepburn con gafas","audrey-hepburn-sunglasses"),
    ("P0006","Charlie Chaplin Portrait","Retrato de Charlie Chaplin","charlie-chaplin-portrait"),
    ("P0007","Frida Kahlo Floral Crown","Frida Kahlo con corona floral","frida-kahlo-floral-crown"),
    ("P0008","Girl with a Pearl Earring Bubble Gum","La joven de la perla con chicle","girl-pearl-earring-bubble-gum"),
    ("P0009","Girl with a Pearl Earring","La joven de la perla","girl-with-a-pearl-earring"),
    ("P0010","Girl with a Pearl Earring Sunglasses","La joven de la perla con gafas","girl-pearl-earring-sunglasses"),
    ("P0011","Marilyn Monroe Blowing Kiss","Marilyn Monroe lanzando un beso","marilyn-monroe-blowing-kiss"),
    ("P0013","Marilyn Monroe Sunglasses","Marilyn Monroe con gafas","marilyn-monroe-sunglasses"),
    ("P0014","Marilyn Monroe Surprise","Marilyn Monroe sorprendida","marilyn-monroe-surprise"),
    ("P0015","Marilyn Monroe Wink","Marilyn Monroe guiñando un ojo","marilyn-monroe-wink"),
    ("P0016","Mona Lisa Portrait","Retrato de la Mona Lisa","mona-lisa-portrait"),
    ("P0017","Salvador Dalí Portrait","Retrato de Salvador Dalí","salvador-dali-portrait"),
    ("P0018","Van Gogh with Sunflower","Van Gogh con girasol","van-gogh-sunflower"),
    ("P0019","Vincent van Gogh Portrait","Retrato de Vincent van Gogh","vincent-van-gogh-portrait"),
    ("P0020","James Dean Portrait","Retrato de James Dean","james-dean-portrait"),
    ("P0021","David Bowie Portrait","Retrato de David Bowie","david-bowie-portrait"),
    ("P0022","Princess Diana Bubble Gum","Princesa Diana con chicle","princess-diana-bubble-gum"),
    ("P0023","Princess Diana Portrait","Retrato de la princesa Diana","princess-diana-portrait"),
    ("P0024","Michael Jackson Portrait","Retrato de Michael Jackson","michael-jackson-portrait"),
    ("P0025","Nelson Mandela Portrait","Retrato de Nelson Mandela","nelson-mandela-portrait"),
    ("P0026","Freddie Mercury Portrait","Retrato de Freddie Mercury","freddie-mercury-portrait"),
]
DESIGN_BY_CODE = {d[0]: d for d in DESIGNS}

# These 13 designs already have a matching approved visual in the historical
# product assets. Reconstruct the 100x120 grid from that asset, but publish it
# under the new Pop Art 25 IDs above.
LEGACY_SOURCE = {
    "P0002": ("P0018", 4933),
    "P0004": ("P0008", 5817),
    "P0005": ("P0007", 5644),
    "P0006": ("P0016", 5138),
    "P0008": ("P0010", 5962),
    "P0009": ("P0009", 5820),
    "P0010": ("P0011", 5871),
    "P0011": ("P0003", 6477),
    "P0013": ("P0004", 6557),
    "P0014": ("P0002", 6604),
    "P0015": ("P0005", 6558),
    "P0016": ("P0013", 5818),
    "P0019": ("P0017", 4941),
}

# New/changed portraits are embedded from the final transparent contact-sheet
# artwork supplied for this collection. Each matrix is 100x120 palette indices.
EMBEDDED_CODES = [
    "P0003","P0007","P0017","P0018","P0020","P0021",
    "P0022","P0023","P0024","P0025","P0026",
]

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

bulk = load_module("drielo_bulk", SYSTEM / "multitech" / "bulk_generate.py")
bootstrap = load_module("drielo_bootstrap", ROOT / ".github" / "scripts" / "bootstrap_pop_art_25.py")

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def embedded_matrices(palette):
    encoded = "".join((DATA_DIR / f"embedded.part0{i}").read_text(encoding="utf-8").strip() for i in range(1, 5))
    raw = zlib.decompress(base64.b64decode(encoded))
    expected = len(EMBEDDED_CODES) * 12000
    if len(raw) != expected:
        raise RuntimeError(f"Embedded matrix payload: expected {expected} bytes, got {len(raw)}")
    result = {}
    for n, code in enumerate(EMBEDDED_CODES):
        chunk = raw[n*12000:(n+1)*12000]
        matrix = []
        counts = Counter()
        for y in range(120):
            row = []
            for x in range(100):
                v = chunk[y*100+x]
                if v == 255:
                    row.append(None)
                else:
                    if v >= len(palette):
                        raise RuntimeError(f"{code}: invalid palette index {v}")
                    sym = SYMBOLS[v]
                    row.append(sym)
                    counts[sym] += 1
            matrix.append(row)
        threads = []
        for i, p in enumerate(palette):
            sym = SYMBOLS[i]
            if counts[sym]:
                threads.append({
                    "symbol": sym, "dmc": str(p["dmc"]), "color": p["hex"],
                    "name": p.get("name", f"DMC {p['dmc']}"), "stitches": counts[sym],
                })
        result[code] = (matrix, threads)
    return result

def save_transparent_source(code, matrix, threads):
    by = {t["symbol"]: t["color"] for t in threads}
    im = Image.new("RGBA", (500, 600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    for y, row in enumerate(matrix):
        for x, sym in enumerate(row):
            if sym:
                draw.rectangle((x*5, y*5, x*5+4, y*5+4), fill=by[sym])
    out = COLLECTION_DIR / "sources" / f"{code}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", optimize=True)

def source_matrix(code, palette, embedded):
    if code in embedded:
        return embedded[code]
    legacy_code, target_stitches = LEGACY_SOURCE[code]
    src = STORE_ASSETS / f"{legacy_code}-gallery-2.webp"
    if not src.is_file():
        raise RuntimeError(f"{code}: missing legacy source {src}")
    return bulk.reconstruct_cross_matrix(src, target_stitches, palette)

def product_json(base, title_en, title_es, slug, suffix):
    cfg = bootstrap.TECHS[suffix]
    cover = {
        "CS": "cross-stitch",
        "C2C": "crochet",
        "TC": "c2c-crochet",
        "LH": "rug",
    }[suffix]
    return {
        "code": f"{base}-{suffix}",
        "base_design_id": base,
        "technique_code": suffix,
        "collection": COLLECTION_ID,
        "title": title_en,
        "title_en": title_en,
        "title_es": title_es,
        "design_slug": slug,
        "technique": cfg[0],
        "pattern_file": f"patterns/{base}-{suffix}/pattern.json",
        "template": cfg[1],
        "website": "www.drielo.com",
        "status": "ready",
        "render_ready": True,
        "renderer": "multitech",
        "source_artwork": f"collections/{COLLECTION_ID}/sources/{base}.png",
        "page_1_asset": f"multitech/assets/cover-{cover}.webp",
        "palette_mode": "strict",
        "palette_size": 25,
        "transparent_source": True,
    }

def pattern_json(base, suffix, matrix, threads):
    cfg = bootstrap.TECHS[suffix]
    total = sum(t["stitches"] for t in threads)
    return {
        "code": f"{base}-{suffix}",
        "base_design_id": base,
        "technique_code": suffix,
        "collection": COLLECTION_ID,
        "palette_collection": COLLECTION_ID,
        "status": "ready",
        "source_asset": f"content/pattern-system/collections/{COLLECTION_ID}/sources/{base}.png",
        "stitch_width": cfg[2],
        "stitch_height": cfg[3],
        "total_stitches": total,
        "color_count": len(threads),
        "palette_size": 25,
        "transparent_background": True,
        "threads": threads,
        "matrix": matrix,
    }

def validate_palette(threads, palette, code):
    allowed = {(str(p["dmc"]), p["hex"].upper()) for p in palette}
    for t in threads:
        pair = (str(t["dmc"]), str(t["color"]).upper())
        if pair not in allowed:
            raise RuntimeError(f"{code}: thread outside fixed 25-colour palette: {pair}")

def update_designs():
    path = COLLECTION_DIR / "designs.json"
    data = read_json(path)
    by = {d["code"]: d for d in data["designs"]}
    for code, en, es, slug in DESIGNS:
        d = by[code]
        d.update({
            "title_en": en,
            "title_es": es,
            "slug": slug,
            "status": "ready",
            "source_artwork": f"sources/{code}.png",
            "transparent_background": True,
            "variants": [f"{code}-{s}" for s in TECH_ORDER],
        })
    data["palette_size"] = 25
    data["transparent_background"] = True
    write_json(path, data)

def build(workers: int):
    collection = read_json(COLLECTION_DIR / "collection.json")
    palette = collection["palette"]
    if len(palette) != 25:
        raise RuntimeError("Pop Art 25 must have exactly 25 master colours")
    if collection["mockup_spec"]["technique_assets"]["C2C"] != "../../multitech/assets/cover-crochet.webp":
        raise RuntimeError("C2C collection cover route changed unexpectedly")
    if collection["mockup_spec"]["technique_assets"]["TC"] != "../../multitech/assets/cover-c2c-crochet.webp":
        raise RuntimeError("TC collection cover route changed unexpectedly")

    embedded = embedded_matrices(palette)
    prepared = {}
    render_tasks = []

    for base, en, es, slug in DESIGNS:
        cs_matrix, cs_threads = source_matrix(base, palette, embedded)
        validate_palette(cs_threads, palette, f"{base}-CS")
        save_transparent_source(base, cs_matrix, cs_threads)

        variants = {"CS": (cs_matrix, cs_threads)}
        for suffix in ("C2C", "TC", "LH"):
            cfg = bootstrap.TECHS[suffix]
            matrix, threads = bulk.downsample(cs_matrix, cs_threads, cfg[2], cfg[3])
            validate_palette(threads, palette, f"{base}-{suffix}")
            variants[suffix] = (matrix, threads)

        bootstrap.BY[base] = (base, en, es, slug)
        for suffix in TECH_ORDER:
            matrix, threads = variants[suffix]
            code = f"{base}-{suffix}"
            write_json(PATTERNS_DIR / code / "pattern.json", pattern_json(base, suffix, matrix, threads))
            write_json(PRODUCTS_DIR / code / "product.json", product_json(base, en, es, slug, suffix))
            data = bulk.pattern_data(code, en, suffix, matrix, threads)
            data["collection"] = "Pop Art"
            data["collection_id"] = COLLECTION_ID
            prepared[(base, suffix)] = data
            render_tasks.append((code, suffix, data))

    update_designs()

    # Generate the 96 PDFs and ecommerce images on the feature branch.
    results = []
    # Render sequentially for reliability: render_one is loaded dynamically and
    # Playwright starts its own Chromium instance per product, so process-pool
    # pickling adds fragility without improving the branch deliverable.
    for task in render_tasks:
        result = bulk.render_one(task)
        results.append(result)
        print("BUILT", result["code"], result["pdf_bytes"], result["image_bytes"], flush=True)

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    for result in results:
        shutil.copy2(result["pdf"], STORE_FILES / Path(result["pdf"]).name)
        shutil.copy2(result["image"], STORE_ASSETS / Path(result["image"]).name)

    # Add all 96 listing rows to the new collection catalogue, leaving P0001/P0012 untouched.
    catalog = read_json(CATALOG_PATH)
    remaining_codes = {f"{base}-{suffix}" for base, *_ in DESIGNS for suffix in TECH_ORDER}
    catalog["products"] = [p for p in catalog["products"] if p.get("code") not in remaining_codes]

    new_rows = []
    for base, en, es, slug in DESIGNS:
        for suffix in TECH_ORDER:
            row = bootstrap.row_for(base, suffix, prepared[(base, suffix)])
            row["gallery_revision"] = 2026092406
            row["collection"] = COLLECTION_ID
            row.pop("previous_skus", None)
            new_rows.append(row)
    catalog["products"].extend(new_rows)
    tech_rank = {"CS":0, "C2C":1, "TC":2, "LH":3}
    catalog["products"].sort(key=lambda p: (
        p.get("base_design_id") or re.sub(r"-.*$", "", p.get("code", "")),
        tech_rank.get(p.get("technique_code", ""), 9),
        p.get("code", ""),
    ))
    write_json(CATALOG_PATH, catalog)

    # Final branch QA.
    pop = [p for p in catalog["products"] if p.get("collection") == COLLECTION_ID]
    if len(pop) != 104:
        raise RuntimeError(f"Expected 104 Pop Art 25 catalogue variants, got {len(pop)}")
    if len(results) != 96:
        raise RuntimeError(f"Expected 96 rendered variants, got {len(results)}")

    for base, *_ in DESIGNS:
        source = COLLECTION_DIR / "sources" / f"{base}.png"
        if not source.is_file() or source.stat().st_size < 1000:
            raise RuntimeError(f"Missing transparent source {source}")
        for suffix in TECH_ORDER:
            code = f"{base}-{suffix}"
            pdf = STORE_FILES / f"Drielo_{code}.pdf"
            img = STORE_ASSETS / f"{code}-product.webp"
            if not pdf.is_file() or pdf.stat().st_size < 100000 or pdf.read_bytes()[:4] != b"%PDF":
                raise RuntimeError(f"Invalid PDF {pdf}")
            if not img.is_file() or img.stat().st_size < 10000:
                raise RuntimeError(f"Invalid product image {img}")

    print(json.dumps({
        "branch_collection": COLLECTION_ID,
        "remaining_designs": len(DESIGNS),
        "rendered_variants": len(results),
        "catalogue_variants_total": len(pop),
        "fixed_palette_colours": len(palette),
    }, indent=2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    build(args.workers)

if __name__ == "__main__":
    main()
