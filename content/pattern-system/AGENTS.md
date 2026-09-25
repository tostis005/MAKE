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
10. Product code must be technique-qualified and unique. Legacy/Pop Art design families use `P####`; the Baby & Nursery collection uses `I####`. Examples: `P0021-CS` or `I0001-CS`, with the same `-CS`, `-C2C`, `-TC`, `-LH` technique suffixes. Keep the shared design family separately as the base design ID.\n11. Every sellable product has exactly ONE public product image. It must contain only the ambient/lifestyle scene with the finished craft visible. Never use the full PDF page as a store image and never include the right-side facts rail, title, subtitle, skill level, finished size, colour/thread count, type, footer, floral ornaments, URL or page number.\n12. The public product image must be derived from the same page-1 composition and the same final vector pattern used in the PDF, so the store image and PDF cover always match. Export it as a 4:5 WebP using the template element marked `[data-product-image]`.\n13. For mass production, generate product JSON + pattern JSON, render PDF + product image in GitHub Actions, then let the product-import workflow publish/update WooCommerce. Do not manually patch PDFs or manually rebuild store screenshots.

## Collection palette

`content/pattern-system/collections/<collection>/collection.json` is authoritative.
WooCommerce may display the collection palette, but it must consume/sync from this file/catalog data; WooCommerce is not a colour source for pattern generation.

## Collection mockup image

Every collection has one hero/mockup image. Its `mockup_spec` describes how that image must be generated. The image should contain an empty framed Aida-fabric area. Do not generate stitched artwork as part of the room image; stitched artwork is inserted later as vector SVG by the HTML renderer.

The frame geometry is stored in source-image pixels (`source_px`, `area_px`). It must identify the INNER usable fabric rectangle, not the outside of the physical frame.

## Stitch preview geometry

Use proportional rules, never a fixed millimetre stitch size:
- Render full cross stitch as a dense coloured stitch cell with layered diagonal thread relief, not as a flat X floating on a white square.
- Use rounded thread strokes, subtle highlight/shadow layers and soft lower/right occlusion so the stitch reads as raised floss.
- The visible grid must behave like real Aida/fabric: vertical gaps are pale, desaturated and slightly fabric-reflective; horizontal gaps are darker recessed shadows.
- Never paint the vertical grid as a pure white line or as the unchanged thread colour.
- The grid must be organically irregular: vary seam position, width, curvature, interruption and occlusion per cell.
- All irregularity must be deterministic from product code + stitch coordinates so the same design always renders identically.
- Horizontal shadow visually dominates at grid intersections; vertical fabric glimpses should be pinched/broken by the stitch geometry.
- Preserve the canonical vector stitch model in customer-facing PDF/product rendering; do not rasterize the stitch layer.
- The geometry scales with the pattern grid and available frame dimensions.
- Preserve aspect ratio and center the pattern within the usable frame area.

## Required files for a new pattern

- `content/pattern-system/products/<CODE>/product.json`
- `content/pattern-system/patterns/<CODE>/pattern.json`
- any private/source assets needed to derive the pattern (do not expose full-resolution customer charts publicly)

## Build command

`python3 content/pattern-system/renderer/render.py --product <CODE>`

The build writes the finished PDF into the configured output directory and verifies that Chromium produced a readable PDF.


## Product image rule

The WooCommerce/Etsy image is NOT a screenshot of page 1. It is the page-1 ambient/product composition only.

Required output:
- one image per technique product;
- 4:5 portrait WebP;
- no brochure UI, no facts rail, no page typography;
- the same final pattern placement used in page 1;
- filename: `<CODE>-product.webp`;
- templates/renderers must expose the exact capture region as `[data-product-image]`.

This image is the only item in the product gallery unless a future project rule explicitly adds additional commercial imagery.

## Staged products

Products that are structurally created but do not yet have approved canonical artwork/page-1 assets must set `render_ready: false`. GitHub Actions must skip those products until their real stitch matrix and approved collection mockup are ready.
