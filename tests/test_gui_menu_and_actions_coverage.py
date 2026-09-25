#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audittest für sämtliche GUI-Aktionen, Menüs, Werkzeug-Dialoge und Bedienelemente in DokuZen.
Erfüllt Nutzerauftrag U1 (Welle-1-Usertest):
Vollständiger automatisierter Funktionstest der GUI: Jede Schaltfläche, jeder Menüpunkt
und jedes Werkzeug wird ausgelöst und das fehlerfreie Verhalten verifiziert.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar, QMessageBox

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.library.manager import LibraryManager
from gui.main_window import MainWindow
from translator import get_translator


@pytest.fixture(scope="module")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_library(tmp_path):
    """Erstellt einen isolierten LibraryManager mit temporärer State-Datei."""
    state_file = tmp_path / ".dokuzen_test_state.json"
    manager = LibraryManager(state_file=state_file)
    manager.initialize()
    manager.themes.create_theme("Standard")
    manager.themes.set_current_theme("Standard")
    manager.save()
    return manager


@pytest.fixture
def main_window(qapp, temp_library):
    """Erstellt ein MainWindow-Exemplar mit isolierter Library."""
    window = MainWindow(library=temp_library)
    yield window
    window.close()


def test_menubar_structure_and_connectivity(main_window):
    """Prüft, ob alle 6 Menüs vorhanden, beschriftet und alle Actions verbunden sind."""
    menubar = main_window.menuBar()
    assert isinstance(menubar, QMenuBar)

    actions = menubar.actions()
    menu_titles = [a.text().replace("&", "") for a in actions]
    expected_menus = ["Datei", "Bearbeiten", "Ansicht", "Themen", "Werkzeuge", "Hilfe"]
    for expected in expected_menus:
        assert expected in menu_titles, f"Menü '{expected}' fehlt in Menüleiste"

    total_actions_checked = 0
    for action in actions:
        menu = action.menu()
        if menu is None:
            continue
        assert isinstance(menu, QMenu)
        for sub_action in menu.actions():
            if sub_action.isSeparator():
                continue
            assert sub_action.text().strip(), f"Action in Menü '{menu.title()}' hat keinen Text"
            assert sub_action.isEnabled(), f"Action '{sub_action.text()}' ist deaktiviert"
            total_actions_checked += 1

    assert total_actions_checked >= 20, f"Zu wenige Menü-Aktionen gefunden: {total_actions_checked}"


def test_toolbar_controls_and_search_box(main_window):
    """Prüft Toolbar-Schaltflächen, Tooltips und Suchfeld."""
    assert main_window._btn_import.text() == "Importieren"
    assert "Ctrl+I" in main_window._btn_import.toolTip()
    assert main_window._btn_smart_ingest.text() == "Smart Ingest"
    assert "Ctrl+Shift+I" in main_window._btn_smart_ingest.toolTip()
    assert main_window._btn_new_theme.text() == "Neues Thema"
    assert main_window._btn_refresh.text() == "Aktualisieren"
    assert main_window._search_box.placeholderText() == "Suchen..."
    assert main_window._search_box.accessibleName() == "Dokumente durchsuchen"

    # Suchtext-Filter Smoke
    main_window._search_box.setText("Testsuche")
    assert main_window._library._search_query == "testsuche"
    main_window._search_box.clear()
    assert main_window._library._search_query == ""


