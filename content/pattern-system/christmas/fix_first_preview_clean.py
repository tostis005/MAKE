#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'content/source-images/collections/christmas/products/N0001-christmas-tree.png'
BG=ROOT/'content/source-images/collections/christmas/background/christmas-collection-background.png'
DMC=ROOT/'content/pattern-system/data/dmc-colors.json'
CAT=ROOT/'content/products/catalog.json'
ASSET=ROOT/'content/products/assets/N0001-CS-product.webp'
PDF=ROOT/'content/products/files/Drielo_N0001-CS.pdf'
PAT=ROOT/'content/pattern-system/patterns/N0001-CS/pattern.json'
PROD=ROOT/'content/pattern-system/products/N0001-CS/product.json'

GRID_W,GRID_H=100,120
MOTIF_W,MOTIF_H=50,60
OFF_X,OFF_Y=25,30
FRAME_X,FRAME_Y,FRAME_W,FRAME_H=438,212,685,822
SYMBOLS=list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")+list("!@#$%&*+=?^~:;/\\")
CODE='N0001-CS'

def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def writej(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def getfont(size,bold=False):
    paths=[
      '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
      '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for p in paths:
        if Path(p).is_file(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def clean_mask(src):
    px=src.load(); w,h=src.size
    greens={(45,75,51),(55,91,60),(109,134,75),(116,151,117)}
    reds={(154,13,16),(161,4,7),(204,87,82),(246,168,152)}
    gold={(202,139,51)}
    browns={(41,21,14),(73,38,20),(124,69,38),(164,99,57)}
    lights={(238,232,220),(245,237,226),(228,198,165),(226,185,147),(161,159,160),(155,156,151)}

    def bounds(y):
        if y<=8: return 20,30
        if y<=15:
            t=(y-9)/6; return round(19-2*t),round(31+2*t)
        if y<=25:
            t=(y-16)/9; return round(16-5*t),round(34+5*t)
        if y<=38:
            t=(y-26)/12; return round(11-7*t),round(39+7*t)
        return 3,47

    allowed=[[False]*w for _ in range(h)]
    for y in range(h):
        a,b=bounds(y)
        for x in range(max(0,a),min(w,b+1)): allowed[y][x]=True

    mask=[[False]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            c=px[x,y]
            mask[y][x]=allowed[y][x] and (c in greens or c in reds or c in gold)

    def neighbours(x,y,m):
        n=0
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if not (dx or dy): continue
                xx,yy=x+dx,y+dy
                if 0<=xx<w and 0<=yy<h and m[yy][xx]: n+=1
        return n

    for _ in range(3):
        new=[r[:] for r in mask]
        for y in range(h):
            for x in range(w):
                if not mask[y][x] and allowed[y][x] and px[x,y] in browns and neighbours(x,y,mask)>=1:
                    new[y][x]=True
        mask=new

    new=[r[:] for r in mask]
    for y in range(h):
        for x in range(w):
            if not mask[y][x] and allowed[y][x] and px[x,y] in lights and neighbours(x,y,mask)>=4:
                new[y][x]=True
    return new

def dmc_rows():
    out=[]; seen=set()
    for r in readj(DMC):
        code=str(r.get('floss','')).strip()
        if not code or code in seen: continue
        try: rgb=(int(r['r']),int(r['g']),int(r['b']))
        except Exception: continue
        out.append({'dmc':code,'name':str(r.get('description') or f'DMC {code}'),'rgb':rgb})
        seen.add(code)
    return out

def nearest(rgb, rows):
    r,g,b=rgb
    return min(rows,key=lambda p:2*(r-p['rgb'][0])**2+4*(g-p['rgb'][1])**2+3*(b-p['rgb'][2])**2)

src=Image.open(SRC).convert('RGB')
assert src.size==(50,60),src.size
mask=clean_mask(src)
used=[src.getpixel((x,y)) for y in range(60) for x in range(50) if mask[y][x]]
colors=list(dict.fromkeys(used))
assert 1<=len(colors)<=20,len(colors)
symbols={c:SYMBOLS[i] for i,c in enumerate(colors)}
counts=Counter()
matrix=[[None]*GRID_W for _ in range(GRID_H)]
for y in range(60):
    for x in range(50):
        if not mask[y][x]: continue
        c=src.getpixel((x,y)); s=symbols[c]
        matrix[OFF_Y+y][OFF_X+x]=s; counts[s]+=1

dmc=dmc_rows()
threads=[]
for c in colors:
    s=symbols[c]; m=nearest(c,dmc)
    threads.append({'symbol':s,'dmc':m['dmc'],'name':m['name'],'source_rgb':list(c),
                    'color':'#%02X%02X%02X'%c,'stitches':counts[s]})
total=sum(counts.values())

pattern={
 'code':CODE,'base_design_id':'N0001','technique_code':'CS','collection':'christmas',
 'status':'ready','source_asset':'source-images/collections/christmas/products/N0001-christmas-tree.png',
 'palette_mode':'shared-20-source-colours','source_motif_width':50,'source_motif_height':60,
 'stitch_width':100,'stitch_height':120,'motif_offset':{'x':25,'y':30},
 'total_stitches':total,'threads':threads,'matrix':matrix}
writej(PAT,pattern)

# Product mockup: preserve the 1536x1536 approved Christmas background and draw
# only real motif stitches. Blank source-preview pixels remain untouched Aida.
bg=Image.open(BG).convert('RGB'); assert bg.size==(1536,1536)
d=ImageDraw.Draw(bg)
cw,ch=FRAME_W/100,FRAME_H/120
for sy in range(60):
    for sx in range(50):
        gx,gy=25+sx,30+sy
        if matrix[gy][gx] is None: continue
        c=src.getpixel((sx,sy))
        x0=FRAME_X+gx*cw; y0=FRAME_Y+gy*ch
        x1=FRAME_X+(gx+1)*cw; y1=FRAME_Y+(gy+1)*ch
        pad=max(.8,min(cw,ch)*.16); width=max(2,round(min(cw,ch)*.36))
        d.line((x0+pad,y0+pad,x1-pad,y1-pad),fill=c,width=width)
        d.line((x1-pad,y0+pad,x0+pad,y1-pad),fill=c,width=width)
ASSET.parent.mkdir(parents=True,exist_ok=True)
bg.save(ASSET,'WEBP',quality=95,method=6)

# One-page printable PDF: full 100x120 grid with the cleaned 50x60 motif centered.
W,H=2480,3508
page=Image.new('RGB',(W,H),'white'); dr=ImageDraw.Draw(page)
dr.text((140,90),'Christmas Tree Mini Cross Stitch Pattern',font=getfont(62,True),fill=(30,30,30))
dr.text((140,175),f'100 x 120 chart - centered 50 x 60 motif area - {total:,} stitches',
        font=getfont(34),fill=(70,70,70))
cell=16; ox=(W-100*cell)//2; oy=285
fcell=getfont(12,True)
for y in range(120):
    for x in range(100):
        s=matrix[y][x]
        if s is None: continue
        c=src.getpixel((x-25,y-30))
        x0=ox+x*cell; y0=oy+y*cell
        dr.rectangle((x0,y0,x0+cell-1,y0+cell-1),fill=c)
        lum=.2126*c[0]+.7152*c[1]+.0722*c[2]; tc=(20,20,20) if lum>145 else (255,255,255)
        bb=dr.textbbox((0,0),s,font=fcell)
        dr.text((x0+(cell-(bb[2]-bb[0]))/2,y0+(cell-(bb[3]-bb[1]))/2-1),s,font=fcell,fill=tc)
for x in range(101):
    xx=ox+x*cell; major=x%10==0
    dr.line((xx,oy,xx,oy+120*cell),fill=(80,80,80) if major else (195,195,195),width=3 if major else 1)
for y in range(121):
    yy=oy+y*cell; major=y%10==0
    dr.line((ox,yy,ox+100*cell,yy),fill=(80,80,80) if major else (195,195,195),width=3 if major else 1)
ly=oy+120*cell+70
dr.text((140,ly),'Colour key',font=getfont(26,True),fill=(30,30,30)); ly+=55
for i,t in enumerate(threads):
    col=i%2; row=i//2; x=140+col*1100; y=ly+row*56; c=tuple(t['source_rgb'])
    dr.rectangle((x,y+5,x+34,y+39),fill=c,outline=(80,80,80))
    dr.text((x+50,y),f"{t['symbol']}   DMC {t['dmc']}   {t['name']}   - {t['stitches']} stitches",
            font=getfont(24),fill=(40,40,40))
dr.text((140,H-150),'Digital counted cross-stitch pattern - Drielo',font=getfont(34),fill=(80,80,80))
PDF.parent.mkdir(parents=True,exist_ok=True); page.save(PDF,'PDF',resolution=300.0,quality=95)

# Refresh product metadata while preserving the already-defined Christmas routing.
prod=readj(PROD) if PROD.is_file() else {}
prod.update({'code':CODE,'base_design_id':'N0001','technique_code':'CS','collection':'christmas',
             'title':'Christmas Tree Mini Cross Stitch Pattern PDF','technique':'cross-stitch',
             'pattern_file':'patterns/N0001-CS/pattern.json','status':'active','render_ready':True,
             'source_artwork':'source-images/collections/christmas/products/N0001-christmas-tree.png',
             'page_1_asset':'source-images/collections/christmas/background/christmas-collection-background.png'})
writej(PROD,prod)

cat=readj(CAT)
row=next(p for p in cat['products'] if p.get('code')==CODE)
row['stitches']=total; row['colours']=len(threads); row['color_count']=len(threads)
row['grid']='100 x 120 stitches'; row['grid_width']=100; row['grid_height']=120
row['motif_width']=50; row['motif_height']=60
row['short_description_en']=row['short_description']=(
    f'Mini Christmas tree cross-stitch PDF. A cleaned 50 x 60 motif area is centered on a 100 x 120 chart, '
    f'leaving genuine blank Aida around and through the design. {total:,} stitched cells and {len(threads)} colours.')
row['short_description_es']=(
    f'Mini patrón PDF de árbol de Navidad. El motivo limpio de 50 x 60 está centrado en una cuadrícula de 100 x 120, '
    f'dejando Aida realmente en blanco alrededor y dentro del diseño. {total:,} puntadas y {len(threads)} colores.')
row['gallery']=[]
coll=next(c for c in cat['collections'] if c.get('slug')=='christmas')
coll['thread_codes']=[str(t['dmc']) for t in threads]
writej(CAT,cat)

print(json.dumps({'code':CODE,'stitches':total,'colours':len(threads),'bbox_area':'50x60',
                  'grid':'100x120','offset':[25,30],'hero':'1536x1536','pdf_pages':1},ensure_ascii=False))
