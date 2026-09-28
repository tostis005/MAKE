#!/usr/bin/env python3
from __future__ import annotations

import colorsys
import io
import json
import math
import re
import subprocess
import zipfile
from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path.cwd()
SRC = ROOT / "content" / "pattern-system" / "collections" / "pop-art-25" / "sources"
DESIGNS_JSON = ROOT / "content" / "pattern-system" / "collections" / "pop-art-25" / "designs.json"
OUT_DIR = ROOT / "exports" / "pop-art-portraits-final"
ZIP_PATH = ROOT / "exports" / "pop-art-portraits-60-100x120.zip"
PREVIEW_PATH = ROOT / "exports" / "pop-art-portraits-60-preview.png"
LEGACY_REF = "ecdabb6f62722ac3533c31f375f0053e46cbac75"

W, H = 100, 120
TOTAL_STITCHES = W * H

# Six current designs that are not human portraits.  We intentionally reuse
# earlier approved Pop Art portrait sources so replacements match the visual
# language and can be harmonised into the same exact 30-colour palette.
REPLACEMENTS = {
    "P1031": {
        "legacy_code": "P0003",
        "title_en": "Bubble Gum Elegance Portrait",
        "title_es": "Retrato elegante con chicle",
        "slug": "bubble-gum-elegance-portrait",
    },
    "P1032": {
        "legacy_code": "P0004",
        "title_en": "Elegant Profile Portrait",
        "title_es": "Retrato elegante de perfil",
        "slug": "elegant-profile-portrait",
    },
    "P1043": {
        "legacy_code": "P0011",
        "title_en": "Blowing Kiss Glam Portrait",
        "title_es": "Retrato glam lanzando un beso",
        "slug": "blowing-kiss-glam-portrait",
    },
    "P1057": {
        "legacy_code": "P0019",
        "title_en": "Post-Impressionist Artist Portrait",
        "title_es": "Retrato de artista postimpresionista",
        "slug": "post-impressionist-artist-portrait",
    },
    "P1059": {
        "legacy_code": "P0022",
        "title_en": "Royal Bubble Gum Portrait",
        "title_es": "Retrato real con chicle",
        "slug": "royal-bubble-gum-portrait",
    },
    "P1060": {
        "legacy_code": "P0008",
        "title_en": "Pearl Earring Bubble Gum Portrait",
        "title_es": "Retrato con pendiente de perla y chicle",
        "slug": "pearl-earring-bubble-gum-portrait",
    },
}

def rgb_distance(a, b):
    return sum((int(a[i]) - int(b[i])) ** 2 for i in range(3))

def hsv(rgb):
    r, g, b = [v / 255 for v in rgb]
    return colorsys.rgb_to_hsv(r, g, b)

def is_bright_saturated(rgb):
    h, s, v = hsv(rgb)
    return s >= 0.56 and v >= 0.62

def load_current_images():
    images = {}
    for i in range(1001, 1061):
        code = f"P{i:04d}"
        p = SRC / f"{code}.png"
        if not p.is_file():
            raise RuntimeError(f"Missing current source {p}")
        im = Image.open(p).convert("RGB")
        if im.size != (W, H):
            raise RuntimeError(f"{p.name}: expected {W}x{H}, got {im.size}")
        images[code] = im
    return images

def load_legacy(code):
    staged = ROOT / "tmp" / "pop-art-legacy" / f"{code}.png"
    if staged.is_file():
        im = Image.open(staged).convert("RGB")
    else:
        path = f"content/pattern-system/collections/pop-art-25/sources/{code}.png"
        raw = subprocess.check_output(["git", "show", f"{LEGACY_REF}:{path}"])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.size != (W, H):
        raise RuntimeError(f"Legacy {code}: expected {W}x{H}, got {im.size}")
    return im

