#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für FormatConverter._convert_from_pdf — doc.close() auch bei Exceptions.

Bugfix: doc.close() wurde nur auf expliziten Rückgabepfaden aufgerufen.
        Bei Exceptions (z. B. pix.save() scheitert) blieb das Dokument offen.
"""

import sys
import types
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import core.converter.formats as _fmt_mod


def _make_doc_mock(page_count=1, save_raises=None, get_text_raises=None):
    """Erstellt einen minimalen fitz-doc-Mock."""
    pix_mock = MagicMock()
    pix_mock.samples = b"\xff\x00\x00" * 4
    pix_mock.width = 2
    pix_mock.height = 2
    if save_raises:
        pix_mock.save.side_effect = save_raises
    else:
        pix_mock.save.return_value = None

    page_mock = MagicMock()
    page_mock.get_pixmap.return_value = pix_mock
    if get_text_raises:
        page_mock.get_text.side_effect = get_text_raises
    else:
        page_mock.get_text.return_value = "Testinhalt"

    doc_mock = MagicMock()
    doc_mock.page_count = page_count
    doc_mock.__getitem__ = lambda self, idx: page_mock
    doc_mock.__iter__ = lambda self: iter([page_mock])
    doc_mock.__len__ = lambda self: page_count
    return doc_mock


class TestFormatConverterPdfClose(unittest.TestCase):

    def _make_fitz_stub(self, doc_mock):
        """Erstellt fitz-Stub und patcht ihn direkt ins Modul."""
        fitz_stub = types.ModuleType("fitz")
        fitz_stub.open = MagicMock(return_value=doc_mock)
        fitz_stub.Matrix = MagicMock(return_value=MagicMock())
        return fitz_stub

    def test_doc_closed_on_txt_success(self):
        """doc.close() wird nach erfolgreicher TXT-Konvertierung aufgerufen."""
        doc_mock = _make_doc_mock()
        fitz_stub = self._make_fitz_stub(doc_mock)
        converter = _fmt_mod.FormatConverter()
        with patch.object(_fmt_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_fmt_mod, 'PYMUPDF_AVAILABLE', True):
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                out = f.name
            try:
                converter._convert_from_pdf("input.pdf", out, ".txt")
                doc_mock.close.assert_called_once()
            finally:
                Path(out).unlink(missing_ok=True)

    def test_doc_closed_when_save_raises(self):
        """doc.close() wird aufgerufen, auch wenn pix.save() eine Exception wirft."""
        doc_mock = _make_doc_mock(save_raises=OSError("Disk voll"))
        fitz_stub = self._make_fitz_stub(doc_mock)
        converter = _fmt_mod.FormatConverter()
        with patch.object(_fmt_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_fmt_mod, 'PYMUPDF_AVAILABLE', True):
            result = converter._convert_from_pdf("input.pdf", "out.png", ".png")

        self.assertFalse(result.success)
        doc_mock.close.assert_called_once()

    def test_doc_closed_when_get_text_raises(self):
        """doc.close() wird aufgerufen, auch wenn get_text() eine Exception wirft."""
        doc_mock = _make_doc_mock(get_text_raises=RuntimeError("Seite kaputt"))
        fitz_stub = self._make_fitz_stub(doc_mock)
        converter = _fmt_mod.FormatConverter()
        with patch.object(_fmt_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_fmt_mod, 'PYMUPDF_AVAILABLE', True):
            result = converter._convert_from_pdf("input.pdf", "out.txt", ".txt")

        self.assertFalse(result.success)
        doc_mock.close.assert_called_once()

    def test_doc_closed_on_unsupported_output(self):
        """doc.close() wird aufgerufen, auch wenn das Ausgabeformat nicht unterstützt wird."""
        doc_mock = _make_doc_mock()
        fitz_stub = self._make_fitz_stub(doc_mock)
        converter = _fmt_mod.FormatConverter()
        with patch.object(_fmt_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_fmt_mod, 'PYMUPDF_AVAILABLE', True):
            result = converter._convert_from_pdf("input.pdf", "out.docx", ".docx")

        self.assertFalse(result.success)
        doc_mock.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
