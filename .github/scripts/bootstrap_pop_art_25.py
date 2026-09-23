# Production refresh: rebuild P0001 and P0012 eight-product set with transparent sources and corrected crochet covers.
#!/usr/bin/env python3
from __future__ import annotations
import base64, importlib.util, json, re, shutil, zlib
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path.cwd()
SYSTEM=ROOT/'content'/'pattern-system'
PRODUCTS_DIR=SYSTEM/'products'
PATTERNS_DIR=SYSTEM/'patterns'
CID='pop-art-25'
CDIR=SYSTEM/'collections'/CID
CATALOG=ROOT/'content'/'products'/'catalog.json'
STORE_ASSETS=ROOT/'content'/'products'/'assets'
STORE_FILES=ROOT/'content'/'products'/'files'
SYMBOLS=list('ABCDEFGHJKLMNPQRSTUVWXYZ23456789')

PALETTE=[
 {'dmc':'310','hex':'#000000','name':'Black'},
 {'dmc':'3799','hex':'#404040','name':'Very Dark Pewter Gray'},
 {'dmc':'414','hex':'#8C8C8C','name':'Dark Steel Gray'},
 {'dmc':'B5200','hex':'#FFFFFF','name':'Snow White'},
 {'dmc':'3865','hex':'#F5ECDF','name':'Winter White'},
 {'dmc':'948','hex':'#FEE7DA','name':'Very Light Peach'},
 {'dmc':'754','hex':'#F7CBBF','name':'Light Peach'},
 {'dmc':'437','hex':'#E4BB8E','name':'Light Tan'},
 {'dmc':'761','hex':'#FC9F8B','name':'Light Salmon'},
 {'dmc':'604','hex':'#E996B8','name':'Light Cranberry'},
 {'dmc':'351','hex':'#E96A67','name':'Coral'},
 {'dmc':'321','hex':'#C72B3B','name':'Red'},
 {'dmc':'970','hex':'#F78B2D','name':'Light Pumpkin'},
 {'dmc':'3820','hex':'#DFB65B','name':'Dark Straw'},
 {'dmc':'444','hex':'#FFD600','name':'Dark Lemon'},
 {'dmc':'434','hex':'#985B3B','name':'Light Brown'},
 {'dmc':'801','hex':'#653919','name':'Dark Coffee Brown'},
 {'dmc':'905','hex':'#627650','name':'Dark Parrot Green'},
 {'dmc':'890','hex':'#17492F','name':'Ultra Dark Pistachio Green'},
 {'dmc':'598','hex':'#8EB8BC','name':'Light Turquoise'},
 {'dmc':'3325','hex':'#86B1D0','name':'Light Baby Blue'},
 {'dmc':'797','hex':'#3157A4','name':'Royal Blue'},
 {'dmc':'820','hex':'#0E365C','name':'Very Dark Royal Blue'},
 {'dmc':'550','hex':'#5C295F','name':'Very Dark Violet'},
 {'dmc':'729','hex':'#D0A53E','name':'Medium Old Gold'},
]
DESIGNS=[
 ('P0001','Albert Einstein Tongue Out','Albert Einstein sacando la lengua','albert-einstein-tongue-out'),
 ('P0002','Apple Man Portrait','Retrato del hombre de la manzana','apple-man-portrait'),
 ('P0003','Audrey Hepburn Classic Portrait','Retrato clásico de Audrey Hepburn','audrey-hepburn-classic'),
 ('P0004','Audrey Hepburn Elegant Profile','Audrey Hepburn de perfil elegante','audrey-hepburn-elegant-profile'),
 ('P0005','Audrey Hepburn Sunglasses','Audrey Hepburn con gafas','audrey-hepburn-sunglasses'),
 ('P0006','Charlie Chaplin Portrait','Retrato de Charlie Chaplin','charlie-chaplin-portrait'),
 ('P0007','Frida Kahlo Floral Crown','Frida Kahlo con corona floral','frida-kahlo-floral-crown'),
 ('P0008','Girl with a Pearl Earring Bubble Gum','La joven de la perla con chicle','girl-pearl-earring-bubble-gum'),
 ('P0009','Girl with a Pearl Earring','La joven de la perla','girl-with-a-pearl-earring'),
 ('P0010','Girl with a Pearl Earring Sunglasses','La joven de la perla con gafas','girl-pearl-earring-sunglasses'),
 ('P0011','Marilyn Monroe Blowing Kiss','Marilyn Monroe lanzando un beso','marilyn-monroe-blowing-kiss'),
 ('P0012','Marilyn Monroe Bubble Gum','Marilyn Monroe con chicle','marilyn-monroe-bubble-gum'),
 ('P0013','Marilyn Monroe Sunglasses','Marilyn Monroe con gafas','marilyn-monroe-sunglasses'),
 ('P0014','Marilyn Monroe Surprise','Marilyn Monroe sorprendida','marilyn-monroe-surprise'),
 ('P0015','Marilyn Monroe Wink','Marilyn Monroe guiñando un ojo','marilyn-monroe-wink'),
 ('P0016','Mona Lisa Portrait','Retrato de la Mona Lisa','mona-lisa-portrait'),
 ('P0017','Salvador Dalí Portrait','Retrato de Salvador Dalí','salvador-dali-portrait'),
 ('P0018','Van Gogh with Sunflower','Van Gogh con girasol','van-gogh-sunflower'),
 ('P0019','Vincent van Gogh Portrait','Retrato de Vincent van Gogh','vincent-van-gogh-portrait'),
 ('P0020','James Dean Portrait','Retrato de James Dean','james-dean-portrait'),
 ('P0021','David Bowie Portrait','Retrato de David Bowie','david-bowie-portrait'),
 ('P0022','Princess Diana Bubble Gum','Princesa Diana con chicle','princess-diana-bubble-gum'),
 ('P0023','Princess Diana Portrait','Retrato de la princesa Diana','princess-diana-portrait'),
 ('P0024','Michael Jackson Portrait','Retrato de Michael Jackson','michael-jackson-portrait'),
 ('P0025','Nelson Mandela Portrait','Retrato de Nelson Mandela','nelson-mandela-portrait'),
 ('P0026','Freddie Mercury Portrait','Retrato de Freddie Mercury','freddie-mercury-portrait'),
]
BY={x[0]:x for x in DESIGNS}
TEST={'P0001','P0012'}
SOURCE_Z={
 'P0001':'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',
 'P0012':'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',
}
TECHS={
 'CS':('cross-stitch','cross-stitch.html',100,120,'Cross Stitch','Punto de cruz','wall-art'),
 'C2C':('c2c-crochet','c2c-crochet.html',60,72,'C2C Crochet','Crochet C2C','blanket'),
 'TC':('tapestry-crochet','crochet.html',80,96,'Tapestry Crochet','Crochet tapestry','tapestry'),
 'LH':('latch-hook','rug.html',60,72,'Latch Hook Rug','Alfombra latch hook','rug'),
}

