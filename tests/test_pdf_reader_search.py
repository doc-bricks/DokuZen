#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFReader.search_text — Case-Sensitivity-Fix.

Bugfix: flags-Variable wurde berechnet aber nie an page.search_for() übergeben;
        case_sensitive=False hatte keinerlei Wirkung.
"""

import re
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Dieser Test braucht ein isoliertes fitz-Doppel. Es darf weder ein bereits
# geladenes PyMuPDF-Modul verändern noch den Stub in sys.modules hinterlassen,
# weil spätere Integrationstests echte PDFs erstellen und öffnen.
_original_fitz = sys.modules.get("fitz")
_fitz_stub = MagicMock()
_fitz_stub.Rect = lambda *a: MagicMock()
sys.modules["fitz"] = _fitz_stub

# reader.py unter einem testspezifischen Modulnamen laden, damit der produktive
# core.pdf.reader-Import nicht durch diesen isolierten Stub ersetzt wird.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "_dokuzen_test_pdf_reader_search",
    PROJECT_ROOT / "core" / "pdf" / "reader.py"
)
_reader_mod = _ilu.module_from_spec(_spec)
sys.modules[_spec.name] = _reader_mod
try:
    _spec.loader.exec_module(_reader_mod)
finally:
    if _original_fitz is None:
        sys.modules.pop("fitz", None)
    else:
        sys.modules["fitz"] = _original_fitz

PDFReader = _reader_mod.PDFReader


# ---------------------------------------------------------------------------

def _make_mock_page(text: str):
    """Mock-Seite mit case-sensitiver search_for-Simulation."""
    page = MagicMock()
    page.get_text.return_value = text

    def fake_search_for(needle):
        results = []
        start = 0
        while True:
            idx = text.find(needle, start)
            if idx == -1:
                break
            results.append(MagicMock())   # simuliertes fitz.Rect
            start = idx + 1
        return results

    page.search_for.side_effect = fake_search_for
    return page


def _make_reader(page_texts):
    reader = PDFReader.__new__(PDFReader)
    reader._logger = MagicMock()
    reader._path = Path("test.pdf")

    mock_doc = MagicMock()
    mock_doc.__bool__ = lambda s: True
    mock_doc.is_encrypted = False
    mock_doc.needs_pass = False
    mock_doc.page_count = len(page_texts)

    pages = [_make_mock_page(t) for t in page_texts]
    mock_doc.__iter__ = MagicMock(return_value=iter(pages))

    reader._doc = mock_doc
    return reader


class TestSearchTextCaseSensitivity(unittest.TestCase):

    def _fresh_iter(self, reader, page_texts):
        """Setzt den Iterator zurück (wird pro search_text-Aufruf benötigt)."""
        pages = [_make_mock_page(t) for t in page_texts]
        reader._doc.__iter__ = MagicMock(return_value=iter(pages))

    def test_case_sensitive_finds_exact_match(self):
        texts = ["Hello World"]
        reader = _make_reader(texts)
        self._fresh_iter(reader, texts)
        results = reader.search_text("Hello", case_sensitive=True)
        self.assertEqual(len(results), 1)

    def test_case_sensitive_misses_different_case(self):
        """case_sensitive=True darf 'Hello' in 'hello world' NICHT finden."""
        texts = ["hello world"]
        reader = _make_reader(texts)
        self._fresh_iter(reader, texts)
        results = reader.search_text("Hello", case_sensitive=True)
        self.assertEqual(len(results), 0)

    def test_case_insensitive_finds_lowercase_text(self):
        """Kerntest des Bugfixes: case_sensitive=False findet 'Hello' in 'hello world'."""
        texts = ["hello world"]
        reader = _make_reader(texts)
        self._fresh_iter(reader, texts)
        results = reader.search_text("Hello", case_sensitive=False)
        self.assertEqual(len(results), 1,
                         "case_sensitive=False muss 'Hello' in 'hello world' finden")

    def test_case_insensitive_finds_uppercase_text(self):
        texts = ["HELLO WORLD"]
        reader = _make_reader(texts)
        self._fresh_iter(reader, texts)
        results = reader.search_text("hello", case_sensitive=False)
        self.assertEqual(len(results), 1)

    def test_empty_query_returns_empty(self):
        reader = _make_reader(["Hello World"])
        results = reader.search_text("", case_sensitive=False)
        self.assertEqual(results, [])

    def test_no_doc_returns_empty(self):
        reader = PDFReader.__new__(PDFReader)
        reader._logger = MagicMock()
        reader._doc = None
        reader._path = None
        results = reader.search_text("test")
        self.assertEqual(results, [])

    def test_no_match_returns_empty(self):
        texts = ["Völlig anderer Text"]
        reader = _make_reader(texts)
        self._fresh_iter(reader, texts)
        results = reader.search_text("nichtvorhanden", case_sensitive=False)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
