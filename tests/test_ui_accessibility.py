#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Barrierefreiheits- und UX-Vertragstests (WCAG 2.1 AA / BITV 2.0)
=======================================================================
Hermetische Testsuite zur Verifikation von Barrierefreiheitsattributen,
Tastaturbedienbarkeit, Label-Buddies, Dialogmodalität und i18n-Konsistenz.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.library.manager import LibraryManager
from gui.main_window import MainWindow
from gui.panels.library_panel import LibraryPanel
from gui.panels.document_list import DocumentListPanel
from gui.panels.preview_panel import PreviewPanel
from gui.dialogs.settings_dialog import SettingsDialog
from translator import get_translator, tr


@pytest.fixture
def qapp():
    """Stellt sicher, dass eine QApplication-Instanz existiert."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_library(tmp_path):
    """Erstellt eine isolierte LibraryManager-Instanz."""
    state_file = tmp_path / ".dokuzen_test_state.json"
    lib = LibraryManager(state_file=state_file)
    lib.initialize()
    lib.themes.create_theme("Standard")
    lib.themes.set_current_theme("Standard")
    lib.save()
    return lib


def test_shortcuts_dialog_modal_and_a11y(qapp, temp_library):
    """Prüft den barrierefreien F1-Tastaturkürzel-Dialog auf Modalität und WCAG-Konformität."""
    win = MainWindow(library=temp_library)
    try:
        # F1-Shortcut und Action verifizieren
        assert hasattr(win, "_action_shortcuts")
        assert win._action_shortcuts.shortcut().toString() == "F1"
        assert "Tastaturkürzel" in win._action_shortcuts.text()

        # Dialog öffnen (Headless-Bypass gibt Dialog-Instanz zurück)
        dialog = win.show_shortcuts_dialog()
        assert dialog is not None
        assert dialog.isModal() is True
        assert dialog.accessibleName() == "Tastaturkürzel und Barrierefreiheit"
        assert "Tastaturkürzel" in dialog.windowTitle()

        # Tree und Kategorien prüfen
        from PySide6.QtWidgets import QTreeWidget, QPushButton, QLabel
        trees = dialog.findChildren(QTreeWidget)
        assert len(trees) >= 1
        tree = trees[0]
        assert tree.topLevelItemCount() >= 5
        assert tree.accessibleName() == "Tastaturkürzel und Barrierefreiheit"

        # BITV / WCAG Hinweis
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any("WCAG 2.1 AA" in t for t in texts)

        # Schließen-Button mit Default-Fokus
        buttons = dialog.findChildren(QPushButton)
        close_btns = [b for b in buttons if b.text() in ("Schließen", "Close", "OK")]
        assert len(close_btns) >= 1
        assert close_btns[0].isDefault() is True

        dialog.close()
    finally:
        win.close()


def test_mainwindow_statusbar_and_toolbar_a11y(qapp, temp_library):
    """Prüft Accessible Names, Descriptions und Tooltips von Toolbar und Statusbar."""
    win = MainWindow(library=temp_library)
    try:
        # Statusbar
        statusbar = win.statusBar()
        assert statusbar.accessibleName() == "Statusleiste"
        assert win._status_theme.accessibleName() == "Aktives Thema"
        assert win._status_docs.accessibleName() == "Anzahl der Dokumente"
        assert win._status_filter.accessibleName() == "Aktiver Filter"
        assert "Aktives Thema" in win._status_theme.accessibleDescription()

        # Toolbar
        assert hasattr(win, "_toolbar")
        assert win._toolbar.accessibleName() == "Hauptwerkzeuge"

        # Suchfeld
        assert win._search_box.accessibleName() == "Dokumente durchsuchen"
        assert "Ctrl+F" in win._search_box.toolTip()
        assert len(win._search_box.accessibleDescription()) > 0

        # Toolbar-Buttons (QToolButton via widgetForAction)
        import_btn = win._toolbar.widgetForAction(win._btn_import)
        if import_btn:
            assert import_btn.accessibleName() == "Dokumente importieren"

        # 3 Panels Accessible Names
        assert win._library_panel.accessibleName() == "Bibliotheks-Panel"
        assert win._document_panel.accessibleName() == "Dokumentenlisten-Panel"
        assert win._preview_panel.accessibleName() == "Vorschau-Panel"
    finally:
        win.close()


def test_library_panel_accessibility_and_keyboard(qapp, temp_library):
    """Prüft Themen-Baum auf Barrierefreiheitsattribute und Tastaturnavigation."""
    panel = LibraryPanel(temp_library)
    try:
        assert panel._tree.accessibleName() == "Themen-Bibliothek"
        assert "Pfeiltasten" in panel._tree.accessibleDescription()
        assert panel._btn_add.accessibleName() == "Neues Thema erstellen"
        assert "Ctrl+N" in panel._btn_add.toolTip()

        # Tastaturevent Return -> theme_selected Signal
        selected_themes = []
        panel.theme_selected.connect(lambda t: selected_themes.append(t))

        item = panel._tree.topLevelItem(0)
        panel._tree.setCurrentItem(item)

        event_return = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        panel._tree.keyPressEvent(event_return)
        assert len(selected_themes) >= 1
    finally:
        panel.close()


def test_document_list_panel_accessibility_buddies_and_keyboard(qapp, temp_library, tmp_path):
    """Prüft Dokumententabelle, Buddy-Labels und Tastaturbedienung (Enter, Delete, Ctrl+C)."""
    # Testdatei zur Library hinzufügen
    sample_file = tmp_path / "test_doc.txt"
    sample_file.write_text("DokuZen A11y Test", encoding="utf-8")
    temp_library.add_documents([str(sample_file)])

    panel = DocumentListPanel(temp_library)
    try:
        # Buddies und Accessibility Attribute
        assert panel._filter_label.buddy() == panel._filter_combo
        assert panel._sort_label.buddy() == panel._sort_combo
        assert panel._filter_combo.accessibleName() == "Dokumentenfilter"
        assert panel._sort_combo.accessibleName() == "Dokumentensortierung"
        assert panel._table.accessibleName() == "Dokumentenliste"
        assert panel._status_label.accessibleName() == "Dokumentenanzahl"
        assert "Enter zum Öffnen" in panel._table.accessibleDescription()

        panel.refresh()
        assert panel._table.rowCount() >= 1

        # Zeile auswählen
        panel._table.selectRow(0)

        # Tastaturevent Enter -> document_double_clicked
        opened_docs = []
        panel.document_double_clicked.connect(lambda p: opened_docs.append(p))

        event_enter = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        panel._table.keyPressEvent(event_enter)
        assert len(opened_docs) == 1
        assert str(sample_file) in opened_docs[0]

        # Tastaturevent Ctrl+C -> Zwischenablage
        clipboard = QApplication.clipboard()
        clipboard.clear()
        event_copy = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        panel._table.keyPressEvent(event_copy)
        assert str(sample_file) in clipboard.text()

        # Tastaturevent F5 -> refresh
        event_f5 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F5, Qt.KeyboardModifier.NoModifier)
        panel._table.keyPressEvent(event_f5)
        assert panel._table.rowCount() >= 1
    finally:
        panel.close()


def test_preview_panel_accessibility(qapp):
    """Prüft Vorschaupanel-Komponenten auf barrierefreie Namen und Tooltips."""
    panel = PreviewPanel()
    try:
        assert panel._btn_open.accessibleName() == "Dokument extern öffnen"
        assert "Standardanwendung" in panel._btn_open.toolTip()
        assert panel._text_widget.accessibleName() == "Text-Vorschau"
        assert panel._image_scroll.accessibleName() == "Bild-Vorschau"
        assert panel._image_label.accessibleName() == "Bild-Vorschau"
        assert panel._empty_label.accessibleName() == "Keine Vorschau"
        assert panel._stack.accessibleName() == "Vorschau-Panel"
    finally:
        panel.close()


def test_settings_dialog_accessibility_and_buddies(qapp):
    """Prüft Einstellungsdialog auf Modalität, Label-Buddies und Accessible Names."""
    dialog = SettingsDialog()
    try:
        assert dialog.isModal() is True
        assert dialog.accessibleName() == "Einstellungen"

        # Buddy-Prüfungen
        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        buddies = {lbl.buddy() for lbl in labels if lbl.buddy() is not None}

        assert dialog._library_path in buddies
        assert dialog._export_path in buddies
        assert dialog._spawn_path in buddies
        assert dialog._language in buddies
        assert dialog._theme in buddies
        assert dialog._font_family in buddies
        assert dialog._font_size in buddies
        assert dialog._icon_size in buddies

        # Accessible Names auf Eingabefeldern
        assert dialog._library_path.accessibleName() == "Bibliothekspfad"
        assert dialog._export_path.accessibleName() == "Exportpfad"
        assert dialog._spawn_path.accessibleName() == "Spawner-Ordnerpfad"
        assert dialog._language.accessibleName() == "Sprache auswählen"
        assert dialog._theme.accessibleName() == "Design-Farbschema"
        assert dialog._font_family.accessibleName() == "Schriftart"
        assert dialog._font_size.accessibleName() == "Schriftgröße"
        assert dialog._icon_size.accessibleName() == "Icon-Größe"
        assert dialog._shortcuts_tree.accessibleName() == "Tastaturkürzel-Konfiguration"
    finally:
        dialog.close()


def test_dynamic_retranslate_ui_accessibility_parity(qapp, temp_library):
    """Prüft dynamische Sprachumschaltung und Parität aller Barrierefreiheitsattribute."""
    win = MainWindow(library=temp_library)
    translator = get_translator()
    original_lang = translator.current_lang

    try:
        for lang in ["de", "en", "es", "zh", "ja", "ru"]:
            translator.set_language(lang)
            win.retranslate_ui()

            # Statusleiste und Toolbar retranslatiert
            assert win._statusbar.accessibleName() == tr("Statusleiste")
            assert win._status_theme.accessibleName() == tr("Aktives Thema")
            assert win._status_docs.accessibleName() == tr("Anzahl der Dokumente")
            assert win._status_filter.accessibleName() == tr("Aktiver Filter")
            assert win._search_box.accessibleName() == tr("Dokumente durchsuchen")

            # Panels retranslatiert
            assert win._library_panel.accessibleName() == tr("Bibliotheks-Panel")
            assert win._document_panel.accessibleName() == tr("Dokumentenlisten-Panel")
            assert win._preview_panel.accessibleName() == tr("Vorschau-Panel")

            assert win._document_panel._table.accessibleName() == tr("Dokumentenliste")
            assert win._library_panel._tree.accessibleName() == tr("Themen-Bibliothek")
    finally:
        translator.set_language(original_lang)
        win.retranslate_ui()
        win.close()
