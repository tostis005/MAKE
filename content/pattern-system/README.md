# Drielo automated pattern PDF system

This system turns a collection definition + product JSON + stitch matrix into the final 17-page customer PDF using the Drielo master HTML template.

## Source of truth

- Collection: `collections/<slug>/collection.json`
- Product metadata: `products/<code>/product.json`
- Stitch data: `patterns/<code>/pattern.json`
- Layout: `template/DRIELO_Pattern_Template_MASTER.html`

## Palette rule

The collection palette is authoritative. Pattern generation must choose only those DMC entries. The renderer performs a second check immediately before PDF export. Unknown/out-of-collection thread colours are automatically remapped to the nearest permitted collection colour when `--fix-palette` is enabled (the GitHub workflow enables it).

## First page / collection mockup

The room/interior image belongs to the collection. It should contain an empty frame with Aida-like fabric. The collection JSON stores the source image dimensions and the inner frame rectangle in pixels. The renderer inserts the pattern as transparent vector X stitches directly in the HTML over that fabric area, centered and aspect-fit.

## Build locally

```bash
python3 renderer/render.py --product P0001 --fix-palette
```

Chromium/Chrome is required. The resulting PDF is written to `output/<CODE>/Drielo_<CODE>.pdf`.

## GitHub Actions

`build-pattern-pdf.yml` runs on changes to this pattern system. It validates/fixes palette data, builds the selected/all product PDFs, and uploads them as private workflow artifacts. Generated PDFs are not committed to the public repository.
