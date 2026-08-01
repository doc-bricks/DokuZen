#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFAnnotator — fitz-Dokument wird auch bei Exception geschlossen.

Bugfix 1: Alle 13 Methoden schlossen doc nur auf dem Erfolgspfad.
          Bei Exception im try-Block blieb das Dokument offen.
Bugfix 2 (#33): `if doc:` schließt 0-Seiten-PDFs nie (bool(doc)==False).
          Korrekt: `if doc is not None:` — alle 13 Guards korrigiert.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

SOURCE = Path(__file__).resolve().parents[1] / "core" / "pdf" / "annotations.py"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_mock_doc(raise_on_save=False, raise_on_page=False):
    """Erstellt ein Mock-fitz-Dokument."""
    doc = MagicMock()
    page = MagicMock()
    doc.__getitem__ = MagicMock(return_value=page)
    doc.__iter__ = MagicMock(return_value=iter([]))
    if raise_on_save:
        doc.save.side_effect = RuntimeError("save failed")
    if raise_on_page:
        doc.__getitem__.side_effect = IndexError("page out of range")
    return doc, page


class TestPDFAnnotatorDocClose(unittest.TestCase):
    """Verifiziert, dass doc.close() immer aufgerufen wird."""

    def _test_method_closes_doc(self, method_name, kwargs, raise_on_save=False):
        """Hilfsmethode: ruft Methode auf und prüft ob doc.close() aufgerufen wurde."""
        import core.pdf.annotations as ann_mod

        mock_doc, mock_page = _make_mock_doc(raise_on_save=raise_on_save)
        mock_annot = MagicMock()
        mock_page.add_highlight_annot.return_value = mock_annot
        mock_page.add_underline_annot.return_value = mock_annot
        mock_page.add_strikeout_annot.return_value = mock_annot
        mock_page.add_text_annot.return_value = mock_annot
        mock_page.add_freetext_annot.return_value = mock_annot
        mock_page.add_stamp_annot.return_value = mock_annot
        mock_page.add_rect_annot.return_value = mock_annot
        mock_page.add_circle_annot.return_value = mock_annot
        mock_page.add_line_annot.return_value = mock_annot
        mock_page.add_ink_annot.return_value = mock_annot

        if not ann_mod.PYMUPDF_AVAILABLE:
            self.skipTest("PyMuPDF nicht installiert")

        annotator = ann_mod.PDFAnnotator.__new__(ann_mod.PDFAnnotator)
        import logging
        annotator._logger = logging.getLogger("test")

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc
        fitz_stub.Rect = MagicMock(side_effect=lambda x: x)
        fitz_stub.Point = MagicMock(side_effect=lambda x: x)

        # Annotationstyp-Konstanten (für _map_annot_type, nicht direkt genutzt hier)
        for attr in ['PDF_ANNOT_HIGHLIGHT', 'PDF_ANNOT_UNDERLINE', 'PDF_ANNOT_STRIKE_OUT',
                     'PDF_ANNOT_SQUIGGLY', 'PDF_ANNOT_TEXT', 'PDF_ANNOT_FREE_TEXT',
                     'PDF_ANNOT_STAMP', 'PDF_ANNOT_SQUARE', 'PDF_ANNOT_CIRCLE',
                     'PDF_ANNOT_LINE', 'PDF_ANNOT_INK']:
            setattr(fitz_stub, attr, 0)

        with patch.object(ann_mod, 'fitz', fitz_stub, create=True):
            method = getattr(annotator, method_name)
            method(**kwargs)

        mock_doc.close.assert_called_once_with(), \
            f"{method_name}: doc.close() wurde nicht aufgerufen"

    def test_add_highlight_closes_doc_on_success(self):
        self._test_method_closes_doc('add_highlight', {
            'pdf_path': 'in.pdf', 'output_path': 'out.pdf',
            'page_index': 0, 'rect': (0, 0, 100, 20)
        })

    def test_add_highlight_closes_doc_on_save_error(self):
        self._test_method_closes_doc('add_highlight', {
            'pdf_path': 'in.pdf', 'output_path': 'out.pdf',
            'page_index': 0, 'rect': (0, 0, 100, 20)
        }, raise_on_save=True)

    def test_add_underline_closes_doc_on_success(self):
        self._test_method_closes_doc('add_underline', {
            'pdf_path': 'in.pdf', 'output_path': 'out.pdf',
            'page_index': 0, 'rect': (0, 0, 100, 20)
        })

    def test_add_strikeout_closes_doc_on_success(self):
        self._test_method_closes_doc('add_strikeout', {
            'pdf_path': 'in.pdf', 'output_path': 'out.pdf',
            'page_index': 0, 'rect': (0, 0, 100, 20)
        })

    def test_add_stamp_closes_doc_on_success(self):
        import core.pdf.annotations as ann_mod
        self._test_method_closes_doc('add_stamp', {
            'pdf_path': 'in.pdf', 'output_path': 'out.pdf',
            'page_index': 0, 'rect': (0, 0, 200, 80),
            'stamp_type': ann_mod.StampType.APPROVED
        })

    def test_remove_all_annotations_closes_doc_on_success(self):
        import core.pdf.annotations as ann_mod

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))

        annotator = ann_mod.PDFAnnotator.__new__(ann_mod.PDFAnnotator)
        import logging
        annotator._logger = logging.getLogger("test")

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        with patch.object(ann_mod, 'fitz', fitz_stub, create=True):
            annotator.remove_all_annotations('in.pdf', 'out.pdf')

        mock_doc.close.assert_called_once_with()

    def test_remove_all_annotations_closes_doc_on_save_error(self):
        import core.pdf.annotations as ann_mod

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_doc.save.side_effect = RuntimeError("disk full")

        annotator = ann_mod.PDFAnnotator.__new__(ann_mod.PDFAnnotator)
        import logging
        annotator._logger = logging.getLogger("test")

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        with patch.object(ann_mod, 'fitz', fitz_stub, create=True):
            result = annotator.remove_all_annotations('in.pdf', 'out.pdf')

        self.assertFalse(result)
        mock_doc.close.assert_called_once_with()


