#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
SYSTEM = ROOT / "content" / "pattern-system"
FILES = ROOT / "content" / "products" / "files"
TEMPLATES = SYSTEM / "multitech" / "templates"
ASSETS = SYSTEM / "multitech" / "assets"
CODES = [f"P{1000+i:04d}-CS" for i in range(1, 61)]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def valid_pdf(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 100000 and path.read_bytes()[:4] == b"%PDF"


def main() -> None:
    missing = [code for code in CODES if not valid_pdf(FILES / f"Drielo_{code}.pdf")]
    if not missing:
        print("POP_ART_PDFS_ALREADY_READY=60")
        return

    bulk = load_module("drielo_pdf_bulk", SYSTEM / "multitech" / "bulk_generate.py")
    template_master = (TEMPLATES / "cross-stitch.html").read_text(encoding="utf-8")
    floral = bulk.data_uri(ASSETS / "floral.png")
    cover = bulk.data_uri(ASSETS / "cover-cross-stitch.webp")
    FILES.mkdir(parents=True, exist_ok=True)

    jobs = []
    for code in missing:
        pattern_path = SYSTEM / "patterns" / code / "pattern.json"
        product_path = SYSTEM / "products" / code / "product.json"
        if not pattern_path.is_file() or not product_path.is_file():
            raise RuntimeError(f"{code}: missing pattern/product source JSON")
        pattern = json.loads(pattern_path.read_text(encoding="utf-8"))
        product = json.loads(product_path.read_text(encoding="utf-8"))
        data = bulk.pattern_data(code, product["title"], "CS", pattern["matrix"], pattern["threads"])
        data["collection"] = "Retratos Pop Art"
        data["collection_id"] = "pop-art-25"

        html = re.sub(
            r'(<script id="template-pattern-data" type="application/json">)(.*?)(</script>)',
            lambda m: m.group(1) + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + m.group(3),
            template_master,
            count=1,
            flags=re.S,
        )
        html = re.sub(
            r'(<script id="template-assets" type="application/json">)(.*?)(</script>)',
            lambda m: m.group(1) + json.dumps({"floral": floral, "cover_image": cover}, separators=(",", ":")) + m.group(3),
            html,
            count=1,
            flags=re.S,
        )
        jobs.append((code, html, FILES / f"Drielo_{code}.pdf"))

    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="drielo-pop-art-pdf-") as td:
        temp = Path(td)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 2000}, device_scale_factor=1.0)
            for n, (code, html, target) in enumerate(jobs, start=1):
                html_path = temp / f"{code}.html"
                html_path.write_text(html, encoding="utf-8")
                page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=120000)
                page.wait_for_function(
                    "document.documentElement.getAttribute('data-drielo-ready') === '1'",
                    timeout=120000,
                )
                page.wait_for_function(
                    "document.documentElement.getAttribute('data-drielo-stitch-renderer') === 'aida-relief-v4'",
                    timeout=120000,
                )
                page.pdf(
                    path=str(target),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
                if not valid_pdf(target):
                    raise RuntimeError(f"{code}: generated PDF is invalid")
                print(f"PDF {n}/{len(jobs)} {code} {target.stat().st_size} bytes", flush=True)
            browser.close()

    ready = [code for code in CODES if valid_pdf(FILES / f"Drielo_{code}.pdf")]
    if len(ready) != 60:
        raise RuntimeError(f"Expected 60 Pop Art PDFs, got {len(ready)}")
    print("POP_ART_PDFS_READY=60")


if __name__ == "__main__":
    main()
