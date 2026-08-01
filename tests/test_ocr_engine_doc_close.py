#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für OCREngine — fitz-Dokument wird auch bei Exception geschlossen.

Bugfix: _recognize_pdf_pymupdf und pdf_to_searchable_pdf schlossen doc
        nur auf dem Erfolgspfad.
Bugfix #35: `if doc:` → `if doc is not None:` in beiden finally-Blöcken.
            0-Seiten-PDFs (bool==False) wurden nie geschlossen.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

SOURCE = Path(__file__).resolve().parents[1] / "core" / "ocr" / "engine.py"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_ocr_engine():
    """Erstellt OCREngine-Instanz ohne echtes Tesseract."""
    import core.ocr.engine as ocr_mod
    engine = ocr_mod.OCREngine.__new__(ocr_mod.OCREngine)
    import logging
    engine._logger = logging.getLogger("test")
    engine._is_available = True
    engine._tesseract_path = None
    return engine


class TestOCREngineDocClose(unittest.TestCase):

    def test_recognize_pdf_closes_doc_on_success(self):
        """doc.close() wird nach erfolgreichem PDF-OCR aufgerufen."""
        import core.ocr.engine as ocr_mod

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_pix = MagicMock()
        mock_pix.width = 10
        mock_pix.height = 10
        mock_pix.samples = b'\x00' * 300
        mock_page.get_pixmap.return_value = mock_pix

        engine = _make_ocr_engine()

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc
        fitz_stub.Matrix = MagicMock(return_value=MagicMock())

        pil_stub = MagicMock()
        fake_img = MagicMock()
        pil_stub.Image.frombytes.return_value = fake_img

        engine.recognize_image_object = MagicMock(
            return_value=MagicMock(success=False)
        )

        with patch.object(ocr_mod, 'fitz', fitz_stub, create=True), \
             patch.object(ocr_mod, 'Image', pil_stub.Image, create=True):
            engine._recognize_pdf_pymupdf('test.pdf', 'deu', None)

        mock_doc.close.assert_called_once_with()

    def test_recognize_pdf_closes_doc_when_pixmap_raises(self):
        """doc.close() wird auch aufgerufen wenn get_pixmap() wirft."""
        import core.ocr.engine as ocr_mod

        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_page = MagicMock()
        mock_page.get_pixmap.side_effect = RuntimeError("render failed")
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        engine = _make_ocr_engine()

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc
        fitz_stub.Matrix = MagicMock(return_value=MagicMock())

        with patch.object(ocr_mod, 'fitz', fitz_stub, create=True):
            result = engine._recognize_pdf_pymupdf('test.pdf', 'deu', None)

        mock_doc.close.assert_called_once_with()
        self.assertEqual(result, [])

    def test_pdf_to_searchable_closes_doc_on_save_error(self):
        """doc.close() wird auch aufgerufen wenn doc.save() wirft."""
        import core.ocr.engine as ocr_mod

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "already has text"
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_doc.save.side_effect = IOError("disk full")

        engine = _make_ocr_engine()

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        pytess_stub = MagicMock()
        pil_stub = MagicMock()

        with patch.object(ocr_mod, 'fitz', fitz_stub, create=True), \
             patch.object(ocr_mod, 'pytesseract', pytess_stub, create=True), \
             patch.object(ocr_mod, 'Image', pil_stub, create=True):
            result = engine.pdf_to_searchable_pdf('in.pdf', 'out.pdf')

        self.assertFalse(result)
        mock_doc.close.assert_called_once_with()


class TestOCREngineZeroPageGuard(unittest.TestCase):
    """Bug #35: `if doc:` → `if doc is not None:` in beiden OCR-finally-Blöcken."""

    def test_no_falsy_doc_guard_in_source(self):
        """engine.py darf kein `if doc:` in finally-Blöcken haben."""
        source = SOURCE.read_text(encoding="utf-8")
        lines = source.splitlines()
        in_finally = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "finally:":
                in_finally = True
            elif in_finally and stripped == "if doc:":
                self.fail(f"Falsy Guard in Zeile {i+1}: {line!r}")
            elif in_finally and stripped and not stripped.startswith("#") and "finally" not in stripped:
                if not stripped.startswith("if") and not stripped.startswith("doc"):
                    in_finally = False

    def test_is_none_guard_count(self):
        """Beide Guards in engine.py müssen `if doc is not None:` verwenden."""
        source = SOURCE.read_text(encoding="utf-8")
        count = source.count("if doc is not None:")
        self.assertGreaterEqual(count, 2,
            f"Erwartet ≥2 `if doc is not None:`-Guards in engine.py, gefunden: {count}")

    def test_recognize_pdf_closes_zero_page_doc(self):
        """_recognize_pdf_pymupdf() ruft doc.close() auch für ein 0-Seiten-Dokument auf."""
        import core.ocr.engine as ocr_mod

        mock_doc = MagicMock()
        mock_doc.__bool__ = MagicMock(return_value=False)
        type(mock_doc).page_count = PropertyMock(return_value=0)

        engine = _make_ocr_engine()

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc
        fitz_stub.Matrix = MagicMock(return_value=MagicMock())

        with patch.object(ocr_mod, 'fitz', fitz_stub, create=True):
            result = engine._recognize_pdf_pymupdf('empty.pdf', 'deu', None)

        mock_doc.close.assert_called_once_with()
        self.assertEqual(result, [])

    def test_pdf_to_searchable_closes_zero_page_doc(self):
        """pdf_to_searchable_pdf() ruft doc.close() auch für ein 0-Seiten-Dokument auf."""
        import core.ocr.engine as ocr_mod

        mock_doc = MagicMock()
        mock_doc.__bool__ = MagicMock(return_value=False)
        type(mock_doc).page_count = PropertyMock(return_value=0)
        mock_doc.__getitem__ = MagicMock(return_value=MagicMock())

        engine = _make_ocr_engine()

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        with patch.object(ocr_mod, 'fitz', fitz_stub, create=True):
            engine.pdf_to_searchable_pdf('empty.pdf', 'out.pdf')

        mock_doc.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
