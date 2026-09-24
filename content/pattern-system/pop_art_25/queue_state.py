#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
QUEUE=ROOT/"content"/"pattern-system"/"pop_art_25"/"publish_queue.json"
CATALOG=ROOT/"content"/"products"/"catalog.json"
PROTECTED={"P0001","P0012"}

def load():
    return json.loads(QUEUE.read_text(encoding="utf-8"))

def save(doc):
    QUEUE.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def get_item(doc,design_id):
    for item in doc["items"]:
        if item["base_design_id"]==design_id:
            return item
    raise SystemExit(f"Unknown design id: {design_id}")


def needs_gallery_backfill(base_id):
    if base_id in PROTECTED or not CATALOG.is_file():
        return False
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    rows={p.get("code"):p for p in catalog.get("products",[])}
    for suffix in ("CS","C2C","TC","LH"):
        row=rows.get(f"{base_id}-{suffix}")
        if not row:
            return True
        gallery=row.get("gallery") or []
        if gallery != [f"assets/{base_id}-{suffix}-gallery-{i}.webp" for i in (2,3,4)]:
            return True
    return False

def gallery_backfill_item(doc):
    for item in doc["items"]:
        base=item["base_design_id"]
        if item.get("status")=="published" and needs_gallery_backfill(base):
            return item
    return None

def cmd_next(args):
    doc=load()
    item=None
    if doc.get("auto_continue",True):
        recovery_limit=int(doc.get("recovery_attempts_per_design",4))
        item=next(
            (x for x in doc["items"]
             if x.get("status")=="failed" and int(x.get("attempts",0))<recovery_limit),
            None
        )
        if item is None:
            item=next((x for x in doc["items"] if x.get("status")=="pending"),None)
        if item is None:
            item=gallery_backfill_item(doc)
    output=args.github_output or os.environ.get("GITHUB_OUTPUT")
    values={
        "design_id":item["base_design_id"] if item else "",
        "title_en":item["title_en"] if item else "",
        "slug":item["slug"] if item else "",
        "attempt":str((item.get("attempts",0)+1) if item else 0),
    }
    if output:
        with open(output,"a",encoding="utf-8") as fh:
            for k,v in values.items():
                fh.write(f"{k}={v}\n")
    print(json.dumps(values,ensure_ascii=False))

def cmd_success(args):
    doc=load()
    item=get_item(doc,args.design_id)
    item["attempts"]=int(item.get("attempts",0))+1
    item["status"]="published"
    item["last_run"]=args.run_url or None
    item["last_error"]=None
    item["published_at"]=now()
    save(doc)
    print(f"PUBLISHED {args.design_id}")

def cmd_fail(args):
    doc=load()
    item=get_item(doc,args.design_id)
    item["attempts"]=int(item.get("attempts",0))+1
    max_attempts=int(doc.get("max_attempts_per_design",2))
    recovery_limit=int(doc.get("recovery_attempts_per_design",4))
    retry=item["attempts"]<max_attempts
    if retry:
        item["status"]="pending"
    elif item["attempts"]<recovery_limit:
        item["status"]="failed"
    else:
        item["status"]="blocked"
    item["last_run"]=args.run_url or None
    item["last_error"]=(args.error or "workflow failed")[:1000]
    item["failed_at"]=now()
    save(doc)
    label="RETRY " if item["status"]=="pending" else ("FAILED " if item["status"]=="failed" else "BLOCKED ")
    print(label+args.design_id)

def cmd_has_work(args):
    doc=load()
    pending=[x for x in doc["items"] if x.get("status")=="pending"]
    recovery_limit=int(doc.get("recovery_attempts_per_design",4))
    recoverable=[x for x in doc["items"] if x.get("status")=="failed" and int(x.get("attempts",0))<recovery_limit]
    backfill=gallery_backfill_item(doc)
    print("yes" if doc.get("auto_continue",True) and (recoverable or pending or backfill) else "no")

def cmd_summary(args):
    doc=load()
    counts={}
    for item in doc["items"]:
        counts[item.get("status","unknown")]=counts.get(item.get("status","unknown"),0)+1
    print(json.dumps(counts,sort_keys=True))

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("next"); p.add_argument("--github-output"); p.set_defaults(func=cmd_next)
    p=sub.add_parser("success"); p.add_argument("design_id"); p.add_argument("--run-url",default=""); p.set_defaults(func=cmd_success)
    p=sub.add_parser("fail"); p.add_argument("design_id"); p.add_argument("--run-url",default=""); p.add_argument("--error",default=""); p.set_defaults(func=cmd_fail)
    p=sub.add_parser("has-work"); p.set_defaults(func=cmd_has_work)
    p=sub.add_parser("summary"); p.set_defaults(func=cmd_summary)
    args=ap.parse_args(); args.func(args)

if __name__=="__main__":
    main()
