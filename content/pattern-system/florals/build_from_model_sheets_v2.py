#!/usr/bin/env python3
from __future__ import annotations

import colorsys
import json
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "florals"
DESIGNS = COL / "designs.json"
COLLECTION = COL / "collection.json"
SOURCE_DIR = COL / "source-designs"
MANIFEST = SOURCE_DIR / "manifest.json"
MODEL_DIR = COL / "model-sheets-v2"

SHEETS = [
    ("model1.png", 1),
    ("model2.png", 7),
    ("model3.png", 13),
    ("model4.png", 19),
    ("model5.png", 25),
]

FAMILY_INDEXES = {
    "cream": [0, 1, 2],
    "brown": [3, 4, 5],
    "green": [6, 7, 8, 9, 10, 11],
    "blue": [12, 13, 14],
    "purple": [15, 16, 17],
    "yellow": [18, 19],
    "pink": [20, 21, 22, 23],
}

ALLOWED_FAMILIES = {
    1: {"cream","brown","green","blue","yellow"},
    2: {"cream","brown","green","yellow","pink"},
    3: {"cream","brown","green","purple"},
    4: {"cream","brown","green","yellow"},
    5: {"cream","green","blue","yellow"},
    6: {"cream","brown","green","yellow","pink"},
    7: {"cream","green","yellow","pink"},
    8: {"cream","brown","green","blue","yellow"},
    9: {"cream","brown","green"},
    10: {"cream","brown","green","yellow","pink"},
    11: {"cream","brown","green","purple","yellow","pink"},
    12: {"cream","brown","green","blue","yellow","pink"},
    13: {"cream","brown","green","pink"},
    14: {"cream","brown","green","pink"},
    15: {"cream","brown","green","blue","pink"},
    16: {"cream","brown","green","yellow"},
    17: {"cream","brown","green","purple","yellow"},
    18: {"cream","brown","green","blue","purple"},
    19: {"cream","brown","green","yellow"},
    20: {"cream","brown","green","blue","yellow","pink"},
    21: {"cream","brown","green","yellow","pink"},
    22: {"cream","brown","green","blue","purple","yellow"},
    23: {"cream","brown","green","pink"},
    24: {"cream","brown","green","blue"},
    25: {"cream","green","yellow"},
    26: {"cream","brown","green","blue","purple","yellow","pink"},
    27: {"cream","brown","green","blue"},
    28: {"cream","brown","green","pink"},
    29: {"cream","brown","green","blue","purple","pink"},
    30: {"cream","brown","green","blue","purple","yellow"},
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rgb(hexv: str):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def nearest_index(rgbv, candidates, palette):
    c = np.array(rgbv, dtype=np.int16)
    arr = palette[np.array(candidates, dtype=int)]
    diff = arr - c
    dist = (diff * diff * np.array([2, 4, 3], dtype=np.int16)).sum(axis=1)
    return int(candidates[int(np.argmin(dist))])


def classify_family(rgbv, allowed, palette):
    r, g, b = [v / 255.0 for v in rgbv]
    hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
    deg = hue * 360.0

    if sat < 0.14:
        if val > 0.68 and "cream" in allowed:
            fam = "cream"
        elif "brown" in allowed:
            fam = "brown"
        elif "green" in allowed:
            fam = "green"
        else:
            fam = sorted(allowed)[0]
    elif 25 <= deg < 75:
        fam = "yellow" if val > 0.55 and sat > 0.25 else "brown"
    elif 75 <= deg < 175:
        fam = "green"
    elif 175 <= deg < 255:
        fam = "blue"
    elif 255 <= deg < 330:
        fam = "purple"
    else:
        fam = "pink"

    if fam in allowed:
        return fam

    best = None
    for candidate in allowed:
        inds = FAMILY_INDEXES[candidate]
        centroid = palette[np.array(inds)].mean(axis=0)
        dist = float(((centroid - np.array(rgbv)) ** 2).sum())
        if best is None or dist < best[0]:
            best = (dist, candidate)
    return best[1]


def keep_largest_component(canvas):
    arr = np.array(canvas.convert("RGBA"))
    mask = arr[:, :, 3] >= 128
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    components = []

    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        q = deque([(int(y), int(x))])
        seen[y, x] = True
        pts = []
        while q:
            yy, xx = q.popleft()
            pts.append((yy, xx))
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                y2, x2 = yy + dy, xx + dx
                if 0 <= y2 < h and 0 <= x2 < w and mask[y2, x2] and not seen[y2, x2]:
                    seen[y2, x2] = True
                    q.append((y2, x2))
        components.append(pts)

    if not components:
        raise RuntimeError("Generated source is empty")
    components.sort(key=len, reverse=True)

    clean = np.zeros_like(arr)
    for y, x in components[0]:
        clean[y, x] = arr[y, x]
    return Image.fromarray(clean, "RGBA"), [len(x) for x in components]


def build_source(cell, design_number, palette):
    src = cell.convert("RGBA")
    raw = np.array(src)
    visible = raw[:, :, 3] >= 180
    if not visible.any():
        visible = raw[:, :, 3] >= 128
    ys, xs = np.where(visible)
    crop = src.crop((
        max(0, int(xs.min()) - 4),
        max(0, int(ys.min()) - 4),
        min(src.width, int(xs.max()) + 5),
        min(src.height, int(ys.max()) + 5),
    ))

    scale = min(92 / crop.width, 112 / crop.height)
    nw = max(1, round(crop.width * scale))
    nh = max(1, round(crop.height * scale))

    # BOX removes the glossy pixel-tile highlight/noise from the generated model
    # while retaining its shape. This is the key difference from the old pipeline.
    small = crop.resize((nw, nh), Image.Resampling.BOX)
    sa = np.array(small)
    opaque = sa[:, :, 3] >= 100

    allowed = ALLOWED_FAMILIES[design_number]
    family = np.empty((nh, nw), dtype=object)
    for y, x in zip(*np.where(opaque)):
        family[y, x] = classify_family(sa[y, x, :3], allowed, palette)

    # Neutral highlights fully inside one chromatic region inherit that region's hue.
    # True white petals and background edges remain cream because they touch transparency.
    for y, x in zip(*np.where(opaque)):
        rr, gg, bb = [float(v) / 255.0 for v in sa[y, x, :3]]
        _, sat, val = colorsys.rgb_to_hsv(rr, gg, bb)
        if sat >= 0.18 or val <= 0.60:
            continue
        y0, y1 = max(0, y - 3), min(nh, y + 4)
        x0, x1 = max(0, x - 3), min(nw, x + 4)
        neighbours = [
            family[yy, xx]
            for yy in range(y0, y1)
            for xx in range(x0, x1)
            if opaque[yy, xx] and family[yy, xx] not in (None, "cream")
        ]
        if len(neighbours) < 10:
            continue
        fam, count = Counter(neighbours).most_common(1)[0]
        local = opaque[max(0, y-1):min(nh, y+2), max(0, x-1):min(nw, x+2)]
        if count / len(neighbours) >= 0.72 and local.all():
            family[y, x] = fam

    full = np.full((120, 100), -1, dtype=np.int16)
    ox = (100 - nw) // 2
    oy = (120 - nh) // 2

    for y, x in zip(*np.where(opaque)):
        fam = family[y, x]
        idx = nearest_index(sa[y, x, :3], FAMILY_INDEXES[fam], palette)
        full[oy + y, ox + x] = idx

    # Keep at most 14 DMC shades for usable charts, remapping dropped shades within
    # their own hue family whenever possible.
    vals, counts = np.unique(full[full >= 0], return_counts=True)
    if len(vals) > 14:
        keep = list(vals[np.argsort(counts)[::-1][:14]])
        for val in vals:
            val = int(val)
            if val in keep:
                continue
            fam = next(name for name, inds in FAMILY_INDEXES.items() if val in inds)
            candidates = [k for k in keep if k in FAMILY_INDEXES[fam]] or keep
            replacement = nearest_index(palette[val], candidates, palette)
            full[full == val] = replacement

    canvas = np.zeros((120, 100, 4), dtype=np.uint8)
    mask = full >= 0
    canvas[mask, :3] = palette[full[mask]]
    canvas[mask, 3] = 255

    clean, components = keep_largest_component(Image.fromarray(canvas, "RGBA"))
    return clean, components


def main():
    collection = read_json(COLLECTION)
    designs_doc = read_json(DESIGNS)
    palette = np.array([rgb(p["hex"]) for p in collection["palette"]], dtype=np.int16)
    if len(palette) != 24:
        raise RuntimeError(f"Florals palette must contain 24 colours, got {len(palette)}")

    by_id = {d["base_design_id"]: d for d in designs_doc["designs"]}
    if len(by_id) != 30:
        raise RuntimeError(f"Expected 30 Florals designs, got {len(by_id)}")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    report = []

    for sheet_name, start in SHEETS:
        path = MODEL_DIR / sheet_name
        if not path.is_file():
            raise RuntimeError(f"Missing model-v2 sheet: {path}")
        sheet = Image.open(path).convert("RGBA")
        width, height = sheet.size

        for slot in range(6):
            number = start + slot
            base_id = f"F{number:04d}"
            design = by_id[base_id]
            row, col = divmod(slot, 3)
            x0 = round(col * width / 3)
            x1 = round((col + 1) * width / 3)
            y0 = round(row * height / 2)
            y1 = round((row + 1) * height / 2)

            source, components = build_source(sheet.crop((x0, y0, x1, y1)), number, palette)
            filename = f"{base_id}-{design['slug']}.png"
            source_path = SOURCE_DIR / filename
            source.save(source_path, "PNG", optimize=True)

            used = set()
            pixels = np.array(source)
            opaque = pixels[:, :, 3] >= 128
            for idx, colour in enumerate(palette):
                if np.any(opaque & np.all(pixels[:, :, :3] == colour, axis=2)):
                    used.add(idx)
            if not (1 <= len(used) <= 14):
                raise RuntimeError(f"{base_id}: invalid colour count {len(used)}")
            if source.size != (100, 120) or source.getchannel("A").getbbox() is None:
                raise RuntimeError(f"{base_id}: invalid canonical source")

            design["source_asset"] = f"collections/florals/source-designs/{filename}"
            design["reference_asset"] = design["source_asset"]
            design["artwork_status"] = "approved-model-v2-source-ready"
            design["pattern_source_policy"] = "models-v2 hue-aware transparent 100x120 source"

            report.append({
                "base_design_id": base_id,
                "model_sheet": sheet_name,
                "slot": slot + 1,
                "source_asset": design["source_asset"],
                "colors": len(used),
                "discarded_components": components[1:],
            })
            print(base_id, "colors", len(used), "discarded", components[1:4])

    write_json(DESIGNS, designs_doc)

    if MANIFEST.is_file():
        manifest = read_json(MANIFEST)
    else:
        manifest = {"collection": "florals", "designs": []}
    manifest_by_id = {x.get("base_design_id"): x for x in manifest.get("designs", [])}
    for row in report:
        entry = manifest_by_id.get(row["base_design_id"])
        if entry is None:
            entry = {"base_design_id": row["base_design_id"]}
            manifest.setdefault("designs", []).append(entry)
        entry["source_asset"] = row["source_asset"]
        entry["status"] = "approved-model-v2-source-ready"
        entry["model_sheet"] = row["model_sheet"]
        entry["model_slot"] = row["slot"]
    manifest["status"] = "all-30-model-v2-sources-ready"
    manifest["source"] = "five user-approved model-v2 sheets"
    manifest["master_grid"] = {"width": 100, "height": 120, "unit": "cross-stitch cells"}
    write_json(MANIFEST, manifest)

    write_json(SYSTEM / "florals" / "models_v2_report.json", {
        "collection": "florals",
        "version": 2,
        "design_count": len(report),
        "source_policy": "transparent hue-aware palette mapping; largest connected motif only; max 14 colours",
        "items": report,
    })

    if len(report) != 30:
        raise RuntimeError(f"Expected 30 sources, built {len(report)}")
    print("FLORALS_MODELS_V2_SOURCES_READY=30")


if __name__ == "__main__":
    main()
