#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
catalog_path=ROOT.parent/'products'/'catalog.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
by={c.get('slug'):c for c in catalog.get('collections',[])}
changed=False

for p in ROOT.glob('collections/*/collection.json'):
 c=json.loads(p.read_text(encoding='utf-8'))
 row=by.get(c['slug'])
 if not row:
  continue
 mode=c.get('palette_mode','shared')
 show_collection_palette=bool(c.get('show_collection_palette', mode=='shared'))
 if row.get('palette_mode')!=mode:
  row['palette_mode']=mode
  changed=True
 if row.get('show_collection_palette')!=show_collection_palette:
  row['show_collection_palette']=show_collection_palette
  changed=True
 if mode=='per-design':
  hs=[]; ds=[]
 else:
  hs=[x['hex'].upper() for x in c.get('palette',[])]
  ds=[str(x['dmc']) for x in c.get('palette',[])]
 if row.get('palette_hex')!=hs:
  row['palette_hex']=hs
  changed=True
 if [str(x) for x in row.get('thread_codes',[])]!=ds:
  row['thread_codes']=ds
  changed=True

if changed:
 catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Catalog collection palette metadata synchronized.')
else:
 print('Catalog collection palette metadata already synchronized.')
