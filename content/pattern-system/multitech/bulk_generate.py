#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, colorsys, json, math, os, re, shutil, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from statistics import median

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]  # content/pattern-system/multitech/bulk_generate.py -> repo root? overridden below
# Repo path is inferred more safely at runtime.
THIS = Path(__file__).resolve()
REPO = THIS.parents[3] if THIS.parts[-4:-1] == ('content','pattern-system','multitech') else Path.cwd()
CONTENT = REPO / 'content'
PRODUCTS_DIR = CONTENT / 'products'
CATALOG_PATH = PRODUCTS_DIR / 'catalog.json'
ASSETS_DIR = PRODUCTS_DIR / 'assets'
FILES_DIR = PRODUCTS_DIR / 'files'
SYSTEM = CONTENT / 'pattern-system'
COLLECTION_PATH = SYSTEM / 'collections' / 'pop-art-portraits' / 'collection.json'
SRC_PRODUCTS = SYSTEM / 'products'
SRC_PATTERNS = SYSTEM / 'patterns'
ENGINE = SYSTEM / 'multitech'
TEMPLATES = ENGINE / 'templates'
ENGINE_ASSETS = ENGINE / 'assets'
OUTPUT = SYSTEM / 'output-multitech'

TECHS = {
    'CS': {
        'template':'cross-stitch.html','technique':'cross-stitch','w':100,'h':120,
        'subtitle':'A modern cross-stitch pattern','stitch_type':'Full cross stitch',
        'materials':['DMC embroidery floss','14-count Aida or preferred fabric','Tapestry needle size 24/26','6-inch hoop (optional)'],
        'fabric_counts':[14,16,18],'size_options':[], 'unit_label':'stitches','measure_label':'Stitches',
        'cover_colour_label':'Threads','facts_colour_label':'Threads used','colour_unit':'DMC colours',
        'finished_subtitle':'A preview of the completed cross-stitch design','finished_caption':'Use this page as a visual reference while you stitch.',
        'facts_subtitle':'Everything you need before you start stitching','preview_label':'Finished cross-stitch preview',
        'cover_overlay':{'left':29.0,'top':12.0,'width':48.0,'height':58.0,'opacity':0.96,'safe_inset_pct':0.0},'cover_stage_scale':125,
        'project':'wall-art','category':['cross-stitch-patterns','portraits','pop-art'],
        'display':'Cross Stitch','count_label':'Total stitches','colour_label':'DMC colours','size_label':'Pattern size',
    },
    'C2C': {
        'template':'c2c-crochet.html','technique':'c2c-crochet','w':60,'h':72,
        'subtitle':'A modern corner-to-corner crochet graph','stitch_type':'Corner-to-corner blocks',
        'materials':['Yarn in the listed collection colours','Crochet hook matched to yarn weight','Scissors','Yarn needle for weaving ends'],
        'fabric_counts':[], 'size_options':None,'unit_label':'blocks','measure_label':'Blocks',
        'cover_colour_label':'Yarn colours','facts_colour_label':'Yarn colours','colour_unit':'collection colours',
        'finished_subtitle':'A preview of the completed C2C crochet design','finished_caption':'Use this page as a visual reference while you crochet.',
        'facts_subtitle':'Everything you need before you start crocheting','preview_label':'Finished C2C preview',
        'cover_overlay':{'left':19.8,'top':7.2,'width':64.5,'height':78.0,'opacity':0.94,'safe_inset_pct':6.0},'cover_stage_scale':123,
        'project':'blanket','category':['c2c-crochet-patterns','c2c-crochet-portraits','c2c-crochet-pop-art'],
        'display':'C2C Crochet','count_label':'Filled blocks','colour_label':'Yarn colours','size_label':'Graph size',
    },
    'TC': {
        'template':'crochet.html','technique':'tapestry-crochet','w':80,'h':96,
        'subtitle':'A modern tapestry crochet colourwork pattern','stitch_type':'Tapestry crochet colourwork',
        'materials':['Yarn in the listed collection colours','Crochet hook matched to chosen yarn','Scissors','Yarn needle for finishing'],
        'fabric_counts':[], 'size_options':None,'unit_label':'crochet stitches','measure_label':'Stitches',
        'cover_colour_label':'Yarn colours','facts_colour_label':'Yarn colours','colour_unit':'collection colours',
        'finished_subtitle':'A preview of the completed tapestry crochet design','finished_caption':'Use this page as a visual reference while you crochet.',
        'facts_subtitle':'Everything you need before you start crocheting','preview_label':'Finished crochet preview',
        'cover_overlay':{'left':27.7,'top':10.8,'width':43.5,'height':63.5,'opacity':0.94,'safe_inset_pct':4.5},'cover_stage_scale':123,
        'project':'tapestry','category':['tapestry-crochet-patterns','tapestry-crochet-portraits','tapestry-crochet-pop-art'],
        'display':'Tapestry Crochet','count_label':'Colourwork stitches','colour_label':'Yarn colours','size_label':'Chart size',
    },
    'LH': {
        'template':'rug.html','technique':'latch-hook','w':60,'h':72,
        'subtitle':'A modern rug and latch-hook colour chart','stitch_type':'Latch hook / rug knots',
        'materials':['Wool or rug yarn in the listed collection colours','Latch hook / tufting tool','Suitable rug canvas or backing','Scissors and finishing materials'],
        'fabric_counts':[], 'size_options':None,'unit_label':'knots','measure_label':'Knots',
        'cover_colour_label':'Wool colours','facts_colour_label':'Wool colours','colour_unit':'collection colours',
        'finished_subtitle':'A preview of the completed rug design','finished_caption':'Use this page as a visual reference while you build the rug.',
        'facts_subtitle':'Everything you need before you start your rug','preview_label':'Finished rug preview',
        'cover_overlay':{'left':21.7,'top':7.5,'width':59.0,'height':71.0,'opacity':0.94,'safe_inset_pct':4.5},'cover_stage_scale':125,
        'project':'rug','category':['latch-hook-rug-patterns','latch-hook-rug-portraits','latch-hook-rug-pop-art'],
        'display':'Latch Hook Rug','count_label':'Filled knots','colour_label':'Wool colours','size_label':'Chart size',
    },
}

