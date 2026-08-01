#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFMerger — fitz-Dokumente werden auch bei Exception geschlossen.

Bugfix: merge(), split(), delete_pages(), rotate_pages() schlossen Dokumente
        nur auf dem Erfolgspfad.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call, PropertyMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE = PROJECT_ROOT / "core" / "pdf" / "merger.py"


def _make_merger():
    import core.pdf.merger as m_mod
    merger = m_mod.PDFMerger.__new__(m_mod.PDFMerger)
    import logging
    merger._logger = logging.getLogger("test")
    return merger


class TestPDFMergerDocClose(unittest.TestCase):

    def test_merge_closes_output_doc_on_save_error(self):
        """output_doc.close() wird aufgerufen wenn save() wirft."""
        import core.pdf.merger as m_mod

        output_doc = MagicMock()
        output_doc.save.side_effect = IOError("disk full")
        output_doc.page_count = 1  # damit total_pages > 0

        src_doc = MagicMock()
        src_doc.is_encrypted = False
        src_doc.page_count = 1

        call_count = [0]
        def fitz_open_side_effect(path=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return output_doc
            return src_doc

        fitz_stub = MagicMock()
        fitz_stub.open.side_effect = fitz_open_side_effect

        merger = _make_merger()

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True), \
             patch.object(m_mod.Path, 'exists', return_value=True):
            items = [m_mod.MergeItem(path='test.pdf')]
            result = merger.merge(items, 'out.pdf')

        self.assertFalse(result.success)
        output_doc.close.assert_called_once_with()

    def test_merge_closes_src_doc_on_insert_error(self):
        """src_doc.close() wird aufgerufen wenn insert_pdf() wirft."""
        import core.pdf.merger as m_mod

        output_doc = MagicMock()
        output_doc.insert_pdf.side_effect = RuntimeError("corrupt page")

        src_doc = MagicMock()
        src_doc.is_encrypted = False
        src_doc.page_count = 1

        call_count = [0]
        def fitz_open_side_effect(path=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return output_doc
            return src_doc

        fitz_stub = MagicMock()
        fitz_stub.open.side_effect = fitz_open_side_effect

        merger = _make_merger()

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True), \
             patch.object(m_mod.Path, 'exists', return_value=True):
            items = [m_mod.MergeItem(path='test.pdf')]
            result = merger.merge(items, 'out.pdf')

        self.assertFalse(result.success)
        src_doc.close.assert_called_once_with()
        output_doc.close.assert_called_once_with()

    def test_split_closes_src_doc_on_error(self):
        """src_doc.close() wird aufgerufen wenn ein Fehler in split() auftritt."""
        import core.pdf.merger as m_mod

        src_doc = MagicMock()
        src_doc.page_count = 2
        # new_doc.save() wirft
        new_doc = MagicMock()
        new_doc.save.side_effect = IOError("write error")

        call_count = [0]
        def fitz_open_side_effect(path=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return src_doc
            return new_doc

        fitz_stub = MagicMock()
        fitz_stub.open.side_effect = fitz_open_side_effect

        merger = _make_merger()

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True), \
             patch.object(m_mod.Path, 'mkdir', return_value=None):
            results = merger.split('test.pdf', '/tmp/out', pages_per_file=2)

        src_doc.close.assert_called_once_with()
        new_doc.close.assert_called_once_with()
        self.assertTrue(any(not r.success for r in results))

    def test_rotate_closes_doc_on_save_error(self):
        """doc.close() wird aufgerufen wenn save() in rotate_pages() wirft."""
        import core.pdf.merger as m_mod

        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.rotation = 0
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_doc.save.side_effect = IOError("disk full")

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        merger = _make_merger()

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True):
            result = merger.rotate_pages('in.pdf', 'out.pdf', rotation=90)

        self.assertFalse(result.success)
        mock_doc.close.assert_called_once_with()

    def test_delete_pages_closes_doc_on_success(self):
        """src_doc.close() wird auch bei erfolgreicher delete_pages() aufgerufen."""
        import core.pdf.merger as m_mod

        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.page_count = 3

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        merger = _make_merger()
        # extract_pages delegates to merge — mock it to avoid real fitz calls
        merger.extract_pages = MagicMock(return_value=m_mod.MergeResult(True, 'out.pdf', 2))

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True):
            result = merger.delete_pages('in.pdf', 'out.pdf', pages_to_delete=[2])

        mock_doc.close.assert_called_once_with()
        self.assertTrue(result.success)


class TestPDFMergerZeroPageGuard(unittest.TestCase):
    """
    Bug #32: `if doc:` vs `if doc is not None:` — 0-Seiten-Dokumente wurden nie geschlossen.

    Prämisse: bool(fitz.open()) == False für ein 0-Seiten-Dokument.
    Fix: alle 6 finally-Guards in merger.py auf `is not None` umgestellt.
    """

    def _make_zero_page_mock(self):
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=0)
        doc.__bool__ = MagicMock(return_value=False)
        type(doc).is_encrypted = PropertyMock(return_value=False)
        type(doc).page_count = PropertyMock(return_value=0)
        return doc

    def test_merge_closes_zero_page_output_doc_when_all_paths_missing(self):
        """output_doc.close() wird aufgerufen wenn alle Eingabedateien fehlen (output bleibt 0 Seiten)."""
        import core.pdf.merger as m_mod

        mock_output = self._make_zero_page_mock()
        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_output

        merger = _make_merger()

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True), \
             patch.object(m_mod.Path, 'exists', return_value=False):
            result = merger.merge([m_mod.MergeItem(path='missing.pdf')], 'out.pdf')

        mock_output.close.assert_called_once_with()
        self.assertFalse(result.success)

    def test_merge_closes_zero_page_src_doc(self):
        """src_doc.close() wird aufgerufen wenn src_doc ein 0-Seiten-Dokument ist."""
        import core.pdf.merger as m_mod

        mock_output = MagicMock()
        type(mock_output).page_count = PropertyMock(return_value=0)

        mock_src = self._make_zero_page_mock()

        call_count = [0]
        def fitz_side(path=None):
            call_count[0] += 1
            return mock_output if call_count[0] == 1 else mock_src

        fitz_stub = MagicMock()
        fitz_stub.open.side_effect = fitz_side

        merger = _make_merger()

        with patch.object(m_mod, 'fitz', fitz_stub, create=True), \
             patch.object(m_mod, 'PYMUPDF_AVAILABLE', True), \
             patch.object(m_mod.Path, 'exists', return_value=True):
            merger.merge([m_mod.MergeItem(path='zero.pdf')], 'out.pdf')

        mock_src.close.assert_called_once_with()

    def test_source_guard_count(self):
        """Alle 6 Guards in merger.py verwenden `is not None`."""
        source = SOURCE.read_text(encoding="utf-8")
        count = source.count("is not None:")
        self.assertGreaterEqual(count, 6,
            f"Erwartet ≥6 `is not None:`-Guards, gefunden: {count}")

    def test_no_falsy_guards_remain(self):
        """Kein `if doc:`, `if src_doc:`, `if output_doc:`, `if new_doc:` darf noch vorkommen."""
        source = SOURCE.read_text(encoding="utf-8")
        for guard in ("if output_doc:", "if src_doc:", "if new_doc:"):
            self.assertNotIn(guard, source, f"Falsy Guard gefunden: {guard}")


if __name__ == "__main__":
    unittest.main()
