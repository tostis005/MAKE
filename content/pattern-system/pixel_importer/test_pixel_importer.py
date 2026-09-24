#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import import_pixel_sheet as px  # noqa: E402


class PixelImporterTests(unittest.TestCase):
    def test_split_is_exact_and_row_major(self):
        sheet = Image.new("RGB", (4, 2))
        sheet.putdata(
            [
                (255, 0, 0), (255, 0, 0), (0, 255, 0), (0, 255, 0),
                (0, 0, 255), (0, 0, 255), (255, 255, 0), (255, 255, 0),
            ]
        )
        tiles = list(px.extract_tiles(sheet, 2, 2, 1, 2))
        self.assertEqual(len(tiles), 2)
        self.assertEqual(tiles[0][0:3], (1, 0, 0))
        self.assertEqual(tiles[1][0:3], (2, 0, 1))
        self.assertEqual(
            list(tiles[0][3].getdata()),
            [(255, 0, 0), (255, 0, 0), (0, 0, 255), (0, 0, 255)],
        )
        self.assertEqual(
            list(tiles[1][3].getdata()),
            [(0, 255, 0), (0, 255, 0), (255, 255, 0), (255, 255, 0)],
        )

    def test_pattern_roundtrip_preserves_every_rgb_pixel(self):
        tile = Image.new("RGB", (3, 2))
        source = [
            (10, 20, 30), (40, 50, 60), (10, 20, 30),
            (70, 80, 90), (40, 50, 60), (1, 2, 3),
        ]
        tile.putdata(source)
        pattern = px.build_exact_pattern(tile, "PX0001-CS", "Test")
        self.assertEqual(pattern["stitch_width"], 3)
        self.assertEqual(pattern["stitch_height"], 2)
        self.assertEqual(pattern["total_stitches"], 6)
        self.assertEqual(len(pattern["threads"]), 4)
        self.assertEqual(px.pattern_pixels(pattern), source)
        px.validate_exact_roundtrip(tile, pattern)

    def test_wrong_geometry_fails_instead_of_resizing(self):
        sheet = Image.new("RGB", (5, 4), (1, 2, 3))
        with self.assertRaises(ValueError):
            px.validate_sheet_geometry(sheet, 2, 2, 2, 2)

    def test_transparency_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "transparent.png"
            im = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
            im.putpixel((1, 1), (0, 0, 0, 0))
            im.save(path)
            with self.assertRaises(ValueError):
                px.read_image(path)


if __name__ == "__main__":
    unittest.main()
