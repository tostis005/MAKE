#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "content" / "source-images" / "collections" / "baby-nursery" / "products"
REPORT = ROOT / "content" / "pattern-system" / "collections" / "baby-nursery" / "shape-repair-2026-09-28.json"

TARGETS = {
    "I0021": "I0021-whale.png",
    "I0026": "I0026-long-neck-dinosaur.png",
    "I0027": "I0027-triceratops.png",
    "I0029": "I0029-stegosaurus.png",
    "I0043": "I0043-rainbow-clouds.png",
}
MAX_ART_W = 80
MAX_ART_H = 100


def alpha_bbox(im: Image.Image):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("empty artwork")
    return bbox


def margins(im: Image.Image):
    l, t, r, b = alpha_bbox(im)
    return {
        "left": l,
        "top": t,
        "right": im.width - r,
        "bottom": im.height - b,
    }


def normalize(im: Image.Image):
    bbox = alpha_bbox(im)
    crop = im.crop(bbox)
    w, h = crop.size
    scale = min(1.0, MAX_ART_W / w, MAX_ART_H / h)
    nw = max(1, round(w * scale))
    nh = max(1, round(h * scale))
    if (nw, nh) != (w, h):
        crop = crop.resize((nw, nh), Image.Resampling.NEAREST)
    out = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
    x = (100 - nw) // 2
    y = (120 - nh) // 2
    out.alpha_composite(crop, (x, y))
    return out, {"scale": scale, "art_size": [nw, nh], "margins": margins(out)}


def repair_whale(im: Image.Image):
    d = ImageDraw.Draw(im)
    outline = (27, 40, 83, 255)
    body = (90, 143, 184, 255)
    highlight = (147, 180, 206, 255)
    d.rectangle((80, 52, 99, 80), fill=(0, 0, 0, 0))
    d.polygon(
        [(74,61),(81,61),(86,58),(93,54),(97,55),(97,59),(93,63),(89,65),
         (93,67),(97,67),(97,72),(94,76),(90,75),(85,71),(81,70),(77,72),(73,69)],
        fill=outline,
    )
    d.polygon(
        [(76,62),(81,63),(87,60),(93,56),(95,56),(95,59),(91,63),(87,65),
         (91,68),(95,68),(95,71),(93,73),(89,72),(85,69),(81,68),(78,70),(75,68)],
        fill=body,
    )
    d.polygon([(88,59),(93,57),(94,57),(92,60),(89,62)], fill=highlight)
    return im


def repair_long_neck(im: Image.Image):
    d = ImageDraw.Draw(im)
    outline = (49, 57, 25, 255)
    body = (148, 171, 79, 255)
    beige = (236, 204, 158, 255)
    d.rectangle((80, 74, 99, 92), fill=(0, 0, 0, 0))
    d.polygon(
        [(72,76),(80,77),(87,79),(93,80),(98,81),(99,83),(97,85),(92,86),
         (87,88),(80,89),(75,88),(72,85)],
        fill=outline,
    )
    d.polygon(
        [(74,78),(81,79),(87,80),(93,82),(96,82),(97,83),(94,84),(88,86),
         (81,87),(76,86),(74,84)],
        fill=body,
    )
    d.polygon([(88,85),(94,84),(92,85),(88,86)], fill=beige)
    return im


def repair_triceratops(im: Image.Image):
    d = ImageDraw.Draw(im)
    outline = (54, 31, 14, 255)
    body = (255, 163, 43, 255)
    shade = (226, 115, 35, 255)
    d.rectangle((80, 68, 99, 88), fill=(0, 0, 0, 0))
    d.polygon(
        [(74,69),(82,70),(88,72),(94,73),(98,75),(99,77),(97,79),(92,80),
         (87,82),(80,84),(76,82),(73,78)],
        fill=outline,
    )
    d.polygon(
        [(76,71),(82,72),(88,73),(94,75),(96,76),(97,77),(94,78),(89,79),
         (84,81),(79,82),(76,80),(75,77)],
        fill=body,
    )
    d.polygon([(84,78),(92,77),(89,80),(83,81)], fill=shade)
    return im


