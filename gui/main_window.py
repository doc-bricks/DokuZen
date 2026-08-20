#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Main Window
=============================
Hauptfenster der Anwendung mit 3-Panel-Layout.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QStatusBar, QMenuBar,
    QMenu, QMessageBox, QFileDialog, QLabel,
    QLineEdit, QApplication
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence

from utils.logger import get_logger, LoggerMixin
from core.library import LibraryManager
from translator import get_translator, tr

# Panels importieren
from gui.panels.library_panel import LibraryPanel
from gui.panels.document_list import DocumentListPanel
from gui.panels.preview_panel import PreviewPanel


class MainWindow(QMainWindow, LoggerMixin):
    """
    Hauptfenster von DokuZen Pro.
    
    Layout:

    ┌─────────────────────────────────────────────────────┐
    │ Menüleiste                                          │
    ├─────────────────────────────────────────────────────┤
    │ Toolbar                                             │
    ├───────────┬─────────────────────┬───────────────────┤
    │           │                     │                   │
    │ Bibliothek│   Dokumentenliste   │    Vorschau       │
    │ (Themen)  │                     │                   │
    │           │                     │                   │
    ├───────────┴─────────────────────┴───────────────────┤
    │ Statusleiste                                        │
    └─────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        
        self.logger.info("Hauptfenster wird erstellt...")
        
        # Library Manager initialisieren
        self._library = LibraryManager()
        self._library.initialize()
        
        # UI aufbauen
        self._setup_window()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_panels()
        self._setup_statusbar()
        self._setup_shortcuts()
        
        # Verbindungen herstellen
        self._connect_signals()
        
        # Auto-Save Timer
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start(60000)  # Alle 60 Sekunden
        
        # Initial-Update
        self._update_statusbar()
        
        self.logger.info("Hauptfenster erstellt")
    
    def _setup_window(self):
        """Konfiguriert das Hauptfenster."""
        self.setWindowTitle(tr("DokuZen"))
        self.setMinimumSize(1000, 600)
        self.resize(1400, 900)
        
        # Zentrales Widget
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        self._main_layout = QVBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
    
    def _setup_menubar(self):
        """Erstellt die Menüleiste."""
        menubar = self.menuBar()
        
        # === Datei-Menü ===
        self._menu_file = menubar.addMenu(tr("&Datei"))
        
        self._action_import = QAction(tr("&Importieren..."), self)
        self._action_import.setShortcut(QKeySequence("Ctrl+I"))
        self._action_import.triggered.connect(self._on_import)
        self._menu_file.addAction(self._action_import)
        
        self._action_import_folder = QAction(tr("Ordner importieren..."), self)
        self._action_import_folder.triggered.connect(self._on_import_folder)
        self._menu_file.addAction(self._action_import_folder)
        
        self._menu_file.addSeparator()
        
        self._action_export_pdf = QAction(tr("Sammel-PDF exportieren..."), self)
        self._action_export_pdf.triggered.connect(self._on_export_pdf)
        self._menu_file.addAction(self._action_export_pdf)
        
        self._menu_file.addSeparator()
        
        self._action_settings = QAction(tr("&Einstellungen..."), self)
        self._action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self._action_settings.triggered.connect(self._on_settings)
        self._menu_file.addAction(self._action_settings)
        
        self._menu_file.addSeparator()
        
        self._action_exit = QAction(tr("&Beenden"), self)
        self._action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        self._action_exit.triggered.connect(self.close)
        self._menu_file.addAction(self._action_exit)
        
        # === Bearbeiten-Menü ===
        self._menu_edit = menubar.addMenu(tr("&Bearbeiten"))
        
        self._action_search = QAction(tr("&Suchen..."), self)
        self._action_search.setShortcut(QKeySequence("Ctrl+F"))
        self._action_search.triggered.connect(self._on_search_focus)
        self._menu_edit.addAction(self._action_search)
        
        self._menu_edit.addSeparator()
        
        self._action_select_all = QAction(tr("Alles auswählen"), self)
        self._action_select_all.setShortcut(QKeySequence("Ctrl+A"))
        self._action_select_all.triggered.connect(self._on_select_all)
        self._menu_edit.addAction(self._action_select_all)
        
        # === Ansicht-Menü ===
        self._menu_view = menubar.addMenu(tr("&Ansicht"))
        
        self._action_refresh = QAction(tr("&Aktualisieren"), self)
        self._action_refresh.setShortcut(QKeySequence("F5"))
        self._action_refresh.triggered.connect(self._on_refresh)
        self._menu_view.addAction(self._action_refresh)
        
        self._menu_view.addSeparator()
        
        self._action_toggle_preview = QAction(tr("Vorschau ein/aus"), self)
        self._action_toggle_preview.setShortcut(QKeySequence("Ctrl+P"))
        self._action_toggle_preview.setCheckable(True)
        self._action_toggle_preview.setChecked(True)
        self._action_toggle_preview.triggered.connect(self._on_toggle_preview)
        self._menu_view.addAction(self._action_toggle_preview)
        
        # === Themen-Menü ===
        self._menu_theme = menubar.addMenu(tr("&Themen"))
        
        self._action_new_theme = QAction(tr("&Neues Thema..."), self)
        self._action_new_theme.setShortcut(QKeySequence("Ctrl+N"))
        self._action_new_theme.triggered.connect(self._on_new_theme)
        self._menu_theme.addAction(self._action_new_theme)
        
        # === Werkzeuge-Menü ===
        self._menu_tools = menubar.addMenu(tr("&Werkzeuge"))
        
        self._action_pdf_workshop = QAction(tr("PDF-&Werkstatt..."), self)
        self._action_pdf_workshop.triggered.connect(self._on_pdf_workshop)
        self._menu_tools.addAction(self._action_pdf_workshop)
        
        self._action_merge = QAction(tr("PDFs &zusammenführen..."), self)
        self._action_merge.triggered.connect(self._on_merge)
        self._menu_tools.addAction(self._action_merge)
        
        self._action_ocr = QAction(tr("&OCR-Texterkennung..."), self)
        self._action_ocr.triggered.connect(self._on_ocr)
        self._menu_tools.addAction(self._action_ocr)
        
        self._action_redaction = QAction(tr("PDF &schwärzen..."), self)
        self._action_redaction.triggered.connect(self._on_redaction)
        self._menu_tools.addAction(self._action_redaction)
        
        self._action_convert = QAction(tr("Format-&Konvertierung..."), self)
        self._action_convert.triggered.connect(self._on_convert)
        self._menu_tools.addAction(self._action_convert)
        
        self._menu_tools.addSeparator()
        
        self._action_text_pool = QAction(tr("Text-&Pooler..."), self)
        self._action_text_pool.triggered.connect(self._on_text_pool)
        self._menu_tools.addAction(self._action_text_pool)
        
        self._action_code_analysis = QAction(tr("&Code-Analyse (.py)..."), self)
        self._action_code_analysis.triggered.connect(self._on_code_analysis)
        self._menu_tools.addAction(self._action_code_analysis)
        
        self._action_form_builder = QAction(tr("&Formular-Builder..."), self)
        self._action_form_builder.triggered.connect(self._on_form_builder)
        self._menu_tools.addAction(self._action_form_builder)
        
        self._action_pdf_marker = QAction(tr("PDF-&Marker (M/D/K)..."), self)
        self._action_pdf_marker.triggered.connect(self._on_pdf_marker)
        self._menu_tools.addAction(self._action_pdf_marker)
        
        self._action_pdf_pages = QAction(tr("PDF-Seiten &verwalten..."), self)
        self._action_pdf_pages.triggered.connect(self._on_pdf_pages)
        self._menu_tools.addAction(self._action_pdf_pages)
        
        self._action_pdf_annotate = QAction(tr("PDF-&Annotationen..."), self)
        self._action_pdf_annotate.triggered.connect(self._on_pdf_annotate)
        self._menu_tools.addAction(self._action_pdf_annotate)

        self._action_signature_overlay = QAction(tr("PDF-Signatur &einbetten..."), self)
        self._action_signature_overlay.triggered.connect(self._on_signature_overlay)
        self._menu_tools.addAction(self._action_signature_overlay)

        self._menu_tools.addSeparator()
        
        self._action_image_tools = QAction(tr("&Bild-Werkzeuge..."), self)
        self._action_image_tools.triggered.connect(self._on_image_tools)
        self._menu_tools.addAction(self._action_image_tools)
        
        self._action_sqlite_viewer = QAction(tr("SQLite-&Viewer..."), self)
        self._action_sqlite_viewer.triggered.connect(self._on_sqlite_viewer)
        self._menu_tools.addAction(self._action_sqlite_viewer)
        
        self._action_pyinstaller = QAction(tr("Python &Kompilieren..."), self)
        self._action_pyinstaller.triggered.connect(self._on_pyinstaller)
        self._menu_tools.addAction(self._action_pyinstaller)
        
        # === Hilfe-Menü ===
        self._menu_help = menubar.addMenu(tr("&Hilfe"))
        
        self._action_about = QAction(tr("Über DokuZen"), self)
        self._action_about.triggered.connect(self._on_about)
        self._menu_help.addAction(self._action_about)
    
    def _setup_toolbar(self):
        """Erstellt die Toolbar."""
        toolbar = QToolBar(tr("Hauptwerkzeuge"))
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Import-Button
        self._btn_import = QAction(tr("Importieren"), self)
        self._btn_import.setToolTip(tr("Dateien zur Bibliothek hinzufügen (Ctrl+I)"))
        self._btn_import.triggered.connect(self._on_import)
        toolbar.addAction(self._btn_import)
        
        # Neues Thema
        self._btn_new_theme = QAction(tr("Neues Thema"), self)
        self._btn_new_theme.setToolTip(tr("Neues Thema erstellen (Ctrl+N)"))
        self._btn_new_theme.triggered.connect(self._on_new_theme)
        toolbar.addAction(self._btn_new_theme)
        
        toolbar.addSeparator()
        
        # Suchfeld
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(tr("Suchen..."))
        self._search_box.setToolTip(tr("Dokumente in der Bibliothek durchsuchen (Ctrl+F)"))
        self._search_box.setAccessibleName(tr("Dokumente durchsuchen"))
        self._search_box.setAccessibleDescription(
            tr("Filtert die angezeigten Dokumente beim Eingeben. Mit Ctrl+F fokussieren.")
        )
        self._search_box.setMaximumWidth(250)
        toolbar.addWidget(self._search_box)
        self._search_box.textChanged.connect(self._on_search_changed)
        
        # Aktualisieren
        self._btn_refresh = QAction(tr("Aktualisieren"), self)
        self._btn_refresh.setToolTip(tr("Ansicht aktualisieren (F5)"))
        self._btn_refresh.triggered.connect(self._on_refresh)
        toolbar.addAction(self._btn_refresh)

    def _setup_panels(self):
        """Erstellt das 3-Panel-Layout."""
        # Splitter für die drei Panels
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_layout.addWidget(self._splitter)
        
        # Panel 1: Bibliothek (Themen-Baum)
        self._library_panel = LibraryPanel(self._library)
        self._splitter.addWidget(self._library_panel)
        
        # Panel 2: Dokumentenliste
        self._document_panel = DocumentListPanel(self._library)
        self._splitter.addWidget(self._document_panel)
        
        # Panel 3: Vorschau
        self._preview_panel = PreviewPanel()
        self._splitter.addWidget(self._preview_panel)
        
        # Größenverhältnis setzen (200:600:400)
        self._splitter.setSizes([200, 600, 400])
        
        # Minimale Breiten
        self._library_panel.setMinimumWidth(150)
        self._document_panel.setMinimumWidth(300)
        self._preview_panel.setMinimumWidth(200)
    
    def _setup_statusbar(self):
        """Erstellt die Statusleiste."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        
        # Permanente Labels
        self._status_theme = QLabel(f"{tr('Thema')}: -")
        self._status_docs = QLabel(f"{tr('Dokumente')}: 0")
        self._status_filter = QLabel(f"{tr('Filter')}: {tr('Alle')}")
        
        self._statusbar.addPermanentWidget(self._status_theme)
        self._statusbar.addPermanentWidget(QLabel(" | "))
        self._statusbar.addPermanentWidget(self._status_docs)
        self._statusbar.addPermanentWidget(QLabel(" | "))
        self._statusbar.addPermanentWidget(self._status_filter)
    
    def _setup_shortcuts(self):
        """Richtet zusätzliche Tastenkürzel ein."""
        pass  # Bereits über Menü-Actions definiert
    
    def _connect_signals(self):
        """Verbindet Signale zwischen Komponenten."""
        # Theme-Auswahl -> Dokumentenliste aktualisieren
        self._library_panel.theme_selected.connect(self._on_theme_selected)
        
        # Dokument-Auswahl -> Vorschau aktualisieren
        self._document_panel.document_selected.connect(self._on_document_selected)
        
        # Doppelklick -> Dokument öffnen
        self._document_panel.document_double_clicked.connect(self._on_document_open)
        
        # Library-Änderungen
        self._library.add_change_callback(self._on_library_changed)
    
    def _update_statusbar(self):
        """Aktualisiert die Statusleiste."""
        theme = self._library.themes.get_current_theme()
        self._status_theme.setText(f"{tr('Thema')}: {theme or '-'}")
        
        docs = self._library.get_documents()
        self._status_docs.setText(f"{tr('Dokumente')}: {len(docs)}")
        self._status_filter.setText(f"{tr('Filter')}: {tr('Alle')}")
    
    def retranslate_ui(self):
        """Aktualisiert alle UI-Texte dynamisch gemäß aktuellem TranslationSystem."""
        t = tr
        self.setWindowTitle(t("DokuZen"))
        
        if hasattr(self, "_menu_file"):
            self._menu_file.setTitle(t("&Datei"))
            self._action_import.setText(t("&Importieren..."))
            self._action_import_folder.setText(t("Ordner importieren..."))
            self._action_export_pdf.setText(t("Sammel-PDF exportieren..."))
            self._action_settings.setText(t("&Einstellungen..."))
            self._action_exit.setText(t("&Beenden"))
            
        if hasattr(self, "_menu_edit"):
            self._menu_edit.setTitle(t("&Bearbeiten"))
            self._action_search.setText(t("&Suchen..."))
            self._action_select_all.setText(t("Alles auswählen"))
            
        if hasattr(self, "_menu_view"):
            self._menu_view.setTitle(t("&Ansicht"))
            self._action_refresh.setText(t("&Aktualisieren"))
            self._action_toggle_preview.setText(t("Vorschau ein/aus"))
            
        if hasattr(self, "_menu_theme"):
            self._menu_theme.setTitle(t("&Themen"))
            self._action_new_theme.setText(t("&Neues Thema..."))
            
        if hasattr(self, "_menu_tools"):
            self._menu_tools.setTitle(t("&Werkzeuge"))
            self._action_pdf_workshop.setText(t("PDF-&Werkstatt..."))
            self._action_merge.setText(t("PDFs &zusammenführen..."))
            self._action_ocr.setText(t("&OCR-Texterkennung..."))
            self._action_redaction.setText(t("PDF &schwärzen..."))
            self._action_convert.setText(t("Format-&Konvertierung..."))
            self._action_text_pool.setText(t("Text-&Pooler..."))
            self._action_code_analysis.setText(t("&Code-Analyse (.py)..."))
            self._action_form_builder.setText(t("&Formular-Builder..."))
            self._action_pdf_marker.setText(t("PDF-&Marker (M/D/K)..."))
            self._action_pdf_pages.setText(t("PDF-Seiten &verwalten..."))
            self._action_pdf_annotate.setText(t("PDF-&Annotationen..."))
            self._action_signature_overlay.setText(t("PDF-Signatur &einbetten..."))
            self._action_image_tools.setText(t("&Bild-Werkzeuge..."))
            self._action_sqlite_viewer.setText(t("SQLite-&Viewer..."))
            self._action_pyinstaller.setText(t("Python &Kompilieren..."))
            
        if hasattr(self, "_menu_help"):
            self._menu_help.setTitle(t("&Hilfe"))
            self._action_about.setText(t("Über DokuZen"))
            
        if hasattr(self, "_btn_import"):
            self._btn_import.setText(t("Importieren"))
            self._btn_import.setToolTip(t("Dateien zur Bibliothek hinzufügen (Ctrl+I)"))
            self._btn_new_theme.setText(t("Neues Thema"))
            self._btn_new_theme.setToolTip(t("Neues Thema erstellen (Ctrl+N)"))
            self._btn_refresh.setText(t("Aktualisieren"))
            self._btn_refresh.setToolTip(t("Ansicht aktualisieren (F5)"))
            self._search_box.setPlaceholderText(t("Suchen..."))
            self._search_box.setToolTip(t("Dokumente in der Bibliothek durchsuchen (Ctrl+F)"))
            
        if hasattr(self, "_library_panel") and hasattr(self._library_panel, "retranslate_ui"):
            self._library_panel.retranslate_ui()
        if hasattr(self, "_document_panel") and hasattr(self._document_panel, "retranslate_ui"):
            self._document_panel.retranslate_ui()
        if hasattr(self, "_preview_panel") and hasattr(self._preview_panel, "retranslate_ui"):
            self._preview_panel.retranslate_ui()
            
        self._update_statusbar()
    
    # === Event Handler ===
    
    def _on_import(self):
        """Importiert Dateien."""
        filter_str = (
            f"{tr('Alle unterstützten')} (*.pdf *.doc *.docx *.txt *.py *.log *.json);;"
            f"{tr('PDF-Dateien')} (*.pdf);;"
            f"{tr('Word-Dokumente')} (*.doc *.docx);;"
            f"{tr('Textdateien')} (*.txt *.log *.py *.json);;"
            f"{tr('Alle Dateien')} (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Dateien importieren"),
            "",
            filter_str
        )
        
        if files:
            success, failed = self._library.add_documents(files)
            self._statusbar.showMessage(
                f"{success} {tr('Datei(en) importiert')}, {failed} {tr('übersprungen')}", 3000
            )
            self._document_panel.refresh()
            self._update_statusbar()
    
    def _on_import_folder(self):
        """Importiert einen ganzen Ordner."""
        folder = QFileDialog.getExistingDirectory(self, tr("Ordner importieren"))
        if folder:
            folder_path = Path(folder)
            files = []
            for ext in self._library.SUPPORTED_EXTENSIONS:
                files.extend(folder_path.glob(f"*{ext}"))
            
            if files:
                success, failed = self._library.add_documents([str(f) for f in files])
                self._statusbar.showMessage(
                    f"{success} {tr('Datei(en) importiert')}, {failed} {tr('übersprungen')}", 3000
                )
                self._document_panel.refresh()
                self._update_statusbar()
            else:
                self._statusbar.showMessage(tr("Keine unterstützten Dateien gefunden"), 3000)
    
    def _on_export_pdf(self):
        """Exportiert Sammel-PDF."""
        self._statusbar.showMessage(tr("Funktion noch nicht implementiert"), 3000)
    
    def _on_settings(self):
        """Öffnet Einstellungen."""
        from gui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self, settings_dict: dict):
        """Wendet geänderte Einstellungen an (Sprache, Theme, etc.)."""
        if not settings_dict:
            return
        lang_code = settings_dict.get("language_code")
        if not lang_code:
            lang = settings_dict.get("language")
            if lang:
                from translator import TranslationSystem
                lang_code = TranslationSystem.normalize_language_code(str(lang))
        if lang_code:
            get_translator().set_language(lang_code)
            self.retranslate_ui()
    
    def _on_search_focus(self):
        """Fokussiert das Suchfeld."""
        self._search_box.setFocus()
        self._search_box.selectAll()
    
    def _on_search_changed(self, text: str):
        """Reagiert auf Suchtext-Änderung."""
        self._library.set_search(text)
        self._document_panel.refresh()
    
    def _on_select_all(self):
        """Wählt alle Dokumente aus."""
        self._document_panel.select_all()
    
    def _on_refresh(self):
        """Aktualisiert die Ansicht."""
        self._library_panel.refresh()
        self._document_panel.refresh()
        self._update_statusbar()
        self._statusbar.showMessage(tr("Aktualisiert"), 1500)
    
    def _on_toggle_preview(self, checked: bool):
        """Blendet Vorschau ein/aus."""
        self._preview_panel.setVisible(checked)
    
    def _on_new_theme(self):
        """Erstellt ein neues Thema."""
        self._library_panel.create_new_theme()
    
    def _on_theme_selected(self, theme_name: str):
        """Reagiert auf Theme-Auswahl."""
        self._library.themes.set_current_theme(theme_name)
        self._document_panel.refresh()
        self._update_statusbar()
    
    def _on_document_selected(self, doc_path: str):
        """Reagiert auf Dokument-Auswahl."""
        self._preview_panel.show_document(doc_path)
    
    def _on_document_open(self, doc_path: str):
        """Öffnet ein Dokument extern."""
        if Path(doc_path).exists():
            if sys.platform == "win32":
                os.startfile(doc_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", doc_path], check=False, timeout=30)
            else:
                subprocess.run(["xdg-open", doc_path], check=False, timeout=30)

    def _resolve_startup_path(self, path: str) -> Optional[str]:
        """Normalisiert einen Startup-Pfad und prüft seine Existenz."""
        normalized = str(Path(path).expanduser().resolve())
        if not Path(normalized).exists():
            self.logger.warning("Startup-Pfad nicht gefunden: %s", normalized)
            self._statusbar.showMessage(f"{tr('Datei nicht gefunden')}: {normalized}", 5000)
            return None
        return normalized

    def _resolve_startup_paths(self, paths: Sequence[str]) -> List[str]:
        """Löst mehrere Startup-Pfade defensiv auf."""
        resolved: List[str] = []
        for path in paths:
            normalized = self._resolve_startup_path(path)
            if normalized:
                resolved.append(normalized)
        return resolved

    def _add_startup_paths_to_library(self, paths: Sequence[str]) -> List[str]:
        """Importiert existierende Startup-Dateien in die Bibliothek."""
        resolved = self._resolve_startup_paths(paths)
        if not resolved:
            return []

        success, failed = self._library.add_documents(resolved)
        self._document_panel.refresh()
        self._update_statusbar()
        self._statusbar.showMessage(
            f"Startup-Import: {success} {tr('Datei(en) importiert')}, {failed} {tr('übersprungen')}",
            4000,
        )
        return resolved

    def _show_path_in_preview(self, path: str) -> None:
        """Zeigt eine Datei direkt in der Vorschau an."""
        self._preview_panel.show_document(path)
        self._statusbar.showMessage(f"{tr('Vorschau geladen')}: {Path(path).name}", 3000)

    def startup_import_paths(self, paths: Sequence[str]) -> None:
        """Importiert Dateien aus dem CLI-Startpfad."""
        imported_paths = self._add_startup_paths_to_library(paths)
        if imported_paths:
            self._show_path_in_preview(imported_paths[0])

    def startup_open_path(self, path: str) -> None:
        """Öffnet eine Datei beim Start und zeigt sie in der Vorschau an."""
        imported_paths = self._add_startup_paths_to_library((path,))
        if imported_paths:
            self._show_path_in_preview(imported_paths[0])

    def startup_ocr_path(self, path: str) -> None:
        """Startet den OCR-Dialog direkt mit einer Datei."""
        resolved = self._resolve_startup_path(path)
        if not resolved:
            return
        self.startup_open_path(resolved)
        from gui.dialogs.ocr_dialog import OCRDialog

        dialog = OCRDialog(self, initial_file=resolved)
        dialog.exec()

    def startup_redaction_path(self, path: str) -> None:
        """Startet den Schwärzungs-Dialog direkt mit einer PDF."""
        resolved = self._resolve_startup_path(path)
        if not resolved:
            return
        self.startup_open_path(resolved)
        from gui.dialogs.redaction_dialog import RedactionDialog

        dialog = RedactionDialog(self, initial_file=resolved)
        dialog.exec()
        self._on_refresh()

    def startup_merge_paths(self, paths: Sequence[str]) -> None:
        """Startet den Merge-Tab der PDF-Werkstatt direkt mit PDFs."""
        resolved = self._add_startup_paths_to_library(paths)
        pdf_files = [path for path in resolved if path.lower().endswith(".pdf")]
        if not pdf_files:
            self._statusbar.showMessage(tr("Keine existierenden PDF-Dateien für --merge gefunden"), 5000)
            return

        from gui.dialogs.pdf_workshop import PDFWorkshopDialog

        dialog = PDFWorkshopDialog(self, initial_files=pdf_files)
        dialog._tabs.setCurrentIndex(0)
        dialog.exec()
        self._on_refresh()
    
    def _on_library_changed(self, event: str, *args):
        """Reagiert auf Bibliotheks-Änderungen."""
        self._update_statusbar()
    
    def _on_pdf_workshop(self):
        """Öffnet PDF-Werkstatt."""
        from gui.dialogs.pdf_workshop import PDFWorkshopDialog
        
        # Falls Dokumente ausgewählt, diese übergeben
        selected = self._document_panel.get_selected_paths()
        pdf_files = [f for f in selected if f.lower().endswith('.pdf')]
        
        dialog = PDFWorkshopDialog(self, initial_files=pdf_files)
        dialog.exec()
        self._on_refresh()
    
    def _on_merge(self):
        """Öffnet Merge-Dialog (PDF-Werkstatt, Merge-Tab)."""
        from gui.dialogs.pdf_workshop import PDFWorkshopDialog
        
        selected = self._document_panel.get_selected_paths()
        pdf_files = [f for f in selected if f.lower().endswith('.pdf')]
        
        dialog = PDFWorkshopDialog(self, initial_files=pdf_files)
        dialog._tabs.setCurrentIndex(0)  # Merge-Tab
        dialog.exec()
        self._on_refresh()
    
    def _on_ocr(self):
        """Öffnet OCR-Dialog."""
        from gui.dialogs.ocr_dialog import OCRDialog
        
        # Falls ein Dokument ausgewählt, dieses übergeben
        selected = self._document_panel.get_selected_paths()
        initial_file = selected[0] if selected else None
        
        dialog = OCRDialog(self, initial_file=initial_file)
        dialog.exec()
    
    def _on_redaction(self):
        """Öffnet Schwärzungs-Dialog."""
        from gui.dialogs.redaction_dialog import RedactionDialog
        
        selected = self._document_panel.get_selected_paths()
        pdf_files = [f for f in selected if f.lower().endswith('.pdf')]
        initial_file = pdf_files[0] if pdf_files else None
        
        dialog = RedactionDialog(self, initial_file=initial_file)
        dialog.exec()
        self._on_refresh()
    
    def _on_convert(self):
        """Öffnet Konvertierungs-Dialog."""
        from gui.dialogs.convert_dialog import ConvertDialog
        
        selected = self._document_panel.get_selected_paths()
        
        dialog = ConvertDialog(self, initial_files=selected)
        dialog.exec()
        self._on_refresh()
    
    def _on_text_pool(self):
        """Öffnet Text-Pooler."""
        from gui.dialogs.text_pool_dialog import TextPoolDialog
        
        selected = self._document_panel.get_selected_paths()
        text_files = [f for f in selected if Path(f).suffix.lower() in ['.txt', '.md', '.py', '.log', '.json']]
        
        dialog = TextPoolDialog(self, initial_files=text_files)
        dialog.exec()
        self._on_refresh()
    
    def _on_code_analysis(self):
        """Öffnet Code-Analyse-Dialog."""
        from gui.dialogs.code_analysis_dialog import CodeAnalysisDialog
        
        selected = self._document_panel.get_selected_paths()
        py_files = [f for f in selected if f.lower().endswith('.py')]
        initial_file = py_files[0] if py_files else None
        
        dialog = CodeAnalysisDialog(self, initial_file=initial_file)
        dialog.exec()
    
    def _on_form_builder(self):
        """Öffnet Formular-Builder."""
        from gui.dialogs.form_builder_dialog import FormBuilderDialog
        
        dialog = FormBuilderDialog(self)
        dialog.exec()
    
    def _on_pdf_marker(self):
        """Öffnet PDF-Marker."""
        from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog
        
        selected = self._document_panel.get_selected_paths()
        pdf_files = [f for f in selected if f.lower().endswith('.pdf')]
        initial_pdf = pdf_files[0] if pdf_files else None
        
        dialog = PDFMarkerDialog(self, pdf_path=initial_pdf)
        dialog.exec()
    
    def _on_image_tools(self):
        """Öffnet Bild-Werkzeuge."""
        from gui.dialogs.image_converter_dialog import ImageConverterDialog
        
        selected = self._document_panel.get_selected_paths()
        image_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        images = [f for f in selected if f.lower().endswith(image_exts)]
        
        dialog = ImageConverterDialog(self, initial_files=images if images else None)
        dialog.exec()
    
    def _on_sqlite_viewer(self):
        """Öffnet SQLite-Viewer."""
        from gui.dialogs.sqlite_viewer_dialog import SQLiteViewerDialog
        
        selected = self._document_panel.get_selected_paths()
        db_files = [f for f in selected if f.lower().endswith(('.db', '.sqlite', '.sqlite3'))]
        initial_db = db_files[0] if db_files else None
        
        dialog = SQLiteViewerDialog(self, db_path=initial_db)
        dialog.exec()
    
    def _on_pyinstaller(self):
        """Öffnet PyInstaller-Dialog."""
        from gui.dialogs.pyinstaller_dialog import PyInstallerDialog
        
        selected = self._document_panel.get_selected_paths()
        py_files = [f for f in selected if f.lower().endswith('.py')]
        initial_script = py_files[0] if py_files else None
        
        dialog = PyInstallerDialog(self, script_path=initial_script)
        dialog.exec()
    
    def _on_pdf_pages(self):
        """Öffnet PDF-Seitenverwaltung."""
        from gui.dialogs.pdf_pages_dialog import PDFPagesDialog
        
        selected = self._document_panel.get_selected_paths()
        pdf_files = [f for f in selected if f.lower().endswith('.pdf')]
        initial_pdf = pdf_files[0] if pdf_files else None
        
        dialog = PDFPagesDialog(self, pdf_path=initial_pdf)
        dialog.exec()
    
    def _on_pdf_annotate(self):
        """Öffnet PDF-Annotationen (Info-Dialog)."""
        QMessageBox.information(
            self,
            tr("PDF-Annotationen"),
            f"{tr('PDF-Annotationen können über die Vorschau hinzugefügt werden:')}\n\n"
            f"• {tr('Rechtsklick auf PDF → Annotieren')}\n"
            f"• {tr('Marker, Kommentare, Stempel')}\n"
            f"• {tr('Freitext-Overlays')}\n"
            f"• {tr('Formen (Rechteck, Kreis, Linie)')}\n\n"
            f"{tr('Oder nutzen Sie die PDF-Werkstatt für erweiterte Optionen.')}"
        )

    def _on_signature_overlay(self):
        """Öffnet den Signatur-Overlay-Dialog."""
        from gui.dialogs.signature_overlay_dialog import SignatureOverlayDialog

        selected = self._document_panel.get_selected_paths()
        pdf_files = [f for f in selected if f.lower().endswith(".pdf")]
        initial_pdf = pdf_files[0] if pdf_files else None

        dialog = SignatureOverlayDialog(self, pdf_path=initial_pdf)
        dialog.exec()

    def _on_about(self):
        """Zeigt About-Dialog."""
        QMessageBox.about(
            self,
            tr("Über DokuZen"),
            f"<h2>DokuZen</h2>"
            f"<p>{tr('Version')} 1.0.0</p>"
            f"<p>{tr('Dokumenten- und Dateiverwaltungssuite')}</p>"
            f"<p>{tr('Vereint 22 Text-, PDF- und Datei-Tools in einer Anwendung.')}</p>"
            f"<hr>"
            f"<p><b>{tr('Features')}:</b></p>"
            f"<ul>"
            f"<li>{tr('Dokumentenbibliothek mit Themen')}</li>"
            f"<li>{tr('PDF-Werkstatt (OCR, Schwärzung, Merge)')}</li>"
            f"<li>{tr('Konvertierung (Word, Text, PDF)')}</li>"
            f"<li>{tr('Formular-Builder')}</li>"
            f"<li>{tr('Entwickler-Tools')}</li>"
            f"</ul>"
        )
    
    def _auto_save(self):
        """Auto-Save Callback."""
        if self._library._persistence.is_dirty:
            self._library.save()
            self.logger.debug("Auto-Save durchgeführt")
    
    # === Window Events ===
    
    def closeEvent(self, event):
        """Wird beim Schließen aufgerufen."""
        # BUGSWEEP-32: Auto-Save-Timer zuerst stoppen, sonst kann er zwischen shutdown() und
        # Objektzerstoerung feuern und auf die bereits heruntergefahrene Persistence zugreifen.
        if hasattr(self, "_auto_save_timer"):
            self._auto_save_timer.stop()

        # Speichern
        self._library.shutdown()
        
        # Fenstergeometrie merken (TODO: in Settings speichern)
        self.logger.info("Hauptfenster geschlossen")
        
        event.accept()
    
    def dragEnterEvent(self, event):
        """Drag-Enter für Datei-Drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Drop-Event für Dateien."""
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(url.toLocalFile())
        
        if files:
            success, failed = self._library.add_documents(files)
            self._statusbar.showMessage(
                f"{success} {tr('Datei(en) importiert')}, {failed} {tr('übersprungen')}", 3000
            )
            self._document_panel.refresh()
            self._update_statusbar()
