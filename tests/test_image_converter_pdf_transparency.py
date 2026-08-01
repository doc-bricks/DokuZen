#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for ImageConverter PDF conversion and RGBA/transparency handling.
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
from core.converter.image_tools import ImageConverter, ImageFormat, PIL_AVAILABLE


class TestImageConverterPdfTransparency(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.converter = ImageConverter()

    def tearDown(self):
        self.temp_dir.cleanup()

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow nicht verfügbar")
    def test_convert_rgba_png_to_pdf(self):
        """Konvertierung eines RGBA-Bildes zu PDF muss erfolgreich sein."""
        src_png = self.temp_path / "sample_rgba.png"
        out_pdf = self.temp_path / "out_sample.pdf"

        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        img.save(str(src_png), "PNG")

        success = self.converter.convert(
            str(src_png),
            str(out_pdf),
            target_format=ImageFormat.PDF
        )
        self.assertTrue(success, "RGBA-zu-PDF Konvertierung fehlgeschlagen")
        self.assertTrue(out_pdf.exists(), "Ausgabe-PDF wurde nicht erstellt")
        self.assertGreater(out_pdf.stat().st_size, 0)

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow nicht verfügbar")
    def test_convert_palette_transparency_to_pdf(self):
        """Konvertierung eines P-Modus-Bildes mit Transparenz zu PDF muss erfolgreich sein."""
        src_p = self.temp_path / "sample_p.png"
        out_pdf = self.temp_path / "out_p.pdf"

        img = Image.new("RGBA", (50, 50), (0, 255, 0, 128))
        p_img = img.convert("P")
        p_img.save(str(src_p), "PNG")

        success = self.converter.convert(
            str(src_p),
            str(out_pdf),
            target_format=ImageFormat.PDF
        )
        self.assertTrue(success, "P-Transparenz-zu-PDF Konvertierung fehlgeschlagen")
        self.assertTrue(out_pdf.exists())

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow nicht verfügbar")
    def test_convert_rgba_to_jpeg_and_bmp(self):
        """Konvertierung eines RGBA-Bildes zu JPEG und BMP muss erfolgreich sein."""
        src_png = self.temp_path / "sample_rgba2.png"
        out_jpg = self.temp_path / "out_sample.jpg"
        out_bmp = self.temp_path / "out_sample.bmp"

        img = Image.new("RGBA", (80, 80), (0, 0, 255, 200))
        img.save(str(src_png), "PNG")

        res_jpg = self.converter.convert(str(src_png), str(out_jpg), target_format=ImageFormat.JPEG)
        self.assertTrue(res_jpg, "RGBA-zu-JPEG Konvertierung fehlgeschlagen")
        self.assertTrue(out_jpg.exists())

        res_bmp = self.converter.convert(str(src_png), str(out_bmp), target_format=ImageFormat.BMP)
        self.assertTrue(res_bmp, "RGBA-zu-BMP Konvertierung fehlgeschlagen")
        self.assertTrue(out_bmp.exists())


if __name__ == "__main__":
    unittest.main()
