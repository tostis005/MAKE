#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent; catalog_path=ROOT.parent/'products'/'catalog.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8')); by={c.get('slug'):c for c in catalog.get('collections',[])}; changed=False
for p in ROOT.glob('collections/*/collection.json'):
 c=json.loads(p.read_text(encoding='utf-8')); row=by.get(c['slug'])
 if not row: continue
 hs=[x['hex'].upper() for x in c['palette']]; ds=[str(x['dmc']) for x in c['palette']]
 if row.get('palette_hex')!=hs: row['palette_hex']=hs; changed=True
 if [str(x) for x in row.get('thread_codes',[])]!=ds: row['thread_codes']=ds; changed=True
if changed: catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print('Catalog palette synchronized.')
else: print('Catalog palette already synchronized.')
