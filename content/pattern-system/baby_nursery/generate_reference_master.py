#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_DIR = SYSTEM / "collections" / "baby-nursery"
LIBRARY_DIR = COLLECTION_DIR / "reference-library"
MANIFEST_PATH = LIBRARY_DIR / "manifest.json"
COLLECTION_PATH = COLLECTION_DIR / "collection.json"
DESIGNS_PATH = COLLECTION_DIR / "designs.json"
SOURCE_DIR = COLLECTION_DIR / "source-designs"
REFERENCE_DIR = COLLECTION_DIR / "reference-masters"

EXPECTED_DECODED_SHA256 = "533a4d7ed0892fd142eed3406b4740a539f70cbfffeaf932813466800a97ad19"
STANDARD_ALPHABET = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def design_meta(base_id: str):
    for item in read_json(DESIGNS_PATH)["designs"]:
        if item["base_design_id"] == base_id:
            return item
    raise RuntimeError(f"Unknown design id: {base_id}")


def load_archive():
    manifest = read_json(MANIFEST_PATH)
    parts = manifest.get("canonical_archive_parts") or []
    if len(parts) != 10:
        raise RuntimeError(f"Expected 10 canonical archive parts, got {parts}")

    encoded = "".join((LIBRARY_DIR / name).read_text(encoding="ascii").strip() for name in parts)
    try:
        compressed = base64.b64decode(encoded, validate=True)
        raw = zlib.decompress(compressed)
    except Exception as exc:
        raise RuntimeError(f"Canonical reference archive cannot be decoded: {exc}") from exc

    digest = hashlib.sha256(raw).hexdigest()
    expected = manifest.get("decoded_sha256") or EXPECTED_DECODED_SHA256
    if digest != expected or digest != EXPECTED_DECODED_SHA256:
        raise RuntimeError(f"Canonical reference archive digest mismatch: {digest}")

    data = json.loads(raw.decode("utf-8"))
    if data.get("version") != 1:
        raise RuntimeError(f"Unsupported canonical archive version: {data.get('version')}")
    if data.get("grid") != {"width": 100, "height": 120}:
        raise RuntimeError(f"Unexpected canonical grid: {data.get('grid')}")
    if len(data.get("designs", {})) != 30:
        raise RuntimeError(f"Expected 30 canonical designs, got {len(data.get('designs', {}))}")
    return manifest, data


def load_design_reference(base_id: str, meta: dict):
    direct = LIBRARY_DIR / f"{base_id}-{meta['slug']}.json"
    if not direct.is_file():
        return None

    d = read_json(direct)
    if d.get("version") != 1:
        raise RuntimeError(f"{base_id}: unsupported direct reference version")
    if d.get("base_design_id") != base_id or d.get("slug") != meta["slug"]:
        raise RuntimeError(f"{base_id}: direct reference identity mismatch")

    try:
        raw = zlib.decompress(base64.b64decode(d["matrix_zlib_base64"], validate=True))
    except Exception as exc:
        raise RuntimeError(f"{base_id}: direct reference matrix cannot be decoded: {exc}") from exc

    digest = hashlib.sha256(raw).hexdigest()
    if digest != d.get("matrix_sha256"):
        raise RuntimeError(f"{base_id}: direct reference matrix digest mismatch: {digest}")

    rows = raw.decode("ascii").splitlines()
    if len(rows) != 120 or any(len(row) != 100 for row in rows):
        raise RuntimeError(f"{base_id}: direct reference matrix is not 100x120")

    manifest = read_json(MANIFEST_PATH)
    manifest_row = next((x for x in manifest["designs"] if x["base_design_id"] == base_id), None)
    if not manifest_row:
        raise RuntimeError(f"{base_id}: missing from reference-library manifest")

    return {
        "manifest": manifest,
        "canonical": {
            "slug": meta["slug"],
            "sheet": int(manifest_row["reference_sheet"]),
            "row": int(manifest_row["row"]),
            "column": int(manifest_row["column"]),
            "rows": rows,
        },
        "alphabet": STANDARD_ALPHABET,
        "source_kind": "direct-user-sheet-crop",
        "source_sha256": digest,
        "direct_metadata": d,
    }


def rgba_from_matrix(rows, palette, alphabet):
    if len(rows) != 120 or any(len(row) != 100 for row in rows):
        raise RuntimeError("Canonical matrix is not 100x120")

    lookup = {}
    for idx, char in enumerate(alphabet):
        if idx >= len(palette):
            raise RuntimeError(f"Palette index {idx} exceeds collection palette")
        h = palette[idx]["hex"].lstrip("#")
        lookup[char] = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    im = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == ".":
                continue
            if char not in lookup:
                raise RuntimeError(f"Unknown palette symbol {char!r} at {x},{y}")
            px[x, y] = lookup[char]
    return im


