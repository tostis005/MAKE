# Drielo Pattern System - Agent Rules

This repository is the source of truth for Drielo cross-stitch PDF generation.

## Non-negotiable workflow

1. Always use `content/pattern-system/template/DRIELO_Pattern_Template_MASTER.html` as the visual/layout source.
2. A product belongs to exactly one collection.
3. A pattern may use ONLY DMC colours listed in that collection's `palette`.
4. When generating a pattern JSON from an image, quantize/map every stitch to the target collection palette before writing the JSON.
5. Before PDF generation, run the second palette validation. If a thread entry is outside the collection palette, remap it to the nearest allowed collection colour and persist the corrected pattern JSON before rendering.
6. Never patch a finished PDF by compositing screenshots or raster layers over it. Edit/render the HTML source and export a fresh PDF.
7. Pages 1-3 use the same canonical vector stitch model. Page 1 places the transparent vector stitch layer inside the collection's frame area over an Aida-style fabric background. Pages 2-3 render the same stitch geometry with the template's fabric preview.
8. Colour charts, symbol charts, rulers and enlarged chart sections must be generated from the same matrix and thread definitions used for the preview.
9. Keep the customer PDF vector wherever the template generates SVG. Do not rasterize vector chart/stitch artwork before PDF export.
10. Product code is the pattern identifier (for example `P0021`).

## Collection palette

`content/pattern-system/collections/<collection>/collection.json` is authoritative.
WooCommerce may display the collection palette, but it must consume/sync from this file/catalog data; WooCommerce is not a colour source for pattern generation.

## Collection mockup image

Every collection has one hero/mockup image. Its `mockup_spec` describes how that image must be generated. The image should contain an empty framed Aida-fabric area. Do not generate stitched artwork as part of the room image; stitched artwork is inserted later as vector SVG by the HTML renderer.

The frame geometry is stored in source-image pixels (`source_px`, `area_px`). It must identify the INNER usable fabric rectangle, not the outside of the physical frame.

## Stitch preview geometry

Use proportional rules, never a fixed millimetre stitch size:
- X endpoint margin defaults to 0.02 of one stitch cell.
- Stroke width defaults to 0.34 of one stitch cell.
- Rounded line caps and joins.
- The geometry scales with the pattern grid and available frame dimensions.
- Aim for dense, realistic full-cross-stitch coverage with minimal visible fabric gaps between adjacent stitches.
- Preserve aspect ratio and center the pattern within the usable frame area.

## Required files for a new pattern

- `content/pattern-system/products/<CODE>/product.json`
- `content/pattern-system/patterns/<CODE>/pattern.json`
- any private/source assets needed to derive the pattern (do not expose full-resolution customer charts publicly)

## Build command

`python3 content/pattern-system/renderer/render.py --product <CODE>`

The build writes the finished PDF into the configured output directory and verifies that Chromium produced a readable PDF.
