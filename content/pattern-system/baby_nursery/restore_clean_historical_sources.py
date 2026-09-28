#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections" / "baby-nursery"
PRODUCTS = SOURCE_ROOT / "products"
PALETTE_PATH = SOURCE_ROOT / "palette50_dmc.json"
MANIFEST_PATH = SOURCE_ROOT / "source-manifest.json"
QA_PATH = SOURCE_ROOT / "qa_report.json"
DESIGNS_PATH = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "designs.json"
REPORT_PATH = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "clean-regeneration-2026-09-28.json"

HISTORICAL_COMMIT = "fbf67f7425153f1955abc6cd87dedd2953e5fc56"
TARGETS = {
    "I0021": "I0021-whale.png",
    "I0026": "I0026-long-neck-dinosaur.png",
    "I0027": "I0027-triceratops.png",
    "I0029": "I0029-stegosaurus.png",
    "I0043": "I0043-rainbow-clouds.png",
}
MAX_ART_W = 78
MAX_ART_H = 96


def git_show_bytes(relpath: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{HISTORICAL_COMMIT}:{relpath}"],
        cwd=ROOT,
    )


def palette():
    doc = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
    rows = doc["colors"]
    return [
        {
            "rgb": tuple(int(v) for v in row["rgb"]),
            "dmc": str(row["dmc"]),
        }
        for row in rows
    ]


def nearest(rgb, pal):
    r, g, b = rgb
    return min(
        pal,
        key=lambda p: (
            2 * (r - p["rgb"][0]) ** 2
            + 4 * (g - p["rgb"][1]) ** 2
            + 3 * (b - p["rgb"][2]) ** 2
        ),
    )


def connected_components(im: Image.Image):
    a = list(im.getchannel("A").getdata())
    w, h = im.size
    mask = [v >= 128 for v in a]
    seen = set()
    out = []
    for y in range(h):
        for x in range(w):
            if not mask[y*w+x] or (x, y) in seen:
                continue
            q = deque([(x, y)])
            seen.add((x, y))
            pts = []
            while q:
                px, py = q.popleft()
                pts.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h and mask[ny*w+nx] and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            q.append((nx, ny))
            out.append(pts)
    out.sort(key=len, reverse=True)
    return out


def remove_tiny_islands(im: Image.Image, max_pixels: int = 12):
    rgba = im.copy()
    comps = connected_components(rgba)
    removed = []
    px = rgba.load()
    # Only remove truly tiny disconnected artifacts. Never remove a meaningful
    # design component such as a cloud, splash, horn, or tail.
    for comp in comps[1:]:
        if len(comp) <= max_pixels:
            removed.append(len(comp))
            for x, y in comp:
                px[x, y] = (0, 0, 0, 0)
    return rgba, removed


def normalize_full_art(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("empty historical artwork")
    crop = im.crop(bbox)
    w, h = crop.size
    scale = min(1.0, MAX_ART_W / w, MAX_ART_H / h)
    nw = max(1, round(w * scale))
    nh = max(1, round(h * scale))
    if (nw, nh) != (w, h):
        crop = crop.resize((nw, nh), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
    x = (100 - nw) // 2
    y = (120 - nh) // 2
    canvas.alpha_composite(crop, (x, y))
    return canvas, scale


def map_to_dmc(im: Image.Image, pal):
    rgba = im.convert("RGBA")
    out = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    src = rgba.load()
    dst = out.load()
    cache = {}
    used = {}
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = src[x, y]
            if a < 128:
                continue
            key = (r, g, b)
            if key not in cache:
                cache[key] = nearest(key, pal)
            p = cache[key]
            dst[x, y] = (*p["rgb"], 255)
            used[p["dmc"]] = p["rgb"]
    return out, sorted(used)


def metrics(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("empty normalized artwork")
    l, t, r, b = bbox
    m = {"left": l, "top": t, "right": im.width-r, "bottom": im.height-b}
    return list(bbox), m


def main():
    pal = palette()
    designs = json.loads(DESIGNS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    by_design = {d["base_design_id"]: d for d in designs["designs"]}
    by_manifest = {p["id"]: p for p in manifest["products"]}

    report = []
    for base, filename in TARGETS.items():
        rel = f"content/source-images/collections/baby-nursery/products/{filename}"
        raw = git_show_bytes(rel)
        temp = ROOT / f".tmp-{filename}"
        temp.write_bytes(raw)
        try:
            original = Image.open(temp).convert("RGBA")
        finally:
            temp.unlink(missing_ok=True)

        if original.size != (100, 120):
            raise RuntimeError(f"{base}: historical source is {original.size}, expected 100x120")

        # Historical I0027 contains a tiny detached residue at the far left.
        # Removing tiny disconnected islands preserves the complete animal while
        # eliminating that artifact. No pixels are cloned or moved.
        cleaned, removed = remove_tiny_islands(original, 40 if base == "I0027" else 12)
        normalized, scale = normalize_full_art(cleaned)
        mapped, codes = map_to_dmc(normalized, pal)
        bbox, m = metrics(mapped)

        if min(m.values()) < 11:
            raise RuntimeError(f"{base}: insufficient safe margin after clean regeneration: {m}")
        if abs(m["left"] - m["right"]) > 2 or abs(m["top"] - m["bottom"]) > 2:
            raise RuntimeError(f"{base}: not centered after clean regeneration: {m}")

        out = PRODUCTS / filename
        mapped.save(out, "PNG", optimize=False)

        colors = {rgb for rgb in mapped.getdata() if rgb[3] == 255}
        by_manifest[base]["color_count"] = len(colors)
        by_manifest[base]["dmc_codes"] = codes
        by_design[base]["source_colour_count"] = len(colors)
        idx = int(base[1:]) - 1
        qa["files"][idx]["colors_used"] = len(colors)
        qa["files"][idx]["margins"] = m

        report.append({
            "id": base,
            "filename": filename,
            "source_commit": HISTORICAL_COMMIT,
            "method": "restore complete historical artwork -> remove only tiny detached islands -> uniformly downscale whole artwork -> center -> nearest DMC50 mapping",
            "tiny_islands_removed": removed,
            "scale": scale,
            "bbox": bbox,
            "margins": m,
            "dmc_codes": codes,
        })
        print("CLEAN_SOURCE", base, "scale", scale, "margins", m, "removed", removed)

    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DESIGNS_PATH.write_text(json.dumps(designs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        json.dumps(
            {
                "version": "historical-clean-v1",
                "historical_commit": HISTORICAL_COMMIT,
                "targets": report,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