SYMBOLS=list('ABCDEFGHJKLMNPQRSTUVWXYZ23456789')

def read_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write_json(p,d):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def slugify(s):
    import unicodedata
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def rgb(hexv):
    h=hexv.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def nearest_palette(col,palette):
    # weighted RGB; enough because source already came from this palette
    r,g,b=col
    def d(p):
        pr,pg,pb=rgb(p['hex']); return 2*(r-pr)**2+4*(g-pg)**2+3*(b-pb)**2
    return min(palette,key=d)

def reconstruct_cross_matrix(image_path,target_stitches,palette):
    im=Image.open(image_path).convert('RGB')
    W,H=im.size
    # Exact grid-image box produced by the approved Finished design page.
    # A4 geometry from master template: image box x=26.665..183.335mm, y=73..261mm.
    x0=W*(26.665/210.0); x1=W*(183.335/210.0)
    y0=H*(73.0/297.0); y1=H*(261.0/297.0)
    pix=im.load(); bg=(251,250,246)
    cells=[]
    for gy in range(120):
        ya=int(round(y0+gy*(y1-y0)/120)); yb=int(round(y0+(gy+1)*(y1-y0)/120)); yb=max(yb,ya+1)
        for gx in range(100):
            xa=int(round(x0+gx*(x1-x0)/100)); xb=int(round(x0+(gx+1)*(x1-x0)/100)); xb=max(xb,xa+1)
            samples=[]; distances=[]
            for yy in range(max(0,ya),min(H,yb)):
                for xx in range(max(0,xa),min(W,xb)):
                    c=pix[xx,yy]
                    dist=math.sqrt(sum((c[i]-bg[i])**2 for i in range(3)))
                    distances.append((dist,c))
            distances.sort(key=lambda z:z[0],reverse=True)
            # X strokes are the farthest pixels from warm-white fabric.
            top=distances[:max(3,int(len(distances)*0.34))]
            score=sum(z[0] for z in top)/max(1,len(top))
            strong=[c for d,c in top if d>26]
            if not strong: strong=[c for _,c in top[:3]]
            col=tuple(int(median([c[i] for c in strong])) for i in range(3))
            cells.append((score,gx,gy,col))
    target=max(1,min(12000,int(target_stitches)))
    filled=sorted(cells,key=lambda z:z[0],reverse=True)[:target]
    # Assign palette symbols deterministically by palette order.
    symbol_for={str(p['dmc']):SYMBOLS[i] for i,p in enumerate(palette)}
    matrix=[[None]*100 for _ in range(120)]
    used=Counter()
    for score,gx,gy,col in filled:
        p=nearest_palette(col,palette); s=symbol_for[str(p['dmc'])]; matrix[gy][gx]=s; used[s]+=1
    threads=[]
    for i,p in enumerate(palette):
        s=SYMBOLS[i]
        if used[s]: threads.append({'symbol':s,'dmc':str(p['dmc']),'color':p['hex'],'name':p.get('name',f"DMC {p['dmc']}"),'stitches':used[s]})
    return matrix,threads

