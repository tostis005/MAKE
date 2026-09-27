# Drielo collection image sources

This directory is the canonical human-managed source for collection artwork.

Each collection has exactly two image areas:

- `background/`: one approved page-1 background image for the collection.
- `products/`: independent product designs. Product designs are PNG files and are expected to be exactly 100 x 120 pixels unless the collection config explicitly says otherwise.

Rules:

1. Never place mosaics, contact sheets, PDF page crops, ZIP archives, or generated WooCommerce gallery images in `products/`.
2. One PNG equals one base design.
3. Product filenames should begin with the stable base design code when one exists, for example `D0034-new-york-statue-liberty.png` or `P1001-glam-blonde-icon.png`.
4. The page-1 background is independent from product designs and must live only in `background/`.
5. Generated PDFs, product JSON, WooCommerce images, galleries and catalogue rows do not belong here. They are outputs.
6. Existing legacy source locations remain valid as fallback during migration, but new approved artwork should be stored here first.

The source registry is `registry.json`.
