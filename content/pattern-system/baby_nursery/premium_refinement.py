#!/usr/bin/env python3
from __future__ import annotations

import math
from collections import Counter, deque

from PIL import Image


def _hex_rgb(value: str):
    h = str(value).lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _near_white_symbols(palette, alphabet, distance=72.0):
    out = set()
    for i, p in enumerate(palette):
        if i >= len(alphabet):
            break
        r, g, b = _hex_rgb(p["hex"])
        d = math.sqrt((255-r)**2 + (255-g)**2 + (255-b)**2)
        if d <= float(distance):
            out.add(alphabet[i])
    return out


def _component_cells(rows, allowed_symbols):
    h = len(rows)
    w = len(rows[0]) if h else 0
    dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    seen = set()
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or rows[y][x] not in allowed_symbols:
                continue
            q = [(y, x)]
            seen.add((y, x))
            comp = []
            while q:
                cy, cx = q.pop()
                comp.append((cy, cx))
                for dy, dx in dirs:
                    yy, xx = cy + dy, cx + dx
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and rows[yy][xx] in allowed_symbols:
                        seen.add((yy, xx))
                        q.append((yy, xx))
            yield comp


def clean_source_edge_speckles(
    rows,
    palette,
    alphabet,
    *,
    white_distance=72.0,
    max_isolated_component_cells=24,
    max_fringe_component_cells=48,
    fringe_boundary_fraction=0.70,
):
    """Remove only small, exterior near-white raster remnants before upscaling.

    Large intentional pale regions (clouds, moon highlights, sails, etc.) are
    protected by the component-size and boundary-fraction guards.
    """
    grid = [list(r) for r in rows]
    h = len(grid)
    w = len(grid[0]) if h else 0
    near_white = _near_white_symbols(palette, alphabet, white_distance)
    if not near_white:
        return rows, {"removed_cells": 0, "removed_components": 0, "near_white_symbols": []}

    dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    removed = 0
    removed_components = 0

    snapshot = ["".join(r) for r in grid]
    for comp in _component_cells(snapshot, near_white):
        boundary = 0
        nonwhite_neighbors = set()
        for y, x in comp:
            exterior = False
            for dy, dx in dirs:
                yy, xx = y + dy, x + dx
                if yy < 0 or yy >= h or xx < 0 or xx >= w:
                    exterior = True
                    continue
                v = snapshot[yy][xx]
                if v == ".":
                    exterior = True
                elif v not in near_white:
                    nonwhite_neighbors.add((yy, xx))
            if exterior:
                boundary += 1

        n = len(comp)
        boundary_fraction = boundary / max(1, n)
        weakly_attached = len(nonwhite_neighbors) <= max(2, n // 3)

        remove = (
            n <= int(max_isolated_component_cells)
            or (
                n <= int(max_fringe_component_cells)
                and boundary_fraction >= float(fringe_boundary_fraction)
                and weakly_attached
            )
        )
        if remove:
            for y, x in comp:
                grid[y][x] = "."
            removed += n
            removed_components += 1

    return ["".join(r) for r in grid], {
        "removed_cells": removed,
        "removed_components": removed_components,
        "near_white_symbols": sorted(near_white),
        "white_distance": float(white_distance),
        "max_isolated_component_cells": int(max_isolated_component_cells),
        "max_fringe_component_cells": int(max_fringe_component_cells),
        "fringe_boundary_fraction": float(fringe_boundary_fraction),
    }


def _occupied_bbox(rows):
    pts = [(x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c != "."]
    if not pts:
        raise RuntimeError("premium refinement source matrix is empty")
    x0 = min(x for x, _ in pts)
    x1 = max(x for x, _ in pts) + 1
    y0 = min(y for _, y in pts)
    y1 = max(y for _, y in pts) + 1
    return x0, y0, x1, y1


def _build_symbol_masks(crop_rows, symbols):
    h = len(crop_rows)
    w = len(crop_rows[0]) if h else 0
    occupied = Image.new("L", (w, h), 0)
    op = occupied.load()
    masks = {}
    for symbol in symbols:
        masks[symbol] = Image.new("L", (w, h), 0)
    pix = {symbol: im.load() for symbol, im in masks.items()}

    for y, row in enumerate(crop_rows):
        for x, symbol in enumerate(row):
            if symbol == ".":
                continue
            op[x, y] = 255
            if symbol not in pix:
                raise RuntimeError(f"Unknown premium-refinement palette symbol {symbol!r}")
            pix[symbol][x, y] = 255
    return occupied, masks


def _render_scaled(
    occupied,
    masks,
    symbols,
    *,
    canvas_w,
    canvas_h,
    new_w,
    new_h,
    alpha_threshold,
    color_threshold,
):
    occ = occupied.resize((new_w, new_h), Image.Resampling.LANCZOS)
    symbol_masks = {
        symbol: masks[symbol].resize((new_w, new_h), Image.Resampling.LANCZOS)
        for symbol in symbols
    }
    occ_px = occ.load()
    sym_px = {s: im.load() for s, im in symbol_masks.items()}

    out = [["."] * canvas_w for _ in range(canvas_h)]
    ox = (canvas_w - new_w) // 2
    oy = (canvas_h - new_h) // 2
    count = 0

    for y in range(new_h):
        for x in range(new_w):
            if occ_px[x, y] < alpha_threshold:
                continue
            best_symbol = None
            best_value = -1
            for symbol in symbols:
                value = sym_px[symbol][x, y]
                if value > best_value:
                    best_value = value
                    best_symbol = symbol
            if best_symbol is None or best_value < color_threshold:
                continue
            yy, xx = oy + y, ox + x
            if 0 <= yy < canvas_h and 0 <= xx < canvas_w:
                out[yy][xx] = best_symbol
                count += 1

    return ["".join(r) for r in out], count, (new_w, new_h), (ox, oy)


def _remove_orphan_cells(rows, max_component_cells=2):
    grid = [list(r) for r in rows]
    h = len(grid)
    w = len(grid[0]) if h else 0
    dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    seen = set()
    removed = 0
    components = 0

    for sy in range(h):
        for sx in range(w):
            if grid[sy][sx] == "." or (sy, sx) in seen:
                continue
            stack = [(sy, sx)]
            seen.add((sy, sx))
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in dirs:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and grid[yy][xx] != "." and (yy, xx) not in seen:
                        seen.add((yy, xx))
                        stack.append((yy, xx))
            if len(comp) <= int(max_component_cells):
                for y, x in comp:
                    grid[y][x] = "."
                removed += len(comp)
                components += 1

    return ["".join(r) for r in grid], {
        "removed_cells": removed,
        "removed_components": components,
        "max_component_cells": int(max_component_cells),
    }


def edge_quality(rows, palette, alphabet, white_distance=72.0):
    h = len(rows)
    w = len(rows[0]) if h else 0
    dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    near_white = _near_white_symbols(palette, alphabet, white_distance)

    occupied = 0
    isolated = 0
    exterior_near_white_weak = 0
    edge_cells = 0

    for y, row in enumerate(rows):
        for x, value in enumerate(row):
            if value == ".":
                continue
            occupied += 1
            neighbors = []
            exterior = False
            for dy, dx in dirs:
                yy, xx = y + dy, x + dx
                if yy < 0 or yy >= h or xx < 0 or xx >= w:
                    exterior = True
                    continue
                nv = rows[yy][xx]
                neighbors.append(nv)
                if nv == ".":
                    exterior = True
            occupied_neighbors = sum(1 for v in neighbors if v != ".")
            if occupied_neighbors <= 1:
                isolated += 1
            if exterior:
                edge_cells += 1
                if value in near_white:
                    nonwhite_neighbors = sum(1 for v in neighbors if v not in near_white and v != ".")
                    if nonwhite_neighbors <= 1:
                        exterior_near_white_weak += 1

    bbox = _occupied_bbox(rows)
    return {
        "occupied_cells": occupied,
        "isolated_cells": isolated,
        "weak_exterior_near_white_cells": exterior_near_white_weak,
        "edge_cells": edge_cells,
        "bbox": list(bbox),
        "near_white_symbols": sorted(near_white),
    }


def refine_rows(rows, palette, alphabet, base_id, policy):
    if len(rows) != 120 or any(len(r) != 100 for r in rows):
        raise RuntimeError(f"{base_id}: premium refinement requires a 100x120 matrix")

    source_count = sum(c != "." for row in rows for c in row)
    source_bbox = _occupied_bbox(rows)

    cleanup = policy.get("source_edge_cleanup", {})
    cleaned_rows, cleanup_stats = clean_source_edge_speckles(
        rows,
        palette,
        alphabet,
        white_distance=float(cleanup.get("white_distance", 72)),
        max_isolated_component_cells=int(cleanup.get("max_isolated_component_cells", 24)),
        max_fringe_component_cells=int(cleanup.get("max_fringe_component_cells", 48)),
        fringe_boundary_fraction=float(cleanup.get("fringe_boundary_fraction", 0.70)),
    )

    x0, y0, x1, y1 = _occupied_bbox(cleaned_rows)
    crop_rows = [row[x0:x1] for row in cleaned_rows[y0:y1]]
    crop_w, crop_h = x1 - x0, y1 - y0
    used_symbols = sorted({c for row in crop_rows for c in row if c != "."})
    if not used_symbols:
        raise RuntimeError(f"{base_id}: premium refinement removed the complete motif")

    occupied, masks = _build_symbol_masks(crop_rows, used_symbols)

    targets = policy.get("target_stitches_by_design", {})
    target = int(targets.get(base_id, policy.get("target_stitches_default", 6000)))
    target_min = int(policy.get("target_stitches_min", 4500))
    target_max = int(policy.get("target_stitches_max", 8000))
    target = max(target_min, min(target_max, target))

    safe_x = int(policy.get("safe_margin_cells_x", 5))
    safe_y = int(policy.get("safe_margin_cells_y", 6))
    max_w = 100 - 2 * safe_x
    max_h = 120 - 2 * safe_y
    if max_w <= 0 or max_h <= 0:
        raise RuntimeError("premium refinement safe margins consume the canvas")

    max_scale = min(max_w / crop_w, max_h / crop_h)
    min_scale = min(1.0, max_scale)
    alpha_threshold = int(policy.get("alpha_threshold", 132))
    color_threshold = int(policy.get("color_threshold", 48))

    def render(scale):
        nw = max(1, min(max_w, int(round(crop_w * scale))))
        nh = max(1, min(max_h, int(round(crop_h * scale))))
        return _render_scaled(
            occupied,
            masks,
            used_symbols,
            canvas_w=100,
            canvas_h=120,
            new_w=nw,
            new_h=nh,
            alpha_threshold=alpha_threshold,
            color_threshold=color_threshold,
        )

    lo, hi = min_scale, max_scale
    best = None
    for _ in range(22):
        mid = (lo + hi) / 2.0
        candidate = render(mid)
        rows2, count, size, offset = candidate
        if best is None or abs(count - target) < abs(best[1] - target):
            best = (rows2, count, size, offset, mid)
        if count < target:
            lo = mid
        else:
            hi = mid

    assert best is not None
    refined_rows, count, size, offset, scale = best

    refined_rows, orphan_stats = _remove_orphan_cells(
        refined_rows,
        max_component_cells=int(policy.get("max_orphan_component_cells", 2)),
    )
    count = sum(c != "." for row in refined_rows for c in row)

    quality = edge_quality(
        refined_rows,
        palette,
        alphabet,
        white_distance=float(cleanup.get("white_distance", 72)),
    )

    effective_min = min(target_min, target)
    tolerance = int(policy.get("target_tolerance_cells", 220))
    if count < effective_min - tolerance:
        raise RuntimeError(
            f"{base_id}: refined motif too sparse: {count} stitches; expected at least {effective_min - tolerance}"
        )
    if count > target_max + tolerance:
        raise RuntimeError(
            f"{base_id}: refined motif too dense: {count} stitches; expected at most {target_max + tolerance}"
        )
    if quality["isolated_cells"] > int(policy.get("max_isolated_cells", 0)):
        raise RuntimeError(
            f"{base_id}: premium QA found isolated stitch cells: {quality['isolated_cells']}"
        )
    if quality["weak_exterior_near_white_cells"] > int(policy.get("max_weak_exterior_near_white_cells", 0)):
        raise RuntimeError(
            f"{base_id}: premium QA found exterior near-white speckles: "
            f"{quality['weak_exterior_near_white_cells']}"
        )

    return refined_rows, {
        "enabled": True,
        "version": 3,
        "source_stitches": source_count,
        "source_bbox": list(source_bbox),
        "source_cleanup": cleanup_stats,
        "target_stitches": target,
        "result_stitches": count,
        "scale": round(scale, 6),
        "scaled_size": list(size),
        "placement": list(offset),
        "alpha_threshold": alpha_threshold,
        "color_threshold": color_threshold,
        "orphan_cleanup": orphan_stats,
        "quality": quality,
    }
