#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
errs=[]; cols={}
for p in ROOT.glob('collections/*/collection.json'):
 try:
  d=load(p); cols[d['id']]=d; mode=d.get('palette_mode','shared'); dm=[str(x['dmc']) for x in d.get('palette',[])]
  if mode not in ('shared','per-design'): errs.append(f'{p}: invalid palette_mode {mode!r}')
  if mode=='shared' and not dm: errs.append(f'{p}: empty shared palette')
  if len(dm)!=len(set(dm)): errs.append(f'{p}: duplicate DMC codes')
  f=d.get('mockup_spec',{}).get('frame',{})
  if f.get('enabled'):
   s=f.get('source_px',{}); a=f.get('area_px',{})
   if min(float(s.get('width',0)),float(s.get('height',0)),float(a.get('width',0)),float(a.get('height',0)))<=0: errs.append(f'{p}: enabled frame needs dimensions')
 except Exception as e: errs.append(f'{p}: {e}')
for p in ROOT.glob('products/*/product.json'):
 if p.parent.name.startswith('_'): continue
 try:
  d=load(p)
  coll=cols.get(d['collection'])
  if not coll:
   errs.append(f'{p}: unknown collection')
  else:
   allowed=set(coll.get('techniques',[]))
   technique=str(d.get('technique',''))
   if allowed and technique not in allowed:
    errs.append(f'{p}: technique {technique!r} is not allowed by collection {d["collection"]!r}')
  if not (ROOT/d['pattern_file']).is_file(): errs.append(f'{p}: missing pattern file')
 except Exception as e: errs.append(f'{p}: {e}')
if errs:
 print('\n'.join('ERROR: '+e for e in errs),file=sys.stderr); sys.exit(1)
print(f'Validated {len(cols)} collections.')
