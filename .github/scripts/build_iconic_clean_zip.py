#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
COL = ROOT / "content" / "pattern-system" / "collections" / "iconic-destinations"
ASSETS = COL / "assets"
SOURCE = ASSETS / "iconic-60-pngs-q50.zip"
OUTPUT = ASSETS / "iconic-60-pngs-q50-clean.zip"
REPORT = ASSETS / "iconic-60-pngs-q50-clean-review.json"

EXPECTED_SOURCE_SHA256 = "c50c5a21d8cbf9c799aad55d8dc213f21f9a36647235ca79d9368bb40b4f932e"
WIDTH = 100
HEIGHT = 120
MAX_COLORS = 50
TOP_CROP_BY_ROW = {1: 3, 2: 14, 3: 17, 4: 20, 5: 20, 6: 13}
LEFT_CROP = 3
RIGHT_CROP = 95
BOTTOM_CROP = 118


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_names() -> list[str]:
    return [f"destino_{r:02d}_{c:02d}.png" for r in range(1, 7) for c in range(1, 11)]


def clean_png(raw: bytes, row: int) -> bytes:
    with Image.open(io.BytesIO(raw)) as im:
        rgb = im.convert("RGB")
        if rgb.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"source PNG is {rgb.size}, expected {(WIDTH, HEIGHT)}")

        crop = rgb.crop((LEFT_CROP, TOP_CROP_BY_ROW[row], RIGHT_CROP, BOTTOM_CROP))
        clean = crop.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)

        colours = len(set(clean.getdata()))
        if not (1 <= colours <= MAX_COLORS):
            raise RuntimeError(f"clean PNG has {colours} colours; expected <= {MAX_COLORS}")

        out = io.BytesIO()
        clean.save(out, "PNG", optimize=True)
        return out.getvalue()


def deterministic_zip(entries: list[tuple[str, bytes]]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return out.getvalue()


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    source_sha = sha256_bytes(source_bytes)
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"Refusing unexpected source ZIP sha256={source_sha}")

    expected = expected_names()
    entries: list[tuple[str, bytes]] = []
    files_report = []
    clean_hashes = set()

    with zipfile.ZipFile(io.BytesIO(source_bytes), "r") as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".png") and not n.endswith("/")]
        if sorted(names) != sorted(expected) or len(names) != 60 or len(set(names)) != 60:
            raise SystemExit("Source ZIP must contain exactly the expected 60 individual PNG names")

        for name in expected:
            row = int(name.split("_")[1])
            raw = zf.read(name)
            cleaned = clean_png(raw, row)

            with Image.open(io.BytesIO(cleaned)) as im:
                rgb = im.convert("RGB")
                colours = len(set(rgb.getdata()))
                if rgb.size != (WIDTH, HEIGHT):
                    raise SystemExit(f"{name}: cleaned size {rgb.size}")
                if not (1 <= colours <= MAX_COLORS):
                    raise SystemExit(f"{name}: cleaned colours {colours}")

            digest = sha256_bytes(cleaned)
            if digest in clean_hashes:
                raise SystemExit(f"{name}: duplicate cleaned image bytes detected")
            clean_hashes.add(digest)

            entries.append((name, cleaned))
            files_report.append({
                "name": name,
                "width": WIDTH,
                "height": HEIGHT,
                "colours": colours,
                "sha256": digest,
                "source_sha256": sha256_bytes(raw),
            })
            print(f"CLEAN_ICONIC_OK {name} row={row} colours={colours}")

    output_bytes = deterministic_zip(entries)
    OUTPUT.write_bytes(output_bytes)

    # Read the final ZIP back; validation is against what will actually be committed.
    with zipfile.ZipFile(io.BytesIO(output_bytes), "r") as zf:
        final_names = [n for n in zf.namelist() if n.lower().endswith(".png")]
        if final_names != expected:
            raise SystemExit("Final clean ZIP ordering/names are not exact")
        for item in files_report:
            raw = zf.read(item["name"])
            if sha256_bytes(raw) != item["sha256"]:
                raise SystemExit(f'{item["name"]}: final ZIP member hash mismatch')

    report = {
        "status": "reviewed-clean-source-candidate",
        "source_zip": str(SOURCE.relative_to(ROOT)),
        "source_sha256": source_sha,
        "clean_zip": str(OUTPUT.relative_to(ROOT)),
        "clean_zip_sha256": sha256_bytes(output_bytes),
        "image_count": 60,
        "dimensions": {"width": WIDTH, "height": HEIGHT},
        "max_colours": MAX_COLORS,
        "duplicate_images": 0,
        "cleaning": {
            "reason": "remove legacy neighbouring-tile bleed visible on top/right borders",
            "left_crop": LEFT_CROP,
            "right_crop": RIGHT_CROP,
            "bottom_crop": BOTTOM_CROP,
            "top_crop_by_source_row": TOP_CROP_BY_ROW,
            "resize": "nearest-neighbour back to 100x120",
        },
        "production_status": "not-published-by-this-workflow",
        "files": files_report,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "CLEAN_ICONIC_ZIP_VALID "
        f"count=60 size=100x120 max_colours={MAX_COLORS} "
        f"sha256={report['clean_zip_sha256']}"
    )


if __name__ == "__main__":
    main()
