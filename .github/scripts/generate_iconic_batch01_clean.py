#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import shutil
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "iconic-destinations"
ASSETS = COL / "assets"
INPUT = COL / "input-pngs-q50"
DESIGNS = COL / "designs.json"
QUEUE = SYSTEM / "iconic_destinations" / "publish_queue.json"
OUT = COL / "_batch01_build"

W, H, S = 100, 120, 4
HW, HH = W * S, H * S
ZIP_REL = "collections/iconic-destinations/assets/iconic-batch-01-clean-q50.zip"
ZIP_PATH = SYSTEM / ZIP_REL

BATCH = [
    ("D0031", "paris-eiffel-tower", "D0031-paris-eiffel-tower.png", "destino_04_01.png", 31),
    ("D0032", "london-big-ben", "D0032-london-big-ben.png", "destino_04_02.png", 32),
    ("D0033", "rome-colosseum", "D0033-rome-colosseum.png", "destino_04_03.png", 33),
    ("D0034", "new-york-statue-liberty", "D0034-new-york-statue-liberty.png", "destino_04_04.png", 34),
    ("D0035", "taj-mahal", "D0035-taj-mahal.png", "destino_04_05.png", 35),
    ("D0036", "great-wall-china", "D0036-great-wall-china.png", "destino_04_06.png", 36),
    ("D0037", "rio-christ-redeemer", "D0037-rio-christ-redeemer.png", "destino_04_07.png", 37),
    ("D0038", "pyramids-giza", "D0038-pyramids-giza.png", "destino_04_08.png", 38),
    ("D0039", "sydney-opera-house", "D0039-sydney-opera-house.png", "destino_04_09.png", 39),
    ("D0046", "cape-town-table-mountain", "D0046-cape-town-table-mountain.png", "destino_05_06.png", 46),
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def base_scene(seed, sky_top=(72, 148, 207), sky_bottom=(224, 232, 220), ground=(76, 108, 73)):
    rng = random.Random(seed)
    im = Image.new("RGB", (HW, HH))
    pix = im.load()
    for y in range(HH):
        t = y / (HH - 1)
        if t < .72:
            c = mix(sky_top, sky_bottom, t / .72)
        else:
            u = (t - .72) / .28
            c = mix(ground, tuple(max(0, x - 24) for x in ground), u)
        for x in range(HW):
            n = rng.randint(-8, 8)
            pix[x, y] = tuple(max(0, min(255, v + n)) for v in c)
    return im, ImageDraw.Draw(im), rng


def q(v): return int(round(v * S))
def rect(d, b, fill): d.rectangle(tuple(q(v) for v in b), fill=fill)
def poly(d, pts, fill): d.polygon([(q(x), q(y)) for x, y in pts], fill=fill)
def ell(d, b, fill): d.ellipse(tuple(q(v) for v in b), fill=fill)
def line(d, pts, fill, width=1): d.line([(q(x), q(y)) for x, y in pts], fill=fill, width=max(1, q(width)))


def clouds(d, rng, ylimit=54):
    for _ in range(5):
        x, y = rng.randint(0, 84), rng.randint(10, ylimit)
        c = rng.choice([(241, 240, 229), (229, 237, 238), (248, 244, 224)])
        ell(d, (x, y, x + 12, y + 5), c)
        ell(d, (x + 5, y - 2, x + 17, y + 5), c)
        ell(d, (x + 10, y, x + 24, y + 5), c)


def eiffel():
    im,d,r=base_scene(31,(80,145,205),(220,228,222),(73,112,76)); clouds(d,r)
    for x in range(0,100,6):
        h=r.randint(4,12); rect(d,(x,87-h,x+5,87),(155+r.randint(-15,15),145,125))
    dark,mid,hi=(63,55,48),(98,77,60),(147,112,77)
    poly(d,[(30,97),(43,36),(48,18),(50,9),(52,18),(57,36),(70,97),(62,97),(54,62),(46,62),(38,97)],mid)
    line(d,[(50,9),(50,98)],dark,1.3)
    for y,w in [(31,11),(45,18),(61,26),(78,33),(95,42)]: line(d,[(50-w/2,y),(50+w/2,y)],dark,1.5)
    for y0,y1,w0,w1 in [(35,60,8,18),(60,96,18,35)]:
        line(d,[(50-w0/2,y0),(50+w1/2,y1)],dark,1); line(d,[(50+w0/2,y0),(50-w1/2,y1)],hi,.7)
    rect(d,(42,33,58,36),dark); rect(d,(36,59,64,62),dark)
    return im


def bigben():
    im,d,r=base_scene(32,(83,141,196),(218,228,224),(60,96,91)); clouds(d,r)
    rect(d,(5,72,80,102),(168,139,91)); rect(d,(8,69,78,74),(190,160,105))
    for x in range(10,76,6): rect(d,(x,80,x+2,96),(79,65,50))
    stone,dark,hi=(181,151,96),(84,70,55),(215,186,126)
    rect(d,(56,28,78,103),stone); poly(d,[(54,29),(67,12),(80,29)],(105,91,72)); rect(d,(60,22,74,28),dark)
    ell(d,(59,36,75,52),(230,224,190)); ell(d,(61,38,73,50),(245,239,205))
    line(d,[(67,44),(67,39)],dark,1); line(d,[(67,44),(72,46)],dark,1)
    for x in (59,63,71,75): line(d,[(x,54),(x,100)],hi,.7)
    rect(d,(0,103,100,120),(42,105,137))
    for y in range(106,120,4): line(d,[(0,y),(100,y)],(82,146,169),1)
    return im


def colosseum():
    im,d,r=base_scene(33,(97,154,205),(224,223,203),(107,103,77)); clouds(d,r)
    stone,shadow=(189,157,112),(112,89,66)
    ell(d,(9,42,92,109),stone); rect(d,(8,67,92,109),stone)
    poly(d,[(10,64),(15,50),(25,45),(40,42),(57,43),(69,46),(82,51),(91,62),(91,70),(10,70)],stone)
    for y in (68,83,98): line(d,[(10,y),(91,y)],shadow,1)
    for y0 in (71,86):
        for x in range(14,88,9): ell(d,(x,y0,x+6,y0+10),shadow); rect(d,(x,y0+5,x+6,y0+10),shadow)
    for x in range(17,86,11): ell(d,(x,51,x+7,64),shadow); rect(d,(x,57,x+7,65),shadow)
    poly(d,[(78,43),(94,42),(94,70),(87,67),(83,57)],(97,154,205))
    return im


def liberty():
    im,d,r=base_scene(34,(72,152,210),(221,231,222),(42,111,145)); clouds(d,r)
    rect(d,(0,88,100,120),(38,112,152))
    for y in range(92,120,5): line(d,[(0,y),(100,y)],(89,158,185),1)
    rect(d,(34,84,67,111),(169,143,104)); rect(d,(38,76,63,88),(185,160,116))
    green,dark,hi=(98,157,133),(43,99,86),(155,203,168)
    poly(d,[(45,31),(55,30),(62,75),(58,85),(43,85),(38,75)],green)
    poly(d,[(43,43),(36,26),(38,9),(43,8),(42,27),(49,44)],green)
    rect(d,(37,6,43,10),dark); poly(d,[(37,6),(40,0),(44,6)],(238,165,49)); ell(d,(43,22,56,35),green)
    for ang in range(-150,-29,20):
        a=math.radians(ang); line(d,[(49+7*math.cos(a),27+7*math.sin(a)),(49+14*math.cos(a),27+14*math.sin(a))],dark,1)
    poly(d,[(55,43),(67,49),(62,66),(52,61)],dark)
    for x in (44,49,54,58): line(d,[(x,38),(x+2,78)],hi if x%2==0 else dark,1)
    return im


def taj():
    im,d,r=base_scene(35,(103,163,211),(230,224,198),(75,129,79)); clouds(d,r)
    white,sh=(226,220,197),(169,164,150)
    rect(d,(18,69,82,100),white); rect(d,(12,98,88,104),sh)
    ell(d,(35,37,65,70),white); rect(d,(34,54,66,70),white); poly(d,[(50,31),(47,39),(53,39)],sh); line(d,[(50,29),(50,37)],sh,1)
    for x in (26,74): ell(d,(x-7,53,x+7,68),white); rect(d,(x-7,61,x+7,72),white)
    for x in (11,89): rect(d,(x-2,44,x+2,98),white); ell(d,(x-4,39,x+4,47),white); line(d,[(x,35),(x,40)],sh,1)
    for x in (28,42,58,72): ell(d,(x-5,73,x+5,91),sh); rect(d,(x-5,81,x+5,91),sh)
    rect(d,(41,104,59,120),(69,133,160))
    return im


def greatwall():
    im,d,r=base_scene(36,(90,155,205),(220,225,205),(72,111,66)); clouds(d,r,45)
    poly(d,[(0,85),(20,55),(38,79),(56,48),(78,76),(100,44),(100,120),(0,120)],(72,108,75))
    poly(d,[(0,100),(25,70),(45,95),(68,65),(100,86),(100,120),(0,120)],(83,122,75))
    wall,dark=(177,157,117),(97,85,67)
    pts=[(3,93),(14,80),(27,83),(39,67),(52,71),(64,54),(77,60),(89,44),(97,48)]
    line(d,pts,wall,7); line(d,pts,dark,1)
    for x,y in [(14,80),(39,67),(64,54),(89,44)]:
        rect(d,(x-4,y-6,x+4,y+5),wall)
        for k in (-3,0,3): rect(d,(x+k-1,y-8,x+k+1,y-5),dark)
    return im


def christ():
    im,d,r=base_scene(37,(91,157,210),(230,228,205),(58,105,69)); clouds(d,r,50)
    poly(d,[(0,105),(20,76),(38,91),(57,69),(78,88),(100,64),(100,120),(0,120)],(64,110,76))
    rect(d,(43,84,57,108),(155,151,137)); statue,sh=(220,216,198),(159,157,148)
    poly(d,[(45,39),(55,39),(59,82),(41,82)],statue); poly(d,[(8,44),(44,39),(46,48),(17,52)],statue)
    poly(d,[(54,39),(92,44),(83,52),(54,48)],statue); ell(d,(45,25,55,38),statue)
    line(d,[(50,39),(50,80)],sh,1); line(d,[(18,48),(45,44)],sh,1); line(d,[(55,44),(82,48)],sh,1)
    return im


def pyramids():
    im,d,r=base_scene(38,(87,153,210),(227,216,183),(191,156,92)); clouds(d,r,45)
    sand,light,dark=(204,166,96),(232,196,122),(155,119,69)
    poly(d,[(0,91),(25,79),(52,91),(75,82),(100,90),(100,120),(0,120)],sand)
    poly(d,[(8,94),(38,43),(68,94)],light); poly(d,[(38,43),(68,94),(52,94)],dark)
    poly(d,[(48,98),(73,59),(98,98)],(219,180,105)); poly(d,[(73,59),(98,98),(84,98)],(151,115,67))
    poly(d,[(0,101),(18,72),(38,101)],(223,185,109)); poly(d,[(18,72),(38,101),(29,101)],(161,122,70))
    for y in range(57,94,7): line(d,[(max(8,38-(94-y)*.55),y),(min(68,38+(94-y)*.55),y)],dark,.5)
    return im


def sydney():
    im,d,r=base_scene(39,(83,151,207),(222,231,228),(33,104,142)); clouds(d,r,50)
    rect(d,(0,82,100,120),(34,112,156))
    for y in range(86,120,5): line(d,[(0,y),(100,y)],(80,159,190),1)
    white,sh=(230,225,205),(164,161,151); rect(d,(16,82,85,89),(153,135,111))
    for pts in [[(18,82),(32,44),(40,82)],[(31,82),(47,34),(56,82)],[(47,82),(62,42),(72,82)],[(60,82),(75,50),(84,82)]]: poly(d,pts,white)
    for pts in [[(32,44),(40,82)],[(47,34),(56,82)],[(62,42),(72,82)]]: line(d,pts,sh,1)
    return im


def table():
    im,d,r=base_scene(46,(79,150,209),(226,231,220),(46,112,122)); clouds(d,r,40)
    rect(d,(0,92,100,120),(40,117,151))
    for x in range(4,98,5):
        h=r.randint(3,10); rect(d,(x,92-h,x+3,92),(155,148,127))
    rock,dark,green=(111,115,96),(75,80,68),(73,107,73)
    poly(d,[(0,87),(14,69),(25,52),(33,47),(69,47),(76,51),(86,67),(100,82),(100,92),(0,92)],rock)
    line(d,[(32,47),(69,47)],dark,2)
    poly(d,[(0,86),(18,72),(28,61),(40,70),(55,58),(70,68),(87,72),(100,84),(100,92),(0,92)],green)
    poly(d,[(31,45),(69,45),(75,50),(28,50)],(229,232,224))
    return im


SCENES = {
    "D0031": eiffel, "D0032": bigben, "D0033": colosseum, "D0034": liberty,
    "D0035": taj, "D0036": greatwall, "D0037": christ, "D0038": pyramids,
    "D0039": sydney, "D0046": table,
}


def exact_50_palette(im: Image.Image) -> Image.Image:
    small = im.resize((W, H), Image.Resampling.LANCZOS)
    rgb = small.quantize(colors=50, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    counts = Counter(rgb.getdata())
    used = set(counts)
    if len(used) < 50:
        common = counts.most_common(1)[0][0]
        slots = [p for p in [(x,y) for y in range(H) for x in range(W)] if rgb.getpixel(p) == common]
        need = 50 - len(used)
        made = []
        delta = 1
        while len(made) < need:
            for ch in range(3):
                for sign in (-1, 1):
                    c = list(common)
                    c[ch] = max(0, min(255, c[ch] + sign * delta))
                    c = tuple(c)
                    if c not in used and c not in made:
                        made.append(c)
                        if len(made) == need: break
                if len(made) == need: break
            delta += 1
        for pos, colour in zip(slots, made):
            rgb.putpixel(pos, colour)
        used = set(rgb.getdata())
    if len(used) != 50:
        raise RuntimeError(f"Expected exactly 50 colours, got {len(used)}")

    colours = list(dict.fromkeys(rgb.getdata()))
    idx = {c:i for i,c in enumerate(colours)}
    pal = Image.new("P", (W,H))
    pal.putdata([idx[p] for p in rgb.getdata()])
    raw = []
    for c in colours: raw.extend(c)
    raw.extend([0] * (768 - len(raw)))
    pal.putpalette(raw)
    return pal


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    INPUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    generated = {}
    for base, slug, member, input_name, seed in BATCH:
        img = exact_50_palette(SCENES[base]())
        path = OUT / member
        img.save(path, format="PNG", optimize=True)
        with Image.open(path) as check:
            colours = len(set(check.convert("RGB").getdata()))
            if check.size != (W,H) or colours != 50:
                raise RuntimeError(f"{base}: invalid output size={check.size} colours={colours}")
        generated[base] = (path, member, input_name, colours)

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for base, _, member, _, _ in BATCH:
            zf.write(generated[base][0], member)

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        if sorted(zf.namelist()) != sorted(x[2] for x in BATCH):
            raise RuntimeError("Batch ZIP member set mismatch")
        for base, _, member, input_name, _ in BATCH:
            raw = zf.read(member)
            target = INPUT / input_name
            target.write_bytes(raw)
            if target.read_bytes() != raw:
                raise RuntimeError(f"{base}: extracted bytes differ from ZIP member")

    # Remove source paths that previously allowed the old mosaic/PDF route.
    for p in [
        ASSETS / "iconic-60-pngs-q50.zip",
        ASSETS / "iconic-60-pngs-q50-mosaic.png",
        ASSETS / "iconic-mosaic-grid-1000x720.png",
        ASSETS / "iconic-mosaic-grid-source.webp",
        ASSETS / "iconic-60-source.pdf",
        COL / "reference-boards.json",
    ]:
        p.unlink(missing_ok=True)
    shutil.rmtree(COL / "pdf-pngs-q50", ignore_errors=True)

    designs_doc = read_json(DESIGNS)
    designs_doc["source_policy"] = "individual-pngs-from-approved-clean-batch-zips-only"
    by_id = {x["base_design_id"]: x for x in designs_doc["designs"]}
    for base, slug, member, input_name, _ in BATCH:
        d = by_id[base]
        rel = f"collections/iconic-destinations/input-pngs-q50/{input_name}"
        d["input_png"] = rel
        d["source_asset"] = rel
        d["source_zip"] = ZIP_REL
        d["source_zip_member"] = member
        d["artwork_status"] = "approved-clean-zip-individual-png-100x120"
        d["palette_mode"] = "per-design"
        d["palette_status"] = "ready-for-direct-png-dmc-map"
        d["source_colour_count"] = 50
        d["target_master_grid"] = {"width":100,"height":120,"max_long_side_stitches":120}
        d["target_chart_pages"] = 4
        for k in ("reference_board","planned_source_asset","preview_mosaic","mosaic_source","mosaic_crop","board_source","source_pdf","source_pdf_page"):
            d.pop(k, None)
    write_json(DESIGNS, designs_doc)

    queue = read_json(QUEUE)
    selected = {x[0] for x in BATCH}
    queue["mode"] = "direct-zip-png-clean-batches-v4"
    queue["auto_continue"] = True
    queue["max_attempts_per_design"] = 3
    queue["active_batch"] = "batch-01"
    queue["source_zip"] = ZIP_REL
    queue["notes"] = [
        "Production artwork is sourced only from approved clean batch ZIP files.",
        "Each selected PNG is exactly 100x120 pixels and uses exactly 50 RGB colours.",
        "The publisher verifies byte identity between ZIP member and extracted input PNG before rendering.",
        "Mosaic, board-crop and PDF artwork sources are forbidden.",
    ]
    for row in queue["items"]:
        base = row["base_design_id"]
        if base in selected:
            _, _, member, input_name, _ = next(x for x in BATCH if x[0] == base)
            rel = f"collections/iconic-destinations/input-pngs-q50/{input_name}"
            row.update({
                "input_png": rel,
                "source_zip": ZIP_REL,
                "source_zip_member": member,
                "status": "pending",
                "attempts": 0,
                "last_run": None,
                "last_error": None,
            })
            row.pop("source_pdf_page", None)
        elif row.get("status") in ("pending","failed"):
            row["status"] = "held"
    write_json(QUEUE, queue)

    shutil.rmtree(OUT, ignore_errors=True)
    print("BATCH01_READY count=10 size=100x120 colours=50 source=clean-zip-only")
    for base, _, member, input_name, _ in BATCH:
        print(f"READY {base} member={member} input={input_name}")


if __name__ == "__main__":
    main()