def validate_master(base_id: str, im: Image.Image):
    if im.size != (800, 960):
        raise RuntimeError(f"{base_id}: master must be 800x960, got {im.size}")
    alpha = im.getchannel("A")
    amin, amax = alpha.getextrema()
    bbox = alpha.getbbox()
    if amin != 0 or amax == 0 or not bbox:
        raise RuntimeError(f"{base_id}: master must contain artwork and transparent background")

    x0, y0, x1, y1 = bbox
    margins = {
        "left": x0,
        "top": y0,
        "right": im.width - x1,
        "bottom": im.height - y1,
    }
    if min(margins.values()) < 32:
        raise RuntimeError(f"{base_id}: canonical artwork lacks safe margin: bbox={bbox}, margins={margins}")
    return bbox, margins


def generate_reference_master(base_id: str):
    base_id = base_id.strip().upper()
    meta = design_meta(base_id)

    direct = load_design_reference(base_id, meta)
    if direct:
        manifest = direct["manifest"]
        canonical = direct["canonical"]
        alphabet = direct["alphabet"]
        source_kind = direct["source_kind"]
        source_digest = direct["source_sha256"]
        direct_metadata = direct["direct_metadata"]
    else:
        manifest, archive = load_archive()
        if base_id not in archive["designs"]:
            raise RuntimeError(f"{base_id}: not found in canonical user-reference archive")
        canonical = archive["designs"][base_id]
        alphabet = archive["palette_indices"]
        source_kind = "legacy-reference-archive"
        source_digest = EXPECTED_DECODED_SHA256
        direct_metadata = None

    if canonical.get("slug") != meta.get("slug"):
        raise RuntimeError(
            f"{base_id}: canonical slug {canonical.get('slug')} != designs.json slug {meta.get('slug')}"
        )

    manifest_row = next((x for x in manifest["designs"] if x["base_design_id"] == base_id), None)
    if not manifest_row:
        raise RuntimeError(f"{base_id}: missing from canonical manifest")
    if (
        manifest_row["slug"] != meta["slug"]
        or int(manifest_row["reference_sheet"]) != int(canonical["sheet"])
        or int(manifest_row["row"]) != int(canonical["row"])
        or int(manifest_row["column"]) != int(canonical["column"])
    ):
        raise RuntimeError(f"{base_id}: canonical manifest/reference mapping mismatch")

    collection = read_json(COLLECTION_PATH)
    palette = collection["palette"]
    grid = rgba_from_matrix(canonical["rows"], palette, alphabet)
    master = grid.resize((800, 960), Image.Resampling.NEAREST)
    bbox, margins = validate_master(base_id, master)

    source_rel = meta["source_asset"]
    source_path = SYSTEM / source_rel
    expected_source = SOURCE_DIR / f"{base_id}-{meta['slug']}.png"
    if source_path != expected_source:
        raise RuntimeError(f"{base_id}: designs.json source path is not canonical: {source_rel}")

    ref_name = f"{base_id}-{meta['slug']}-reference.png"
    ref_path = REFERENCE_DIR / ref_name
    ref_rel = f"collections/baby-nursery/reference-masters/{ref_name}"

    source_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    master.save(source_path, "PNG", optimize=True)
    master.save(ref_path, "PNG", optimize=True)

    source_check = Image.open(source_path).convert("RGBA")
    ref_check = Image.open(ref_path).convert("RGBA")
    if source_check.tobytes() != ref_check.tobytes():
        raise RuntimeError(f"{base_id}: source/reference masters diverged after save")
    bbox2, margins2 = validate_master(base_id, ref_check)
    if bbox2 != bbox or margins2 != margins:
        raise RuntimeError(f"{base_id}: master geometry changed after persistence")

    result = {
        "design_id": base_id,
        "slug": meta["slug"],
        "reference_sheet": canonical["sheet"],
        "reference_row": canonical["row"],
        "reference_column": canonical["column"],
        "source_asset": source_rel,
        "reference_asset": ref_rel,
        "bbox": bbox,
        "margins": margins,
        "reference_source": source_kind,
        "reference_sha256": source_digest,
    }
    if direct_metadata:
        result["source_crop_bbox"] = direct_metadata.get("source_crop_bbox")
        result["source_crop_size"] = direct_metadata.get("source_crop_size")
        result["palette_policy"] = direct_metadata.get("palette_policy")

    print("CANONICAL_REFERENCE_MASTER_OK", json.dumps(result, ensure_ascii=False))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_id", help="I0001 .. I0030")
    args = ap.parse_args()
    generate_reference_master(args.design_id)


if __name__ == "__main__":
    main()
