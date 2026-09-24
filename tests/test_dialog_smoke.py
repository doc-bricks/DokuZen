import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from gui.dialogs.code_analysis_dialog import CodeAnalysisDialog
from gui.dialogs.collection_export_dialog import CollectionExportDialog
from gui.dialogs.convert_dialog import ConvertDialog
from gui.dialogs.form_builder_dialog import FormBuilderDialog
from gui.dialogs.image_converter_dialog import ImageConverterDialog
from gui.dialogs.ocr_dialog import OCRDialog
from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog, PageThumbnail
from gui.dialogs.pdf_annotation_dialog import PDFAnnotationDialog
from gui.dialogs.pdf_pages_dialog import PDFPagesDialog
from gui.dialogs.pdf_workshop import PDFWorkshopDialog
from gui.dialogs.pyinstaller_dialog import PyInstallerDialog
from gui.dialogs.redaction_dialog import RedactionDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.signature_overlay_dialog import SignatureOverlayDialog
from gui.dialogs.text_pool_dialog import TextPoolDialog
from gui.dialogs.smart_ingest_dialog import SmartIngestDialog
from gui.dialogs.sqlite_viewer_dialog import SQLiteViewerDialog


class DialogSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_convert_dialog_instantiates(self):
        dialog = ConvertDialog()
        self.assertIsNotNone(dialog)
        dialog.close()

    def test_redaction_dialog_instantiates(self):
        dialog = RedactionDialog()
        self.assertIsNotNone(dialog)
        dialog.close()

    def test_ocr_dialog_instantiates(self):
        dialog = OCRDialog()
        self.assertIsNotNone(dialog)
        dialog.close()

    def test_text_pool_dialog_instantiates(self):
        dialog = TextPoolDialog()
        self.assertIsNotNone(dialog)
        dialog.close()

    def test_signature_overlay_dialog_instantiates_with_existing_check_enabled(self):
        dialog = SignatureOverlayDialog()
        self.assertIsNotNone(dialog)
        self.assertTrue(dialog._detect_existing_check.isChecked())
        dialog.close()

    def test_pdf_marker_page_notation_controls_expose_accessible_context(self):
        dialog = PDFMarkerDialog()
        self.assertIsNotNone(dialog)

        self.assertEqual(dialog._page_notation.toolTip(), "Wendet Seiten per Textnotation auf eine Markierungsart an.")
        self.assertEqual(dialog._page_notation.accessibleName(), "Seiten-Notation")
        self.assertEqual(
            dialog._page_notation.accessibleDescription(),
            "Eingabefeld für Seitenangaben wie 1-5, 7 oder 9-12.",
        )

        self.assertEqual(
            dialog._notation_marker.toolTip(),
            "Legt fest, ob die Seiten als Auszug, Entfernen oder Behalten markiert werden.",
        )
        self.assertEqual(
            dialog._notation_marker.accessibleName(),
            "Markierungsart für Seiten-Notation",
        )
        self.assertEqual(
            dialog._notation_marker.accessibleDescription(),
            "Wählt die Zielmarkierung für die eingegebene Seiten-Notation.",
        )

        apply_button = next(
            button
            for button in dialog.findChildren(QPushButton)
            if button.text() == "Notation anwenden"
        )
        self.assertEqual(
            apply_button.toolTip(),
            "Überträgt die Seiten-Notation auf die gewählte Markierungsart.",
        )
        self.assertEqual(apply_button.accessibleName(), "Seiten-Notation anwenden")
        self.assertEqual(
            apply_button.accessibleDescription(),
            "Markiert die eingegebenen Seiten als Auszug, Entfernen oder Behalten.",
        )

        dialog.close()

    def test_pdf_marker_crop_margin_exposes_accessible_context(self):
        dialog = PDFMarkerDialog()

        self.assertEqual(
            dialog._crop_margin_mm.toolTip(),
            "Legt den Beschnittrand für exportierte Seiten in Millimetern fest.",
        )
        self.assertEqual(dialog._crop_margin_mm.accessibleName(), "Beschnittrand")
        self.assertEqual(
            dialog._crop_margin_mm.accessibleDescription(),
            "Bestimmt den gleichmäßigen Beschnittrand der exportierten Seiten in Millimetern.",
        )

        dialog.close()

    def test_pdf_marker_thumbnail_is_keyboard_accessible(self):
        thumbnail = PageThumbnail(0)
        selected_pages = []
        thumbnail.clicked.connect(selected_pages.append)

        self.assertEqual(thumbnail.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        self.assertEqual(thumbnail.accessibleName(), "Seite 1, nicht markiert")
        self.assertEqual(
            thumbnail.accessibleDescription(),
            "Seite 1, nicht markiert. Mit Enter oder Leertaste für eine Aktion auswählen.",
        )
        self.assertEqual(
            thumbnail.toolTip(),
            "Seite 1, nicht markiert. Mit Enter oder Leertaste auswählen.",
        )

        thumbnail.show()
        thumbnail.setFocus()
        QTest.keyClick(thumbnail, Qt.Key.Key_Return)
        QTest.keyClick(thumbnail, Qt.Key.Key_Space)

        self.assertEqual(selected_pages, [0, 0])
        thumbnail.close()

    def test_settings_dialog_compact_browse_buttons_expose_accessible_context(self):
        dialog = SettingsDialog(settings={})
        self.assertIsNotNone(dialog)

        browse_buttons = {
            button.accessibleName(): (
                button.toolTip(),
                button.accessibleDescription(),
            )
            for button in dialog.findChildren(QPushButton)
            if button.text() == "..."
        }

        self.assertEqual(
            browse_buttons,
            {
                "Bibliotheksordner auswählen": (
                    "Bibliotheksordner auswählen",
                    "Öffnet den Ordnerdialog für den Speicherort der DokuZen-Bibliothek.",
                ),
                "Export-Ordner auswählen": (
                    "Export-Ordner auswählen",
                    "Öffnet den Ordnerdialog für den Standardpfad exportierter Dateien.",
                ),
                "Spawner-Ordner auswählen": (
                    "Spawner-Ordner auswählen",
                    "Öffnet den Ordnerdialog für den Ablageordner des TextSpawners.",
                ),
                "Tesseract-Datei auswählen": (
                    "Tesseract-Datei auswählen",
                    "Öffnet den Dateidialog für die ausführbare Tesseract-OCR-Datei.",
                ),
            },
        )

        dialog.close()

    def test_collection_export_dialog_instantiates(self):
        dialog = CollectionExportDialog()
        self.assertIsNotNone(dialog)
        self.assertTrue(dialog._check_bookmarks.isChecked())
        self.assertFalse(dialog._check_numbers.isChecked())
        self.assertEqual(dialog._list_widget.count(), 0)
        self.assertEqual(dialog._check_bookmarks.accessibleName(), "Lesezeichen erstellen")
        dialog.close()

    def test_smart_ingest_dialog_instantiates(self):
        dialog = SmartIngestDialog()
        self.assertIsNotNone(dialog)
        self.assertTrue(dialog.chk_auto_convert.isChecked())
        self.assertTrue(dialog.chk_skip_dupes.isChecked())
        self.assertTrue(dialog.chk_recursive.isChecked())
        self.assertEqual(dialog.table.rowCount(), 0)
        dialog.close()

    def test_pdf_annotation_dialog_instantiates(self):
        dialog = PDFAnnotationDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "PDF-Annotationen verwalten")
        self.assertTrue(dialog._radio_inplace.isChecked())
        self.assertEqual(dialog._table_annots.columnCount(), 5)
        self.assertEqual(dialog._tab_widget.count(), 5)
        dialog.close()

    def test_code_analysis_dialog_instantiates(self):
        dialog = CodeAnalysisDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "Python Code-Analyse")
        dialog.close()

    def test_form_builder_dialog_instantiates(self):
        dialog = FormBuilderDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "Formular-Builder")
        dialog.close()

    def test_image_converter_dialog_instantiates(self):
        dialog = ImageConverterDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "Bild-Werkzeuge")
        dialog.close()

    def test_pdf_pages_dialog_instantiates(self):
        dialog = PDFPagesDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "PDF-Seiten verwalten")
        dialog.close()

    def test_pdf_workshop_dialog_instantiates(self):
        dialog = PDFWorkshopDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "PDF-Werkstatt")
        dialog.close()

    def test_pyinstaller_dialog_instantiates(self):
        dialog = PyInstallerDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "Python Kompilator")
        dialog.close()

    def test_sqlite_viewer_dialog_instantiates(self):
        dialog = SQLiteViewerDialog()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "SQLite Viewer")
        dialog.close()


if __name__ == "__main__":
    unittest.main()