def test_all_tools_menu_actions_dispatch_cleanly(main_window, tmp_path):
    """
    Testet das saubere Auslösen aller 15 Werkzeug-Aktionen im Werkzeuge-Menü
    inklusive Dialog-Instanziierung und nachfolgendem Refresh.
    """
    # Dummy-Dateien für Selektions-Simulation
    dummy_pdf = tmp_path / "sample.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    dummy_py = tmp_path / "script.py"
    dummy_py.write_text("print('hello')", encoding="utf-8")
    dummy_txt = tmp_path / "notes.txt"
    dummy_txt.write_text("hello world", encoding="utf-8")
    dummy_db = tmp_path / "data.db"
    dummy_db.write_bytes(b"SQLite format 3\x00")

    main_window._library.add_documents([str(dummy_pdf), str(dummy_py), str(dummy_txt), str(dummy_db)])
    main_window._document_panel.refresh()

    # 1. PDF-Werkstatt
    with patch("gui.dialogs.pdf_workshop.PDFWorkshopDialog.exec", return_value=0):
        main_window._action_pdf_workshop.trigger()

    # 2. PDF Merge
    with patch("gui.dialogs.pdf_workshop.PDFWorkshopDialog.exec", return_value=0):
        main_window._action_merge.trigger()

    # 3. OCR
    with patch("gui.dialogs.ocr_dialog.OCRDialog.exec", return_value=0):
        main_window._action_ocr.trigger()

    # 4. Redaction / Schwärzen
    with patch("gui.dialogs.redaction_dialog.RedactionDialog.exec", return_value=0):
        main_window._action_redaction.trigger()

    # 5. Konvertierung
    with patch("gui.dialogs.convert_dialog.ConvertDialog.exec", return_value=0):
        main_window._action_convert.trigger()

    # 6. Text-Pooler
    with patch("gui.dialogs.text_pool_dialog.TextPoolDialog.exec", return_value=0):
        main_window._action_text_pool.trigger()

    # 7. Code-Analyse
    with patch("gui.dialogs.code_analysis_dialog.CodeAnalysisDialog.exec", return_value=0):
        main_window._action_code_analysis.trigger()

    # 8. Formular-Builder
    with patch("gui.dialogs.form_builder_dialog.FormBuilderDialog.exec", return_value=0):
        main_window._action_form_builder.trigger()

    # 9. PDF-Marker
    with patch("gui.dialogs.pdf_marker_dialog.PDFMarkerDialog.exec", return_value=0):
        main_window._action_pdf_marker.trigger()

    # 10. PDF-Seitenverwaltung
    with patch("gui.dialogs.pdf_pages_dialog.PDFPagesDialog.exec", return_value=0):
        main_window._action_pdf_pages.trigger()

    # 11. PDF-Annotationen
    with patch("gui.dialogs.pdf_annotation_dialog.PDFAnnotationDialog.exec", return_value=0):
        main_window._action_pdf_annotate.trigger()

    # 12. Signatur-Overlay
    with patch("gui.dialogs.signature_overlay_dialog.SignatureOverlayDialog.exec", return_value=0):
        main_window._action_signature_overlay.trigger()

    # 13. Bild-Werkzeuge
    with patch("gui.dialogs.image_converter_dialog.ImageConverterDialog.exec", return_value=0):
        main_window._action_image_tools.trigger()

    # 14. SQLite-Viewer
    with patch("gui.dialogs.sqlite_viewer_dialog.SQLiteViewerDialog.exec", return_value=0):
        main_window._action_sqlite_viewer.trigger()

    # 15. Python Kompilieren / PyInstaller
    with patch("gui.dialogs.pyinstaller_dialog.PyInstallerDialog.exec", return_value=0):
        main_window._action_pyinstaller.trigger()


def test_file_menu_actions_dispatch(main_window, tmp_path):
    """Testet alle Datei-Menü-Aktionen (Import, Smart Ingest, Sammel-PDF, Workspace, Einstellungen, Über)."""
    # Smart Ingest
    with patch("gui.dialogs.smart_ingest_dialog.SmartIngestDialog.exec", return_value=0):
        main_window._action_smart_ingest.trigger()

    # Sammel-PDF
    with patch("gui.dialogs.collection_export_dialog.CollectionExportDialog.exec", return_value=0):
        main_window._action_export_pdf.trigger()

    # Arbeitsbereich exportieren
    dummy_out = str(tmp_path / "workspace.json")
    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(dummy_out, "JSON (*.json)")):
        main_window._action_export_workspace.trigger()
        assert Path(dummy_out).exists()

    # Einstellungen
    with patch("gui.dialogs.settings_dialog.SettingsDialog.exec", return_value=0):
        main_window._action_settings.trigger()

    # Über DokuZen
    with patch("PySide6.QtWidgets.QMessageBox.about") as mock_about:
        main_window._action_about.trigger()
        assert mock_about.called


def test_edit_view_and_theme_actions(main_window):
    """Testet Bearbeiten-, Ansichts- und Themen-Aktionen."""
    # Suchen fokussieren
    with patch.object(main_window._search_box, "setFocus") as mock_focus, \
         patch.object(main_window._search_box, "selectAll") as mock_select:
        main_window._action_search.trigger()
        assert mock_focus.called
        assert mock_select.called

    # Alles auswählen
    main_window._action_select_all.trigger()

    # Ansicht aktualisieren
    main_window._action_refresh.trigger()

    # Vorschau umschalten
    assert not main_window._preview_panel.isHidden()
    main_window._action_toggle_preview.trigger()
    assert main_window._preview_panel.isHidden()
    main_window._action_toggle_preview.trigger()
    assert not main_window._preview_panel.isHidden()

    # Neues Thema Dialog
    with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("NeuesThemaTest", True)):
        main_window._action_new_theme.trigger()
        assert "NeuesThemaTest" in main_window._library.themes.get_theme_names()


def test_retranslate_ui_full_cycle(main_window):
    """Testet vollständigen Durchlauf von retranslate_ui über alle 6 Sprachen."""
    translator = get_translator()
    languages = ["en", "es", "zh", "ja", "ru", "de"]

    for lang in languages:
        translator.set_language(lang)
        main_window.retranslate_ui()
        assert main_window.windowTitle().startswith("DokuZen")
        assert main_window._search_box.placeholderText().strip()
        assert main_window._btn_import.text().strip()

    # Am Ende wieder auf Deutsch zurücksetzen
    translator.set_language("de")
    main_window.retranslate_ui()
    assert main_window._btn_import.text() == "Importieren"


