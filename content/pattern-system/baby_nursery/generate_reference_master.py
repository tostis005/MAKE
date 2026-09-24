#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

from PIL import Image
from premium_refinement import refine_rows

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_DIR = SYSTEM / "collections" / "baby-nursery"
LIBRARY_DIR = COLLECTION_DIR / "reference-library"
MANIFEST_PATH = LIBRARY_DIR / "manifest.json"
COLLECTION_PATH = COLLECTION_DIR / "collection.json"
DESIGNS_PATH = COLLECTION_DIR / "designs.json"
SOURCE_DIR = COLLECTION_DIR / "source-designs"
REFERENCE_DIR = COLLECTION_DIR / "reference-masters"

EXPECTED_DECODED_SHA256 = "533a4d7ed0892fd142eed3406b4740a539f70cbfffeaf932813466800a97ad19"
STANDARD_ALPHABET = list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def design_meta(base_id: str):
    for item in read_json(DESIGNS_PATH)["designs"]:
        if item["base_design_id"] == base_id:
            return item
    raise RuntimeError(f"Unknown design id: {base_id}")


def load_archive():
    manifest = read_json(MANIFEST_PATH)
    parts = manifest.get("canonical_archive_parts") or []
    if len(parts) != 10:
        raise RuntimeError(f"Expected 10 canonical archive parts, got {parts}")

    encoded = "".join((LIBRARY_DIR / name).read_text(encoding="ascii").strip() for name in parts)
    try:
        compressed = base64.b64decode(encoded, validate=True)
        raw = zlib.decompress(compressed)
    except Exception as exc:
        raise RuntimeError(f"Canonical reference archive cannot be decoded: {exc}") from exc

    digest = hashlib.sha256(raw).hexdigest()
    expected = manifest.get("decoded_sha256") or EXPECTED_DECODED_SHA256
    if digest != expected or digest != EXPECTED_DECODED_SHA256:
        raise RuntimeError(f"Canonical reference archive digest mismatch: {digest}")

    data = json.loads(raw.decode("utf-8"))
    if data.get("version") != 1:
        raise RuntimeError(f"Unsupported canonical archive version: {data.get('version')}")
    if data.get("grid") != {"width": 100, "height": 120}:
        raise RuntimeError(f"Unexpected canonical grid: {data.get('grid')}")
    if len(data.get("designs", {})) != 30:
        raise RuntimeError(f"Expected 30 canonical designs, got {len(data.get('designs', {}))}")
    return manifest, data


def load_design_reference(base_id: str, meta: dict):
    manifest = read_json(MANIFEST_PATH)
    direct = LIBRARY_DIR / f"{base_id}-{meta['slug']}.json"
    source_kind = "direct-user-sheet-crop"

    if direct.is_file():
        d = read_json(direct)
    else:
        parts = manifest.get("direct_reference_bundle_parts") or []
        if not parts:
            return None
        encoded = "".join((LIBRARY_DIR / name).read_text(encoding="ascii").strip() for name in parts)
        try:
            bundle_raw = zlib.decompress(base64.b64decode(encoded, validate=True))
        except Exception as exc:
            raise RuntimeError(f"Direct reference bundle cannot be decoded: {exc}") from exc
        bundle_digest = hashlib.sha256(bundle_raw).hexdigest()
        expected_bundle = manifest.get("direct_reference_bundle_decoded_sha256")
        if not expected_bundle or bundle_digest != expected_bundle:
            raise RuntimeError(
                f"Direct reference bundle digest mismatch: {bundle_digest} != {expected_bundle}"
            )
        bundle = json.loads(bundle_raw.decode("utf-8"))
        if bundle.get("version") != 1:
            raise RuntimeError(f"Unsupported direct reference bundle version: {bundle.get('version')}")
        d = (bundle.get("designs") or {}).get(base_id)
        if d is None:
            return None
        source_kind = "direct-user-sheet-bundle"

    if d.get("version") != 1:
        raise RuntimeError(f"{base_id}: unsupported direct reference version")
    if d.get("base_design_id") != base_id or d.get("slug") != meta["slug"]:
        raise RuntimeError(f"{base_id}: direct reference identity mismatch")

    try:
        raw = zlib.decompress(base64.b64decode(d["matrix_zlib_base64"], validate=True))
    except Exception as exc:
        raise RuntimeError(f"{base_id}: direct reference matrix cannot be decoded: {exc}") from exc

    digest = hashlib.sha256(raw).hexdigest()
    if digest != d.get("matrix_sha256"):
        raise RuntimeError(f"{base_id}: direct reference matrix digest mismatch: {digest}")

    rows = raw.decode("ascii").splitlines()
    if len(rows) != 120 or any(len(row) != 100 for row in rows):
        raise RuntimeError(f"{base_id}: direct reference matrix is not 100x120")

    manifest_row = next((x for x in manifest["designs"] if x["base_design_id"] == base_id), None)
    if not manifest_row:
        raise RuntimeError(f"{base_id}: missing from reference-library manifest")

    return {
        "manifest": manifest,
        "canonical": {
            "slug": meta["slug"],
            "sheet": int(manifest_row["reference_sheet"]),
            "row": int(manifest_row["row"]),
            "column": int(manifest_row["column"]),
            "rows": rows,
        },
        "alphabet": STANDARD_ALPHABET,
        "source_kind": source_kind,
        "source_sha256": digest,
        "direct_metadata": d,
    }


