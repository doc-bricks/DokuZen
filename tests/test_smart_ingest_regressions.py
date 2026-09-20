#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Regression Tests for Smart Ingest & Multi-Format Routing
=================================================================
Prüft Fehlerbehebungen für:
- Format-Routing von .odt, .doc, .rtf (direkte Bibliotheksaufnahme statt scheiternder PDF-Wandlung)
- PDF-Konvertierung von .markdown, .htm, .tif
- Windows-Pfadnormalisierung bei Duplikatserkennung (Case-Insensitivität)
"""

import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from core.ingest.models import (
    FileType,
    IngestAction,
)
from core.ingest.detector import FormatDetector
from core.ingest.service import SmartIngestService
from core.converter.formats import FormatConverter
from core.library.manager import LibraryManager


class TestSmartIngestRegressions(unittest.TestCase):
    """Regressionstests für Multi-Format Routing und Ingest."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.state_file = self.root / "state.json"
        self.library = LibraryManager(state_file=str(self.state_file))
        self.service = SmartIngestService(self.library)
        self.detector = FormatDetector()

    def tearDown(self):
        self.library.shutdown()
        self.temp_dir.cleanup()

    def test_odt_rtf_doc_routed_to_add_direct(self):
        """ODT, RTF und DOC dürfen nicht fälschlich als PDF-konvertierbar eingestuft werden."""
        odt_file = self.root / "contract.odt"
        odt_file.write_bytes(b"PK\x03\x04odt_content")

        rtf_file = self.root / "notes.rtf"
        rtf_file.write_text(r"{\rtf1\ansi test}", encoding="utf-8")

        doc_file = self.root / "legacy.doc"
        doc_file.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1word")

        for f in (odt_file, rtf_file, doc_file):
            self.assertFalse(
                self.detector.is_convertible_to_pdf(str(f)),
                f"{f.suffix} sollte nicht als konvertierbar zu PDF gelten, da FormatConverter dies nicht unterstützt"
            )

            cand = self.detector.create_candidate(str(f), auto_convert_non_pdf=True)
            self.assertEqual(
                cand.selected_action,
                IngestAction.ADD_DIRECT,
                f"{f.suffix} sollte direkt zur Bibliothek hinzugefügt werden"
            )

            res = self.service.ingest_single(cand)
            self.assertTrue(res.success, f"Ingest für {f.name} fehlgeschlagen: {res.error}")
            self.assertEqual(res.action_performed, IngestAction.ADD_DIRECT)

    def test_markdown_htm_tif_successful_conversion_and_ingest(self):
        """Markdown (.markdown), HTML (.htm) und TIFF (.tif) müssen sauber nach PDF konvertiert werden."""
        md_file = self.root / "guide.markdown"
        md_file.write_text("# DokuZen Ingest Guide\n\nAutomatisches Formatrouting.", encoding="utf-8")

        htm_file = self.root / "webpage.htm"
        htm_file.write_text("<html><body><h1>Web Dokument</h1><p>Test</p></body></html>", encoding="utf-8")

        tif_file = self.root / "scan.tif"
        img = Image.new("RGB", (30, 30), color="blue")
        img.save(str(tif_file))

        for f in (md_file, htm_file, tif_file):
            self.assertTrue(
                self.detector.is_convertible_to_pdf(str(f)),
                f"{f.suffix} muss als konvertierbar zu PDF erkannt werden"
            )

            cand = self.detector.create_candidate(str(f), auto_convert_non_pdf=True)
            self.assertEqual(cand.selected_action, IngestAction.CONVERT_TO_PDF)

            res = self.service.ingest_single(cand)
            self.assertTrue(res.success, f"Ingest & Konvertierung für {f.name} fehlgeschlagen: {res.error}")
            self.assertEqual(res.action_performed, IngestAction.CONVERT_TO_PDF)
            self.assertIsNotNone(res.output_path)
            self.assertTrue(Path(res.output_path).exists())
            self.assertTrue(res.output_path.endswith(".pdf"))

    def test_windows_path_normalization_duplicate_detection(self):
        """Duplikatserkennung muss auf Windows unabhängig von Casing und Slash-Stil greifen."""
        pdf_file = self.root / "receipt.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        # Ingest original file
        cand1 = self.detector.create_candidate(str(pdf_file))
        self.service.ingest_single(cand1)

        # Existing paths from library
        existing = self.service.get_existing_paths()

        # Check variation with flipped case and forward slashes
        path_str = str(pdf_file.resolve())
        variations = [
            path_str.lower(),
            path_str.upper(),
            path_str.replace("\\", "/"),
            path_str.replace("\\", "/").lower(),
        ]

        for var in variations:
            action = self.detector.determine_action(
                FileType.PDF,
                var,
                existing_paths=existing,
            )
            self.assertEqual(
                action,
                IngestAction.SKIP_DUPLICATE,
                f"Pfad-Variante '{var}' wurde nicht als Duplikat erkannt"
            )


if __name__ == "__main__":
    unittest.main()