def _thread_visual_props(thread):
    r,g,b=(v/255.0 for v in rgb(thread['color']))
    _h,s,v=colorsys.rgb_to_hsv(r,g,b)
    return s,v

def colorfulness_score(matrix,threads):
    props={t['symbol']:_thread_visual_props(t) for t in threads}
    vals=[v for row in matrix for v in row if v]
    if not vals: return 0.0
    # Average saturation of actually-used cells. This is a QA metric, not a colour transform.
    return sum(props.get(v,(0.0,0.0))[0] for v in vals)/len(vals)

def downsample(matrix,threads,new_w,new_h):
    """Downsample while preserving chromatic accents.

    A simple majority vote caused cream/beige cells to erase pink/blue/gold accents
    in C2C, tapestry crochet and rug versions. We still respect the collection
    palette, but weight each candidate by chroma and a small dark-line bonus so
    visually important colours survive block reduction.
    """
    h=len(matrix); w=len(matrix[0])
    props={t['symbol']:_thread_visual_props(t) for t in threads}
    out=[]
    for yy in range(new_h):
        ya=int(yy*h/new_h); yb=max(ya+1,int((yy+1)*h/new_h))
        row=[]
        for xx in range(new_w):
            xa=int(xx*w/new_w); xb=max(xa+1,int((xx+1)*w/new_w))
            vals=[matrix[y][x] for y in range(ya,min(h,yb)) for x in range(xa,min(w,xb)) if matrix[y][x]]
            if not vals:
                row.append(None); continue
            counts=Counter(vals); area=len(vals)
            def visual_vote(sym):
                sat,val=props.get(sym,(0.0,0.5))
                # Count remains the base signal; chroma gets a strong area-level
                # bonus, while dark contours receive a smaller preservation bonus.
                return counts[sym] + area*(1.65*sat + 0.42*(1.0-val))
            row.append(max(counts,key=visual_vote))
        out.append(row)
    counts=Counter(v for row in out for v in row if v)
    used_threads=[]
    for t in threads:
        if counts[t['symbol']]:
            nt=dict(t); nt['stitches']=counts[t['symbol']]; used_threads.append(nt)
    return out,used_threads

def technique_size_options(suffix,w,h):
    if suffix=='C2C':
        vals=[('Fine yarn - 1.5 cm/block',1.5),('Medium yarn - 2.0 cm/block',2.0),('Chunky yarn - 2.5 cm/block',2.5)]
    elif suffix=='TC':
        vals=[('Fine gauge - 0.45 cm/stitch',.45),('Medium gauge - 0.55 cm/stitch',.55),('Relaxed gauge - 0.65 cm/stitch',.65)]
    elif suffix=='LH':
        vals=[('Fine canvas - 0.6 cm/knot',.6),('Medium canvas - 0.8 cm/knot',.8),('Large canvas - 1.0 cm/knot',1.0)]
    else: return []
    return [{'label':label,'cmW':round(w*cm,1),'cmH':round(h*cm,1),'inW':round(w*cm/2.54,1),'inH':round(h*cm/2.54,1)} for label,cm in vals]

