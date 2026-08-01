#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für den Architektur-Fix der Redaction-Reliability:
Span/Rect-basierte Schwärzung statt schlichtem page.search_for(match.text).
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from core.redaction.detector import (
    RedactionDetector, RedactionApplier, Match, SensitiveType,
    extract_page_text_and_char_rects, char_bboxes_to_rects, redact_pdf
)


class TestRedactionSpanRects(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_pdf = str(Path(self.temp_dir.name) / "input.pdf")
        self.output_pdf = str(Path(self.temp_dir.name) / "output.pdf")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_pdf(self, lines):
        doc = fitz.open()
        page = doc.new_page()
        y = 50
        for line in lines:
            page.insert_text((50, y), line)
            y += 20
        doc.save(self.input_pdf)
        doc.close()

    def test_extract_page_text_and_char_rects_alignment(self):
        """Prüft, ob text_str und char_rects die gleiche Länge aufweisen."""
        self._create_sample_pdf(["Max Mustermann", "IBAN: DE89 3704 1234 5678 90"])
        doc = fitz.open(self.input_pdf)
        page = doc[0]
        text, char_rects = extract_page_text_and_char_rects(page)
        doc.close()

        self.assertEqual(len(text), len(char_rects))
        self.assertIn("DE89 3704 1234 5678 90", text)

    def test_char_bboxes_to_rects(self):
        """Prüft die Zusammenfassung zeilenbasierter Bounding-Boxes."""
        bboxes = [
            (50.0, 50.0, 60.0, 65.0),
            (60.0, 50.0, 70.0, 65.0),
            # Neue Zeile (y0 verschoben)
            (50.0, 80.0, 60.0, 95.0),
            (60.0, 80.0, 70.0, 95.0),
        ]
        rects = char_bboxes_to_rects(bboxes)
        self.assertEqual(len(rects), 2)
        self.assertEqual(rects[0], (50.0, 50.0, 70.0, 65.0))
        self.assertEqual(rects[1], (50.0, 80.0, 70.0, 95.0))

    def test_multiline_iban_redaction_without_misses(self):
        """Prüft, dass mehrzeilige IBANs über Span/Rects ohne Misses geschwärzt werden."""
        # IBAN über zwei Zeilen hinweg
        self._create_sample_pdf([
            "Konto-Informationen:",
            "IBAN: DE89 3704",
            "1234 5678 9012 34",
            "E-Mail: test@example.com"
        ])

        doc = fitz.open(self.input_pdf)
        page = doc[0]
        text, char_rects = extract_page_text_and_char_rects(page)
        doc.close()

        detector = RedactionDetector()
        matches = detector.detect(text, page=1, char_rects=char_rects)

        # Überprüfen, ob Rects an den Matches angehängt wurden
        iban_matches = [m for m in matches if m.type == SensitiveType.IBAN]
        self.assertTrue(len(iban_matches) > 0)
        for m in iban_matches:
            self.assertIsNotNone(m.rects)
            self.assertGreater(len(m.rects), 0)

        applier = RedactionApplier()
        success = applier.redact_pdf(self.input_pdf, self.output_pdf, matches)

        self.assertTrue(success)
        self.assertEqual(applier.last_redaction_stats["missed"], 0)
        self.assertGreater(applier.last_redaction_stats["redacted"], 0)

        # Prüfen, ob der sensibler Text aus dem Ergebnis-PDF entfernt wurde
        doc_out = fitz.open(self.output_pdf)
        out_text = doc_out[0].get_text()
        doc_out.close()

        self.assertNotIn("DE89 3704", out_text)
        self.assertNotIn("test@example.com", out_text)

    def test_redact_pdf_convenience_function(self):
        """Prüft die Modul-Funktion redact_pdf() mit automatischer Rect-Extraktion."""
        self._create_sample_pdf(["Wichtig:", "E-Mail: kontakt@firma.de"])
        res = redact_pdf(self.input_pdf, self.output_pdf)
        self.assertTrue(res)

        doc_out = fitz.open(self.output_pdf)
        out_text = doc_out[0].get_text()
        doc_out.close()
        self.assertNotIn("kontakt@firma.de", out_text)


if __name__ == "__main__":
    unittest.main()
