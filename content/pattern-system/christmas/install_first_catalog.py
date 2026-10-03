#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CATALOG=ROOT/'content/products/catalog.json'
CODE='N0001-CS'
SKU='DRIELO-N0001-CS'
TITLE_EN='Christmas Tree Mini Cross Stitch Pattern PDF'
TITLE_ES='Patrón Mini de Árbol de Navidad en Punto de Cruz PDF'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

catalog=load(CATALOG)

cats=catalog.setdefault('categories',[])
child={
  'slug':'cross-stitch-christmas',
  'name':'Christmas Cross Stitch',
  'name_en':'Christmas Cross Stitch',
  'name_es':'Punto de cruz de Navidad',
  'parent':'cross-stitch-patterns',
}
idx=next((i for i,c in enumerate(cats) if c.get('slug')==child['slug']),None)
if idx is None: cats.append(child)
else: cats[idx].update(child)

palette=load(ROOT/'content/source-images/collections/christmas/palette20_rgb.json')['palette_rgb']
palette_hex=['#%02X%02X%02X'%tuple(c) for c in palette]
collection={
  'id':'christmas','slug':'christmas',
  'name':'Christmas','name_en':'Christmas','name_es':'Navidad',
  'description':'Mini Christmas cross-stitch patterns designed as quick, beginner-friendly seasonal projects.',
  'description_en':'Mini Christmas cross-stitch patterns designed as quick, beginner-friendly seasonal projects.',
  'description_es':'Mini patrones navideños de punto de cruz pensados como proyectos rápidos y aptos para principiantes.',
  'techniques':['cross-stitch'],
  'cover_asset':f'assets/{CODE}-product.webp',
  'visible':True,'force_visibility_sync':True,
  'palette_mode':'shared','show_collection_palette':True,
  'palette_hex':palette_hex,
}
collections=catalog.setdefault('collections',[])
idx=next((i for i,c in enumerate(collections) if c.get('slug')=='christmas'),None)
if idx is None: collections.append(collection)
else: collections[idx].update(collection)

total=3000
colours=19
short_en='Mini Christmas tree cross-stitch PDF. A 50 × 60 full-coverage motif is centered on a 100 × 120 chart, leaving generous blank canvas around it. 3,000 stitches and 19 colours.'
short_es='Mini patrón PDF de árbol de Navidad. El motivo de 50 × 60 queda centrado en una cuadrícula de 100 × 120, dejando bastante lienzo en blanco alrededor. 3.000 puntadas y 19 colores.'
desc_en=(
  f'<p><strong>{TITLE_EN}</strong> is a digital counted cross-stitch pattern from the Christmas Minis collection.</p>'
  '<p>The artwork itself is 50 × 60 stitches and is centered inside a 100 × 120 chart. '
  'The extra area stays blank, so the storefront mockup keeps the same physical scale as Drielo\'s existing 100 × 120 patterns.</p>'
  '<h3>Pattern details</h3><ul><li>Code: N0001-CS</li><li>Chart: 100 × 120 stitches</li>'
  '<li>Stitched motif: 50 × 60 stitches</li><li>Total stitched cells: 3,000</li>'
  '<li>Colours: 19</li><li>PDF: 1 page</li><li>Skill level: Beginner friendly</li></ul><p>Digital product only.</p>'
)
desc_es=(
  f'<p><strong>{TITLE_ES}</strong> es un patrón digital contado de la colección Christmas Minis.</p>'
  '<p>El dibujo ocupa 50 × 60 puntos y está centrado dentro de una cuadrícula de 100 × 120. '
  'La zona adicional queda en blanco para conservar en el mockup la misma escala física que los patrones Drielo de 100 × 120.</p>'
  '<h3>Detalles</h3><ul><li>Código: N0001-CS</li><li>Cuadrícula: 100 × 120</li>'
  '<li>Motivo bordado: 50 × 60</li><li>Puntadas: 3.000</li><li>Colores: 19</li>'
  '<li>PDF: 1 página</li><li>Nivel: apto para principiantes</li></ul><p>Producto exclusivamente digital.</p>'
)
row={
  'code':CODE,'sku':SKU,'price':2.99,
  'categories':['cross-stitch-patterns','cross-stitch-christmas'],
  'purchase_note_en':'Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.',
  'purchase_note_es':'Tu PDF digital estará disponible desde la confirmación del pedido y en Mi cuenta > Descargas una vez completado el pago.',
  'title':TITLE_EN,'title_en':TITLE_EN,'title_es':TITLE_ES,
  'slug':'christmas-tree-mini-cross-stitch-pattern','collection':'christmas',
  'stitches':total,'grid':'100 × 120 stitches','colours':colours,'color_count':colours,
  'grid_width':100,'grid_height':120,'motif_width':50,'motif_height':60,
  'skill':'Beginner friendly','skill_en':'Beginner friendly','skill_es':'Apto para principiantes',
  'stitch_type':'Full cross stitch','stitch_type_en':'Full cross stitch','stitch_type_es':'Punto de cruz completo',
  'short_description':short_en,'short_description_en':short_en,'short_description_es':short_es,
  'description':desc_en,'description_en':desc_en,'description_es':desc_es,
  'gallery':[],
  'download':f'files/Drielo_{CODE}.pdf',
  'featured_image':f'assets/{CODE}-product.webp',
  'seo_title':f'{TITLE_EN} | Drielo','seo_title_en':f'{TITLE_EN} | Drielo','seo_title_es':f'{TITLE_ES} | Drielo',
  'meta_description':short_en[:155],'meta_description_en':short_en[:155],'meta_description_es':short_es[:155],
  'tags':['christmas tree','christmas cross stitch','mini cross stitch','cross stitch pdf','counted cross stitch','digital pattern'],
  'etsy_tags_en':['christmas tree','christmas cross stitch','mini cross stitch','cross stitch pdf','counted cross stitch','digital pattern'],
  'etsy_tags_es':['árbol de navidad','punto de cruz navidad','mini punto de cruz','patrón pdf','punto de cruz','patrón digital'],
  'design_id':CODE,'base_design_id':'N0001','technique_code':'CS','technique':'cross-stitch',
  'size_attribute_label':'Pattern size','colour_attribute_label':'Colours','type_attribute_label':'Technique','count_attribute_label':'Total stitches',
  'filters':{
    'technique':['cross-stitch'],'theme':['holidays-seasons'],'style':['cute'],'project':['wall-art'],
    'orientation':['portrait'],'difficulty':['beginner'],'color-family':['multicolor'],'season':['christmas'],
  },
}
products=catalog.setdefault('products',[])
idx=next((i for i,p in enumerate(products) if p.get('code')==CODE or p.get('sku')==SKU),None)
if idx is None: products.append(row)
else: products[idx]=row
catalog['retired_products']=[x for x in catalog.get('retired_products',[]) if x!=SKU]
save(CATALOG,catalog)
print('CHRISTMAS_FIRST_CATALOG_READY', CODE)