def pattern_data(code,base_title,suffix,matrix,threads):
    cfg=TECHS[suffix]; total=sum(1 for row in matrix for v in row if v)
    return {
      'product_code':code,'collection':'Pop Art Portraits','collection_id':'pop-art-portraits','title':base_title,
      'technique': 'crochet' if suffix=='TC' else ('rug' if suffix=='LH' else cfg['technique']),
      'subtitle':cfg['subtitle'],'stitch_width':cfg['w'],'stitch_height':cfg['h'],'total_stitches':total,
      'threads':threads,'matrix':matrix,'skill_level':'Beginner friendly','stitch_type':cfg['stitch_type'],
      'website':'www.drielo.com','materials':cfg['materials'],'fabric_counts':cfg['fabric_counts'],
      'size_options': technique_size_options(suffix,cfg['w'],cfg['h']), 'unit_label':cfg['unit_label'],'measure_label':cfg['measure_label'],
      'cover_colour_label':cfg['cover_colour_label'],'cover_colour_value':f"{len(threads)} {cfg['colour_unit']}",
      'facts_colour_label':cfg['facts_colour_label'],'colour_unit':cfg['colour_unit'],'finished_title':'Finished design',
      'finished_subtitle':cfg['finished_subtitle'],'finished_caption':cfg['finished_caption'],'facts_title':'Pattern facts',
      'facts_subtitle':cfg['facts_subtitle'],'preview_label':cfg['preview_label'],'cover_overlay':cfg['cover_overlay'],'cover_stage_scale':cfg['cover_stage_scale']
    }

def product_source(code,base_code,title,suffix):
    cfg=TECHS[suffix]
    return {'code':code,'base_design_id':base_code,'technique_code':suffix,'collection':'pop-art-portraits','title':title,
            'technique':cfg['technique'],'pattern_file':f'patterns/{code}/pattern.json','template':cfg['template']}

def data_uri(path):
    p=Path(path); mime='image/png' if p.suffix.lower()=='.png' else 'image/jpeg'
    return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode('ascii')

def render_one(task):
    code,suffix,data=task
    from playwright.sync_api import sync_playwright
    cfg=TECHS[suffix]
    template=(TEMPLATES/cfg['template']).read_text(encoding='utf-8')
    # replace pattern-data block
    template=re.sub(r'(<script id="template-pattern-data" type="application/json">)(.*?)(</script>)',
                    lambda m:m.group(1)+json.dumps(data,ensure_ascii=False,separators=(',',':'))+m.group(3),template,count=1,flags=re.S)
    cover=ENGINE_ASSETS/f"cover-{ {'CS':'cross-stitch','C2C':'c2c-crochet','TC':'crochet','LH':'rug'}[suffix] }.png"
    floral=ENGINE_ASSETS/'floral.png'
    assets={'floral':data_uri(floral),'cover_image':data_uri(cover)}
    template=re.sub(r'(<script id="template-assets" type="application/json">)(.*?)(</script>)',
                    lambda m:m.group(1)+json.dumps(assets,separators=(',',':'))+m.group(3),template,count=1,flags=re.S)
    out=OUTPUT/code; out.mkdir(parents=True,exist_ok=True)
    html=out/f'{code}.html'; pdf=out/f'Drielo_{code}.pdf'; img=out/f'{code}-product.webp'; png=out/'capture.png'
    html.write_text(template,encoding='utf-8')
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={'width':1600,'height':2000},device_scale_factor=1.5)
        page.goto(html.resolve().as_uri(),wait_until='load',timeout=120000)
        page.wait_for_function("document.documentElement.getAttribute('data-drielo-ready') === '1'",timeout=120000)
        page.pdf(path=str(pdf),format='A4',print_background=True,prefer_css_page_size=True)

        # Store image = exact ambient scene + final pattern, with none of the PDF
        # card/border/background. Clone only the cover stage into a clean capture
        # layer so ancestor borders, sepia filler and facts-rail can never leak in.
        page.evaluate("""() => {
          const src=document.querySelector('#cover-stage');
          if(!src) throw new Error('Missing #cover-stage');
          const clone=src.cloneNode(true);
          clone.id='drielo-product-capture';
          clone.removeAttribute('data-product-image');
          Object.assign(clone.style,{
            position:'fixed',left:'0',top:'0',width:'1200px',height:'1200px',
            aspectRatio:'1 / 1',maxWidth:'none',margin:'0',padding:'0',
            border:'0',boxShadow:'none',background:'transparent',overflow:'hidden',
            zIndex:'2147483647',transform:'none'
          });
          document.body.appendChild(clone);
        }""")
        loc=page.locator('#drielo-product-capture')
        if loc.count()!=1: raise RuntimeError(f'{code}: clean product capture missing')
        loc.screenshot(path=str(png),type='png')
        browser.close()
    im=Image.open(png).convert('RGB')
    # Clean edge-to-edge 4:5 ecommerce crop; no added canvas/padding/border.
    ImageOps.fit(im,(1200,1500),method=Image.Resampling.LANCZOS,centering=(.5,.5)).save(img,'WEBP',quality=92,method=6)
    png.unlink(missing_ok=True)
    if pdf.stat().st_size<100000: raise RuntimeError(f'{code}: PDF too small')
    return {'code':code,'pdf':str(pdf),'image':str(img),'pdf_bytes':pdf.stat().st_size,'image_bytes':img.stat().st_size}

