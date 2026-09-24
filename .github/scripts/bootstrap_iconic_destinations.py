#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
PS=ROOT/'content'/'pattern-system'
CID='iconic-destinations'
designs=json.loads((PS/'collections'/CID/'designs.json').read_text(encoding='utf-8'))['designs']

for d in designs:
    base=d['base_design_id']
    code=f'{base}-CS'
    product_dir=PS/'products'/code
    pattern_dir=PS/'patterns'/code
    product_dir.mkdir(parents=True,exist_ok=True)
    pattern_dir.mkdir(parents=True,exist_ok=True)

    product={
        'code':code,
        'base_design_id':base,
        'technique_code':'CS',
        'collection':CID,
        'title':d['title_en'],
        'title_en':d['title_en'],
        'title_es':d['title_es'],
        'design_slug':d['slug'],
        'technique':'cross-stitch',
        'pattern_file':f'patterns/{code}/pattern.json',
        'template':'cross-stitch.html',
        'website':'www.drielo.com',
        'status':'draft',
        'render_ready':False,
        'renderer':'multitech',
        'source_artwork':None,
        'page_1_asset':None,
        'palette_mode':'per-design',
    }
    pattern={
        'code':code,
        'base_design_id':base,
        'technique_code':'CS',
        'collection':CID,
        'palette_mode':'per-design',
        'status':'awaiting-source-artwork',
        'source_asset':None,
        'stitch_width':100,
        'stitch_height':120,
        'total_stitches':0,
        'threads':[],
        'matrix':[],
    }
    (product_dir/'product.json').write_text(json.dumps(product,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (pattern_dir/'pattern.json').write_text(json.dumps(pattern,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(f'Staged {len(designs)} Iconic Destinations cross-stitch product/pattern stubs.')
