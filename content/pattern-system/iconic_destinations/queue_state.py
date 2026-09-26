#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUEUE = ROOT / "content" / "pattern-system" / "iconic_destinations" / "publish_queue.json"


def load():
    return json.loads(QUEUE.read_text(encoding="utf-8"))


def save(doc):
    QUEUE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def item(doc, design_id):
    for row in doc["items"]:
        if row["base_design_id"] == design_id:
            return row
    raise SystemExit(f"Unknown design: {design_id}")


def pdf_mode_enabled(doc):
    return str(doc.get("mode", "")).startswith("pdf-source-")


def cmd_next(args):
    doc = load()
    row = None if (not doc.get("auto_continue", False) or not pdf_mode_enabled(doc)) else next((x for x in doc["items"] if x.get("status") == "pending"), None)
    values = {
        "design_id": row["base_design_id"] if row else "",
        "title_en": row["title_en"] if row else "",
        "slug": row["slug"] if row else "",
        "attempt": str((row.get("attempts", 0) + 1) if row else 0),
    }
    output = args.github_output or os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            for k, v in values.items():
                fh.write(f"{k}={v}\n")
    print(json.dumps(values, ensure_ascii=False))


def cmd_success(args):
    doc = load()
    row = item(doc, args.design_id)
    row["attempts"] = int(row.get("attempts", 0)) + 1
    row["status"] = "published"
    row["last_run"] = args.run_url or None
    row["last_error"] = None
    row["published_at"] = now()
    save(doc)
    print(f"PUBLISHED {args.design_id}")


def cmd_fail(args):
    doc = load()
    row = item(doc, args.design_id)
    row["attempts"] = int(row.get("attempts", 0)) + 1
    retry = row["attempts"] < int(doc.get("max_attempts_per_design", 2))
    row["status"] = "pending" if retry else "failed"
    row["last_run"] = args.run_url or None
    row["last_error"] = (args.error or "workflow failed")[:1000]
    row["failed_at"] = now()
    save(doc)
    print(("RETRY " if retry else "FAILED ") + args.design_id)


def cmd_has_work(args):
    doc = load()
    pending = any(x.get("status") == "pending" for x in doc["items"])
    print("yes" if doc.get("auto_continue", False) and pdf_mode_enabled(doc) and pending else "no")


def cmd_summary(args):
    doc = load()
    counts = {}
    for row in doc["items"]:
        status = row.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps(counts, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("next"); p.add_argument("--github-output"); p.set_defaults(func=cmd_next)
    p = sub.add_parser("success"); p.add_argument("design_id"); p.add_argument("--run-url", default=""); p.set_defaults(func=cmd_success)
    p = sub.add_parser("fail"); p.add_argument("design_id"); p.add_argument("--run-url", default=""); p.add_argument("--error", default=""); p.set_defaults(func=cmd_fail)
    p = sub.add_parser("has-work"); p.set_defaults(func=cmd_has_work)
    p = sub.add_parser("summary"); p.set_defaults(func=cmd_summary)
    args = ap.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
