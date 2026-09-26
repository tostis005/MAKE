# Iconic Destinations / Destinos icónicos

This collection contains 60 cross-stitch products generated from one approved ZIP of 60 individual PNG files.

## Production source policy

The only production artwork source is:

`assets/iconic-60-pngs-q50.zip`

The ZIP must contain exactly:

- `destino_01_01.png` through `destino_06_10.png`
- 60 unique PNG files
- each file exactly 100 × 120 pixels
- each file with no more than 50 source colours

The import step extracts those files byte-for-byte to `input-pngs-q50/`. Each product then reads its own `input_png` directly.

Forbidden production sources:

- mosaics
- reference boards
- board crops
- collage crops
- `.pixz` intermediates
- any generated image used as replacement source artwork

Derived DMC-mapped images, PDF previews and WooCommerce mockups may be generated only after the individual ZIP PNG has passed byte and dimension validation.

## Pattern format

- Technique: cross stitch only (`D####-CS`)
- Master grid: **100 × 120 stitches**
- Total cells: **12,000**
- Chart target: **4 grid pages**
- Palette: selected independently per design and mapped to DMC

## Storefront

The WooCommerce hero is a lifestyle mockup generated from the validated pattern matrix. It is not an artwork source and cannot feed back into pattern generation.

## Guardrails

The importer and publisher fail if:

- the queue is not in hardened ZIP-PNG-only mode
- a product's `input_png` does not match its queue record
- the extracted PNG differs byte-for-byte from its ZIP member
- a legacy mosaic/reference-board field is present
- the source image is not exactly 100 × 120
- the source image exceeds 50 colours
