#!/usr/bin/env python3
from __future__ import annotations

import json, math, random, shutil, zipfile
from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COL = SYSTEM / "collections" / "iconic-destinations"
ASSETS = COL / "assets"
INPUT = COL / "input-pngs-q50"
DESIGNS = COL / "designs.json"
QUEUE = SYSTEM / "iconic_destinations" / "publish_queue.json"

W,H,S = 100,120,8
HW,HH = W*S,H*S
ZIP_REL = "collections/iconic-destinations/assets/iconic-batch-01-clean-q50.zip"
ZIP_PATH = SYSTEM / ZIP_REL

BATCH = [
    ("D0031","paris-eiffel-tower","D0031-paris-eiffel-tower.png","destino_04_01.png"),
    ("D0032","london-big-ben","D0032-london-big-ben.png","destino_04_02.png"),
    ("D0033","rome-colosseum","D0033-rome-colosseum.png","destino_04_03.png"),
    ("D0034","new-york-statue-liberty","D0034-new-york-statue-liberty.png","destino_04_04.png"),
    ("D0035","taj-mahal","D0035-taj-mahal.png","destino_04_05.png"),
    ("D0036","great-wall-china","D0036-great-wall-china.png","destino_04_06.png"),
    ("D0037","rio-christ-redeemer","D0037-rio-christ-redeemer.png","destino_04_07.png"),
    ("D0038","pyramids-giza","D0038-pyramids-giza.png","destino_04_08.png"),
    ("D0039","sydney-opera-house","D0039-sydney-opera-house.png","destino_04_09.png"),
    ("D0046","cape-town-table-mountain","D0046-cape-town-table-mountain.png","destino_05_06.png"),
]

def q(v): return int(round(v*S))
def pt(x,y): return (q(x),q(y))
def rect(d,b,fill): d.rectangle(tuple(q(v) for v in b),fill=fill)
def ell(d,b,fill): d.ellipse(tuple(q(v) for v in b),fill=fill)
def poly(d,pts,fill): d.polygon([pt(x,y) for x,y in pts],fill=fill)
def line(d,pts,fill,width=1): d.line([pt(x,y) for x,y in pts],fill=fill,width=max(1,q(width)),joint="curve")
def mix(a,b,t): return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))

def gradient_sky(top,bottom,horizon=.70):
    im=Image.new("RGB",(HW,HH))
    p=im.load()
    for y in range(HH):
        t=min(1,y/(HH*horizon))
        c=mix(top,bottom,t)
        for x in range(HW): p[x,y]=c
    return im

def soft_clouds(im,seed,low=10,high=52):
    rng=random.Random(seed)
    lay=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
    for _ in range(8):
        x=rng.uniform(0,90); y=rng.uniform(low,high); w=rng.uniform(9,24); h=rng.uniform(3,7)
        alpha=rng.randint(40,95); c=(245,245,238,alpha)
        d.ellipse((q(x),q(y),q(x+w*.55),q(y+h)),fill=c)
        d.ellipse((q(x+w*.20),q(y-h*.35),q(x+w*.75),q(y+h*.9)),fill=c)
        d.ellipse((q(x+w*.45),q(y),q(x+w),q(y+h)),fill=c)
    lay=lay.filter(ImageFilter.GaussianBlur(q(.6)))
    return Image.alpha_composite(im.convert("RGBA"),lay).convert("RGB")

def atmospheric_ground(im,seed,base=(72,103,74),y0=82):
    rng=random.Random(seed); d=ImageDraw.Draw(im)
    for y in range(q(y0),HH):
        t=(y-q(y0))/max(1,(HH-q(y0)))
        c=mix(base,tuple(max(0,v-28) for v in base),t)
        d.line((0,y,HW,y),fill=c)
    # subtle texture
    pix=im.load()
    for _ in range(3500):
        x=rng.randrange(HW); y=rng.randrange(q(y0),HH)
        c=pix[x,y]; n=rng.randint(-5,5); pix[x,y]=tuple(max(0,min(255,v+n)) for v in c)
    return im

def add_glow(im,center=(25,20),radius=30,colour=(255,220,145),strength=72):
    lay=Image.new("RGBA",im.size,(0,0,0,0)); px=lay.load()
    cx,cy=q(center[0]),q(center[1]); rr=q(radius)
    for y in range(max(0,cy-rr),min(HH,cy+rr)):
        for x in range(max(0,cx-rr),min(HW,cx+rr)):
            dist=((x-cx)**2+(y-cy)**2)**.5/rr
            if dist<1:
                a=int((1-dist)**2*strength); px[x,y]=(*colour,a)
    return Image.alpha_composite(im.convert("RGBA"),lay).convert("RGB")