class TestPDFAnnotatorZeroPageGuard(unittest.TestCase):
    """Bug #33: `if doc:` → `if doc is not None:` in allen 13 Annotator-Methoden."""

    def test_no_falsy_doc_guard_in_source(self):
        """annotations.py darf kein `if doc:` in finally-Blöcken haben."""
        source = SOURCE.read_text(encoding="utf-8")
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "if doc:":
                self.fail(f"Falsy Guard in Zeile {i+1}: {line!r}")

    def test_is_none_guard_count(self):
        """Alle 13 Guards müssen `if doc is not None:` verwenden."""
        source = SOURCE.read_text(encoding="utf-8")
        count = source.count("if doc is not None:")
        self.assertGreaterEqual(count, 13,
            f"Erwartet ≥13 `if doc is not None:`-Guards, gefunden: {count}")

    def test_add_highlight_closes_zero_page_doc(self):
        """add_highlight() ruft doc.close() auch für ein 0-Seiten-Dokument auf."""
        import core.pdf.annotations as ann_mod

        mock_doc = MagicMock()
        mock_doc.__bool__ = MagicMock(return_value=False)
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_page = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_annot = MagicMock()
        mock_page.add_highlight_annot.return_value = mock_annot

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc
        fitz_stub.Rect = MagicMock(side_effect=lambda x: x)

        annotator = ann_mod.PDFAnnotator.__new__(ann_mod.PDFAnnotator)
        import logging
        annotator._logger = logging.getLogger("test")

        with patch.object(ann_mod, 'fitz', fitz_stub, create=True), \
             patch.object(ann_mod, 'PYMUPDF_AVAILABLE', True):
            annotator.add_highlight('in.pdf', 'out.pdf', page_index=0, rect=(0, 0, 10, 10))

        mock_doc.close.assert_called_once_with()

    def test_get_annotations_closes_zero_page_doc(self):
        """get_annotations() ruft doc.close() auch für ein 0-Seiten-Dokument auf."""
        import core.pdf.annotations as ann_mod

        mock_doc = MagicMock()
        mock_doc.__bool__ = MagicMock(return_value=False)
        mock_doc.__iter__ = MagicMock(return_value=iter([]))

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = mock_doc

        annotator = ann_mod.PDFAnnotator.__new__(ann_mod.PDFAnnotator)
        import logging
        annotator._logger = logging.getLogger("test")

        with patch.object(ann_mod, 'fitz', fitz_stub, create=True), \
             patch.object(ann_mod, 'PYMUPDF_AVAILABLE', True):
            result = annotator.get_annotations('empty.pdf')

        mock_doc.close.assert_called_once_with()
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