def current_palette(images):
    colors = set()
    for im in images.values():
        colors.update(im.getdata())
    if len(colors) != 30:
        raise RuntimeError(f"Current Pop Art source union has {len(colors)} colours; expected exactly 30")
    return sorted(colors)

def quantize_to_palette(im, palette_rgb):
    pal = Image.new("P", (1, 1))
    flat = []
    for c in palette_rgb:
        flat.extend(c)
    flat += [0] * (768 - len(flat))
    pal.putpalette(flat)
    q = im.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE)
    return q.convert("RGB")

def border_pixels(im):
    px = im.load()
    vals = []
    for x in range(W):
        vals.append(px[x, 0]); vals.append(px[x, H-1])
    for y in range(1, H-1):
        vals.append(px[0, y]); vals.append(px[W-1, y])
    return vals

def choose_background_candidates(images, palette_rgb):
    counts = Counter()
    for im in images.values():
        counts.update(border_pixels(im))

    # Prefer vivid colours that recur on many outer edges. These are the
    # background block colours in the source collection. Keep enough candidates
    # to cross colour-to-colour joins in the multicolour backgrounds.
    ranked = [c for c, _ in counts.most_common() if c in palette_rgb and is_bright_saturated(c)]
    if len(ranked) < 7:
        ranked = [c for c, _ in counts.most_common() if c in palette_rgb]
    candidates = ranked[:10]
    if len(candidates) < 5:
        raise RuntimeError("Could not identify enough background candidate colours")
    return candidates, counts

