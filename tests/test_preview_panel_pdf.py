#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PreviewPanel._show_pdf — doc.close() wird auch bei Exceptions aufgerufen.

Bugfix: doc.close() stand nach dem if-Block, wurde bei Exceptions im Render-Pfad
        (z. B. page.get_pixmap()) übersprungen → Datei blieb geöffnet (Resource-Leak).
"""

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication


class TestPreviewPanelPdfClose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _make_panel(self):
        from gui.panels.preview_panel import PreviewPanel
        return PreviewPanel()

    def _make_fitz_stub(self, page_count=1, pixmap_raises=None):
        """Erzeugt einen minimalen fitz-Stub für Tests."""
        pix_mock = MagicMock()
        pix_mock.samples = b"\xff\x00\x00" * 4  # 2×2 RGB
        pix_mock.width = 2
        pix_mock.height = 2
        pix_mock.stride = 6

        page_mock = MagicMock()
        if pixmap_raises:
            page_mock.get_pixmap.side_effect = pixmap_raises
        else:
            page_mock.get_pixmap.return_value = pix_mock

        doc_mock = MagicMock()
        doc_mock.page_count = page_count
        doc_mock.__getitem__ = lambda self, idx: page_mock

        fitz_stub = types.ModuleType("fitz")
        fitz_stub.open = MagicMock(return_value=doc_mock)
        fitz_stub.Matrix = MagicMock(return_value=MagicMock())
        return fitz_stub, doc_mock

    def test_doc_closed_on_success(self):
        """doc.close() wird nach erfolgreichem Rendern aufgerufen."""
        import tempfile, struct, zlib

        # Minimales gültiges PDF-Existenz — Pfad muss nur existieren
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            panel = self._make_panel()
            fitz_stub, doc_mock = self._make_fitz_stub(page_count=1)

            with patch.dict(sys.modules, {"fitz": fitz_stub}):
                panel._show_pdf(Path(pdf_path))

            doc_mock.close.assert_called_once()
        finally:
            import os
            os.unlink(pdf_path)

    def test_doc_closed_when_pixmap_raises(self):
        """doc.close() wird aufgerufen, auch wenn get_pixmap() eine Exception wirft."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            panel = self._make_panel()
            fitz_stub, doc_mock = self._make_fitz_stub(
                page_count=1,
                pixmap_raises=RuntimeError("Render-Fehler simuliert")
            )

            with patch.dict(sys.modules, {"fitz": fitz_stub}):
                # Darf nicht unkontrolliert propagieren
                panel._show_pdf(Path(pdf_path))

            doc_mock.close.assert_called_once()
        finally:
            import os
            os.unlink(pdf_path)

    def test_doc_closed_when_page_count_zero(self):
        """doc.close() wird auch aufgerufen, wenn page_count == 0."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            panel = self._make_panel()
            fitz_stub, doc_mock = self._make_fitz_stub(page_count=0)

            with patch.dict(sys.modules, {"fitz": fitz_stub}):
                panel._show_pdf(Path(pdf_path))

            doc_mock.close.assert_called_once()
        finally:
            import os
            os.unlink(pdf_path)


if __name__ == "__main__":
    unittest.main()
