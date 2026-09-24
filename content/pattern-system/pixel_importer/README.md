# Drielo pixel-by-pixel importer

This importer is intentionally deterministic.

## Rule

**1 source pixel = 1 full cross stitch.**

It does not resize, resample, quantize, smooth, clean, reinterpret, or map colours to DMC. The RGB value stored in the source tile is the RGB value used in the generated pattern.

The importer is only for cross stitch.

## Input

A single sheet containing multiple designs arranged in a regular grid.

Required geometry:

- tile width in pixels
- tile height in pixels
- number of rows
- number of columns

Optional geometry defaults to zero:

- origin X/Y
- horizontal/vertical gap

The complete sheet dimensions must match the supplied geometry exactly. If they do not, the import stops instead of guessing.

## Example

    python3 content/pattern-system/pixel_importer/import_pixel_sheet.py \
      --image /path/to/sheet.png \
      --tile-width 120 \
      --tile-height 110 \
      --rows 2 \
      --cols 5 \
      --run-id example

This creates 10 exact patterns in row-major order.

Outputs are written below:

    content/pattern-system/pixel_importer/output/<run-id>/

For every tile the run contains:

- the exact PNG crop
- an exact pattern JSON
- the generated cross-stitch PDF

A run-level manifest records all coordinates and output paths.

## Exact-colour behaviour

Colours are not merged. The pattern colour code is the exact source HEX value.

If an input contains more distinct colours than the chart can represent with the configured single-character symbols, the importer stops with an error. It never silently reduces the palette.

Transparent or partially transparent pixels are rejected because every source pixel must represent one stitch colour.

## Tests

    python3 content/pattern-system/pixel_importer/test_pixel_importer.py

## GitHub Actions

The workflow pixel-by-pixel-import.yml can run the importer against a sheet already present in the repository and uploads the generated run as an artifact.
