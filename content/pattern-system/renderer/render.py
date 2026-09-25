#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent; TEMPLATE=ROOT/'template'/'DRIELO_Pattern_Template_MASTER.html'; COLLECTIONS=ROOT/'collections'; PRODUCTS=ROOT/'products'; OUTPUT=ROOT/'output'
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def write_json(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def hex_rgb(v):
 h=v.strip().lstrip('#'); h=''.join(c*2 for c in h) if len(h)==3 else h
 if not re.fullmatch(r'[0-9A-Fa-f]{6}',h): raise ValueError(f'Invalid HEX colour: {v}')
 return tuple(int(h[i:i+2],16) for i in (0,2,4))
def lab(v):
 r,g,b=[x/255 for x in hex_rgb(v)]
 def lin(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
 r,g,b=map(lin,(r,g,b)); x=(r*.4124+g*.3576+b*.1805)/.95047; y=r*.2126+g*.7152+b*.0722; z=(r*.0193+g*.1192+b*.9505)/1.08883
 def f(t): return t**(1/3) if t>.008856 else 7.787*t+16/116
 fx,fy,fz=f(x),f(y),f(z); return 116*fy-16,500*(fx-fy),200*(fy-fz)
def nearest(h,pal):
 a=lab(h); return min(pal,key=lambda p:sum((x-y)**2 for x,y in zip(a,lab(p['hex']))))
def validate_fix(pattern,collection,fix):
 mode=collection.get('palette_mode','shared')
 pal=collection.get('palette') or []; by={str(p['dmc']):p for p in pal}; changes=[]
 if mode=='per-design':
  for t in pattern.get('threads',[]):
   d=str(t.get('dmc','')).strip(); color=str(t.get('color','')).strip()
   if not d: raise ValueError(f'Missing DMC code for symbol {t.get("symbol")!r}')
   if not color: raise ValueError(f'Missing HEX colour for DMC {d}')
   hex_rgb(color)
   t['color']='#'+color.strip().lstrip('#').upper()
  return changes
 if not pal: raise ValueError('Shared collection palette is empty')
 for t in pattern.get('threads',[]):
  d=str(t.get('dmc','')); p=by.get(d)
  if p:
   target=p['hex'].upper()
   if str(t.get('color','')).upper()!=target or (p.get('name') and t.get('name')!=p.get('name')):
    if not fix: raise ValueError(f'DMC {d} is not using canonical collection HEX')
    old=(d,t.get('color')); t['color']=target; t['name']=p.get('name',t.get('name','')); changes.append((t.get('symbol'),old,(d,target)))
  else:
   if not fix: raise ValueError(f'DMC {d} is outside collection palette')
   if not t.get('color'): raise ValueError(f'Cannot remap {t.get("symbol")} without HEX')
   p=nearest(t['color'],pal); old=(d,t['color']); t.update(dmc=str(p['dmc']),color=p['hex'].upper(),name=p.get('name',f"DMC {p['dmc']}")); changes.append((t.get('symbol'),old,(t['dmc'],t['color'])))
 return changes
def validate_matrix(pattern):
 w,h=int(pattern['stitch_width']),int(pattern['stitch_height']); m=pattern.get('matrix') or []; syms={t['symbol'] for t in pattern.get('threads',[])}
 if len(m)!=h: raise ValueError(f'Matrix rows {len(m)} != {h}')
 counts={s:0 for s in syms}; total=0
 for y,row in enumerate(m):
  if len(row)!=w: raise ValueError(f'Row {y} cells {len(row)} != {w}')
  for c in row:
   if c in (None,''): continue
   if c not in syms: raise ValueError(f'Unknown symbol {c!r}')
   counts[c]+=1; total+=1
 pattern['total_stitches']=total
 for t in pattern['threads']: t['stitches']=counts[t['symbol']]
 return total
def data_uri(p):
 mime={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp'}.get(p.suffix.lower())
 if not mime: raise ValueError(f'Unsupported image {p}')
 return f'data:{mime};base64,'+base64.b64encode(p.read_bytes()).decode('ascii')
def export_outputs(html_path, pdf_path, product_image_path):
 from playwright.sync_api import sync_playwright
 from PIL import Image,ImageOps
 tmp=product_image_path.with_suffix('.capture.png')
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  page=browser.new_page(viewport={'width':1400,'height':2000},device_scale_factor=2)
  page.goto(html_path.resolve().as_uri(),wait_until='load',timeout=120000)
  page.wait_for_function("document.documentElement.getAttribute('data-drielo-ready') === '1'",timeout=120000)
  selector='[data-product-image]'
  if page.locator(selector).count()!=1: raise RuntimeError('Template must expose exactly one [data-product-image] element')
  page.eval_on_selector(selector,"el=>{el.style.border='0';el.style.boxShadow='none';}")
  page.locator(selector).screenshot(path=str(tmp),type='png')
  page.pdf(path=str(pdf_path),format='A4',print_background=True,prefer_css_page_size=True)
  browser.close()
 im=Image.open(tmp).convert('RGB')
 product=ImageOps.fit(im,(1200,1500),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
 product.save(product_image_path,'WEBP',quality=90,method=6)
 tmp.unlink(missing_ok=True)
def render(code,fix=False):
 pp=PRODUCTS/code/'product.json'
 if not pp.is_file(): raise FileNotFoundError(pp)
 product=read_json(pp); cp=COLLECTIONS/product['collection']/'collection.json'; coll=read_json(cp); patp=ROOT/product['pattern_file']; pattern=read_json(patp)
 changes=validate_fix(pattern,coll,fix); total=validate_matrix(pattern)
 if fix: write_json(patp,pattern)
 mock=coll.get('mockup_spec',{}); rel=mock.get('asset')
 if not rel: raise ValueError(f"Collection {coll['id']} has no approved mockup asset yet")
 hero=(cp.parent/rel).resolve()
 if not hero.is_file(): raise FileNotFoundError(hero)
 data={'product_code':product['code'],'collection':coll.get('name',coll['id']),'title':product['title'],'subtitle':product.get('subtitle','A modern cross-stitch pattern'),'stitch_width':pattern['stitch_width'],'stitch_height':pattern['stitch_height'],'total_stitches':pattern['total_stitches'],'threads':pattern['threads'],'matrix':pattern['matrix'],'skill_level':product.get('skill_level','Beginner friendly'),'stitch_type':product.get('stitch_type','Full cross stitch'),'website':product.get('website','www.drielo.com'),'materials':product.get('materials',['DMC embroidery floss','14-count Aida or preferred fabric','Tapestry needle size 24/26','6-inch hoop (optional)']),'fabric_counts':product.get('fabric_counts',[14,16,18]),'preview_rules':coll.get('preview_rules',{}),'source_mode':pattern.get('source_mode','')}
 html=TEMPLATE.read_text(encoding='utf-8').replace('__DRIELO_PATTERN_JSON__',json.dumps(data,ensure_ascii=False,separators=(',',':')),1)

 if data.get('source_mode')=='pixel-exact':
  replacements={
   '<th>DMC</th>':'<th>Colour code</th>',
   '${threadCount} DMC colours':'${threadCount} exact colours',
   'Each chart symbol corresponds to one DMC colour.':'Each chart symbol corresponds to one exact source colour.',
   'Use this overview together with the enlarged symbol sections and the DMC colour key.':'Use this overview together with the enlarged symbol sections and the exact colour key.',
   'Keep the DMC key nearby':'Keep the colour key nearby',
   'Every symbol maps to the same DMC number shown on the thread-colour page.':'Every symbol maps to the same exact source colour shown on the thread-colour page.',
   'Use the DMC colour key on page 4 together with the colour and symbol charts throughout this booklet.':'Use the exact colour key on page 4 together with the colour and symbol charts throughout this booklet.',
  }
  for old,new in replacements.items(): html=html.replace(old,new)
 m=re.search(r'<script id="template-assets" type="application/json">(.*?)</script>',html,re.S)
 if not m: raise ValueError('Template assets block missing')
 a=json.loads(m.group(1)); a.update({'cover_image':data_uri(hero),'frame':mock.get('frame',{})}); html=html[:m.start(1)]+json.dumps(a,ensure_ascii=False,separators=(',',':'))+html[m.end(1):]
 out=OUTPUT/code; out.mkdir(parents=True,exist_ok=True); hp=out/f'{code}.html'; pdf=out/f'Drielo_{code}.pdf'; product_image=out/f'{code}-product.webp'; hp.write_text(html,encoding='utf-8')
 export_outputs(hp,pdf,product_image)
 if not pdf.is_file() or pdf.stat().st_size<10000: raise RuntimeError('PDF export failed')
 if not product_image.is_file() or product_image.stat().st_size<10000: raise RuntimeError('Product image export failed')
 print(json.dumps({'product':code,'collection':coll['id'],'stitches':total,'palette_fixes':len(changes),'pdf':str(pdf),'pdf_bytes':pdf.stat().st_size,'product_image':str(product_image),'product_image_bytes':product_image.stat().st_size},indent=2)); return pdf
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--product',required=True); ap.add_argument('--fix-palette',action='store_true'); a=ap.parse_args(); render(a.product,a.fix_palette)
if __name__=='__main__': main()
