#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path.cwd()
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "pop-art-25"
COLLECTION_DIR = SYSTEM / "collections" / COLLECTION_ID
PRODUCTS_DIR = SYSTEM / "products"
PATTERNS_DIR = SYSTEM / "patterns"

PALETTE = [
    {"dmc":"310","hex":"#000000","name":"Black"},
    {"dmc":"3799","hex":"#404040","name":"Very Dark Pewter Gray"},
    {"dmc":"414","hex":"#8C8C8C","name":"Dark Steel Gray"},
    {"dmc":"B5200","hex":"#FFFFFF","name":"Snow White"},
    {"dmc":"3865","hex":"#F5ECDF","name":"Winter White"},
    {"dmc":"948","hex":"#FEE7DA","name":"Very Light Peach"},
    {"dmc":"754","hex":"#F7CBBF","name":"Light Peach"},
    {"dmc":"437","hex":"#E4BB8E","name":"Light Tan"},
    {"dmc":"761","hex":"#FC9F8B","name":"Light Salmon"},
    {"dmc":"604","hex":"#E996B8","name":"Light Cranberry"},
    {"dmc":"351","hex":"#E96A67","name":"Coral"},
    {"dmc":"321","hex":"#C72B3B","name":"Red"},
    {"dmc":"970","hex":"#F78B2D","name":"Light Pumpkin"},
    {"dmc":"3820","hex":"#DFB65B","name":"Dark Straw"},
    {"dmc":"444","hex":"#FFD600","name":"Dark Lemon"},
    {"dmc":"434","hex":"#985B3B","name":"Light Brown"},
    {"dmc":"801","hex":"#653919","name":"Dark Coffee Brown"},
    {"dmc":"905","hex":"#627650","name":"Dark Parrot Green"},
    {"dmc":"890","hex":"#17492F","name":"Ultra Dark Pistachio Green"},
    {"dmc":"598","hex":"#8EB8BC","name":"Light Turquoise"},
    {"dmc":"3325","hex":"#86B1D0","name":"Light Baby Blue"},
    {"dmc":"797","hex":"#3157A4","name":"Royal Blue"},
    {"dmc":"820","hex":"#0E365C","name":"Very Dark Royal Blue"},
    {"dmc":"550","hex":"#5C295F","name":"Very Dark Violet"},
    {"dmc":"729","hex":"#D0A53E","name":"Medium Old Gold"},
]