def border_reachable_mask(im, candidates):
    pix = im.load()
    allowed = set(candidates)
    seen = [[False] * W for _ in range(H)]
    q = deque()

    def add(x, y):
        if not seen[y][x] and pix[x, y] in allowed:
            seen[y][x] = True
            q.append((x, y))

    for x in range(W):
        add(x, 0); add(x, H-1)
    for y in range(H):
        add(0, y); add(W-1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and pix[nx, ny] in allowed:
                seen[ny][nx] = True
                q.append((nx, ny))

    # Guarantee that the image perimeter is background. This removes any
    # accidental black frame/edge while costing only one pixel of the artwork.
    for x in range(W):
        seen[0][x] = True
        seen[H-1][x] = True
    for y in range(H):
        seen[y][0] = True
        seen[y][W-1] = True

    return seen

def enlarge_bg_mask(mask, im, candidates):
    # Remove residual candidate-colour islands outside the face/core portrait.
    # This helps make gaps around shoulders/hair read as one solid background.
    pix = im.load()
    allowed = set(candidates)
    visited = [[False] * W for _ in range(H)]

    for y in range(H):
        for x in range(W):
            if visited[y][x] or mask[y][x] or pix[x, y] not in allowed:
                continue
            comp = []
            q = deque([(x, y)])
            visited[y][x] = True
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for nx, ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                    if 0 <= nx < W and 0 <= ny < H and not visited[ny][nx] and not mask[ny][nx] and pix[nx, ny] in allowed:
                        visited[ny][nx] = True
                        q.append((nx, ny))

            # Protect the core face rectangle from over-cleaning. Elsewhere,
            # sufficiently large islands are background fragments.
            intersects_face = any(27 <= cx <= 73 and 22 <= cy <= 82 for cx, cy in comp)
            if len(comp) >= 20 and not intersects_face:
                for cx, cy in comp:
                    mask[cy][cx] = True
    return mask

def nearest_other_colour(rgb, palette_rgb, forbidden):
    choices = [c for c in palette_rgb if c != forbidden]
    return min(choices, key=lambda c: rgb_distance(rgb, c))

def select_bg_colour(im, mask, candidate_colours, palette_rgb, index):
    # Prefer vivid palette colours with very low foreground usage. This makes
    # background colour exclusive, so "stitches without background" can be
    # computed simply and exactly.
    fg_counts = Counter()
    px = im.load()
    for y in range(H):
        for x in range(W):
            if not mask[y][x]:
                fg_counts[px[x, y]] += 1

    vivid = [c for c in candidate_colours if is_bright_saturated(c)]
    if not vivid:
        vivid = list(candidate_colours)

    ranked = sorted(
        vivid,
        key=lambda c: (fg_counts[c], -sum(rgb_distance(c, other) for other in palette_rgb) / len(palette_rgb))
    )
    # Among the best low-usage options, rotate for collection variety.
    pool = ranked[:min(4, len(ranked))]
    return pool[index % len(pool)]

def harmonise_one(im, palette_rgb, candidates, index):
    # Legacy replacements are first snapped to the exact current 30-colour palette.
    im = quantize_to_palette(im, palette_rgb)
    mask = border_reachable_mask(im, candidates)
    mask = enlarge_bg_mask(mask, im, candidates)

    bg = select_bg_colour(im, mask, candidates, palette_rgb, index)
    px = im.load()

    # Make the selected background colour exclusive to background pixels.
    remap = nearest_other_colour(bg, palette_rgb, bg)
    for y in range(H):
        for x in range(W):
            if mask[y][x]:
                px[x, y] = bg
            elif px[x, y] == bg:
                px[x, y] = remap

    # Remove only an actual dark outer frame: if most of an edge is near-black,
    # replace its second pixel line too. Internal black facial detail is kept.
    def dark(c):
        return max(c) <= 55

    edges = [
        ([(x,0) for x in range(W)], [(x,1) for x in range(W)]),
        ([(x,H-1) for x in range(W)], [(x,H-2) for x in range(W)]),
        ([(0,y) for y in range(H)], [(1,y) for y in range(H)]),
        ([(W-1,y) for y in range(H)], [(W-2,y) for y in range(H)]),
    ]
    for edge, inner in edges:
        ratio = sum(1 for x,y in edge if dark(px[x,y])) / len(edge)
        if ratio >= 0.65:
            for x,y in edge + inner:
                px[x,y] = bg
                mask[y][x] = True

    # Hard guarantee: one-pixel perimeter is the same solid background colour.
    for x in range(W):
        px[x, 0] = bg; mask[0][x] = True
        px[x, H-1] = bg; mask[H-1][x] = True
    for y in range(H):
        px[0, y] = bg; mask[y][0] = True
        px[W-1, y] = bg; mask[y][W-1] = True

    # Recheck exclusivity.
    for y in range(H):
        for x in range(W):
            if not mask[y][x] and px[x,y] == bg:
                px[x,y] = remap

    bg_stitches = sum(1 for row in mask for v in row if v)
    return im, bg, bg_stitches

def load_design_metadata():
    data = json.loads(DESIGNS_JSON.read_text(encoding="utf-8"))
    rows = {}
    for d in data.get("designs", []):
        code = d.get("code")
        if code and re.fullmatch(r"P10\d{2}", code):
            rows[code] = {
                "title_en": d.get("title_en") or code,
                "title_es": d.get("title_es") or d.get("title_en") or code,
                "slug": d.get("slug") or code.lower(),
            }
    return rows

def save_preview(processed, metadata):
    cols, rows = 10, 6
    label_h = 18
    scale = 2
    tile_w = W * scale
    tile_h = H * scale + label_h
    canvas = Image.new("RGB", (cols * tile_w, rows * tile_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    for idx, code in enumerate(sorted(processed)):
        im = processed[code].resize((W*scale, H*scale), Image.Resampling.NEAREST)
        x = (idx % cols) * tile_w
        y = (idx // cols) * tile_h
        canvas.paste(im, (x, y))
        label = f"{code} {metadata[code]['title_en'][:20]}"
        draw.text((x+3, y + H*scale + 3), label, fill="black", font=font)
    canvas.save(PREVIEW_PATH)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            p.unlink()

    current = load_current_images()
    palette_rgb = current_palette(current)
    candidates, border_counts = choose_background_candidates(current, palette_rgb)

    metadata = load_design_metadata()

    working = dict(current)
    for code, spec in REPLACEMENTS.items():
        working[code] = load_legacy(spec["legacy_code"])
        metadata[code] = {
            "title_en": spec["title_en"],
            "title_es": spec["title_es"],
            "slug": spec["slug"],
        }

    processed = {}
    manifest_designs = []

    for idx, code in enumerate(sorted(working)):
        out, bg, bg_stitches = harmonise_one(working[code], palette_rgb, candidates, idx)
        out_path = OUT_DIR / f"{code}.png"
        out.save(out_path, "PNG", optimize=True)
        processed[code] = out

        manifest_designs.append({
            "code": code,
            "filename": f"{code}.png",
            "title_en": metadata[code]["title_en"],
            "title_es": metadata[code]["title_es"],
            "slug": metadata[code]["slug"],
            "width": W,
            "height": H,
            "stitches_total": TOTAL_STITCHES,
            "background_rgb": list(bg),
            "background_hex": "#%02X%02X%02X" % bg,
            "background_stitches": bg_stitches,
            "stitches_without_background": TOTAL_STITCHES - bg_stitches,
            "portrait": True,
            "solid_background": True,
            "replacement": code in REPLACEMENTS,
        })

    # Technical QA.
    union = set()
    for code, im in processed.items():
        if im.size != (W, H):
            raise RuntimeError(f"{code}: invalid output size")
        union.update(im.getdata())

        # No black/dark rectangular frame: perimeter cannot have a long dark run.
        px = im.load()
        edges = [
            [px[x,0] for x in range(W)],
            [px[x,H-1] for x in range(W)],
            [px[0,y] for y in range(H)],
            [px[W-1,y] for y in range(H)],
        ]
        for edge in edges:
            if sum(1 for c in edge if max(c) <= 55) > len(edge) * 0.25:
                raise RuntimeError(f"{code}: dark outer border remains")

    if not union.issubset(set(palette_rgb)):
        raise RuntimeError("Outputs use colours outside the common 30-colour palette")
    if len(union) != 30:
        raise RuntimeError(f"Final 60-image union has {len(union)} colours; expected exactly 30")

    manifest = {
        "schema": "drielo.pop-art-portraits.v1",
        "collection_id": "pop-art-25",
        "collection_title_en": "Pop Art Portraits",
        "collection_title_es": "Retratos Pop Art",
        "design_count": 60,
        "image_size": [W, H],
        "shared_palette_size": 30,
        "palette_rgb": [list(c) for c in palette_rgb],
        "palette_hex": ["#%02X%02X%02X" % c for c in palette_rgb],
        "all_portraits": True,
        "solid_background_per_design": True,
        "outer_black_frame": False,
        "stitch_count_rule": {
            "total": TOTAL_STITCHES,
            "without_background": "total pixels minus the design's solid background pixels",
            "background_colour_is_exclusive": True,
        },
        "replaced_non_portrait_codes": sorted(REPLACEMENTS),
        "designs": manifest_designs,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    save_preview(processed, metadata)

    ZIP_PATH.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for code in sorted(processed):
            zf.write(OUT_DIR / f"{code}.png", arcname=f"{code}.png")
        zf.write(OUT_DIR / "manifest.json", arcname="manifest.json")

    # ZIP QA: exactly 60 PNG + manifest.
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        if len([n for n in names if n.endswith(".png")]) != 60 or "manifest.json" not in names:
            raise RuntimeError("ZIP contents are incomplete")

    print("PALETTE", [list(c) for c in palette_rgb])
    print("BACKGROUND_CANDIDATES", [list(c) for c in candidates])
    print("REPLACED", sorted(REPLACEMENTS))
    print("ZIP", ZIP_PATH, ZIP_PATH.stat().st_size)
    print("PREVIEW", PREVIEW_PATH)

if __name__ == "__main__":
    main()
