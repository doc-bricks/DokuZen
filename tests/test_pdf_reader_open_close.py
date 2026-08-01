#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFReader — fitz-Dokument wird auch bei Exception in open() geschlossen.

Bugfix 1: open() setzte self._doc = None ohne close() aufzurufen, wenn nach
          fitz.open() eine Exception auftrat (z.B. in doc.authenticate()).
Bugfix 2: close() verwendete `if self._doc:` statt `if self._doc is not None:`.
          Bei 0-Seiten-PDFs (bool(doc)==False) wurde das Dokument nie geschlossen.
Bugfix #38: Properties (page_count, is_encrypted, needs_password, get_info, get_text, etc.)
            verwendeten `if not self._doc` statt `if self._doc is None` —
            0-Seiten-PDFs wurden als "nicht geladen" behandelt.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestPDFReaderOpenClose(unittest.TestCase):

    def test_open_closes_doc_when_authenticate_raises(self):
        """doc.close() wird aufgerufen wenn authenticate() eine Exception wirft."""
        import core.pdf.reader as reader_mod

        mock_doc = MagicMock()
        type(mock_doc).is_encrypted = PropertyMock(return_value=True)
        mock_doc.authenticate.side_effect = RuntimeError("corrupt pdf")

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = None
        reader._path = None

        with patch.object(reader_mod, 'fitz', fitz_stub, create=True), \
             patch.object(reader_mod, 'PYMUPDF_AVAILABLE', True):
            result = reader.open("test.pdf", "")

        self.assertFalse(result)
        mock_doc.close.assert_called_once_with()
        self.assertIsNone(reader._doc)

    def test_open_does_not_call_close_when_fitz_open_raises(self):
        """Wenn fitz.open() selbst wirft, wird close() nicht aufgerufen (kein doc)."""
        import core.pdf.reader as reader_mod

        fitz_stub = MagicMock()
        fitz_stub.open.side_effect = RuntimeError("file not found")

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = None
        reader._path = None

        with patch.object(reader_mod, 'fitz', fitz_stub, create=True), \
             patch.object(reader_mod, 'PYMUPDF_AVAILABLE', True):
            result = reader.open("test.pdf", "")

        self.assertFalse(result)
        self.assertIsNone(reader._doc)

    def test_open_success_doc_stays_open(self):
        """Nach erfolgreichem open() ist self._doc gesetzt und nicht geschlossen."""
        import core.pdf.reader as reader_mod

        mock_doc = MagicMock()
        type(mock_doc).is_encrypted = PropertyMock(return_value=False)
        type(mock_doc).page_count = PropertyMock(return_value=3)

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = None
        reader._path = None

        with patch.object(reader_mod, 'fitz', fitz_stub, create=True), \
             patch.object(reader_mod, 'PYMUPDF_AVAILABLE', True):
            result = reader.open("test.pdf", "")

        self.assertTrue(result)
        mock_doc.close.assert_not_called()
        self.assertIs(reader._doc, mock_doc)


    def test_close_works_with_zero_page_doc(self):
        """close() schließt auch ein 0-Seiten-Dokument (bool(doc)==False, aber not None)."""
        import core.pdf.reader as reader_mod

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_doc.__bool__ = MagicMock(return_value=False)

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = mock_doc
        reader._path = "test.pdf"

        reader.close()

        mock_doc.close.assert_called_once_with()
        self.assertIsNone(reader._doc)
        self.assertIsNone(reader._path)


    def test_close_works_with_real_zero_page_doc(self):
        """close() schließt ein echtes fitz-0-Seiten-Dokument — verankert #31-Prämisse an Realität."""
        try:
            import fitz
        except ImportError:
            self.skipTest("fitz/PyMuPDF nicht installiert — Test übersprungen")

        import core.pdf.reader as reader_mod

        real_doc = fitz.open()  # leeres In-Memory-Dokument, 0 Seiten
        self.assertFalse(bool(real_doc),
            "Prämisse von Bug #31: bool(fitz.open()) muss False sein")
        self.assertEqual(len(real_doc), 0)

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = real_doc
        reader._path = "test.pdf"

        reader.close()

        self.assertIsNone(reader._doc)
        self.assertIsNone(reader._path)


SOURCE = Path(__file__).resolve().parents[1] / "core" / "pdf" / "reader.py"


class TestPDFReaderZeroPageProperties(unittest.TestCase):
    """Bug #38: `if self._doc` / `if not self._doc` → korrekte is-None-Guards."""

    def test_no_falsy_doc_guards_in_source(self):
        """reader.py darf keine `if self._doc else` / `if not self._doc:` Guards mehr haben."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("if self._doc else", source,
            "Falsy inline-guard `if self._doc else` in reader.py gefunden")
        self.assertNotIn("if not self._doc:", source,
            "Falsy guard `if not self._doc:` in reader.py gefunden")

    def test_is_open_uses_is_not_none(self):
        """is_open muss `is not None` verwenden."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("return self._doc is not None", source)

    def test_zero_page_doc_is_open(self):
        """is_open gibt True zurück für ein 0-Seiten-Dokument (nicht None!)."""
        import core.pdf.reader as reader_mod

        mock_doc = MagicMock()
        mock_doc.__bool__ = MagicMock(return_value=False)
        mock_doc.__len__ = MagicMock(return_value=0)

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = mock_doc
        reader._path = "zero.pdf"

        self.assertTrue(reader.is_open,
            "is_open muss True für ein 0-Seiten-Dokument zurückgeben")

    def test_zero_page_doc_is_encrypted_checked(self):
        """`is_encrypted` wird auch für 0-Seiten-Dokumente geprüft (nicht überspringen)."""
        import core.pdf.reader as reader_mod

        mock_doc = MagicMock()
        mock_doc.__bool__ = MagicMock(return_value=False)
        type(mock_doc).is_encrypted = PropertyMock(return_value=True)

        reader = reader_mod.PDFReader.__new__(reader_mod.PDFReader)
        import logging
        reader._logger = logging.getLogger("test")
        reader._doc = mock_doc
        reader._path = "zero_encrypted.pdf"

        self.assertTrue(reader.is_encrypted,
            "is_encrypted muss True für ein verschlüsseltes 0-Seiten-Dokument zurückgeben")


if __name__ == "__main__":
    unittest.main()
