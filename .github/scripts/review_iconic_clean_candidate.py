#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
COL = ROOT / "content" / "pattern-system" / "collections" / "iconic-destinations"
SOURCE = COL / "assets" / "iconic-60-pngs-q50.zip"
REVIEW = COL / "review"
OUT_DIR = REVIEW / "candidate-pngs"
OUT_ZIP = REVIEW / "iconic_60_pngs_q50_limpio_candidate.zip"
CONTACT = REVIEW / "iconic_60_pngs_q50_limpio_candidate_contact.png"
REPORT = REVIEW / "REVIEW.md"

WIDTH, HEIGHT = 100, 120
COUNT = 60
MAX_COLORS = 50


def row_diff(im: Image.Image, y: int) -> float:
    a = list(im.crop((0, y - 1, WIDTH, y)).getdata())
    b = list(im.crop((0, y, WIDTH, y + 1)).getdata())
    return sum(
        abs(r1-r2) + abs(g1-g2) + abs(b1-b2)
        for (r1,g1,b1),(r2,g2,b2) in zip(a,b)
    ) / WIDTH


def col_diff(im: Image.Image, x: int) -> float:
    a = list(im.crop((x - 1, 0, x, HEIGHT)).getdata())
    b = list(im.crop((x, 0, x + 1, HEIGHT)).getdata())
    return sum(
        abs(r1-r2) + abs(g1-g2) + abs(b1-b2)
        for (r1,g1,b1),(r2,g2,b2) in zip(a,b)
    ) / HEIGHT


def main():
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source ZIP: {SOURCE}")

    shutil.rmtree(REVIEW, ignore_errors=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    expected = [f"destino_{r:02d}_{c:02d}.png" for r in range(1, 7) for c in range(1, 11)]
    rows = []
    top_flags = []
    right_flags = []

    with zipfile.ZipFile(SOURCE, "r") as zf:
        names = sorted(n for n in zf.namelist() if n.lower().endswith(".png"))
        if names != expected:
            raise SystemExit("Source ZIP filenames are not the expected 60-design set")

        for idx, name in enumerate(names):
            raw = zf.read(name)
            with Image.open(io.BytesIO(raw)) as opened:
                im = opened.convert("RGB")
            if im.size != (WIDTH, HEIGHT):
                raise SystemExit(f"{name}: wrong dimensions {im.size}")
            colours = len(set(im.getdata()))
            if not (1 <= colours <= MAX_COLORS):
                raise SystemExit(f"{name}: {colours} colours")

            # Reproduce the candidate reviewed in chat: only repair the final
            # five columns by mirroring inward. This intentionally does not
            # touch the top edge, so residual mosaic contamination remains
            # visible and measurable instead of being hidden by destructive
            # reconstruction.
            fixed = im.copy()
            for offset, x in enumerate(range(95, 100)):
                source_x = 94 - offset
                fixed.paste(fixed.crop((source_x, 0, source_x + 1, HEIGHT)), (x, 0))

            path = OUT_DIR / name
            fixed.save(path, "PNG", optimize=True)

            top_candidates = [(y, row_diff(fixed, y)) for y in range(1, 25)]
            top_y, top_score = max(top_candidates, key=lambda t: t[1])
            right_candidates = [(x, col_diff(fixed, x)) for x in range(80, 99)]
            right_x, right_score = max(right_candidates, key=lambda t: t[1])

            # Rows 2-6 show a clear, systematic mosaic-row transition. A
            # score >150 is far above the first-row baseline (<70 in review).
            if idx // 10 >= 1 and top_score > 150:
                top_flags.append((name, top_y, top_score))
            if right_score > 150:
                right_flags.append((name, right_x, right_score))

            rows.append((name, colours, top_y, top_score, right_x, right_score))

    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(OUT_DIR.glob("*.png")):
            zf.write(path, arcname=path.name)

    # Contact sheet for human review.
    cell_w, cell_h = 220, 280
    sheet = Image.new("RGB", (cell_w * 5, cell_h * 12), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(sorted(OUT_DIR.glob("*.png"))):
        thumb = Image.open(path).convert("RGB").resize((200, 240), Image.Resampling.NEAREST)
        x = (idx % 5) * cell_w + 10
        y = (idx // 5) * cell_h + 10
        sheet.paste(thumb, (x, y))
        draw.text((x, y + 244), path.name, fill="black")
    sheet.save(CONTACT, "PNG", optimize=True)

    sha256 = hashlib.sha256(OUT_ZIP.read_bytes()).hexdigest()
    status = "REJECTED" if top_flags or right_flags else "PASS"

    lines = [
        "# Iconic Destinations clean-ZIP review",
        "",
        f"**STATUS: {status}**",
        "",
        f"- Candidate ZIP: `{OUT_ZIP.name}`",
        f"- SHA-256: `{sha256}`",
        f"- PNG count: {len(rows)}",
        "- Dimensions: 100×120 for every PNG",
        "- Palette: 1–50 RGB colours per PNG",
        f"- Residual top-edge mosaic flags: {len(top_flags)}",
        f"- Residual right-edge flags after five-column repair: {len(right_flags)}",
        "",
        "## Conclusion",
        "",
        "This candidate is not approved for WooCommerce. The original 60-PNG pack contains pixels from neighbouring mosaic cells. Repairing only the right edge does not remove the systematic horizontal contamination visible across rows 2–6. Reconstructing those missing source pixels by mirroring would invent artwork rather than recover the original designs.",
        "",
        "The production queue must remain blocked until clean independent source artwork is supplied (preferably the original 60-page PDF or truly independent PNG exports).",
        "",
        "## Top-edge flags",
        "",
    ]
    for name, y, score in top_flags:
        lines.append(f"- `{name}`: strongest early-row seam y={y}, score={score:.1f}")
    lines += ["", "## Right-edge flags", ""]
    for name, x, score in right_flags:
        lines.append(f"- `{name}`: strongest late-column seam x={x}, score={score:.1f}")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"REVIEW_STATUS={status}")
    print(f"CANDIDATE_SHA256={sha256}")
    print(f"TOP_FLAGS={len(top_flags)}")
    print(f"RIGHT_FLAGS={len(right_flags)}")


if __name__ == "__main__":
    main()
