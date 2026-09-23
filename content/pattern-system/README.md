# Drielo automated pattern PDF system

This system turns a collection definition + product JSON + stitch matrix into the final 17-page customer PDF using the Drielo master HTML template.

## Source of truth

- Collection: `collections/<slug>/collection.json`
- Product metadata: `products/<code>/product.json`
- Stitch data: `patterns/<code>/pattern.json`
- Layout: `template/DRIELO_Pattern_Template_MASTER.html`

The installed master template is derived from the approved `DRIELO_Pattern_Template_MASTER_v8.html` supplied for Drielo and remains the single visual/layout source of truth.

## Palette rule

The collection palette is authoritative. Pattern generation must choose only those DMC entries. The renderer performs a second check immediately before PDF export. Unknown/out-of-collection thread colours are automatically remapped to the nearest permitted collection colour when `--fix-palette` is enabled (the GitHub workflow enables it).

## First page / collection mockup

The room/interior image belongs to the collection. It should contain an empty frame with Aida-like fabric. The collection JSON stores the source image dimensions and the inner frame rectangle in pixels. The renderer inserts the pattern as transparent vector X stitches directly in the HTML over that fabric area, centered and aspect-fit.

The room/mockup must never contain a baked-in pattern. The pattern layer is generated from the stitch matrix at build time so the PDF keeps the design vectorial and reusable across every product in the collection.

## Build locally

```bash
python3 renderer/render.py --product P0001-CS --fix-palette
```

Chromium/Chrome is required. The resulting PDF is written to `output/<CODE>/Drielo_<CODE>.pdf`.

## Product-code convention

Every sellable pattern code is technique-qualified and unique. The legacy/Pop Art families use `P####`; Baby & Nursery uses `I####`:

- Cross Stitch: `P0001-CS` or `I0001-CS`
- C2C Crochet: `P0001-C2C` or `I0001-C2C`
- Tapestry Crochet: `P0001-TC` or `I0001-TC`
- Latch Hook / Rug: `P0001-LH` or `I0001-LH`

The shared artwork/design family keeps the base ID separately (for example `P0001`). Never publish a technique product using only the base ID.

## GitHub Actions

`build-pattern-pdf.yml` runs on changes to this pattern system. It validates/fixes palette data, synchronizes the collection palette back to the WooCommerce catalogue source, builds the selected/all product PDFs, and uploads them as private workflow artifacts. Generated PDFs are not committed to the public repository.


## Store product image

The customer-facing product image is generated from the page-1 lifestyle composition but excludes every PDF-layout element. The output contains only the ambient scene and the finished craft, uses a 4:5 portrait WebP, and is exported from the element marked `[data-product-image]`.

The product image is generated alongside the PDF so WooCommerce never needs a manually-created screenshot. Its standard filename is `<CODE>-product.webp`.

## Fast production path

For bulk production, keep the source of truth in GitHub:
1. generate/update collection, product and pattern JSON;
2. GitHub Actions renders the HTML once;
3. the same render produces both `Drielo_<CODE>.pdf` and `<CODE>-product.webp`;
4. the WooCommerce importer consumes the catalogue plus those generated assets.

This removes the slow manual loop of rendering files locally, sending them through chat, and re-uploading them one by one.

## Draft / staged products

A product may be committed before its final artwork and cover imagery exist by setting `render_ready: false`. The build workflow ignores those entries until they are complete, while preserving the folder structure and metadata in GitHub.
