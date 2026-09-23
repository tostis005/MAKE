# Drielo Pop Art — multicraft PDF templates

These files are the technique-specific companions to the existing cross-stitch PDF system.

## Shared rules

- A4 print layout, one `.page` per PDF page.
- Product identity is the technique-qualified pattern code only (for example `P0001-CS`, `P0001-C2C`, `P0001-TC` or `P0001-LH`).
- Collection is `Pop Art`; the technique is displayed separately.
- The product URL is centered and clickable.
- Pattern artwork is inserted as vector SVG, never as a raster screenshot.
- Cover mockups contain a dedicated vector insertion group so the design can be replaced without rebuilding the lifestyle scene.
- Color/symbol charts are vector slots sized for zooming and PDF export.

## Templates

- `pop-art/c2c-crochet.html`
- `pop-art/tapestry-crochet.html`
- `pop-art/latch-hook.html`
- `pop-art/diamond-painting.html`
- `pop-art/fuse-beads.html`
- `pop-art/intarsia-knitting.html`
- `pop-art/bead-loom.html`

All templates use `../shared/drielo-pattern-template.css`.

## Product-code convention

The base design number groups the same artwork across techniques, but the sellable code is always unique:

| Technique | Suffix | Example |
| --- | --- | --- |
| Cross Stitch | `CS` | `P0001-CS` |
| C2C Crochet | `C2C` | `P0001-C2C` |
| Tapestry Crochet | `TC` | `P0001-TC` |
| Latch Hook / Rug | `LH` | `P0001-LH` |

## Placeholder convention

Common placeholders include:

`{{PATTERN_CODE}}`, `{{PRODUCT_URL}}`, `{{PATTERN_PREVIEW_SVG}}`, `{{COLOR_CHART_SVG}}`,
`{{SYMBOL_CHART_SVG}}`, `{{COLOR_KEY_ROWS}}`, `{{COPYRIGHT_YEAR}}`.

Technique-specific placeholders are documented in comments inside each HTML file.

## Pop Art suitability

The C2C, tapestry crochet, latch hook and diamond-painting templates are designed to accept a derived version of the existing Pop Art matrix directly. Fuse beads and intarsia expect a reduced-color/reduced-resolution derivative. Bead loom expects a separate bracelet/cuff crop or reinterpretation rather than the original portrait matrix.


## Ecommerce product-image contract

Every technique template must expose exactly one element with the attribute `data-product-image`. That element must contain only the lifestyle/ambient mockup plus the finished technique-specific pattern. It must not contain title text, facts, size/skill information, badges, headers, footers, floral decorations or page numbering.

The renderer exports that element as one 4:5 WebP named `<CODE>-product.webp`. WooCommerce should use only that image as the product gallery image unless a later project rule explicitly requests extra images.
