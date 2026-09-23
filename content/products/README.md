# Drielo product catalogue

This directory is the source-of-truth staging area for future digital products.

## Product defaults

- Product type: simple, virtual, downloadable WooCommerce product.
- Base price: 4.99.
- Store currency: USD by default, with EUR available from the storefront switcher.
- Quantity: sold individually.
- Deliverable: one customer-downloadable PDF per product unless explicitly specified otherwise.
- Collection add-on price: 1.49 per additional design selected from the same collection.

## Collection model

Assign every compatible group to the `product_collection` taxonomy. A collection means the designs intentionally reuse the same thread/colour palette. Store:

- collection name and slug;
- short collection description;
- HEX palette values for visual swatches;
- DMC/thread codes;
- all product IDs belonging to the collection.

A shopper can browse either individual patterns or collections. On an individual product page, sibling products from the same collection can be selected and added for 1.49 each.

## PDF preview policy

When source PDFs are supplied:

1. Page 1 is the primary storefront image. It should be exported as a web preview, not the original-resolution page.
2. Page 2 is an optional secondary gallery preview, also downsampled.
3. Never upload a full-resolution chart/pattern page as a public product image.
4. Keep the original PDF private as the WooCommerce downloadable file.
5. Preferred web previews: WebP/JPEG, approximately 900–1200 px on the long edge, visually clear but unsuitable as a replacement for the purchased PDF.

## Catalogue manifest

`catalog.json` is populated as PDFs are added. Each product record should include:

- `sku`
- `title_es` / `title_en`
- `slug`
- `pdf`
- `price`
- `collection`
- `palette_hex`
- `thread_codes`
- `preview_page_primary` (default 1)
- `preview_page_secondary` (default 2)
- WooCommerce product ID after import

## Catalogue filters and structured craft metadata

Every product must define a stable `design_id`, `grid_width`, `grid_height`, `color_count`, and a `filters` object. The filter keys are `technique`, `theme`, `style`, `project`, `orientation`, `difficulty`, `color-family`, and `season`. Values are stable taxonomy slugs, not display labels.

`collection` remains the dedicated `product_collection` taxonomy because collections are commercial/artistic groups, while the filter attributes describe the design and its craft use. The importer writes these fields to WooCommerce global attributes and to Drielo REST-visible product metadata so reimports preserve the storefront filters.
