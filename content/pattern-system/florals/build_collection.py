#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "florals"
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"
MANIFEST_PATH = COL_DIR / "source-designs" / "manifest.json"
SOURCE_DIR = COL_DIR / "source-designs"
PATTERNS_DIR = SYSTEM / "patterns"
PRODUCTS_DIR = SYSTEM / "products"
STATUS_PATH = SYSTEM / "florals" / "generation_status.json"

sys.path.insert(0, str((SYSTEM / "multitech").resolve()))
import bulk_generate as bg  # noqa: E402

SYMBOLS = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
TECHNIQUES = ("CS", "C2C", "TC", "LH")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def source_rel(base_id: str, slug: str) -> str:
    return f"collections/florals/source-designs/{base_id}-{slug}.png"


def build_master_matrix(image_path: Path, palette: list[dict]):
    image = Image.open(image_path).convert("RGBA")
    if image.size != (100, 120):
        raise RuntimeError(f"{image_path.name}: expected 100x120, got {image.size}")

    exact = {}
    for idx, item in enumerate(palette):
        rgb = tuple(int(item["hex"][i:i+2], 16) for i in (1, 3, 5))
        exact[rgb] = idx

    matrix = []
    counts = Counter()
    non_palette = []

    for y in range(120):
        row = []
        for x in range(100):
            r, g, b, a = image.getpixel((x, y))
            if a < 128:
                row.append(None)
                continue
            idx = exact.get((r, g, b))
            if idx is None:
                non_palette.append((x, y, (r, g, b)))
                row.append(None)
                continue
            symbol = SYMBOLS[idx]
            row.append(symbol)
            counts[symbol] += 1
        matrix.append(row)

    if non_palette:
        preview = ", ".join(str(x) for x in non_palette[:5])
        raise RuntimeError(
            f"{image_path.name}: {len(non_palette)} opaque pixels outside the Florals palette; "
            f"first: {preview}"
        )
    if not counts:
        raise RuntimeError(f"{image_path.name}: source contains no opaque stitches")
    if len(counts) > 14:
        raise RuntimeError(
            f"{image_path.name}: uses {len(counts)} colours; approved maximum is 14"
        )

    threads = []
    for idx, item in enumerate(palette):
        symbol = SYMBOLS[idx]
        if counts[symbol]:
            threads.append(
                {
                    "symbol": symbol,
                    "dmc": str(item["dmc"]),
                    "color": item["hex"].upper(),
                    "name": item.get("name", f"DMC {item['dmc']}"),
                    "stitches": counts[symbol],
                }
            )
    return matrix, threads


def pattern_doc(base_id, suffix, source, matrix, threads):
    cfg = bg.TECHS[suffix]
    return {
        "code": f"{base_id}-{suffix}",
        "base_design_id": base_id,
        "technique_code": suffix,
        "collection": "florals",
        "palette_collection": "florals",
        "status": "ready",
        "source_asset": source,
        "reference_asset": source,
        "source_policy": "approved-100x120-one-pixel-one-cross",
        "stitch_width": cfg["w"],
        "stitch_height": cfg["h"],
        "total_stitches": sum(1 for row in matrix for value in row if value),
        "threads": threads,
        "matrix": matrix,
        "outline_policy": {"enabled": False},
        "external_white_cleanup": {"enabled": False},
    }


def product_doc(base_id, title, suffix, source, page1_asset):
    cfg = bg.TECHS[suffix]
    return {
        "code": f"{base_id}-{suffix}",
        "base_design_id": base_id,
        "technique_code": suffix,
        "collection": "florals",
        "title": title,
        "pattern_file": f"patterns/{base_id}-{suffix}/pattern.json",
        "website": "www.drielo.com",
        "technique": cfg["technique"],
        "template": cfg["template"],
        "source_artwork": source,
        "reference_artwork": source,
        "page_1_asset": page1_asset,
        "render_ready": True,
        "status": "active",
    }