def safe_tag(s): return len(s)<=20

def technique_tags(suffix,base):
    name=base.lower()
    proper=[]
    for needle in ['marilyn monroe','audrey hepburn','mona lisa','frida kahlo','salvador dali','albert einstein','charlie chaplin','van gogh']:
        if needle in name and safe_tag(needle): proper=[needle]; break
    sets={
      'C2C':['c2c crochet','crochet pattern','crochet graph','corner to corner','portrait crochet','pop art crochet','crochet blanket','digital pattern','instant download','colorwork crochet','beginner crochet','portrait pattern'],
      'TC':['tapestry crochet','crochet pattern','crochet chart','colorwork crochet','portrait crochet','pop art crochet','wall hanging','digital pattern','instant download','crochet pdf','beginner crochet','portrait pattern'],
      'LH':['latch hook pattern','rug pattern pdf','latch hook rug','rug making chart','portrait rug','pop art rug','rug wall art','digital pattern','instant download','beginner rug','colorwork rug','portrait pattern'],
    }
    tags=proper+sets[suffix]
    return tags[:13]

def compact_desc(title,code,cfg,total,colors):
    return f"Downloadable {title} {cfg['display']} pattern PDF. {cfg['w']} x {cfg['h']} {cfg['unit_label']}; {total:,} {cfg['count_label'].lower()}; {colors} coordinated collection colours; beginner friendly. Pattern code: {code}."

