# Iconic Destinations / Destinos icónicos

The canonical artwork source for this collection is now the **manifest-driven source image structure**:

`content/pattern-system/collections/iconic-destinations/source-images/`

## Canonical source structure

- `source-images/manifest.json` is the source of truth for design identity and product naming.
- Every PNG listed by the manifest is a standalone source image. Mosaics, collage crops and inferred image positions are forbidden.
- The importer must read `id`, `filename`, `slug`, `title_en`, `title_es`, `product_title_en` and `product_title_es` from the manifest. It must never infer a title or slug from image content, file order or a mosaic position.
- Files under `source-images/package/` are transport/audit packages only. They are not a naming source.
- `input-pngs-q50/current/` is generated staging created by the manifest importer.
- `source-designs/` is derived output after DMC mapping; it is not the canonical input artwork.

The shared schema contract is documented by:

`content/pattern-system/collections/source-images-manifest.schema.json`

## Current image contract

Each current Iconic Destinations source image must be:

- PNG
- exactly **100 × 120 pixels**
- exactly **50 source colours**
- no dithering
- an independent palette per design
- listed exactly once in `source-images/manifest.json`

The current manifest contains 100 audited designs. Only manifest-listed designs are eligible for a new import run.

## Pattern format

- Technique: cross stitch only (`D####-CS`)
- Master grid: **100 × 120 stitches**
- Total cells: **12,000**
- Chart target: **4 grid pages**
- Palette: selected independently per design and mapped to DMC

## Storefront

The WooCommerce hero is a lifestyle mockup generated from the validated pattern matrix. It is not an artwork source and cannot feed back into pattern generation.

## Guardrails

A manifest import must fail if:

- an image is missing from the manifest or the manifest points to a missing image
- IDs, filenames or slugs are duplicated
- a title required for the web is missing
- a PNG is not exactly 100 × 120
- a PNG does not contain exactly 50 source colours
- a queue/design record disagrees with the manifest
- an extracted staging PNG differs byte-for-byte from its canonical source image
- a mosaic, collage crop, PDF page or inferred filename/title is used as source artwork

Publication is deliberately separate from source installation. Uploading or updating `source-images/` must **not** publish products by itself.
