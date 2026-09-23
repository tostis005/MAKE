#!/usr/bin/env python3
from __future__ import annotations
import base64, importlib.util, json, re, shutil, zlib
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path.cwd()
SYSTEM=ROOT/'content'/'pattern-system'
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
 im=Image.new('RGB',(400,480),'white'); d=ImageDraw.Draw(im)
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
      'download':f'files/Drielo_{code}.pdf','gallery_revision':2026092307,
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
   m,t=load_source(base); save_preview(base,m,t); variants['CS']=(m,t)
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
