#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "content" / "source-images" / "collections"
REGISTRY = SOURCE_ROOT / "registry.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
FORBIDDEN_TOKENS = ("mosaic", "mosaico", "contact-sheet", "contact_sheet", "sheet", "board", "collage")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def configured_collections() -> dict[str, dict]:
    registry = read_json(REGISTRY)
    out = {}
    for item in registry.get("collections", []):
        cfg_path = SOURCE_ROOT / item["config"]
        cfg = read_json(cfg_path)
        out[cfg["collection_id"]] = cfg
    return out


def image_files(folder: Path):
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.name.lower() != "readme.md"
        and p.suffix.lower() in IMAGE_EXTS
    )


def product_files(folder: Path):
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.name.lower() != "readme.md"
    )


def validate_background(cfg: dict, require: bool) -> list[Path]:
    folder = SOURCE_ROOT / cfg["collection_id"] / cfg.get("background_directory", "background")
    files = image_files(folder)
    if len(files) > 1:
        raise SystemExit(
            f"{cfg['collection_id']}: expected at most one canonical background image, found {len(files)}: "
            + ", ".join(p.name for p in files)
        )
    if require and not files:
        fallbacks = cfg.get("legacy_background_fallbacks", [])
        raise SystemExit(
            f"{cfg['collection_id']}: canonical background missing. "
            f"Legacy fallbacks configured: {fallbacks}"
        )
    return files


def reject_non_images(folder: Path):
    bad = [
        p.name for p in product_files(folder)
        if p.suffix.lower() != ".png"
    ]
    if bad:
        raise SystemExit(
            f"{folder}: product sources must be individual PNG files only; invalid files: {bad}"
        )


def validate_product(path: Path, expected_size: tuple[int, int]):
    low = path.name.lower()
    if any(token in low for token in FORBIDDEN_TOKENS):
        raise SystemExit(f"{path}: forbidden mosaic/contact-sheet style filename")
    if path.suffix.lower() != ".png":
        raise SystemExit(f"{path}: expected PNG")
    try:
        with Image.open(path) as im:
            if im.size != expected_size:
                raise SystemExit(
                    f"{path}: expected {expected_size[0]}x{expected_size[1]} px, got {im.size[0]}x{im.size[1]}"
                )
            im.verify()
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"{path}: invalid image: {exc}") from exc


def select_products(cfg: dict, selector: str | None) -> list[Path]:
    folder = SOURCE_ROOT / cfg["collection_id"] / cfg.get("product_directory", "products")
    reject_non_images(folder)
    files = [p for p in product_files(folder) if p.suffix.lower() == ".png"]
    if selector:
        wanted = selector.strip().lower()
        matches = [
            p for p in files
            if p.stem.lower() == wanted
            or p.stem.lower().startswith(wanted + "-")
            or p.stem.lower().startswith(wanted + "_")
        ]
        if len(matches) != 1:
            raise SystemExit(
                f"{cfg['collection_id']}: selector {selector!r} matched {len(matches)} files; "
                f"expected exactly one. Matches: {[p.name for p in matches]}"
            )
        files = matches

    expected = tuple(int(x) for x in cfg.get("product_size_px", [100, 120]))
    for path in files:
        validate_product(path, expected)
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Validate/select canonical Drielo collection image sources."
    )
    parser.add_argument("--collection", required=True)
    parser.add_argument(
        "--product",
        help="Optional base design code or filename stem. Omit to select the whole collection.",
    )
    parser.add_argument(
        "--require-background",
        action="store_true",
        help="Fail unless the canonical background folder already contains its single approved image.",
    )
    parser.add_argument(
        "--github-output",
        help="Optional GitHub Actions output file.",
    )
    args = parser.parse_args()

    collections = configured_collections()
    if args.collection not in collections:
        raise SystemExit(
            f"Unknown collection {args.collection!r}. Available: {', '.join(sorted(collections))}"
        )
    cfg = collections[args.collection]
    backgrounds = validate_background(cfg, args.require_background)
    products = select_products(cfg, args.product)

    mode = "single" if args.product else "collection"
    payload = {
        "collection": args.collection,
        "mode": mode,
        "background": str(backgrounds[0].relative_to(ROOT)) if backgrounds else None,
        "products": [str(p.relative_to(ROOT)) for p in products],
        "product_count": len(products),
        "expected_product_size_px": cfg.get("product_size_px", [100, 120]),
        "legacy_background_fallbacks": cfg.get("legacy_background_fallbacks", []),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.github_output:
        out = Path(args.github_output)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(f"collection={args.collection}\n")
            fh.write(f"mode={mode}\n")
            fh.write(f"product_count={len(products)}\n")
            fh.write("products_json=" + json.dumps(payload["products"], separators=(",", ":")) + "\n")
            fh.write(f"background={payload['background'] or ''}\n")


if __name__ == "__main__":
    main()
