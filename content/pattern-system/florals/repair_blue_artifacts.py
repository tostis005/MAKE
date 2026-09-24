#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL_DIR = SYSTEM / "collections" / "florals"
DESIGNS_PATH = COL_DIR / "designs.json"
COLLECTION_PATH = COL_DIR / "collection.json"

PALE_BLUE = {
    (0xC7, 0xD8, 0xE8),  # DMC 3753
    (0xD3, 0xD7, 0xED),  # DMC 3747
}
ALL_BLUE = PALE_BLUE | {
    (0x86, 0xB1, 0xD0),  # DMC 3325
    (0x55, 0x8E, 0xBD),  # DMC 3760
}

# These motifs are not blue subjects. The pale-blue shades came from the original
# quantisation/highlight pass and visually cut through the artwork.
PALE_BLUE_REPAIR_IDS = {
    "F0002","F0003","F0004","F0006","F0007","F0009","F0010",
    "F0012","F0013","F0014","F0015","F0016","F0017","F0018",
    "F0019","F0021","F0023","F0025","F0028","F0029",
}

# The three already-published offenders must contain no blue family at all.
ALL_BLUE_REPAIR_IDS = {"F0002","F0003","F0004"}


def repair_nearest(image: Image.Image, bad_colours: set[tuple[int, int, int]]):
    arr = np.array(image.convert("RGBA"))
    h, w = arr.shape[:2]
    opaque = arr[:, :, 3] >= 128
    bad = np.zeros((h, w), dtype=bool)

    for colour in bad_colours:
        bad |= opaque & np.all(arr[:, :, :3] == colour, axis=2)

    count = int(bad.sum())
    if count == 0:
        return image.convert("RGBA"), 0

    valid = opaque & ~bad
    if not valid.any():
        raise RuntimeError("Artwork contains no valid non-blue pixels")

    dist = np.full((h, w), 1_000_000, dtype=np.int32)
    labels = np.zeros((h, w, 3), dtype=np.uint8)
    queue: deque[tuple[int, int]] = deque()

    ys, xs = np.where(valid)
    for y, x in zip(ys, xs):
        dist[y, x] = 0
        labels[y, x] = arr[y, x, :3]
        queue.append((y, x))

    neighbours = (
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1),
    )

    while queue:
        y, x = queue.popleft()
        next_dist = dist[y, x] + 1
        for dy, dx in neighbours:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and opaque[yy, xx] and next_dist < dist[yy, xx]:
                dist[yy, xx] = next_dist
                labels[yy, xx] = labels[y, x]
                queue.append((yy, xx))

    out = arr.copy()
    out[bad, :3] = labels[bad]
    return Image.fromarray(out, "RGBA"), count


def _rgb(hexv: str):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _snap_out_of_palette(image: Image.Image, palette_rgb: list[tuple[int, int, int]]):
    arr = np.array(image.convert("RGBA"))
    opaque = arr[:, :, 3] >= 128
    allowed = set(palette_rgb)
    repaired = 0
    for y, x in zip(*np.where(opaque)):
        col = tuple(int(v) for v in arr[y, x, :3])
        if col in allowed:
            continue
        r, g, b = col
        best = min(
            palette_rgb,
            key=lambda p: 2*(r-p[0])**2 + 4*(g-p[1])**2 + 3*(b-p[2])**2
        )
        arr[y, x, :3] = best
        repaired += 1
    return Image.fromarray(arr, "RGBA"), repaired


def main():
    designs = json.loads(DESIGNS_PATH.read_text(encoding="utf-8"))["designs"]
    collection = json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))
    palette_rgb = [_rgb(p["hex"]) for p in collection["palette"]]
    report = []

    for design in designs:
        bid = design["base_design_id"]
        source = SYSTEM / design["source_asset"]
        if not source.is_file():
            raise RuntimeError(f"{bid}: source missing: {source}")

        image = Image.open(source).convert("RGBA")
        if image.size != (100, 120):
            raise RuntimeError(f"{bid}: expected 100x120, got {image.size}")

        if bid in ALL_BLUE_REPAIR_IDS:
            bad = ALL_BLUE
            policy = "all-blue"
        elif bid in PALE_BLUE_REPAIR_IDS:
            bad = PALE_BLUE
            policy = "pale-blue"
        else:
            bad = set()
            policy = "preserve"

        repaired, count = repair_nearest(image, bad) if bad else (image, 0)
        repaired, snapped = _snap_out_of_palette(repaired, palette_rgb)
        repaired.save(source, "PNG", optimize=True)

        colours = {
            (r, g, b)
            for r, g, b, a in repaired.getdata()
            if a >= 128
        }
        if bid in ALL_BLUE_REPAIR_IDS and colours & ALL_BLUE:
            raise RuntimeError(f"{bid}: blue artefact remains after repair")
        if bid in PALE_BLUE_REPAIR_IDS and colours & PALE_BLUE:
            raise RuntimeError(f"{bid}: pale-blue artefact remains after repair")

        report.append({
            "base_design_id": bid,
            "policy": policy,
            "pixels_repaired": count,
            "out_of_palette_pixels_snapped": snapped,
            "source_asset": design["source_asset"],
        })
        if count or snapped:
            print(bid, policy, "pixels_repaired", count, "palette_snapped", snapped)

    out = SYSTEM / "florals" / "artwork_quality_review.json"
    out.write_text(
        json.dumps({
            "collection": "florals",
            "status": "blue-artifact-repair-applied",
            "auto_publish": False,
            "published_offenders_for_qa": ["F0002", "F0003", "F0004"],
            "report": report,
            "next_action": "Review QA renders before resuming WooCommerce publication",
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("FLORALS_BLUE_ARTIFACT_REPAIR_COMPLETE")


if __name__ == "__main__":
    main()
