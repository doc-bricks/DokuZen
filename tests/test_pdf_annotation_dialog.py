#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-Tests für PDFAnnotationDialog (gui/dialogs/pdf_annotation_dialog.py).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from core.pdf.annotations import PYMUPDF_AVAILABLE
if PYMUPDF_AVAILABLE:
    import fitz

from gui.dialogs.pdf_annotation_dialog import PDFAnnotationDialog


def create_sample_pdf(path: str, pages: int = 2) -> None:
    """Erzeugt eine Test-PDF mit definierter Seitenanzahl und Text."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"DokuZen Test Dokument Seite {i + 1}")
        page.insert_text((72, 120), "Suchbegriff zum Markieren")
    doc.save(path)
    doc.close()


@unittest.skipUnless(PYMUPDF_AVAILABLE, "PyMuPDF nicht verfügbar")
class TestPDFAnnotationDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.temp_dir.name, "test_doc.pdf")
        create_sample_pdf(self.pdf_path, pages=2)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_without_pdf(self):
        dialog = PDFAnnotationDialog()
        self.assertEqual(dialog.windowTitle(), "PDF-Annotationen verwalten")
        self.assertFalse(dialog._btn_add_annot.isEnabled())
        self.assertFalse(dialog._btn_delete_selected.isEnabled())
        self.assertEqual(dialog._current_doc_pages, 0)
        dialog.close()

    def test_init_with_valid_pdf(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        self.assertEqual(dialog._current_doc_pages, 2)
        self.assertEqual(dialog._page_spin.maximum(), 2)
        self.assertTrue(dialog._btn_add_annot.isEnabled())
        self.assertIn("Seite 1 von 2", dialog._lbl_page_info.text())
        dialog.close()

    def test_output_mode_toggle(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        self.assertTrue(dialog._radio_inplace.isChecked())
        self.assertFalse(dialog._output_path.isEnabled())
        self.assertFalse(dialog._btn_browse_output.isEnabled())

        dialog._radio_new_file.setChecked(True)
        self.assertTrue(dialog._output_path.isEnabled())
        self.assertTrue(dialog._btn_browse_output.isEnabled())

        dialog._radio_inplace.setChecked(True)
        self.assertFalse(dialog._output_path.isEnabled())
        self.assertFalse(dialog._btn_browse_output.isEnabled())
        dialog.close()

    def test_add_highlight_annotation(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        signals_received = []
        dialog.annotations_changed.connect(signals_received.append)

        # Tab 0: Marker, Search text
        dialog._tab_widget.setCurrentIndex(0)
        dialog._marker_search_text.setText("Suchbegriff")
        dialog._add_current_annotation()

        self.assertGreaterEqual(len(signals_received), 1)
        self.assertGreaterEqual(len(dialog._loaded_annotations), 1)
        self.assertEqual(dialog._table_annots.rowCount(), 1)
        self.assertEqual(dialog._table_annots.item(0, 1).text(), "HIGHLIGHT")
        dialog.close()

    def test_add_note_annotation(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        dialog._tab_widget.setCurrentIndex(1)
        dialog._note_author.setText("Tester")
        dialog._note_text.setPlainText("Testkommentar")
        dialog._add_current_annotation()

        self.assertGreaterEqual(len(dialog._loaded_annotations), 1)
        ann = dialog._loaded_annotations[-1]
        self.assertEqual(ann.author, "Tester")
        self.assertIn("Testkommentar", ann.content)
        dialog.close()

    def test_add_freetext_and_stamp_and_shape(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        
        # Freitext
        dialog._tab_widget.setCurrentIndex(2)
        dialog._ft_text.setText("Freitext Overlay")
        dialog._add_current_annotation()

        # Stempel
        dialog._tab_widget.setCurrentIndex(3)
        dialog._combo_stamp_pos.setCurrentIndex(1)  # Oben links
        dialog._add_current_annotation()

        # Form
        dialog._tab_widget.setCurrentIndex(4)
        dialog._combo_shape_type.setCurrentIndex(0)  # Rechteck
        dialog._add_current_annotation()

        self.assertGreaterEqual(len(dialog._loaded_annotations), 3)
        dialog.close()

    def test_delete_selected_annotation(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        # Add a note
        dialog._tab_widget.setCurrentIndex(1)
        dialog._note_text.setPlainText("Zu löschen")
        dialog._add_current_annotation()
        self.assertEqual(len(dialog._loaded_annotations), 1)

        # Select first row in table
        dialog._table_annots.selectRow(0)
        dialog._delete_selected_annotation()

        self.assertEqual(len(dialog._loaded_annotations), 0)
        self.assertEqual(dialog._table_annots.rowCount(), 0)
        dialog.close()

    def test_delete_all_annotations(self):
        dialog = PDFAnnotationDialog(pdf_path=self.pdf_path)
        # Add two annotations
        dialog._tab_widget.setCurrentIndex(1)
        dialog._note_text.setPlainText("Notiz 1")
        dialog._add_current_annotation()
        dialog._note_text.setPlainText("Notiz 2")
        dialog._add_current_annotation()
        self.assertEqual(len(dialog._loaded_annotations), 2)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            dialog._delete_all_annotations()

        self.assertEqual(len(dialog._loaded_annotations), 0)
        self.assertEqual(dialog._table_annots.rowCount(), 0)
        dialog.close()

    def test_accessibility_compliance(self):
        dialog = PDFAnnotationDialog()

        # Every input and button must have non-empty accessible name and tooltip
        widgets = [
            dialog._input_path,
            dialog._btn_browse_input,
            dialog._page_spin,
            dialog._radio_inplace,
            dialog._radio_new_file,
            dialog._output_path,
            dialog._btn_browse_output,
            dialog._check_current_page_only,
            dialog._table_annots,
            dialog._btn_delete_selected,
            dialog._btn_delete_page,
            dialog._btn_delete_all,
            dialog._combo_marker_type,
            dialog._combo_marker_color,
            dialog._marker_search_text,
            dialog._marker_comment,
            dialog._note_author,
            dialog._note_text,
            dialog._ft_text,
            dialog._combo_stamp_type,
            dialog._combo_stamp_pos,
            dialog._combo_shape_type,
            dialog._btn_add_annot,
            dialog._btn_close,
        ]

        for w in widgets:
            self.assertTrue(len(w.accessibleName().strip()) > 0, f"Missing accessibleName for {w}")
            self.assertTrue(len(w.toolTip().strip()) > 0, f"Missing toolTip for {w}")

        dialog.close()


if __name__ == "__main__":
    unittest.main()
