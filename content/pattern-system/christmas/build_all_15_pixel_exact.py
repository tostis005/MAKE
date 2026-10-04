#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
COL = ROOT / "content/source-images/collections/christmas"
PRODUCTS_DIR = COL / "products"
PALETTE_PATH = COL / "palette20_rgb.json"
DMC_PATH = ROOT / "content/pattern-system/data/dmc-colors.json"
PATTERN_ROOT = ROOT / "content/pattern-system/patterns"
PRODUCT_ROOT = ROOT / "content/pattern-system/products"
GEN_DIR = ROOT / "content/pattern-system/christmas/generated"
PDF_DIR = ROOT / "content/pattern-system/christmas/pattern-pdfs"

GRID_W, GRID_H = 100, 120
SRC_W, SRC_H = 50, 60
OFF_X, OFF_Y = 25, 30
SYMBOLS = list("ABCDEFGHJKLMNPQRSTUV")

DESIGNS = [
    ("N0001", "christmas-tree", "Christmas Tree", "Árbol de Navidad"),
    ("N0002", "snowman", "Snowman", "Muñeco de Nieve"),
    ("N0003", "santa-face", "Santa Face", "Cara de Papá Noel"),
    ("N0004", "reindeer", "Reindeer", "Reno"),
    ("N0005", "christmas-stocking", "Christmas Stocking", "Calcetín de Navidad"),
    ("N0006", "gingerbread-house", "Gingerbread House", "Casa de Jengibre"),
    ("N0007", "christmas-wreath", "Christmas Wreath", "Corona de Navidad"),
    ("N0008", "candy-cane-mug", "Candy Cane Mug", "Taza con Bastón de Caramelo"),
    ("N0009", "nutcracker", "Nutcracker", "Cascanueces"),
    ("N0010", "ornament-bauble", "Christmas Bauble", "Bola de Navidad"),
    ("N0011", "christmas-gnome", "Christmas Gnome", "Gnomo de Navidad"),
    ("N0012", "poinsettia", "Poinsettia", "Flor de Pascua"),
    ("N0013", "robin-on-holly", "Robin on Holly", "Petirrojo sobre Acebo"),
    ("N0014", "polar-bear-with-scarf", "Polar Bear with Scarf", "Oso Polar con Bufanda"),
    ("N0015", "holiday-church", "Christmas Chapel", "Capilla de Navidad"),
]

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def font(size: int, bold: bool=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def load_dmc():
    rows=[]
    seen=set()
    for r in read_json(DMC_PATH):
        code=str(r.get("floss","")).strip()
        if not code or code in seen:
            continue
        try:
            rgb=(int(r["r"]),int(r["g"]),int(r["b"]))
        except Exception:
            continue
        rows.append({
            "dmc":code,
            "name":str(r.get("description") or f"DMC {code}"),
            "rgb":rgb,
            "hex":"#%02X%02X%02X" % rgb,
        })
        seen.add(code)
    if len(rows) < 400:
        raise RuntimeError("DMC table incomplete")
    return rows

def nearest_dmc(rgb, rows):
    r,g,b=rgb
    return min(rows, key=lambda p: 2*(r-p["rgb"][0])**2 + 4*(g-p["rgb"][1])**2 + 3*(b-p["rgb"][2])**2)

def render_padded_png(src: Image.Image, target: Path, blank_rgb=(255,255,255)):
    out=Image.new("RGB", (GRID_W,GRID_H), blank_rgb)
    out.paste(src, (OFF_X,OFF_Y))
    target.parent.mkdir(parents=True, exist_ok=True)
    out.save(target, "PNG", optimize=True)

def render_pdf(base_id, title, src, matrix, threads, target):
    W,H=2480,3508
    page=Image.new("RGB",(W,H),"white")
    d=ImageDraw.Draw(page)
    d.text((140,90), f"{title} Cross Stitch Pattern", font=font(58,True), fill=(30,30,30))
    d.text((140,170), "Pixel exact: 1 source pixel = 1 stitch · 50 × 60 centered on 100 × 120", font=font(31), fill=(75,75,75))

    cell=16
    ox=(W-GRID_W*cell)//2
    oy=270
    fcell=font(12,True)

    for y in range(GRID_H):
        for x in range(GRID_W):
            sym=matrix[y][x]
            if sym is None:
                continue
            c=src.getpixel((x-OFF_X,y-OFF_Y))
            x0=ox+x*cell
            y0=oy+y*cell
            d.rectangle((x0,y0,x0+cell-1,y0+cell-1),fill=c)
            lum=.2126*c[0]+.7152*c[1]+.0722*c[2]
            tc=(20,20,20) if lum>145 else (255,255,255)
            bb=d.textbbox((0,0),sym,font=fcell)
            d.text((x0+(cell-(bb[2]-bb[0]))/2, y0+(cell-(bb[3]-bb[1]))/2-1), sym, font=fcell, fill=tc)

    for x in range(GRID_W+1):
        xx=ox+x*cell
        major=x%10==0
        d.line((xx,oy,xx,oy+GRID_H*cell),fill=(75,75,75) if major else (195,195,195),width=3 if major else 1)
    for y in range(GRID_H+1):
        yy=oy+y*cell
        major=y%10==0
        d.line((ox,yy,ox+GRID_W*cell,yy),fill=(75,75,75) if major else (195,195,195),width=3 if major else 1)

    ly=oy+GRID_H*cell+65
    d.text((140,ly),"Shared Christmas palette",font=font(26,True),fill=(30,30,30))
    ly+=50
    for i,t in enumerate(threads):
        col=i%2
        row=i//2
        x=140+col*1100
        y=ly+row*54
        c=tuple(t["source_rgb"])
        d.rectangle((x,y+5,x+34,y+39),fill=c,outline=(80,80,80))
        label=f'{t["symbol"]}   RGB {c[0]},{c[1]},{c[2]}   · DMC {t["dmc"]} {t["name"]}   · {t["stitches"]}'
        d.text((x+50,y),label,font=font(22),fill=(40,40,40))

    d.text((140,H-130),f"{base_id}-CS · 3,000 stitches · Drielo",font=font(30),fill=(90,90,90))
    target.parent.mkdir(parents=True, exist_ok=True)
    page.save(target,"PDF",resolution=300.0,quality=95)

def main():
    pal_doc=read_json(PALETTE_PATH)
    palette=[tuple(map(int,c)) for c in pal_doc["palette_rgb"]]
    if len(palette) != 20 or len(set(palette)) != 20:
        raise RuntimeError("Christmas palette must contain exactly 20 distinct RGB colours")
    if len(SYMBOLS) != 20:
        raise RuntimeError("Expected exactly 20 fixed symbols")

    symbol_for={c:SYMBOLS[i] for i,c in enumerate(palette)}
    dmc_rows=load_dmc()
    mapped={c:nearest_dmc(c,dmc_rows) for c in palette}

    union=set()
    summary=[]

    for base_id,slug,title_en,title_es in DESIGNS:
        source=PRODUCTS_DIR/f"{base_id}-{slug}.png"
        if not source.is_file():
            raise RuntimeError(f"Missing source {source}")
        src=Image.open(source).convert("RGB")
        if src.size != (SRC_W,SRC_H):
            raise RuntimeError(f"{source.name}: expected 50x60, got {src.size}")

        pixels=list(src.getdata())
        outside=sorted(set(pixels)-set(palette))
        if outside:
            raise RuntimeError(f"{source.name}: colours outside shared palette: {outside[:5]}")
        union.update(pixels)

        matrix=[[None]*GRID_W for _ in range(GRID_H)]
        counts=Counter()
        for sy in range(SRC_H):
            for sx in range(SRC_W):
                c=src.getpixel((sx,sy))
                sym=symbol_for[c]
                matrix[OFF_Y+sy][OFF_X+sx]=sym
                counts[sym]+=1

        if sum(counts.values()) != SRC_W*SRC_H:
            raise RuntimeError(f"{base_id}: pixel-to-stitch mismatch")

        threads=[]
        for c in palette:
            sym=symbol_for[c]
            if counts[sym] <= 0:
                continue
            dm=mapped[c]
            threads.append({
                "symbol":sym,
                "source_rgb":list(c),
                "source_hex":"#%02X%02X%02X" % c,
                "dmc":dm["dmc"],
                "name":dm["name"],
                "mapped_dmc_rgb":list(dm["rgb"]),
                "mapped_dmc_hex":dm["hex"],
                "stitches":counts[sym],
            })

        code=f"{base_id}-CS"
        pattern={
            "code":code,
            "base_design_id":base_id,
            "technique_code":"CS",
            "collection":"christmas",
            "status":"ready",
            "algorithm":"pixel-exact-1px-1stitch",
            "source_asset":f"source-images/collections/christmas/products/{source.name}",
            "palette_mode":"shared-exact-20-rgb",
            "shared_palette_rgb":[list(c) for c in palette],
            "source_width":SRC_W,
            "source_height":SRC_H,
            "stitch_width":GRID_W,
            "stitch_height":GRID_H,
            "source_offset":{"x":OFF_X,"y":OFF_Y},
            "total_stitches":SRC_W*SRC_H,
            "threads":threads,
            "matrix":matrix,
        }
        write_json(PATTERN_ROOT/code/"pattern.json",pattern)

        product={
            "code":code,
            "base_design_id":base_id,
            "technique_code":"CS",
            "collection":"christmas",
            "title":f"{title_en} Mini Cross Stitch Pattern PDF",
            "title_en":f"{title_en} Mini Cross Stitch Pattern PDF",
            "title_es":f"Patrón Mini de {title_es} en Punto de Cruz PDF",
            "design_slug":slug,
            "technique":"cross-stitch",
            "pattern_file":f"patterns/{code}/pattern.json",
            "status":"ready",
            "render_ready":True,
            "renderer":"christmas-pixel-exact",
            "source_artwork":f"source-images/collections/christmas/products/{source.name}",
            "palette_mode":"shared-exact-20-rgb",
        }
        write_json(PRODUCT_ROOT/code/"product.json",product)

        padded=GEN_DIR/f"{base_id}-{slug}-100x120.png"
        render_padded_png(src,padded)

        pdf=PDF_DIR/f"Drielo_{code}.pdf"
        render_pdf(base_id,title_en,src,matrix,threads,pdf)

        summary.append({
            "base_design_id":base_id,
            "slug":slug,
            "source":source.name,
            "source_size":[50,60],
            "grid_size":[100,120],
            "offset":[25,30],
            "stitches":3000,
            "used_colours":len(set(pixels)),
            "pattern":str((PATTERN_ROOT/code/"pattern.json").relative_to(ROOT)),
            "pdf":str(pdf.relative_to(ROOT)),
            "padded_png":str(padded.relative_to(ROOT)),
        })

    if union != set(palette):
        missing=[list(c) for c in palette if c not in union]
        extra=[list(c) for c in union if c not in palette]
        raise RuntimeError(f"15-design union must equal exact 20-colour palette; missing={missing} extra={extra}")

    report={
        "collection":"christmas",
        "algorithm":"pixel-exact-1px-1stitch",
        "design_count":15,
        "source_size":[50,60],
        "grid_size":[100,120],
        "offset":[25,30],
        "shared_palette_rgb":[list(c) for c in palette],
        "shared_palette_count":20,
        "union_palette_count":len(union),
        "patterns":summary,
    }
    write_json(ROOT/"content/pattern-system/christmas/pixel-exact-build-report.json",report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
