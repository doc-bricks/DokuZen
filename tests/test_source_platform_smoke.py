import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from PySide6.QtWidgets import QApplication

import gui.main_window as main_window_module
from core.library.persistence import PersistenceManager
from gui.main_window import MainWindow


class SourcePlatformSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.state_file = self.tmp_path / "dokuzen_state.json"
        self.original_state_file = PersistenceManager.DEFAULT_STATE_FILE
        PersistenceManager.DEFAULT_STATE_FILE = self.state_file

        self.text_path = self.tmp_path / "Überblick_äöü.md"
        self.text_path.write_text(
            "# Überblick\n\nEin kurzer Text mit Umlauten: äöü ß.\n",
            encoding="utf-8",
        )

        self.pdf_path = self.tmp_path / "Vertrag_äöü.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "DokuZen Prüfdokument äöü")
        doc.save(self.pdf_path)
        doc.close()

        self.window = MainWindow()

    def tearDown(self):
        try:
            self.window.close()
        finally:
            PersistenceManager.DEFAULT_STATE_FILE = self.original_state_file
            self._tmp.cleanup()

    def test_startup_import_and_preview_handle_utf8_text_and_pdf(self):
        self.window.startup_import_paths((str(self.text_path), str(self.pdf_path)))

        documents = {Path(doc.path).name for doc in self.window._library.get_documents()}
        self.assertEqual(documents, {self.text_path.name, self.pdf_path.name})
        self.assertEqual(
            Path(self.window._preview_panel._current_path).name,
            self.text_path.name,
        )
        self.assertIn("äöü", self.window._preview_panel._text_widget.toPlainText())

        self.window.startup_open_path(str(self.pdf_path))

        self.assertEqual(
            Path(self.window._preview_panel._current_path).name,
            self.pdf_path.name,
        )
        self.assertEqual(self.window._preview_panel._stack.currentIndex(), 2)
        pixmap = self.window._preview_panel._image_label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())

    def test_library_add_button_exposes_accessible_context(self):
        add_button = self.window._library_panel._btn_add

        self.assertEqual(add_button.text(), "+")
        self.assertEqual(add_button.toolTip(), "Neues Thema erstellen (Ctrl+N)")
        self.assertEqual(add_button.accessibleName(), "Neues Thema erstellen")
        self.assertEqual(
            add_button.accessibleDescription(),
            "Öffnet einen Dialog zum Anlegen eines neuen Bibliotheksthemas.",
        )

    def test_search_box_exposes_accessible_context(self):
        search_box = self.window._search_box

        self.assertEqual(search_box.toolTip(), "Dokumente in der Bibliothek durchsuchen (Ctrl+F)")
        self.assertEqual(search_box.accessibleName(), "Dokumente durchsuchen")
        self.assertEqual(
            search_box.accessibleDescription(),
            "Filtert die angezeigten Dokumente beim Eingeben. Mit Ctrl+F fokussieren.",
        )

    def test_macos_external_open_uses_open(self):
        with mock.patch.object(main_window_module.sys, "platform", "darwin"):
            with mock.patch("subprocess.run") as subprocess_run:
                self.window._on_document_open(str(self.text_path))
        # BUGSWEEP-33: Produktionscode ruft external-open mit check=False, timeout=30 (subprocess-
        # Timeout-Standard, vorbestehend) — Assertion entsprechend aktualisiert (war veraltet).
        subprocess_run.assert_called_once_with(["open", str(self.text_path)], check=False, timeout=30)

    def test_linux_external_open_uses_xdg_open(self):
        with mock.patch.object(main_window_module.sys, "platform", "linux"):
            with mock.patch("subprocess.run") as subprocess_run:
                self.window._on_document_open(str(self.text_path))
        subprocess_run.assert_called_once_with(["xdg-open", str(self.text_path)], check=False, timeout=30)


if __name__ == "__main__":
    unittest.main()