def write_json(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def load_source(code):
 raw=zlib.decompress(base64.b64decode(SOURCE_Z[code]))
 if len(raw)!=12000: raise RuntimeError(f'{code}: bad source length {len(raw)}')
 matrix=[]; counts=Counter()
 for y in range(120):
  row=[]
  for x in range(100):
   v=raw[y*100+x]
   if v==255: row.append(None)
   else:
    if v>=len(PALETTE): raise RuntimeError(f'{code}: palette index {v}')
    s=SYMBOLS[v]; row.append(s); counts[s]+=1
  matrix.append(row)
 threads=[]
 for i,p in enumerate(PALETTE):
  s=SYMBOLS[i]
  if counts[s]:
   threads.append({'symbol':s,'dmc':p['dmc'],'color':p['hex'],'name':p['name'],'stitches':counts[s]})
 return matrix,threads

def save_preview(code,matrix,threads):
 by={t['symbol']:t['color'] for t in threads}
 im=Image.new('RGBA',(400,480),(0,0,0,0)); d=ImageDraw.Draw(im)
 for y,row in enumerate(matrix):
  for x,s in enumerate(row):
   if s: d.rectangle((x*4,y*4,x*4+3,y*4+3),fill=by[s])
 out=CDIR/'sources'/f'{code}.png'; out.parent.mkdir(parents=True,exist_ok=True); im.save(out)

def product_json(base,title_en,title_es,slug,suffix,ready):
 technique,template,w,h,display_en,display_es,project=TECHS[suffix]
 return {
  'code':f'{base}-{suffix}','base_design_id':base,'technique_code':suffix,'collection':CID,
  'title':title_en,'title_en':title_en,'title_es':title_es,'design_slug':slug,'technique':technique,
  'pattern_file':f'patterns/{base}-{suffix}/pattern.json','template':template,'website':'www.drielo.com',
  'status':'published-test' if ready else 'draft','render_ready':False,'renderer':'multitech',
  'source_artwork':f'collections/{CID}/sources/{base}.png' if ready else None,
  'page_1_asset':f'multitech/assets/cover-{ {"CS":"cross-stitch","C2C":"c2c-crochet","TC":"crochet","LH":"rug"}[suffix] }.webp'
 }

def pattern_json(base,suffix,matrix=None,threads=None):
 technique,template,w,h,display_en,display_es,project=TECHS[suffix]
 matrix=matrix or []; threads=threads or []
 return {'code':f'{base}-{suffix}','base_design_id':base,'technique_code':suffix,'collection':CID,
         'palette_collection':CID,'status':'ready' if matrix else 'awaiting-source-artwork',
         'source_asset':f'content/pattern-system/collections/{CID}/sources/{base}.png' if matrix else None,
         'stitch_width':w,'stitch_height':h,'total_stitches':sum(t.get('stitches',0) for t in threads),
         'threads':threads,'matrix':matrix}

def row_for(base,suffix,data):
 code=f'{base}-{suffix}'; _,title_en,title_es,slug=BY[base]
 technique,template,w,h,display_en,display_es,project=TECHS[suffix]
 colors=len(data['threads']); total=data['total_stitches']
 if suffix=='CS':
  title=f'{title_en} Cross Stitch Pattern PDF'; title_es_full=f'Patrón PDF de punto de cruz: {title_es}'
  stitch='Full cross stitch'; stitch_es='Punto de cruz completo'; unit='stitches'; count_label='Total stitches'; color_label='DMC colours'
  cats=['cross-stitch-patterns','portraits','pop-art']; tagtech='cross stitch'
 elif suffix=='C2C':
  title=f'{title_en} C2C Crochet Pattern PDF'; title_es_full=f'Patrón PDF de crochet C2C: {title_es}'
  stitch='Corner-to-corner blocks'; stitch_es='Bloques de crochet C2C'; unit='blocks'; count_label='Filled blocks'; color_label='Yarn colours'
  cats=['c2c-crochet-patterns','c2c-crochet-portraits','c2c-crochet-pop-art']; tagtech='c2c crochet'
 elif suffix=='TC':
  title=f'{title_en} Tapestry Crochet Pattern PDF'; title_es_full=f'Patrón PDF de crochet tapestry: {title_es}'
  stitch='Tapestry crochet colourwork'; stitch_es='Crochet tapestry en color'; unit='crochet stitches'; count_label='Colourwork stitches'; color_label='Yarn colours'
  cats=['tapestry-crochet-patterns','tapestry-crochet-portraits','tapestry-crochet-pop-art']; tagtech='tapestry crochet'
 else:
  title=f'{title_en} Latch Hook Rug Pattern PDF'; title_es_full=f'Patrón PDF de alfombra latch hook: {title_es}'
  stitch='Latch hook / rug knots'; stitch_es='Nudos latch hook / alfombra'; unit='knots'; count_label='Filled knots'; color_label='Wool colours'
  cats=['latch-hook-rug-patterns','latch-hook-rug-portraits','latch-hook-rug-pop-art']; tagtech='latch hook'
 grid=f'{w} × {h} {unit}'
 short=f'Downloadable {title_en} {display_en} pattern PDF. {grid}; {total:,} positions; {colors} colours selected exclusively from the fixed 25-colour Pop Art palette; beginner friendly. Pattern code: {code}.'
 short_es=f'Patrón PDF descargable de {display_es}: {title_es}. {w} × {h}; {total:,} posiciones; {colors} colores seleccionados exclusivamente de la paleta fija Pop Art de 25 colores; apto para principiantes. Código: {code}.'
 desc=f'<p><strong>{title}</strong> is a downloadable digital pattern from Drielo’s new Pop Art collection.</p><p><strong>Pattern code:</strong> {code}</p><p>This design uses only colours from the collection’s fixed 25-colour master palette. No colours outside that palette are introduced.</p><h3>Pattern details</h3><ul><li>Chart: {w} × {h} {unit}</li><li>{count_label}: {total:,}</li><li>Colours used: {colors} from the fixed 25-colour palette</li><li>Technique: {stitch}</li><li>Beginner friendly</li></ul><h3>What you receive</h3><p>A complete printable PDF with finished preview, pattern facts, colour key, charts, symbols, enlarged sections and working guide.</p><p>Digital product only. Personal use only.</p>'
 desc_es=f'<p><strong>{title_es_full}</strong> es un patrón digital descargable de la nueva colección Pop Art de Drielo.</p><p><strong>Código:</strong> {code}</p><p>Este diseño utiliza únicamente colores de la paleta maestra fija de 25 colores de la colección. No se introduce ningún color fuera de esa paleta.</p><h3>Detalles</h3><ul><li>Gráfico: {w} × {h}</li><li>Posiciones: {total:,}</li><li>Colores usados: {colors} de la paleta fija de 25 colores</li><li>Técnica: {stitch_es}</li><li>Apto para principiantes</li></ul><h3>Qué recibirás</h3><p>PDF completo e imprimible con vista previa, datos del patrón, clave de colores, gráficos, símbolos, secciones ampliadas y guía de trabajo.</p><p>Producto digital. Solo para uso personal.</p>'
 tags=[tagtech,'digital pattern','pop art portrait','portrait pattern','instant download','beginner pattern','colorwork chart',slug[:20]]
 row={'code':code,'sku':f'DRIELO-{code}','base_design_id':base,'design_id':code,'technique_code':suffix,'technique':technique,
      'title':title,'title_en':title,'title_es':title_es_full,'slug':f'{slug}-{technique}-pattern','price':4.99,'collection':CID,
      'stitches':total,'grid':grid,'colours':colors,'color_count':colors,'grid_width':w,'grid_height':h,
      'skill':'Beginner friendly','skill_en':'Beginner friendly','skill_es':'Apto para principiantes',
      'stitch_type':stitch,'stitch_type_en':stitch,'stitch_type_es':stitch_es,
      'short_description':short,'short_description_en':short,'short_description_es':short_es,
      'description':desc,'description_en':desc,'description_es':desc_es,'categories':cats,'tags':tags,
      'etsy_tags_en':tags,'etsy_tags_es':tags,'gallery':[],'featured_image':f'assets/{code}-product.webp',
      'download':f'files/Drielo_{code}.pdf','gallery_revision':2026092403,
      'seo_title':f'{title_en} {display_en} Pattern PDF | Drielo','seo_title_en':f'{title_en} {display_en} Pattern PDF | Drielo',
      'seo_title_es':f'{title_es} - patrón {display_es} PDF | Drielo',
      'meta_description':f'{title_en} {display_en} PDF {code}: {w} × {h}, {colors} colours from a fixed 25-colour palette.',
      'meta_description_en':f'{title_en} {display_en} PDF {code}: {w} × {h}, {colors} colours from a fixed 25-colour palette.',
      'meta_description_es':f'{title_es}, patrón {display_es} PDF {code}: {w} × {h}, {colors} colores de una paleta fija de 25 colores.',
      'purchase_note_en':'Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.',
      'purchase_note_es':'Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.',
      'size_attribute_label':'Pattern size','colour_attribute_label':color_label,'type_attribute_label':'Technique','count_attribute_label':count_label,
      'filters':{'technique':[technique],'theme':['people-portraits'],'style':['pop-art','colorful'],'project':[project],
                 'orientation':['portrait'],'difficulty':['beginner'],'color-family':['multicolor'],'season':[]}}
 if base=='P0012' and suffix=='CS': row['previous_skus']=['DRIELO-P0012']
 return row

def main():
 # Load existing multitech renderer so we reuse the already-approved four Pop Art page-1 backgrounds.
 modpath=SYSTEM/'multitech'/'bulk_generate.py'
 spec=importlib.util.spec_from_file_location('drielo_bulk',modpath); bulk=importlib.util.module_from_spec(spec); spec.loader.exec_module(bulk)

 collection={'id':CID,'name':'Pop Art','name_en':'Pop Art','name_es':'Pop Art','slug':'pop-art-25','code_prefix':'P',
  'description':'A new 26-design Pop Art portrait collection built on one strict shared palette of 25 colours and four grid-based craft techniques.',
  'description_en':'A new 26-design Pop Art portrait collection built on one strict shared palette of 25 colours and four grid-based craft techniques.',
  'description_es':'Nueva colección Pop Art de 26 diseños construida con una única paleta estricta de 25 colores y cuatro técnicas artesanales basadas en cuadrícula.',
  'palette':PALETTE,'design_count':26,'techniques':['cross-stitch','c2c-crochet','tapestry-crochet','latch-hook'],
  'mockup_spec':{'asset':'../../multitech/assets/cover-cross-stitch.webp','technique_assets':{
    'CS':'../../multitech/assets/cover-cross-stitch.webp','C2C':'../../multitech/assets/cover-c2c-crochet.webp',
    'TC':'../../multitech/assets/cover-crochet.webp','LH':'../../multitech/assets/cover-rug.webp'},'frame':{'enabled':False}},
  'preview_rules':{'palette_mode':'strict','allowed_palette_size':25,'gradients':False,'extra_colours':False}}
 write_json(CDIR/'collection.json',collection)
 write_json(CDIR/'designs.json',{'collection':CID,'designs':[{'code':c,'title_en':en,'title_es':es,'slug':s,'status':'ready' if c in TEST else 'draft','variants':[f'{c}-{x}' for x in TECHS]} for c,en,es,s in DESIGNS]})

 prepared={}
 for base,en,es,slug in DESIGNS:
  variants={}
  if base in TEST:
   # Always rebuild the two production test portraits from the canonical clean
   # transparent source matrices. Do not inherit stale pattern backgrounds.
   m,t=load_source(base)
   expected={'P0001':8568,'P0012':8735}[base]
   actual=sum(tt.get('stitches',0) for tt in t)
   if actual != expected:
    raise RuntimeError(f'{base}: canonical clean matrix expected {expected} stitches, got {actual}')
   save_preview(base,m,t); variants['CS']=(m,t)
   for suf in ('C2C','TC','LH'):
    _,_,w,h,_,_,_=TECHS[suf]
    variants[suf]=bulk.downsample(m,t,w,h)
  for suf in TECHS:
   if base in TEST: m,t=variants[suf]
   else: m,t=[],[]
   write_json(PATTERNS_DIR/f'{base}-{suf}'/'pattern.json',pattern_json(base,suf,m,t))
   write_json(PRODUCTS_DIR/f'{base}-{suf}'/'product.json',product_json(base,en,es,slug,suf,base in TEST))
   if base in TEST:
    data=bulk.pattern_data(f'{base}-{suf}',en,suf,m,t); data['collection']='Pop Art'; data['collection_id']=CID
    prepared[(base,suf)]=data

 # Render the 8 test products using the existing Pop Art covers.
 STORE_ASSETS.mkdir(parents=True,exist_ok=True); STORE_FILES.mkdir(parents=True,exist_ok=True)
 for (base,suf),data in prepared.items():
  result=bulk.render_one((f'{base}-{suf}',suf,data))
  shutil.copy2(result['pdf'],STORE_FILES/Path(result['pdf']).name)
  shutil.copy2(result['image'],STORE_ASSETS/Path(result['image']).name)

 # Update WooCommerce catalogue: keep the old collection for comparison, but replace P0001/P0012 families.
 catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
 collection_row={'id':CID,'name':'Pop Art','slug':'pop-art-25','name_en':'Pop Art','name_es':'Pop Art',
   'description':collection['description_en'],'description_en':collection['description_en'],'description_es':collection['description_es'],
   'palette_hex':[p['hex'] for p in PALETTE],'thread_codes':[p['dmc'] for p in PALETTE],
   'cover_asset':'assets/P0001-CS-product.webp','techniques':collection['techniques']}
 catalog['collections']=[c for c in catalog.get('collections',[]) if c.get('slug')!='pop-art-25']+[collection_row]
 def family(p):
  return p.get('base_design_id') or re.sub(r'-.*$','',p.get('code',''))
 catalog['products']=[p for p in catalog.get('products',[]) if family(p) not in TEST]
 for base in ('P0001','P0012'):
  for suf in ('CS','C2C','TC','LH'):
   catalog['products'].append(row_for(base,suf,prepared[(base,suf)]))
 catalog['products'].sort(key=lambda p:(family(p),{'CS':0,'C2C':1,'TC':2,'LH':3}.get(p.get('technique_code',''),9),p.get('code','')))
 write_json(CATALOG,catalog)

 # Hard QA: every used thread is one of the exact 25 canonical pairs and every output exists.
 allowed={(p['dmc'],p['hex'].upper()) for p in PALETTE}
 for (base,suf),data in prepared.items():
  for t in data['threads']:
   if (str(t['dmc']),str(t['color']).upper()) not in allowed: raise RuntimeError(f'Out-of-palette thread: {base}-{suf} {t}')
  code=f'{base}-{suf}'
  if not (STORE_FILES/f'Drielo_{code}.pdf').is_file(): raise RuntimeError(f'Missing PDF {code}')
  if not (STORE_ASSETS/f'{code}-product.webp').is_file(): raise RuntimeError(f'Missing product image {code}')
 print(json.dumps({'collection':CID,'design_jsons':26,'variant_product_jsons':104,'variant_pattern_jsons':104,'published_test_products':8,'palette_size':len(PALETTE)},indent=2))

if __name__=='__main__':
 main()