def make_catalog_variant(base, suffix, data):
    cfg=TECHS[suffix]; code=f"{base['code']}-{suffix}"; title=base['title']; total=data['total_stitches']; colors=len(data['threads'])
    p=dict(base)
    p['code']=code; p['sku']=f'DRIELO-{code}'; p['base_design_id']=base['code']; p['design_id']=code; p['technique_code']=suffix; p['technique']=cfg['technique']
    if suffix=='CS':
        p['previous_skus']=[base['sku']]
        p['download']=f'files/Drielo_{code}.pdf'; p['gallery']=[f'assets/{code}-product.webp']; p['gallery_revision']=20260923
        p['filters']=dict(base['filters']); p['filters']['technique']=['cross-stitch']; p['filters']['project']=['wall-art']
        p['short_description']=p['short_description_en']=compact_desc(title,code,cfg,total,colors)
        p['short_description_es']=f"Patrón PDF descargable de {title}. {cfg['w']} x {cfg['h']} puntos; {total:,} puntadas; {colors} colores DMC; apto para principiantes. Código: {code}.".replace(',', '.')
        p['description']=p['description_en']=(f"<p><strong>{title} Cross Stitch Pattern PDF</strong> is a downloadable counted cross-stitch pattern.</p><p><strong>Pattern code:</strong> {code}</p><h3>Pattern details</h3><ul><li>Grid: {cfg['w']} x {cfg['h']} stitches</li><li>Total stitches: {total:,}</li><li>Colours: {colors} DMC colours</li><li>Full cross stitch</li><li>Beginner friendly</li></ul><h3>What you receive</h3><p>A complete 17-page PDF with finished preview, colour key, colour and symbol charts, enlarged sections and working guide.</p><p>Digital product only. Personal use only.</p>")
        p['description_es']=(f"<p><strong>{title} - patrón PDF de punto de cruz</strong>.</p><p><strong>Código:</strong> {code}</p><h3>Detalles</h3><ul><li>Cuadrícula: {cfg['w']} x {cfg['h']} puntos</li><li>Puntadas: {total:,}</li><li>Colores: {colors} DMC</li><li>Punto de cruz completo</li><li>Apto para principiantes</li></ul><p>Incluye PDF completo de 17 páginas. Producto digital para uso personal.</p>")
    else:
        p.pop('previous_skus',None)
        p['title']=f"{title} {cfg['display']} Pattern PDF"; p['title_en']=p['title']; p['title_es']=f"Patrón PDF {cfg['display']}: {title}"
        p['slug']=f"{slugify(title)}-{slugify(cfg['display'])}-pattern"
        p['stitches']=total; p['grid']=f"{cfg['w']} x {cfg['h']} {cfg['unit_label']}"; p['colours']=colors; p['color_count']=colors; p['grid_width']=cfg['w']; p['grid_height']=cfg['h']; p['stitch_type']=cfg['stitch_type']; p['stitch_type_en']=cfg['stitch_type']; p['stitch_type_es']=cfg['stitch_type']
        p['categories']=cfg['category']; p['download']=f'files/Drielo_{code}.pdf'; p['gallery']=[f'assets/{code}-product.webp']; p['gallery_revision']=20260923
        p['filters']=json.loads(json.dumps(base['filters'])); p['filters']['technique']=[cfg['technique']]; p['filters']['project']=[cfg['project']]
        desc=compact_desc(title,code,cfg,total,colors); p['short_description']=p['short_description_en']=desc; p['short_description_es']=f"Patrón PDF descargable de {title} para {cfg['display']}. {cfg['w']} x {cfg['h']} {cfg['unit_label']}; {total:,} posiciones; {colors} colores coordinados. Código: {code}.".replace(',', '.')
        p['description']=p['description_en']=(f"<p><strong>{title} {cfg['display']} Pattern PDF</strong> is a downloadable digital pattern from the Pop Art Portraits collection.</p><p><strong>Pattern code:</strong> {code}</p><p><strong>Digital product only:</strong> no finished item or physical materials are included.</p><h3>Pattern details</h3><ul><li>Chart: {cfg['w']} x {cfg['h']} {cfg['unit_label']}</li><li>{cfg['count_label']}: {total:,}</li><li>Colours: {colors} coordinated collection colours</li><li>Technique: {cfg['stitch_type']}</li><li>Beginner friendly</li></ul><h3>What you receive</h3><p>17-page PDF with finished-design preview, pattern facts, colour key, full chart, symbols, enlarged sections and technique guide.</p><p>Personal use only.</p>")
        p['description_es']=(f"<p><strong>{title} - patrón PDF {cfg['display']}</strong>.</p><p><strong>Código:</strong> {code}</p><p><strong>Producto digital:</strong> no se incluye el artículo terminado ni materiales físicos.</p><h3>Detalles</h3><ul><li>Gráfico: {cfg['w']} x {cfg['h']} {cfg['unit_label']}</li><li>{cfg['count_label']}: {total:,}</li><li>Colores: {colors} colores coordinados</li><li>Técnica: {cfg['stitch_type']}</li><li>Apto para principiantes</li></ul><p>Incluye PDF de 17 páginas con vista previa, clave de colores, gráficos, símbolos y guía.</p>")
        p['tags']=technique_tags(suffix,title); p['etsy_tags_en']=p['tags']; p['etsy_tags_es']=p['tags']
        p['etsy_title_en']=p['title']; p['etsy_title_es']=p['title_es']; p['etsy_description_en']=re.sub('<[^>]+>','',p['description_en']).replace('&strong;',''); p['etsy_description_es']=re.sub('<[^>]+>','',p['description_es'])
    p['size_attribute_label']=cfg['size_label']; p['colour_attribute_label']=cfg['colour_label']; p['type_attribute_label']='Technique' if suffix!='CS' else 'Stitch type'; p['count_attribute_label']=cfg['count_label']
    p['seo_title']=p['seo_title_en']=f"{title} {cfg['display']} Pattern PDF | Drielo"; p['seo_title_es']=f"{title} - patrón {cfg['display']} PDF | Drielo"
    p['meta_description']=p['meta_description_en']=f"{title} {cfg['display']} PDF, {code}: {cfg['w']} x {cfg['h']} {cfg['unit_label']}, {colors} colours, printable charts and beginner-friendly guide."
    p['meta_description_es']=f"{title}, patrón {cfg['display']} PDF {code}: {cfg['w']} x {cfg['h']} {cfg['unit_label']}, {colors} colores y gráficos imprimibles."
    return p