def rows_from_master_image(image, palette, alphabet):
    image=image.convert("RGBA")
    if image.size != (800,960):
        raise RuntimeError(f"Expected 800x960 approved master, got {image.size}")
    pal=[]
    for p in palette:
        hx=str(p["hex"]).lstrip("#")
        pal.append(tuple(int(hx[i:i+2],16) for i in (0,2,4)))

    rows=[]
    px=image.load()
    for gy in range(120):
        row=[]
        for gx in range(100):
            samples=[]
            for yy in range(gy*8, gy*8+8):
                for xx in range(gx*8, gx*8+8):
                    r,g,b,a=px[xx,yy]
                    if a >= 128:
                        samples.append((r,g,b))
            if len(samples) < 8:
                row.append(".")
                continue
            # Average the occupied pixels so old palette colours can be mapped
            # cleanly into the rebuilt vivid palette.
            rr=sum(c[0] for c in samples)/len(samples)
            gg=sum(c[1] for c in samples)/len(samples)
            bb=sum(c[2] for c in samples)/len(samples)
            idx=min(
                range(len(pal)),
                key=lambda i: 2*(rr-pal[i][0])**2 + 4*(gg-pal[i][1])**2 + 3*(bb-pal[i][2])**2,
            )
            row.append(alphabet[idx])
        rows.append("".join(row))
    return rows


def remove_exterior_dark_rows(rows, palette, alphabet, dark_dmc="310", neighborhood=8):
    grid=[list(r) for r in rows]
    h=len(grid); w=len(grid[0]) if h else 0
    try:
        dark_index=next(i for i,p in enumerate(palette) if str(p.get("dmc","")).upper()==str(dark_dmc).upper())
    except StopIteration:
        return rows, {"removed_cells":0,"components":0,"symbol":None}
    if dark_index >= len(alphabet):
        return rows, {"removed_cells":0,"components":0,"symbol":None}
    dark=alphabet[dark_index]

    if neighborhood == 4:
        dirs=[(-1,0),(1,0),(0,-1),(0,1)]
    else:
        dirs=[(dy,dx) for dy in (-1,0,1) for dx in (-1,0,1) if not (dy==0 and dx==0)]

    # Exterior dark outline is the set of dark components that touch
    # transparency or the canvas boundary. Isolated internal dark details
    # (eyes, mouth, lettering, accents) are intentionally preserved.
    exterior_seeds=[]
    for y in range(h):
        for x in range(w):
            if grid[y][x] != dark:
                continue
            exterior=False
            for dy,dx in dirs:
                yy,xx=y+dy,x+dx
                if yy<0 or yy>=h or xx<0 or xx>=w or grid[yy][xx]==".":
                    exterior=True
                    break
            if exterior:
                exterior_seeds.append((y,x))

    seen=set()
    removed=set()
    components=0
    for seed in exterior_seeds:
        if seed in seen:
            continue
        components+=1
        stack=[seed]
        seen.add(seed)
        comp=[]
        while stack:
            y,x=stack.pop()
            comp.append((y,x))
            for dy,dx in dirs:
                yy,xx=y+dy,x+dx
                if 0<=yy<h and 0<=xx<w and grid[yy][xx]==dark and (yy,xx) not in seen:
                    seen.add((yy,xx))
                    stack.append((yy,xx))
        removed.update(comp)

    for y,x in removed:
        grid[y][x]="."

    return ["".join(r) for r in grid], {
        "removed_cells":len(removed),
        "components":components,
        "symbol":dark,
        "dmc":str(dark_dmc),
        "neighborhood":neighborhood,
    }