DESIGNS = [
    ("P0001","Albert Einstein Tongue Out","Albert Einstein sacando la lengua","albert-einstein-tongue-out"),
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
    ("P0012","Marilyn Monroe Bubble Gum","Marilyn Monroe con chicle","marilyn-monroe-bubble-gum"),
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

# C2C and tapestry use the corrected cover mapping requested for the new collection.
TECHS = {
    "CS": {
        "technique":"cross-stitch","template":"cross-stitch.html","w":100,"h":120,
        "page_1_asset":"multitech/assets/cover-cross-stitch.webp",
    },
    "C2C": {
        "technique":"c2c-crochet","template":"c2c-crochet.html","w":60,"h":72,
        "page_1_asset":"multitech/assets/cover-crochet.webp",
    },
    "TC": {
        "technique":"tapestry-crochet","template":"crochet.html","w":80,"h":96,
        "page_1_asset":"multitech/assets/cover-c2c-crochet.webp",
    },
    "LH": {
        "technique":"latch-hook","template":"rug.html","w":60,"h":72,
        "page_1_asset":"multitech/assets/cover-rug.webp",
    },
}

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def existing_pattern(code: str) -> dict | None:
    p = PATTERNS_DIR / code / "pattern.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def pattern_has_data(data: dict | None) -> bool:
    return bool(data and data.get("matrix") and data.get("threads") and int(data.get("total_stitches") or 0) > 0)

def product_json(base: str, en: str, es: str, slug: str, suffix: str, ready: bool) -> dict:
    cfg = TECHS[suffix]
    return {
        "code": f"{base}-{suffix}",
        "base_design_id": base,
        "technique_code": suffix,
        "collection": COLLECTION_ID,
        "title": en,
        "title_en": en,
        "title_es": es,
        "design_slug": slug,
        "technique": cfg["technique"],
        "pattern_file": f"patterns/{base}-{suffix}/pattern.json",
        "template": cfg["template"],
        "website": "www.drielo.com",
        "status": "ready" if ready else "awaiting-source-artwork",
        "render_ready": bool(ready),
        "renderer": "multitech",
        "source_artwork": f"collections/{COLLECTION_ID}/sources/{base}.png",
        "page_1_asset": cfg["page_1_asset"],
        "palette_mode": "strict",
        "palette_size": 25,
        "transparent_source": True,
    }

def shell_pattern(base: str, suffix: str) -> dict:
    cfg = TECHS[suffix]
    return {
        "code": f"{base}-{suffix}",
        "base_design_id": base,
        "technique_code": suffix,
        "collection": COLLECTION_ID,
        "palette_collection": COLLECTION_ID,
        "status": "awaiting-source-artwork",
        "source_asset": f"content/pattern-system/collections/{COLLECTION_ID}/sources/{base}.png",
        "stitch_width": cfg["w"],
        "stitch_height": cfg["h"],
        "total_stitches": 0,
        "color_count": 0,
        "palette_size": 25,
        "transparent_background": True,
        "threads": [],
        "matrix": [],
    }

def main() -> None:
    COLLECTION_DIR.mkdir(parents=True, exist_ok=True)
    (COLLECTION_DIR / "sources").mkdir(parents=True, exist_ok=True)

    collection = {
        "id": COLLECTION_ID,
        "name": "Pop Art",
        "name_en": "Pop Art",
        "name_es": "Pop Art",
        "slug": "pop-art-25",
        "code_prefix": "P",
        "description": "26 colourful Pop Art designs sharing one strict 25-colour palette across four grid-based craft techniques.",
        "description_en": "26 colourful Pop Art designs sharing one strict 25-colour palette across four grid-based craft techniques.",
        "description_es": "26 diseños Pop Art coloridos que comparten una única paleta estricta de 25 colores en cuatro técnicas basadas en cuadrícula.",
        "palette": PALETTE,
        "design_count": 26,
        "techniques": ["cross-stitch","c2c-crochet","tapestry-crochet","latch-hook"],
        "mockup_spec": {
            "asset": "../../multitech/assets/cover-cross-stitch.webp",
            "technique_assets": {
                "CS": "../../multitech/assets/cover-cross-stitch.webp",
                "C2C": "../../multitech/assets/cover-crochet.webp",
                "TC": "../../multitech/assets/cover-c2c-crochet.webp",
                "LH": "../../multitech/assets/cover-rug.webp",
            },
            "frame": {"enabled": False},
        },
        "preview_rules": {
            "palette_mode": "strict",
            "allowed_palette_size": 25,
            "gradients": False,
            "extra_colours": False,
            "transparent_background": True,
        },
    }
    write_json(COLLECTION_DIR / "collection.json", collection)

    design_rows = []
    ready_variants = 0

    for base, en, es, slug in DESIGNS:
        variant_codes = []
        source_exists = (COLLECTION_DIR / "sources" / f"{base}.png").is_file()

        for suffix in ("CS","C2C","TC","LH"):
            code = f"{base}-{suffix}"
            old = existing_pattern(code)

            # Keep valid pattern matrices already generated for the new collection.
            if pattern_has_data(old) and old.get("collection") == COLLECTION_ID:
                pattern = dict(old)
                pattern.update({
                    "code": code,
                    "base_design_id": base,
                    "technique_code": suffix,
                    "collection": COLLECTION_ID,
                    "palette_collection": COLLECTION_ID,
                    "source_asset": f"content/pattern-system/collections/{COLLECTION_ID}/sources/{base}.png",
                    "palette_size": 25,
                    "transparent_background": True,
                })
                ready = source_exists
                pattern["status"] = "ready" if ready else "awaiting-source-artwork"
            else:
                pattern = shell_pattern(base, suffix)
                ready = False

            write_json(PATTERNS_DIR / code / "pattern.json", pattern)
            write_json(PRODUCTS_DIR / code / "product.json", product_json(base,en,es,slug,suffix,ready))
            variant_codes.append(code)
            if ready:
                ready_variants += 1

        design_rows.append({
            "code": base,
            "title_en": en,
            "title_es": es,
            "slug": slug,
            "status": "ready" if source_exists else "awaiting-source-artwork",
            "source_artwork": f"sources/{base}.png",
            "transparent_background": True,
            "variants": variant_codes,
        })

    write_json(COLLECTION_DIR / "designs.json", {
        "collection": COLLECTION_ID,
        "palette_size": 25,
        "transparent_background": True,
        "designs": design_rows,
    })

    # QA: exact 26 x 4 structure and corrected C2C/TC cover mapping.
    missing = []
    for base, *_ in DESIGNS:
        for suffix in TECHS:
            if not (PRODUCTS_DIR / f"{base}-{suffix}" / "product.json").is_file():
                missing.append(f"{base}-{suffix} product")
            if not (PATTERNS_DIR / f"{base}-{suffix}" / "pattern.json").is_file():
                missing.append(f"{base}-{suffix} pattern")
    if missing:
        raise RuntimeError("Missing generated files: " + ", ".join(missing))

    if TECHS["C2C"]["page_1_asset"] != "multitech/assets/cover-crochet.webp":
        raise RuntimeError("C2C cover mapping is not corrected")
    if TECHS["TC"]["page_1_asset"] != "multitech/assets/cover-c2c-crochet.webp":
        raise RuntimeError("Tapestry cover mapping is not corrected")

    print(json.dumps({
        "collection": COLLECTION_ID,
        "designs": len(DESIGNS),
        "product_jsons": len(DESIGNS) * len(TECHS),
        "pattern_jsons": len(DESIGNS) * len(TECHS),
        "palette_size": len(PALETTE),
        "ready_variants_preserved": ready_variants,
    }, indent=2))

if __name__ == "__main__":
    main()