def prepare(start,end):
    catalog=read_json(CATALOG_PATH); collection=read_json(COLLECTION_PATH); palette=collection['palette']
    originals={p['code']:p for p in catalog['products'] if re.fullmatch(r'P\d{4}',p.get('code',''))}
    cs_variants={p.get('base_design_id'):p for p in catalog['products'] if p.get('technique_code')=='CS' and p.get('base_design_id')}
    generated=[]; render_tasks=[]
    for n in range(start,end+1):
        base_code=f'P{n:04d}'; base=originals.get(base_code)
        if not base and base_code in cs_variants:
            base=dict(cs_variants[base_code])
            base['code']=base_code
            base['sku']=(base.get('previous_skus') or [f'DRIELO-{base_code}'])[0]
            base.pop('base_design_id',None); base.pop('design_id',None); base.pop('technique_code',None)
        if not base: raise RuntimeError(f'Missing source product {base_code}')
        src=ASSETS_DIR/f'{base_code}-gallery-2.webp'
        if not src.is_file(): raise RuntimeError(f'Missing design source {src}')
        matrix_cs,threads_cs=reconstruct_cross_matrix(src,base['stitches'],palette)
        technique_mats={'CS':(matrix_cs,threads_cs)}
        base_colorfulness=colorfulness_score(matrix_cs,threads_cs)
        for suffix in ('C2C','TC','LH'):
            cfg=TECHS[suffix]
            dm,dt=downsample(matrix_cs,threads_cs,cfg['w'],cfg['h'])
            score=colorfulness_score(dm,dt)
            # QA guard: reduction must not wash the design out relative to CS.
            # A low score indicates neutral-majority collapse rather than a valid
            # technique conversion.
            if base_colorfulness>0.08 and score < base_colorfulness*0.82:
                raise RuntimeError(f'{base_code}-{suffix}: colourfulness collapsed {score:.3f} vs CS {base_colorfulness:.3f}')
            technique_mats[suffix]=(dm,dt)
        for suffix in ('CS','C2C','TC','LH'):
            code=f'{base_code}-{suffix}'; matrix,threads=technique_mats[suffix]; data=pattern_data(code,base['title'],suffix,matrix,threads)
            pattern={'code':code,'base_design_id':base_code,'technique_code':suffix,'stitch_width':data['stitch_width'],'stitch_height':data['stitch_height'],'total_stitches':data['total_stitches'],'threads':threads,'matrix':matrix,'source_asset':f'content/products/assets/{base_code}-gallery-2.webp','palette_collection':'pop-art-portraits'}
            write_json(SRC_PATTERNS/code/'pattern.json',pattern); write_json(SRC_PRODUCTS/code/'product.json',product_source(code,base_code,base['title'],suffix))
            generated.append(make_catalog_variant(base,suffix,data)); render_tasks.append((code,suffix,data))
    replace_codes={p['code'] for p in generated}; bases={f'P{n:04d}' for n in range(start,end+1)}
    catalog['products']=[p for p in catalog['products'] if p.get('code') not in replace_codes and p.get('code') not in bases]
    catalog['products'].extend(generated)
    catalog['products'].sort(key=lambda p:(p.get('base_design_id',re.sub(r'-.*$','',p.get('code',''))), {'CS':0,'C2C':1,'TC':2,'LH':3}.get(p.get('technique_code','CS'),9)))
    write_json(CATALOG_PATH,catalog)
    return render_tasks

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--start',type=int,default=2); ap.add_argument('--end',type=int,default=20); ap.add_argument('--workers',type=int,default=2); ap.add_argument('--prepare-only',action='store_true'); args=ap.parse_args()
    tasks=prepare(args.start,args.end)
    print(f'PREPARED={len(tasks)}')
    if args.prepare_only: return
    OUTPUT.mkdir(parents=True,exist_ok=True); FILES_DIR.mkdir(parents=True,exist_ok=True); ASSETS_DIR.mkdir(parents=True,exist_ok=True)
    results=[]
    with ProcessPoolExecutor(max_workers=max(1,args.workers)) as ex:
        futs={ex.submit(render_one,t):t[0] for t in tasks}
        for fut in as_completed(futs):
            r=fut.result(); results.append(r); print('BUILT',json.dumps(r),flush=True)
    for r in results:
        shutil.copy2(r['pdf'],FILES_DIR/Path(r['pdf']).name)
        shutil.copy2(r['image'],ASSETS_DIR/Path(r['image']).name)
    print('GENERATED='+str(len(results)))

if __name__=='__main__': main()