def main():
    collection = read_json(COLLECTION_PATH)
    designs_doc = read_json(DESIGNS_PATH)
    manifest = read_json(MANIFEST_PATH)

    palette = collection["palette"]
    if len(palette) != 24:
        raise RuntimeError(f"Florals master palette must have 24 colours, got {len(palette)}")

    technique_assets = collection.get("mockup_spec", {}).get("technique_assets", {})
    for suffix in TECHNIQUES:
        if suffix not in technique_assets:
            raise RuntimeError(f"Missing page-1 asset mapping for {suffix}")

    manifest_by_id = {
        item["base_design_id"]: item for item in manifest.get("designs", [])
    }

    built = []
    technique_counts = Counter()

    for design in designs_doc["designs"]:
        base_id = design["base_design_id"]
        slug = design["slug"]
        if not re.fullmatch(r"F\d{4}", base_id):
            raise RuntimeError(f"Invalid Florals base id: {base_id}")

        source = source_rel(base_id, slug)
        source_path = SYSTEM / source
        if not source_path.is_file():
            raise RuntimeError(f"{base_id}: approved source is missing: {source_path}")

        master_matrix, master_threads = build_master_matrix(source_path, palette)
        variants = {"CS": (master_matrix, master_threads)}
        for suffix in ("C2C", "TC", "LH"):
            cfg = bg.TECHS[suffix]
            variants[suffix] = bg.downsample(
                master_matrix, master_threads, cfg["w"], cfg["h"]
            )

        design["source_asset"] = source
        design["reference_asset"] = source
        design["artwork_status"] = "approved-pattern-source-ready"
        design["pattern_source_policy"] = "100x120 one-pixel-one-cross approved preview"

        m = manifest_by_id.get(base_id)
        if m is None:
            raise RuntimeError(f"{base_id}: missing from source-design manifest")
        m["source_asset"] = source
        m["status"] = "approved-pattern-source-ready"

        per_design = {
            "base_design_id": base_id,
            "slug": slug,
            "source_asset": source,
            "techniques": {},
        }

        for suffix in TECHNIQUES:
            matrix, threads = variants[suffix]
            cfg = bg.TECHS[suffix]
            if len(matrix) != cfg["h"] or any(len(row) != cfg["w"] for row in matrix):
                raise RuntimeError(f"{base_id}-{suffix}: malformed {cfg['w']}x{cfg['h']} matrix")
            if not threads or len(threads) > 14:
                raise RuntimeError(
                    f"{base_id}-{suffix}: invalid colour count {len(threads)}"
                )

            pattern = pattern_doc(base_id, suffix, source, matrix, threads)
            product = product_doc(
                base_id,
                design["title_en"],
                suffix,
                source,
                f"collections/florals/{technique_assets[suffix]}",
            )

            write_json(PATTERNS_DIR / f"{base_id}-{suffix}" / "pattern.json", pattern)
            write_json(PRODUCTS_DIR / f"{base_id}-{suffix}" / "product.json", product)

            technique_counts[suffix] += 1
            per_design["techniques"][suffix] = {
                "code": f"{base_id}-{suffix}",
                "grid": [cfg["w"], cfg["h"]],
                "filled_cells": pattern["total_stitches"],
                "colors": len(threads),
            }

        built.append(per_design)
        print(
            base_id,
            "CS", per_design["techniques"]["CS"]["filled_cells"],
            "C2C", per_design["techniques"]["C2C"]["filled_cells"],
            "TC", per_design["techniques"]["TC"]["filled_cells"],
            "LH", per_design["techniques"]["LH"]["filled_cells"],
        )

    manifest["status"] = "all-30-approved-pattern-sources-ready"
    manifest["source"] = "approved 100x120 pixel/cross previews"
    manifest["master_grid"] = {"width": 100, "height": 120, "unit": "cross-stitch cells"}

    write_json(DESIGNS_PATH, designs_doc)
    write_json(MANIFEST_PATH, manifest)

    status = {
        "collection": "florals",
        "branch_purpose": "pattern-generation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_policy": "30 approved PNGs; 100x120; one opaque pixel equals one cross",
        "master_palette_colors": len(palette),
        "design_count": len(built),
        "pattern_count": sum(technique_counts.values()),
        "patterns_by_technique": dict(technique_counts),
        "production_publish": False,
        "designs": built,
    }
    write_json(STATUS_PATH, status)

    if len(built) != 30:
        raise RuntimeError(f"Expected 30 Florals designs, built {len(built)}")
    if sum(technique_counts.values()) != 120:
        raise RuntimeError(
            f"Expected 120 technique patterns, built {sum(technique_counts.values())}"
        )

    print(json.dumps({
        "designs": len(built),
        "patterns": sum(technique_counts.values()),
        "by_technique": dict(technique_counts),
    }, indent=2))


if __name__ == "__main__":
    main()
