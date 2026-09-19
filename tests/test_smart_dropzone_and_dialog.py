#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Test Suite: Smart Dropzone & Ingest Dialog
===================================================
UI- und Interaktionstests für SmartDropzoneWidget und SmartIngestDialog.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QUrl, QMimeData, QPointF
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QComboBox

from core.library.manager import LibraryManager
from core.ingest.models import IngestAction
from gui.widgets.dropzone import SmartDropzoneWidget
from gui.dialogs.smart_ingest_dialog import SmartIngestDialog


class TestSmartDropzoneWidget(unittest.TestCase):
    """Tests für das SmartDropzoneWidget."""

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_widget_properties_and_accessibility(self):
        widget = SmartDropzoneWidget(compact=False)
        self.assertIsNotNone(widget)
        self.assertTrue(widget.acceptDrops())
        self.assertEqual(widget.accessibleName(), "Smart Ingest Dropzone")
        self.assertIn("Eingabetaste", widget.accessibleDescription())

        # Compact mode toggle
        widget.set_compact_mode(True)
        self.assertTrue(widget._compact)
        widget.close()

    def test_drop_event_emits_files(self):
        widget = SmartDropzoneWidget()
        dropped_files = []
        widget.files_dropped.connect(lambda paths: dropped_files.extend(paths))

        temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        temp.close()
        temp_path = temp.name

        try:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(temp_path)])

            drop_event = QDropEvent(
                QPointF(10, 10),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            widget.dropEvent(drop_event)

            self.assertEqual(len(dropped_files), 1)
            self.assertEqual(os.path.normpath(dropped_files[0]), os.path.normpath(temp_path))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            widget.close()


class TestSmartIngestDialog(unittest.TestCase):
    """Tests für den SmartIngestDialog und dessen Workflow."""

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.state_file = self.root / "state.json"

        self.library = LibraryManager(state_file=str(self.state_file))

    def tearDown(self):
        self.library.shutdown()
        self.temp_dir.cleanup()

    def test_dialog_lifecycle_and_candidate_loading(self):
        f1 = self.root / "doc1.pdf"
        f1.write_bytes(b"%PDF-1.4 test")
        f2 = self.root / "doc2.txt"
        f2.write_text("sample content", encoding="utf-8")

        dialog = SmartIngestDialog(
            library_manager=self.library,
            initial_paths=[str(f1), str(f2)]
        )

        self.assertEqual(dialog.table.rowCount(), 2)
        self.assertIn("2", dialog.lbl_count.text())
        self.assertTrue(dialog.btn_start.isEnabled())

        # Test ComboBox widget in Table for Row 0
        action_combo = dialog.table.cellWidget(0, 2)
        self.assertIsInstance(action_combo, QComboBox)

        # Toggle auto-convert
        dialog.chk_auto_convert.setChecked(False)
        # Should now be direct import for txt if not auto converting
        dialog.chk_auto_convert.setChecked(True)

        # Test remove selection
        dialog.table.selectRow(0)
        dialog._on_remove_selected()
        self.assertEqual(dialog.table.rowCount(), 1)

        # Test clear all
        dialog._on_clear_all()
        self.assertEqual(dialog.table.rowCount(), 0)
        self.assertFalse(dialog.btn_start.isEnabled())

        dialog.close()

    def test_dialog_ingest_execution(self):
        f1 = self.root / "imported.pdf"
        f1.write_bytes(b"%PDF-1.4 test execution")

        dialog = SmartIngestDialog(
            library_manager=self.library,
            initial_paths=[str(f1)]
        )

        results_emitted = []
        dialog.ingest_finished.connect(lambda summary: results_emitted.append(summary))

        dialog._on_start_ingest()

        self.assertEqual(len(results_emitted), 1)
        summary = results_emitted[0]
        self.assertEqual(summary.added_count, 1)
        self.assertIn("1", dialog.lbl_status.text())

        # Table row 0 status should show success
        status_item = dialog.table.item(0, 4)
        self.assertIsNotNone(status_item)
        self.assertIn("importiert", status_item.text())

        dialog.close()


if __name__ == "__main__":
    unittest.main()