def shadow_layer(base, draw_fn, blur=1.4, offset=(1.2,1.7), alpha=85):
    lay=Image.new("RGBA",base.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
    draw_fn(d,True)
    lay=lay.filter(ImageFilter.GaussianBlur(q(blur)))
    shifted=Image.new("RGBA",base.size,(0,0,0,0))
    shifted.alpha_composite(lay,(q(offset[0]),q(offset[1])))
    return Image.alpha_composite(base.convert("RGBA"),shifted).convert("RGB")

def eiffel():
    im=gradient_sky((40,103,170),(220,226,219)); im=add_glow(im,(19,20),36); im=soft_clouds(im,31)
    d=ImageDraw.Draw(im); rect(d,(0,87,100,120),(86,105,74))
    # distant Paris skyline
    rng=random.Random(31)
    for x in range(0,100,4):
        h=rng.randint(3,11); c=rng.choice([(151,143,128),(168,154,132),(137,145,148)])
        rect(d,(x,87-h,x+3.5,87),c)
    def tower(dd,shadow=False):
        c=(30,28,28,90) if shadow else (83,71,58)
        c2=(30,28,28,90) if shadow else (126,102,77)
        poly(dd,[(31,99),(43,39),(47.5,21),(49.2,9),(50.8,9),(52.5,21),(57,39),(69,99),(62.3,99),(55,63),(45,63),(37.7,99)],c)
        for y,w in [(30,12),(44,20),(62,28),(80,36),(97,45)]: line(dd,[(50-w/2,y),(50+w/2,y)],c2,1.2)
        for y0,y1,w0,w1 in [(37,60,10,21),(61,98,21,38)]:
            line(dd,[(50-w0/2,y0),(50+w1/2,y1)],c2,.8); line(dd,[(50+w0/2,y0),(50-w1/2,y1)],c2,.8)
    im=shadow_layer(im,tower); d=ImageDraw.Draw(im); tower(d)
    line(d,[(46,21),(50,9),(54,21)],(180,145,98),.7)
    return im

def bigben():
    im=gradient_sky((56,114,171),(215,222,216)); im=add_glow(im,(78,18),38); im=soft_clouds(im,32)
    d=ImageDraw.Draw(im); rect(d,(0,101,100,120),(50,105,130))
    # palace
    stone=(177,148,103); dark=(84,71,58); hi=(215,184,126)
    rect(d,(0,72,79,101),stone)
    for x in range(3,76,6): rect(d,(x,81,x+1.5,97),dark)
    for x in range(5,75,11): poly(d,[(x,72),(x+4,66),(x+8,72)],dark)
    # tower shadow then tower
    def tower(dd,shadow=False):
        a=(30,30,30,90) if shadow else stone
        b=(30,30,30,90) if shadow else dark
        rect(dd,(57,27,78,102),a); poly(dd,[(55,28),(67.5,11),(80,28)],b); rect(dd,(60,20,75,28),b)
    im=shadow_layer(im,tower,1.2,(1.1,1.5)); d=ImageDraw.Draw(im); tower(d)
    ell(d,(59.5,35,75.5,51),(232,225,191)); ell(d,(61,36.5,74,49.5),(247,240,206))
    line(d,[(67.5,43),(67.5,38.5)],dark,.8); line(d,[(67.5,43),(72,45.5)],dark,.8)
    for x in (60,64,71,75): line(d,[(x,55),(x,98)],hi,.55)
    for y in range(105,120,5): line(d,[(0,y),(100,y)],(92,151,170),.8)
    return im

def colosseum():
    im=gradient_sky((65,122,175),(224,218,198)); im=add_glow(im,(22,22),42,(255,205,130),85); im=soft_clouds(im,33)
    d=ImageDraw.Draw(im); rect(d,(0,101,100,120),(116,101,75))
    stone=(196,161,111); mid=(158,127,91); dark=(92,73,59); hi=(229,198,148)
    # silhouette
    poly(d,[(8,68),(11,55),(21,48),(36,44),(53,43),(69,46),(84,52),(93,63),(92,105),(8,105)],stone)
    # cutaway right upper damage
    poly(d,[(77,45),(96,42),(96,67),(89,64),(84,54)],(121,159,190))
    for y in (68,83,98): line(d,[(10,y),(91,y)],mid,1)
    for y0 in (51,71,86):
        step=9 if y0>60 else 10
        for x in range(14,88,step):
            ell(d,(x,y0,x+6.2,y0+10),dark); rect(d,(x,y0+5,x+6.2,y0+11),dark)
            line(d,[(x+.7,y0+5),(x+5.4,y0+5)],hi,.35)
    return im

def liberty():
    im=gradient_sky((45,123,188),(214,227,219)); im=add_glow(im,(21,16),35); im=soft_clouds(im,34)
    d=ImageDraw.Draw(im); rect(d,(0,90,100,120),(34,105,143))
    # skyline
    rng=random.Random(8)
    for x in range(3,98,5):
        h=rng.randint(4,16); rect(d,(x,90-h,x+3.4,90),rng.choice([(115,132,143),(135,142,140),(157,145,126)]))
    rect(d,(36,84,66,111),(176,148,109)); rect(d,(39,77,63,87),(197,169,126))
    green=(91,156,133); dark=(42,91,81); mid=(119,181,149); hi=(169,211,177)
    # statue body
    poly(d,[(44,35),(55,34),(63,76),(58,85),(43,85),(37,74)],green)
    poly(d,[(43,45),(36,28),(38,10),(43,9),(42,29),(50,45)],mid)
    rect(d,(37,7,43,11),dark); poly(d,[(37,7),(40,1),(44,7)],(241,167,46))
    ell(d,(44,23,55.5,35),green)
    for ang in range(-160,-20,20):
        a=math.radians(ang); line(d,[(50+6*math.cos(a),27+6*math.sin(a)),(50+13*math.cos(a),27+13*math.sin(a))],dark,.8)
    poly(d,[(54,45),(67,50),(62,67),(53,62)],dark)
    for x in (43,47,51,55,59): line(d,[(x,38),(x+2,79)],hi if x in (47,55) else dark,.55)
    return im

def taj():
    im=gradient_sky((78,144,198),(231,221,193)); im=add_glow(im,(50,18),40,(255,218,154),90); im=soft_clouds(im,35)
    d=ImageDraw.Draw(im); rect(d,(0,103,100,120),(78,125,75))
    white=(230,224,202); warm=(201,190,166); shadow=(151,150,143); hi=(250,244,221)
    rect(d,(17,69,83,101),white); rect(d,(12,99,88,105),warm)
    ell(d,(35,37,65,70),white); rect(d,(34,55,66,71),white); poly(d,[(50,30),(47,39),(53,39)],warm); line(d,[(50,26),(50,36)],shadow,.7)
    for x in (25,75): ell(d,(x-7,54,x+7,69),white); rect(d,(x-7,62,x+7,73),white)
    for x in (10,90):
        rect(d,(x-2.2,43,x+2.2,100),white); ell(d,(x-4.2,38,x+4.2,47),white); line(d,[(x,34),(x,40)],shadow,.7)
    for x in (28,42,58,72):
        ell(d,(x-5,73,x+5,91),shadow); rect(d,(x-5,81,x+5,92),shadow)
        line(d,[(x-3,75),(x-3,90)],hi,.35)
    rect(d,(42,105,58,120),(65,129,151))
    return im

def greatwall():
    im=gradient_sky((70,132,184),(218,218,192)); im=add_glow(im,(18,19),39,(255,205,130),75); im=soft_clouds(im,36,12,44)
    d=ImageDraw.Draw(im)
    poly(d,[(0,87),(17,55),(35,78),(54,47),(76,75),(100,42),(100,120),(0,120)],(77,105,72))
    poly(d,[(0,100),(24,70),(43,94),(67,64),(100,85),(100,120),(0,120)],(91,123,78))
    wall=(178,156,112); dark=(93,82,66); hi=(218,197,153)
    pts=[(3,94),(14,81),(27,84),(39,68),(52,72),(64,55),(77,61),(89,45),(98,49)]
    line(d,pts,dark,8); line(d,pts,wall,6); line(d,[(4,91),(14,78),(27,81),(39,65),(52,69),(64,52),(77,58),(89,42)],hi,.55)
    for x,y in [(14,81),(39,68),(64,55),(89,45)]:
        rect(d,(x-4,y-6,x+4,y+5),wall)
        for k in (-3,0,3): rect(d,(x+k-1,y-8,x+k+1,y-5),dark)
    return im

def christ():
    im=gradient_sky((67,133,187),(223,221,197)); im=add_glow(im,(22,18),39,(255,205,140),70); im=soft_clouds(im,37)
    d=ImageDraw.Draw(im)
    poly(d,[(0,107),(20,77),(37,91),(56,68),(78,88),(100,64),(100,120),(0,120)],(63,106,73))
    rect(d,(43,84,57,108),(149,146,134))
    stone=(224,218,199); sh=(157,156,149); hi=(248,242,220)
    poly(d,[(45,40),(55,40),(59,82),(41,82)],stone)
    poly(d,[(7,45),(44,40),(46,49),(17,53)],stone); poly(d,[(54,40),(93,45),(83,53),(54,49)],stone)
    ell(d,(45,26,55,39),stone)
    line(d,[(50,40),(50,80)],sh,.7); line(d,[(18,49),(44,45)],sh,.6); line(d,[(56,45),(82,49)],sh,.6)
    line(d,[(47,31),(52,31)],hi,.35)
    return im

def pyramids():
    im=gradient_sky((73,139,193),(230,211,171)); im=add_glow(im,(20,18),44,(255,201,117),95); im=soft_clouds(im,38,8,35)
    d=ImageDraw.Draw(im); rect(d,(0,86,100,120),(193,153,86))
    sand=(210,169,98); light=(238,198,120); dark=(153,113,64); haze=(219,185,126)
    poly(d,[(0,94),(22,81),(48,93),(72,84),(100,91),(100,120),(0,120)],sand)
    poly(d,[(8,96),(38,43),(68,96)],light); poly(d,[(38,43),(68,96),(52,96)],dark)
    poly(d,[(48,100),(73,60),(99,100)],(221,179,105)); poly(d,[(73,60),(99,100),(84,100)],(149,111,64))
    poly(d,[(0,103),(18,73),(39,103)],(226,185,109)); poly(d,[(18,73),(39,103),(29,103)],(158,117,67))
    for y in range(58,94,7): line(d,[(max(9,38-(95-y)*.52),y),(min(67,38+(95-y)*.52),y)],haze,.35)
    return im

def sydney():
    im=gradient_sky((51,121,181),(217,228,222)); im=add_glow(im,(78,20),40); im=soft_clouds(im,39)
    d=ImageDraw.Draw(im); rect(d,(0,82,100,120),(35,111,153))
    for y in range(86,120,5): line(d,[(0,y),(100,y)],(83,159,187),.7)
    rect(d,(15,82,86,89),(150,133,111))
    white=(235,231,216); shadow=(162,161,154); warm=(213,205,190)
    sails=[[(18,82),(32,44),(40,82)],[(31,82),(47,34),(56,82)],[(47,82),(62,42),(72,82)],[(60,82),(75,50),(84,82)]]
    for pts in sails: poly(d,pts,white)
    for pts in [[(32,44),(40,82)],[(47,34),(56,82)],[(62,42),(72,82)],[(75,50),(84,82)]]: line(d,pts,shadow,.7)
    for x in (20,35,50,65): line(d,[(x,83),(x+12,83)],warm,.4)
    return im

def table():
    im=gradient_sky((49,118,183),(219,228,218)); im=add_glow(im,(24,18),42); im=soft_clouds(im,46,10,38)
    d=ImageDraw.Draw(im); rect(d,(0,93,100,120),(38,111,145))
    # city foreground
    rng=random.Random(46)
    for x in range(2,100,4):
        h=rng.randint(3,11); rect(d,(x,93-h,x+3,93),rng.choice([(141,139,126),(161,150,130),(126,139,141)]))
    rock=(107,113,95); dark=(68,76,65); green=(69,102,70); light=(145,151,128)
    poly(d,[(0,88),(13,70),(25,53),(33,47),(69,47),(77,52),(86,68),(100,83),(100,94),(0,94)],rock)
    line(d,[(32,47),(69,47)],dark,1.5)
    poly(d,[(0,87),(18,73),(29,62),(40,71),(55,58),(70,69),(87,73),(100,85),(100,94),(0,94)],green)
    line(d,[(10,82),(26,57),(38,51)],light,.55); line(d,[(71,52),(85,73)],dark,.55)
    # conceptual table-cloth cloud
    poly(d,[(30,44),(68,44),(76,49),(28,50)],(232,235,228))
    return im

SCENES={"D0031":eiffel,"D0032":bigben,"D0033":colosseum,"D0034":liberty,"D0035":taj,
        "D0036":greatwall,"D0037":christ,"D0038":pyramids,"D0039":sydney,"D0046":table}

def quantize_scene(im):
    im=ImageEnhance.Contrast(im).enhance(1.05)
    im=ImageEnhance.Color(im).enhance(1.05)
    im=im.resize((W,H),Image.Resampling.LANCZOS)
    qimg=im.quantize(colors=50,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    rgb=qimg.convert("RGB"); colours=len(set(rgb.getdata()))
    if colours<45:
        # force close-to-50 without altering the image perceptibly
        counts=Counter(rgb.getdata()); common=counts.most_common(1)[0][0]
        positions=[(x,y) for y in range(H) for x in range(W) if rgb.getpixel((x,y))==common]
        used=set(rgb.getdata()); need=50-len(used); made=[]; delta=1
        while len(made)<need:
            for ch in range(3):
                for sign in (-1,1):
                    c=list(common); c[ch]=max(0,min(255,c[ch]+sign*delta)); c=tuple(c)
                    if c not in used and c not in made:
                        made.append(c)
                        if len(made)==need: break
                if len(made)==need: break
            delta+=1
        for pos,c in zip(positions,made): rgb.putpixel(pos,c)
        qimg=rgb.quantize(colors=50,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    return qimg

def main():
    INPUT.mkdir(parents=True,exist_ok=True); ASSETS.mkdir(parents=True,exist_ok=True)
    tmp=COL/"_conceptual_batch01"; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir(parents=True)
    generated={}
    for base,slug,member,input_name in BATCH:
        im=quantize_scene(SCENES[base]())
        path=tmp/member; im.save(path,"PNG",optimize=True)
        with Image.open(path) as chk:
            rgb=chk.convert("RGB"); colours=len(set(rgb.getdata()))
            if rgb.size!=(100,120) or not (45<=colours<=50):
                raise RuntimeError(f"{base}: invalid source size={rgb.size} colours={colours}")
        generated[base]=(path,member,input_name,colours)
        print(f"CONCEPTUAL_SOURCE_OK {base} size=100x120 colours={colours}")

    with zipfile.ZipFile(ZIP_PATH,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for base,slug,member,input_name in BATCH: zf.write(generated[base][0],member)
    with zipfile.ZipFile(ZIP_PATH,"r") as zf:
        for base,slug,member,input_name in BATCH:
            raw=zf.read(member); target=INPUT/input_name; target.write_bytes(raw)
            if target.read_bytes()!=raw: raise RuntimeError(f"{base}: ZIP/input byte mismatch")

    designs_doc=json.loads(DESIGNS.read_text(encoding="utf-8"))
    designs_doc["source_policy"]="individual-pngs-from-approved-clean-batch-zips-only"
    by_id={x["base_design_id"]:x for x in designs_doc["designs"]}
    for base,slug,member,input_name in BATCH:
        rel=f"collections/iconic-destinations/input-pngs-q50/{input_name}"
        d=by_id[base]
        d.update({"input_png":rel,"source_asset":rel,"source_zip":ZIP_REL,"source_zip_member":member,
                  "artwork_status":"approved-conceptual-realistic-zip-png-100x120",
                  "palette_mode":"per-design","palette_status":"ready-for-direct-png-dmc-map",
                  "source_colour_count":generated[base][3],"source_style":"conceptual-realistic-illustration",
                  "target_master_grid":{"width":100,"height":120,"max_long_side_stitches":120},
                  "target_chart_pages":4})
        for k in ("source_reference_file","source_reference_license","source_pdf","source_pdf_page","reference_board","planned_source_asset","preview_mosaic","mosaic_source","mosaic_crop","board_source"):
            d.pop(k,None)
    DESIGNS.write_text(json.dumps(designs_doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    queue=json.loads(QUEUE.read_text(encoding="utf-8"))
    active={x[0] for x in BATCH}
    queue["mode"]="direct-zip-png-clean-batches-v4"; queue["auto_continue"]=True
    queue["active_batch"]="batch-01-conceptual-realistic"; queue["source_zip"]=ZIP_REL
    queue["notes"]=[
      "Batch 01 uses original conceptual realistic illustrations, not photographs.",
      "Each final PNG is exactly 100x120 and uses approximately 50 discrete colours.",
      "The ZIP member is the authoritative source and is byte-checked before product generation.",
      "Mosaic, PDF-page, board-crop and external-photo sources are forbidden."
    ]
    for row in queue["items"]:
        if row["base_design_id"] in active:
            base,slug,member,input_name=next(x for x in BATCH if x[0]==row["base_design_id"])
            row.update({"input_png":f"collections/iconic-destinations/input-pngs-q50/{input_name}",
                        "source_zip":ZIP_REL,"source_zip_member":member,"status":"pending","attempts":0,
                        "last_run":None,"last_error":None})
        elif row.get("status") in ("pending","failed"): row["status"]="held"
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    shutil.rmtree(tmp,ignore_errors=True)
    print("CONCEPTUAL_BATCH01_READY count=10 grid=100x120 palette=45..50")

if __name__=="__main__": main()