def repair_stegosaurus(im: Image.Image):
    d = ImageDraw.Draw(im)
    outline = (27, 40, 83, 255)
    body = (147, 180, 206, 255)
    beige = (236, 204, 158, 255)
    orange = (226, 115, 35, 255)
    d.rectangle((79, 57, 99, 88), fill=(0, 0, 0, 0))
    d.polygon(
        [(72,66),(80,67),(87,68),(93,70),(98,71),(99,73),(97,75),(91,76),
         (85,78),(79,79),(74,77),(72,74)],
        fill=outline,
    )
    d.polygon(
        [(74,68),(81,69),(87,70),(93,71),(96,72),(97,73),(94,74),(89,75),
         (84,77),(78,77),(74,75)],
        fill=body,
    )
    d.polygon([(87,75),(94,73),(91,75),(87,76)], fill=beige)
    d.polygon([(77,67),(80,60),(85,66),(84,70)], fill=outline)
    d.polygon([(79,66),(80,62),(83,66),(83,68)], fill=orange)
    return im


def repair_rainbow(im: Image.Image):
    # The source crop lost the right side of the second cloud. Rebuild the
    # complete right-hand cloud by mirroring the intact left half below the
    # rainbow centre line. This preserves the original palette and style.
    px = im.load()
    source = im.copy()
    src = source.load()
    for y in range(55, 96):
        for x in range(50, 100):
            px[x, y] = src[99 - x, y]
    return im


REPAIRS = {
    "I0021": repair_whale,
    "I0026": repair_long_neck,
    "I0027": repair_triceratops,
    "I0029": repair_stegosaurus,
    "I0043": repair_rainbow,
}


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if REPORT.is_file():
        old = json.loads(REPORT.read_text(encoding="utf-8"))
        if old.get("repair_version") == "complete-edges-v1":
            current = {k: sha(SOURCE / v) for k, v in TARGETS.items()}
            expected = old.get("final_sha256") or {}
            if all(current.get(k) == expected.get(k) for k in TARGETS):
                print("SHAPE_REPAIR_ALREADY_APPLIED")
                return

    rows = []
    final_hashes = {}
    for base, filename in TARGETS.items():
        path = SOURCE / filename
        im = Image.open(path).convert("RGBA")
        if im.size != (100, 120):
            raise SystemExit(f"{base}: expected 100x120, got {im.size}")

        before = {"bbox": list(alpha_bbox(im)), "margins": margins(im)}
        repaired = REPAIRS[base](im.copy())
        normalized, info = normalize(repaired)

        m = info["margins"]
        if min(m.values()) < 10:
            raise SystemExit(f"{base}: safe margin failed after reconstruction: {m}")
        if abs(m["left"] - m["right"]) > 1 or abs(m["top"] - m["bottom"]) > 1:
            raise SystemExit(f"{base}: centering failed after reconstruction: {m}")

        normalized.save(path, "PNG", optimize=False)
        final_hashes[base] = sha(path)
        rows.append({
            "id": base,
            "file": filename,
            "before": before,
            "after": {
                "bbox": list(alpha_bbox(normalized)),
                "margins": margins(normalized),
                "scale": info["scale"],
                "art_size": info["art_size"],
                "sha256": final_hashes[base],
            },
            "repair": {
                "I0021": "reconstructed complete whale tail flukes",
                "I0026": "reconstructed and tapered long-neck dinosaur tail",
                "I0027": "reconstructed and tapered triceratops tail",
                "I0029": "reconstructed and tapered stegosaurus tail",
                "I0043": "rebuilt complete right cloud by mirroring intact left cloud geometry",
            }[base],
        })
        print(base, rows[-1]["repair"], rows[-1]["after"]["margins"])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "repair_version": "complete-edges-v1",
                "canvas": [100, 120],
                "max_art": [80, 100],
                "targets": rows,
                "final_sha256": final_hashes,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("SHAPE_REPAIR_OK")


if __name__ == "__main__":
    main()
