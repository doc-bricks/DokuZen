#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für das erweiterte Kontextmenü im DocumentListPanel (DokuZen).

Validiert:
1. Kontextmenü-Aktionen bei Einzelauswahl einer PDF (Annotieren, Seiten verwalten,
   Schwärzen, OCR, Signatur).
2. Kontextmenü-Aktionen bei Mehrfachauswahl von PDFs (Merge-Aktion).
3. Ausschluss von PDF-spezifischen Aktionen bei Nicht-PDF-Dateien.
4. Korrekte Parameterübergabe an die Dialoge (_manage_pdf_pages, _redact_pdf,
   _ocr_pdf, _sign_pdf, _merge_selected_pdfs).
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QMenu

from core.library.manager import LibraryManager
from gui.panels.document_list import DocumentListPanel


class TestDocumentListContextMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.library = MagicMock(spec=LibraryManager)
        self.library.get_documents.return_value = []
        self.library.themes.get_current_theme.return_value = "TestTheme"
        self.panel = DocumentListPanel(self.library)

    def tearDown(self):
        self.panel.close()

    def test_context_menu_empty_selection_returns_none(self):
        """Wenn keine Pfade ausgewählt sind, wird kein Menü erzeugt."""
        menu = self.panel.create_context_menu([])
        self.assertIsNone(menu)

    def test_context_menu_single_pdf_actions(self):
        """Bei genau einer PDF sind alle PDF-spezifischen Aktionen verfügbar."""
        pdf_path = "C:/docs/report.pdf"
        menu = self.panel.create_context_menu([pdf_path])
        self.assertIsNotNone(menu)
        actions = [a.text() for a in menu.actions() if not a.isSeparator()]

        self.assertIn("Öffnen", actions)
        self.assertIn("Als Sammel-PDF exportieren...", actions)
        self.assertIn("PDF annotieren...", actions)
        self.assertIn("PDF-Seiten verwalten...", actions)
        self.assertIn("PDF schwärzen...", actions)
        self.assertIn("OCR-Texterkennung...", actions)
        self.assertIn("PDF-Signatur einbetten...", actions)
        self.assertNotIn("Ausgewählte PDFs zusammenführen...", actions)

    def test_context_menu_multiple_pdf_actions(self):
        """Bei mehreren ausgewählten PDFs erscheint die Option zum Zusammenführen."""
        pdf_paths = ["C:/docs/part1.pdf", "C:/docs/part2.pdf"]
        menu = self.panel.create_context_menu(pdf_paths)
        self.assertIsNotNone(menu)
        actions = [a.text() for a in menu.actions() if not a.isSeparator()]

        self.assertIn("Ausgewählte PDFs zusammenführen...", actions)
        self.assertNotIn("PDF-Seiten verwalten...", actions)
        self.assertNotIn("PDF schwärzen...", actions)
        self.assertNotIn("OCR-Texterkennung...", actions)
        self.assertNotIn("PDF-Signatur einbetten...", actions)

    def test_context_menu_non_pdf_file_omits_pdf_actions(self):
        """Bei Text- oder Bilddateien fehlen PDF-spezifischen Aktionen."""
        txt_path = "C:/docs/notes.txt"
        menu = self.panel.create_context_menu([txt_path])
        self.assertIsNotNone(menu)
        actions = [a.text() for a in menu.actions() if not a.isSeparator()]

        self.assertIn("Öffnen", actions)
        self.assertIn("Als Sammel-PDF exportieren...", actions)
        self.assertNotIn("PDF annotieren...", actions)
        self.assertNotIn("PDF-Seiten verwalten...", actions)
        self.assertNotIn("PDF schwärzen...", actions)
        self.assertNotIn("OCR-Texterkennung...", actions)
        self.assertNotIn("PDF-Signatur einbetten...", actions)
        self.assertNotIn("Ausgewählte PDFs zusammenführen...", actions)

    def test_manage_pdf_pages_invokes_dialog(self):
        """_manage_pdf_pages öffnet PDFPagesDialog mit dem gewählten Pfad."""
        with patch("gui.dialogs.pdf_pages_dialog.PDFPagesDialog.__init__", return_value=None) as mock_init, \
             patch("gui.dialogs.pdf_pages_dialog.PDFPagesDialog.exec", return_value=0), \
             patch.object(self.panel, "refresh") as mock_refresh:
            self.panel._manage_pdf_pages("C:/docs/sample.pdf")
            mock_init.assert_called_once_with(self.panel, pdf_path="C:/docs/sample.pdf")
            mock_refresh.assert_called_once()

    def test_redact_pdf_invokes_dialog(self):
        """_redact_pdf öffnet RedactionDialog mit initial_file."""
        with patch("gui.dialogs.redaction_dialog.RedactionDialog.__init__", return_value=None) as mock_init, \
             patch("gui.dialogs.redaction_dialog.RedactionDialog.exec", return_value=0), \
             patch.object(self.panel, "refresh") as mock_refresh:
            self.panel._redact_pdf("C:/docs/sample.pdf")
            mock_init.assert_called_once_with(self.panel, initial_file="C:/docs/sample.pdf")
            mock_refresh.assert_called_once()

    def test_ocr_pdf_invokes_dialog(self):
        """_ocr_pdf öffnet OCRDialog mit initial_file."""
        with patch("gui.dialogs.ocr_dialog.OCRDialog.__init__", return_value=None) as mock_init, \
             patch("gui.dialogs.ocr_dialog.OCRDialog.exec", return_value=0), \
             patch.object(self.panel, "refresh") as mock_refresh:
            self.panel._ocr_pdf("C:/docs/sample.pdf")
            mock_init.assert_called_once_with(self.panel, initial_file="C:/docs/sample.pdf")
            mock_refresh.assert_called_once()

    def test_sign_pdf_invokes_dialog(self):
        """_sign_pdf öffnet SignatureOverlayDialog mit pdf_path."""
        with patch("gui.dialogs.signature_overlay_dialog.SignatureOverlayDialog.__init__", return_value=None) as mock_init, \
             patch("gui.dialogs.signature_overlay_dialog.SignatureOverlayDialog.exec", return_value=0), \
             patch.object(self.panel, "refresh") as mock_refresh:
            self.panel._sign_pdf("C:/docs/sample.pdf")
            mock_init.assert_called_once_with(self.panel, pdf_path="C:/docs/sample.pdf")
            mock_refresh.assert_called_once()

    def test_merge_selected_pdfs_invokes_workshop_merge_tab(self):
        """_merge_selected_pdfs öffnet PDFWorkshopDialog mit Tab 0 (Merge)."""
        paths = ["C:/docs/a.pdf", "C:/docs/b.pdf"]
        with patch("gui.dialogs.pdf_workshop.PDFWorkshopDialog.__init__", return_value=None) as mock_init, \
             patch("gui.dialogs.pdf_workshop.PDFWorkshopDialog.exec", return_value=0), \
             patch.object(self.panel, "refresh") as mock_refresh:
            self.panel._merge_selected_pdfs(paths)
            mock_init.assert_called_once_with(self.panel, initial_files=paths)
            mock_refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()