def test_panels_buttons_and_interactions(main_window, tmp_path):
    """
    Testet alle Schaltflächen, Auswahllisten, Signale und Kontextaktionen der 3 Panels:
    LibraryPanel, DocumentListPanel und PreviewPanel.
    """
    # 1. LibraryPanel
    lib_panel = main_window._library_panel
    assert lib_panel._btn_add.text() == "+"
    assert lib_panel._btn_add.toolTip() != ""

    with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("ThemaB", True)):
        lib_panel.create_new_theme()
        assert "ThemaB" in main_window._library.themes.get_theme_names()

    # 2. DocumentListPanel
    doc_panel = main_window._document_panel

    # Filter- und Sortier-Combos umschalten
    doc_panel._filter_combo.setCurrentIndex(1)
    doc_panel._on_filter_changed(1)
    doc_panel._sort_combo.setCurrentIndex(1)
    doc_panel._on_sort_changed(1)

    # Testdateien anlegen
    import fitz
    pdf_file = tmp_path / "doc.pdf"
    doc1 = fitz.open()
    doc1.new_page()
    doc1.save(str(pdf_file))
    doc1.close()

    pdf_file2 = tmp_path / "doc2.pdf"
    doc2 = fitz.open()
    doc2.new_page()
    doc2.save(str(pdf_file2))
    doc2.close()

    txt_file = tmp_path / "doc.txt"
    txt_file.write_text("Text content", encoding="utf-8")

    main_window._library.add_documents([str(pdf_file), str(pdf_file2), str(txt_file)])
    doc_panel.refresh()

    # Kontextmenü für Einzelauswahl PDF
    menu_single = doc_panel.create_context_menu([str(pdf_file)])
    assert menu_single is not None
    action_texts = [a.text() for a in menu_single.actions() if not a.isSeparator()]
    assert any("Sammel-PDF" in t for t in action_texts)
    assert any("annotieren" in t for t in action_texts)
    assert any("verwalten" in t for t in action_texts)
    assert any("schwärzen" in t for t in action_texts)
    assert any("OCR" in t for t in action_texts)
    assert any("Signatur" in t for t in action_texts)
    assert any("gelesen" in t for t in action_texts)

    # Einzelne Aktionen auslösen (mit Mocks)
    with patch("gui.dialogs.collection_export_dialog.CollectionExportDialog.exec", return_value=0):
        doc_panel._export_as_collection_pdf([str(pdf_file)])

    with patch("gui.dialogs.pdf_annotation_dialog.PDFAnnotationDialog.exec", return_value=0):
        doc_panel._annotate_pdf(str(pdf_file))

    with patch("gui.dialogs.pdf_pages_dialog.PDFPagesDialog.exec", return_value=0):
        doc_panel._manage_pdf_pages(str(pdf_file))

    with patch("gui.dialogs.redaction_dialog.RedactionDialog.exec", return_value=0):
        doc_panel._redact_pdf(str(pdf_file))

    with patch("gui.dialogs.ocr_dialog.OCRDialog.exec", return_value=0):
        doc_panel._ocr_pdf(str(pdf_file))

    # Gelesen / Ungelesen markieren (Filter auf ALL zurücksetzen, um alle Dokumente zu prüfen)
    doc_panel._filter_combo.setCurrentIndex(0)
    doc_panel._on_filter_changed(0)
    doc_panel._mark_as_read([str(pdf_file)], True)
    docs = main_window._library.get_documents(theme=main_window._library.themes.get_current_theme())
    pdf_doc = next(d for d in docs if Path(d.path) == pdf_file.resolve())
    assert pdf_doc.is_read is True

    doc_panel._mark_as_read([str(pdf_file)], False)
    docs_after = main_window._library.get_documents(theme=main_window._library.themes.get_current_theme())
    pdf_doc_after = next(d for d in docs_after if Path(d.path) == pdf_file.resolve())
    assert pdf_doc_after.is_read is False

    # Mehrfachauswahl Merge
    menu_multi = doc_panel.create_context_menu([str(pdf_file), str(pdf_file2)])
    assert menu_multi is not None
    multi_texts = [a.text() for a in menu_multi.actions() if not a.isSeparator()]
    assert any("zusammenführen" in t for t in multi_texts)

    # 3. PreviewPanel
    prev_panel = main_window._preview_panel
    assert prev_panel._btn_open is not None

    # Text-Vorschau
    prev_panel.show_document(str(txt_file))
    assert prev_panel._stack.currentIndex() == 1
    assert "Text content" in prev_panel._text_widget.toPlainText()
    assert prev_panel._btn_open.isEnabled()

    # Nicht unterstütztes Format
    unknown_file = tmp_path / "unknown.bin"
    unknown_file.write_bytes(b"\x00\x01\x02\x03")
    prev_panel.show_document(str(unknown_file))
    assert prev_panel._stack.currentIndex() == 3

    # Reset / Clear
    prev_panel.clear()
    assert prev_panel._stack.currentIndex() == 0
    assert not prev_panel._btn_open.isEnabled()