def clean_exterior_near_white_rows(rows, palette, alphabet, max_component_cells=16, white_distance=70):
    grid=[list(r) for r in rows]
    h=len(grid); w=len(grid[0]) if h else 0
    near_white=set()
    for i,p in enumerate(palette):
        if i >= len(alphabet):
            break
        hx=str(p.get("hex","")).lstrip("#")
        if len(hx)!=6:
            continue
        rgb=tuple(int(hx[j:j+2],16) for j in (0,2,4))
        dist=sum((255-v)**2 for v in rgb) ** 0.5
        if dist <= white_distance:
            near_white.add(alphabet[i])
    if not near_white:
        return rows, {"removed_components":0,"removed_cells":0,"symbols":[]}

    dirs=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    seen=set()
    removed_components=0
    removed_cells=0

    for sy in range(h):
        for sx in range(w):
            if (sy,sx) in seen or grid[sy][sx] not in near_white:
                continue
            stack=[(sy,sx)]
            seen.add((sy,sx))
            comp=[]
            nonwhite_neighbors=set()
            enclosed=0
            boundary_cells=0
            while stack:
                y,x=stack.pop()
                comp.append((y,x))
                is_boundary=False
                for dy,dx in dirs:
                    yy,xx=y+dy,x+dx
                    if yy<0 or yy>=h or xx<0 or xx>=w:
                        is_boundary=True
                        continue
                    v=grid[yy][xx]
                    if v==".":
                        is_boundary=True
                    elif v in near_white:
                        if (yy,xx) not in seen:
                            seen.add((yy,xx))
                            stack.append((yy,xx))
                    else:
                        nonwhite_neighbors.add((yy,xx))
                if is_boundary:
                    boundary_cells+=1

                left=any(grid[y][xx]!="." and grid[y][xx] not in near_white for xx in range(max(0,x-4),x))
                right=any(grid[y][xx]!="." and grid[y][xx] not in near_white for xx in range(x+1,min(w,x+5)))
                up=any(grid[yy][x]!="." and grid[yy][x] not in near_white for yy in range(max(0,y-4),y))
                down=any(grid[yy][x]!="." and grid[yy][x] not in near_white for yy in range(y+1,min(h,y+5)))
                if (left and right) or (up and down):
                    enclosed+=1

            n=len(comp)
            fully_exterior = boundary_cells == n
            weakly_attached = len(nonwhite_neighbors) <= 1
            intentional = n >= 20 or enclosed >= max(1,n//3) or len(nonwhite_neighbors) >= 3

            # Remove detached white/near-white flecks and very small exterior
            # antialias remnants even when they touch one coloured cell.
            remove = (
                (n <= max_component_cells and weakly_attached and not intentional)
                or (n <= 4 and fully_exterior and not intentional)
            )
            if remove:
                for y,x in comp:
                    grid[y][x]="."
                removed_components+=1
                removed_cells+=n

    return ["".join(r) for r in grid], {
        "removed_components":removed_components,
        "removed_cells":removed_cells,
        "symbols":sorted(near_white),
        "white_distance":white_distance,
        "max_component_cells":max_component_cells,
    }


def rgba_from_matrix(rows, palette, alphabet):
    if len(rows) != 120 or any(len(row) != 100 for row in rows):
        raise RuntimeError("Canonical matrix is not 100x120")

    lookup = {}
    for idx, char in enumerate(alphabet[:len(palette)]):
        h = palette[idx]["hex"].lstrip("#")
        lookup[char] = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    im = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == ".":
                continue
            if char not in lookup:
                raise RuntimeError(f"Unknown palette symbol {char!r} at {x},{y}")
            px[x, y] = lookup[char]
    return im


def validate_master(base_id: str, im: Image.Image):
    if im.size != (800, 960):
        raise RuntimeError(f"{base_id}: master must be 800x960, got {im.size}")
    alpha = im.getchannel("A")
    amin, amax = alpha.getextrema()
    bbox = alpha.getbbox()
    if amin != 0 or amax == 0 or not bbox:
        raise RuntimeError(f"{base_id}: master must contain artwork and transparent background")

    x0, y0, x1, y1 = bbox
    margins = {
        "left": x0,
        "top": y0,
        "right": im.width - x1,
        "bottom": im.height - y1,
    }
    if min(margins.values()) < 32:
        raise RuntimeError(f"{base_id}: canonical artwork lacks safe margin: bbox={bbox}, margins={margins}")
    return bbox, margins


def generate_reference_master(base_id: str):
    base_id = base_id.strip().upper()
    meta = design_meta(base_id)
    collection = read_json(COLLECTION_PATH)
    strict_policy = collection.get("pattern_rules", {}).get("approved_master_policy", {})

    direct = load_design_reference(base_id, meta)
    if strict_policy.get("enabled", False):
        if not direct:
            raise RuntimeError(f"{base_id}: approved preview v2 direct reference is required; legacy fallback disabled")
        if not direct.get("direct_metadata", {}).get("approved_preview_v2"):
            raise RuntimeError(f"{base_id}: direct reference is not marked approved_preview_v2")

    if direct:
        manifest = direct["manifest"]
        canonical = direct["canonical"]
        alphabet = direct["alphabet"]
        source_kind = "approved-preview-v2" if direct["direct_metadata"].get("approved_preview_v2") else direct["source_kind"]
        source_digest = direct["source_sha256"]
        direct_metadata = direct["direct_metadata"]
    elif base_id == "I0001":
        # Keep the approved full-feet silhouette, but rebuild its colours and
        # exterior treatment under the new collection rules.
        manifest = read_json(MANIFEST_PATH)
        collection = read_json(COLLECTION_PATH)
        palette = collection["palette"]
        alphabet = STANDARD_ALPHABET
        source_rel = meta["source_asset"]
        source_path = SYSTEM / source_rel
        if not source_path.is_file():
            raise RuntimeError("I0001 approved full-feet source master is missing")
        approved = Image.open(source_path).convert("RGBA")
        rows = rows_from_master_image(approved, palette, alphabet)

        dark_rule=collection.get("pattern_rules",{}).get("external_dark_cleanup",{})
        if dark_rule.get("enabled",False):
            rows,dark_stats=remove_exterior_dark_rows(
                rows,palette,alphabet,
                dark_dmc=str(dark_rule.get("dmc","310")),
                neighborhood=int(dark_rule.get("neighborhood",8)),
            )
        else:
            dark_stats={"removed_cells":0,"components":0,"symbol":None}

        white_rule=collection.get("pattern_rules",{}).get("external_white_cleanup",{})
        if white_rule.get("enabled",False):
            rows,near_white_stats=clean_exterior_near_white_rows(
                rows,palette,alphabet,
                max_component_cells=int(white_rule.get("max_isolated_component_cells",16)),
                white_distance=float(white_rule.get("near_white_distance",70)),
            )
        else:
            near_white_stats={"removed_components":0,"removed_cells":0,"symbols":[]}

        master=rgba_from_matrix(rows,palette,alphabet).resize((800,960),Image.Resampling.NEAREST)
        bbox,margins=validate_master(base_id,master)
        ref_name=f"{base_id}-{meta['slug']}-reference.png"
        ref_path=REFERENCE_DIR/ref_name
        ref_rel=f"collections/baby-nursery/reference-masters/{ref_name}"
        source_path.parent.mkdir(parents=True,exist_ok=True)
        ref_path.parent.mkdir(parents=True,exist_ok=True)
        master.save(source_path,"PNG",optimize=True)
        master.save(ref_path,"PNG",optimize=True)
        result={
            "design_id":base_id,
            "slug":meta["slug"],
            "reference_sheet":1,
            "reference_row":1,
            "reference_column":1,
            "source_asset":source_rel,
            "reference_asset":ref_rel,
            "bbox":bbox,
            "margins":margins,
            "reference_source":"approved-full-feet-master-recoloured",
            "reference_sha256":hashlib.sha256(master.tobytes()).hexdigest(),
            "exterior_dark_cleanup":dark_stats,
            "near_white_cleanup":near_white_stats,
        }
        print("CANONICAL_REFERENCE_MASTER_OK",json.dumps(result,ensure_ascii=False))
        return result
    else:
        manifest, archive = load_archive()
        if base_id not in archive["designs"]:
            raise RuntimeError(f"{base_id}: not found in canonical user-reference archive")
        canonical = archive["designs"][base_id]
        alphabet = archive["palette_indices"]
        source_kind = "legacy-reference-archive"
        source_digest = EXPECTED_DECODED_SHA256
        direct_metadata = None

    if canonical.get("slug") != meta.get("slug"):
        raise RuntimeError(
            f"{base_id}: canonical slug {canonical.get('slug')} != designs.json slug {meta.get('slug')}"
        )

    manifest_row = next((x for x in manifest["designs"] if x["base_design_id"] == base_id), None)
    if not manifest_row:
        raise RuntimeError(f"{base_id}: missing from canonical manifest")
    if (
        manifest_row["slug"] != meta["slug"]
        or int(manifest_row["reference_sheet"]) != int(canonical["sheet"])
        or int(manifest_row["row"]) != int(canonical["row"])
        or int(manifest_row["column"]) != int(canonical["column"])
    ):
        raise RuntimeError(f"{base_id}: canonical manifest/reference mapping mismatch")

    palette = collection["palette"]
    rows = canonical["rows"]

    premium_rule = collection.get("pattern_rules", {}).get("premium_refinement", {})
    if premium_rule.get("enabled", False):
        rows, premium_stats = refine_rows(
            rows,
            palette,
            alphabet,
            base_id,
            premium_rule,
        )
    else:
        premium_stats = {
            "enabled": False,
            "version": None,
            "source_stitches": sum(c != "." for row in rows for c in row),
            "result_stitches": sum(c != "." for row in rows for c in row),
        }

    dark_rule = collection.get("pattern_rules", {}).get("external_dark_cleanup", {})
    if dark_rule.get("enabled", False):
        rows, dark_stats = remove_exterior_dark_rows(
            rows,
            palette,
            alphabet,
            dark_dmc=str(dark_rule.get("dmc", "310")),
            neighborhood=int(dark_rule.get("neighborhood", 8)),
        )
    else:
        dark_stats = {"removed_cells":0,"components":0,"symbol":None}

    white_rule = collection.get("pattern_rules", {}).get("external_white_cleanup", {})
    if white_rule.get("enabled", False):
        rows, near_white_stats = clean_exterior_near_white_rows(
            rows,
            palette,
            alphabet,
            max_component_cells=int(white_rule.get("max_isolated_component_cells", 16)),
            white_distance=float(white_rule.get("near_white_distance", 70)),
        )
    else:
        near_white_stats = {"removed_components":0,"removed_cells":0,"symbols":[]}
    grid = rgba_from_matrix(rows, palette, alphabet)
    master = grid.resize((800, 960), Image.Resampling.NEAREST)
    bbox, margins = validate_master(base_id, master)

    source_rel = meta["source_asset"]
    source_path = SYSTEM / source_rel
    expected_source = SOURCE_DIR / f"{base_id}-{meta['slug']}.png"
    if source_path != expected_source:
        raise RuntimeError(f"{base_id}: designs.json source path is not canonical: {source_rel}")

    ref_name = f"{base_id}-{meta['slug']}-reference.png"
    ref_path = REFERENCE_DIR / ref_name
    ref_rel = f"collections/baby-nursery/reference-masters/{ref_name}"

    source_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    master.save(source_path, "PNG", optimize=True)
    master.save(ref_path, "PNG", optimize=True)

    source_check = Image.open(source_path).convert("RGBA")
    ref_check = Image.open(ref_path).convert("RGBA")
    if source_check.tobytes() != ref_check.tobytes():
        raise RuntimeError(f"{base_id}: source/reference masters diverged after save")
    bbox2, margins2 = validate_master(base_id, ref_check)
    if bbox2 != bbox or margins2 != margins:
        raise RuntimeError(f"{base_id}: master geometry changed after persistence")

    result = {
        "design_id": base_id,
        "slug": meta["slug"],
        "reference_sheet": canonical["sheet"],
        "reference_row": canonical["row"],
        "reference_column": canonical["column"],
        "source_asset": source_rel,
        "reference_asset": ref_rel,
        "bbox": bbox,
        "margins": margins,
        "reference_source": source_kind,
        "reference_sha256": source_digest,
        "exterior_dark_cleanup": dark_stats,
        "near_white_cleanup": near_white_stats,
        "premium_refinement": premium_stats,
    }
    if direct_metadata:
        result["source_crop_bbox"] = direct_metadata.get("source_crop_bbox")
        result["source_crop_size"] = direct_metadata.get("source_crop_size")
        result["palette_policy"] = direct_metadata.get("palette_policy")

    print("CANONICAL_REFERENCE_MASTER_OK", json.dumps(result, ensure_ascii=False))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_id", help="I0001 .. I0030")
    args = ap.parse_args()
    generate_reference_master(args.design_id)


if __name__ == "__main__":
    main()
