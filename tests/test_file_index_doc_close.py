#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für FileIndex — fitz-Dokument wird auch bei Exception geschlossen.

Bugfix: _extract_pdf_metadata() schloss doc nur auf dem Erfolgspfad.
Bugfix 2: if doc: statt if doc is not None: — 0-Seiten-PDF wurde nie geschlossen.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_file_index():
    """Erstellt FileIndex-Instanz ohne echte DB-Verbindung."""
    import core.knowledge.file_index as fi_mod
    index = fi_mod.FileIndex.__new__(fi_mod.FileIndex)
    import logging
    index._logger = logging.getLogger("test")
    return index


class TestFileIndexDocClose(unittest.TestCase):

    def test_extract_pdf_metadata_closes_doc_on_success(self):
        """doc.close() wird nach erfolgreichem Metadaten-Lesen aufgerufen."""
        import core.knowledge.file_index as fi_mod

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_doc.is_encrypted = False
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_doc.metadata = {'title': 'Test', 'author': 'Author'}

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        index = _make_file_index()

        with patch.object(fi_mod, 'fitz', fitz_stub, create=True), \
             patch.object(fi_mod, 'PYMUPDF_AVAILABLE', True):
            result = index._extract_pdf_metadata('test.pdf')

        mock_doc.close.assert_called_once_with()
        self.assertEqual(result['pdf_pages'], 3)

    def test_extract_pdf_metadata_closes_doc_when_metadata_raises(self):
        """doc.close() wird aufgerufen wenn doc.metadata eine Exception wirft."""
        import core.knowledge.file_index as fi_mod

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.is_encrypted = False
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        type(mock_doc).metadata = property(lambda self: (_ for _ in ()).throw(RuntimeError("corrupt")))

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        index = _make_file_index()

        with patch.object(fi_mod, 'fitz', fitz_stub, create=True), \
             patch.object(fi_mod, 'PYMUPDF_AVAILABLE', True):
            result = index._extract_pdf_metadata('test.pdf')

        mock_doc.close.assert_called_once_with()
        # Metadaten bleiben None bei Fehler
        self.assertIsNone(result['pdf_title'])

    def test_extract_pdf_metadata_closes_doc_with_zero_pages(self):
        """doc.close() wird auch bei einem 0-Seiten-PDF aufgerufen (if doc is not None:)."""
        import core.knowledge.file_index as fi_mod

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_doc.__bool__ = MagicMock(return_value=False)
        mock_doc.is_encrypted = False
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_doc.metadata = {}

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        index = _make_file_index()

        with patch.object(fi_mod, 'fitz', fitz_stub, create=True), \
             patch.object(fi_mod, 'PYMUPDF_AVAILABLE', True):
            result = index._extract_pdf_metadata('test.pdf')

        mock_doc.close.assert_called_once_with()
        self.assertEqual(result['pdf_pages'], 0)

    def test_extract_pdf_metadata_skips_when_pymupdf_unavailable(self):
        """Ohne PyMuPDF wird fitz gar nicht aufgerufen."""
        import core.knowledge.file_index as fi_mod

        fitz_stub = MagicMock()

        index = _make_file_index()

        with patch.object(fi_mod, 'fitz', fitz_stub, create=True), \
             patch.object(fi_mod, 'PYMUPDF_AVAILABLE', False):
            result = index._extract_pdf_metadata('test.pdf')

        fitz_stub.open.assert_not_called()
        self.assertIsNone(result['pdf_pages'])


if __name__ == "__main__":
    unittest.main()
