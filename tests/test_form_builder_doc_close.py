#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für FormBuilder — doc.close() wird auch bei Exceptions aufgerufen.

Bugfix: extract_form_fields, fill_form und _add_interactive_fields schlossen
        das fitz-Dokument nicht wenn eine Exception geworfen wurde (Resource-Leak).
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import core.forms.builder as _builder_mod


def _make_doc_mock(widgets=None, iter_raises=None):
    """Erstellt minimalen fitz-doc-Mock."""
    doc_mock = MagicMock()
    doc_mock.page_count = 1

    page_mock = MagicMock()
    if iter_raises:
        page_mock.widgets.side_effect = iter_raises
    else:
        page_mock.widgets.return_value = iter(widgets or [])

    doc_mock.__getitem__ = lambda self, idx: page_mock
    doc_mock.__iter__ = lambda self: iter([page_mock])
    doc_mock.__len__ = lambda self: 1
    return doc_mock, page_mock


def _make_fitz_stub(doc_mock):
    stub = types.ModuleType("fitz")
    stub.open = MagicMock(return_value=doc_mock)
    stub.Rect = MagicMock(return_value=MagicMock())
    stub.Widget = MagicMock
    stub.PDF_WIDGET_TYPE_TEXT = 1
    stub.PDF_WIDGET_TYPE_CHECKBOX = 2
    stub.PDF_WIDGET_TYPE_LISTBOX = 3
    return stub


class TestFormBuilderDocClose(unittest.TestCase):

    def _builder(self):
        return _builder_mod.FormBuilder()

    def test_extract_form_fields_closes_doc_on_success(self):
        """doc.close() wird nach erfolgreichem Extrahieren aufgerufen."""
        doc_mock, _ = _make_doc_mock(widgets=[])
        fitz_stub = _make_fitz_stub(doc_mock)
        builder = self._builder()
        with patch.object(_builder_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_builder_mod, 'PYMUPDF_AVAILABLE', True):
            builder.extract_form_fields("test.pdf")
        doc_mock.close.assert_called_once()

    def test_extract_form_fields_closes_doc_when_widgets_raises(self):
        """doc.close() wird aufgerufen, auch wenn page.widgets() eine Exception wirft."""
        doc_mock, _ = _make_doc_mock(iter_raises=RuntimeError("Widgets kaputt"))
        fitz_stub = _make_fitz_stub(doc_mock)
        builder = self._builder()
        with patch.object(_builder_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_builder_mod, 'PYMUPDF_AVAILABLE', True):
            result = builder.extract_form_fields("test.pdf")
        self.assertEqual(result, [])
        doc_mock.close.assert_called_once()

    def test_fill_form_closes_doc_on_success(self):
        """doc.close() wird nach erfolgreichem Ausfüllen aufgerufen."""
        doc_mock, _ = _make_doc_mock(widgets=[])
        fitz_stub = _make_fitz_stub(doc_mock)
        builder = self._builder()
        with patch.object(_builder_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_builder_mod, 'PYMUPDF_AVAILABLE', True):
            builder.fill_form("test.pdf", "out.pdf", {})
        doc_mock.close.assert_called_once()

    def test_fill_form_closes_doc_when_save_raises(self):
        """doc.close() wird aufgerufen, auch wenn doc.save() eine Exception wirft."""
        doc_mock, _ = _make_doc_mock(widgets=[])
        doc_mock.save.side_effect = OSError("Disk voll")
        fitz_stub = _make_fitz_stub(doc_mock)
        builder = self._builder()
        with patch.object(_builder_mod, 'fitz', fitz_stub, create=True), \
             patch.object(_builder_mod, 'PYMUPDF_AVAILABLE', True):
            result = builder.fill_form("test.pdf", "out.pdf", {})
        self.assertFalse(result)
        doc_mock.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
