#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Main Window
=============================
Hauptfenster der Anwendung mit 3-Panel-Layout.
"""

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
        self.setWindowTitle("DokuZen")
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
        file_menu = menubar.addMenu("&Datei")
        
        self._action_import = QAction("&Importieren...", self)
        self._action_import.setShortcut(QKeySequence("Ctrl+I"))
        self._action_import.triggered.connect(self._on_import)
        file_menu.addAction(self._action_import)
        
        self._action_import_folder = QAction("Ordner importieren...", self)
        self._action_import_folder.triggered.connect(self._on_import_folder)
        file_menu.addAction(self._action_import_folder)
        
        file_menu.addSeparator()
        
        self._action_export_pdf = QAction("Sammel-PDF exportieren...", self)
        self._action_export_pdf.triggered.connect(self._on_export_pdf)
        file_menu.addAction(self._action_export_pdf)
        
        file_menu.addSeparator()
        
        self._action_settings = QAction("&Einstellungen...", self)
        self._action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self._action_settings.triggered.connect(self._on_settings)
        file_menu.addAction(self._action_settings)
        
        file_menu.addSeparator()
        
        self._action_exit = QAction("&Beenden", self)
        self._action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        self._action_exit.triggered.connect(self.close)
        file_menu.addAction(self._action_exit)
        
        # === Bearbeiten-Menü ===
        edit_menu = menubar.addMenu("&Bearbeiten")
        
        self._action_search = QAction("&Suchen...", self)
        self._action_search.setShortcut(QKeySequence("Ctrl+F"))
        self._action_search.triggered.connect(self._on_search_focus)
        edit_menu.addAction(self._action_search)
        
        edit_menu.addSeparator()
        
        self._action_select_all = QAction("Alles auswählen", self)
        self._action_select_all.setShortcut(QKeySequence("Ctrl+A"))
        self._action_select_all.triggered.connect(self._on_select_all)
        edit_menu.addAction(self._action_select_all)
        
        # === Ansicht-Menü ===
        view_menu = menubar.addMenu("&Ansicht")
        
        self._action_refresh = QAction("&Aktualisieren", self)
        self._action_refresh.setShortcut(QKeySequence("F5"))
        self._action_refresh.triggered.connect(self._on_refresh)
        view_menu.addAction(self._action_refresh)
        
        view_menu.addSeparator()
        
        self._action_toggle_preview = QAction("Vorschau ein/aus", self)
        self._action_toggle_preview.setShortcut(QKeySequence("Ctrl+P"))
        self._action_toggle_preview.setCheckable(True)
        self._action_toggle_preview.setChecked(True)
        self._action_toggle_preview.triggered.connect(self._on_toggle_preview)
        view_menu.addAction(self._action_toggle_preview)
        
        # === Themen-Menü ===
        theme_menu = menubar.addMenu("&Themen")
        
        self._action_new_theme = QAction("&Neues Thema...", self)
        self._action_new_theme.setShortcut(QKeySequence("Ctrl+N"))
        self._action_new_theme.triggered.connect(self._on_new_theme)
        theme_menu.addAction(self._action_new_theme)
        
        # === Werkzeuge-Menü ===
        tools_menu = menubar.addMenu("&Werkzeuge")
        
        self._action_pdf_workshop = QAction("PDF-&Werkstatt...", self)
        self._action_pdf_workshop.triggered.connect(self._on_pdf_workshop)
        tools_menu.addAction(self._action_pdf_workshop)
        
        self._action_merge = QAction("PDFs &zusammenführen...", self)
        self._action_merge.triggered.connect(self._on_merge)
        tools_menu.addAction(self._action_merge)
        
        self._action_ocr = QAction("&OCR-Texterkennung...", self)
        self._action_ocr.triggered.connect(self._on_ocr)
        tools_menu.addAction(self._action_ocr)
        
        self._action_redaction = QAction("PDF &schwärzen...", self)
        self._action_redaction.triggered.connect(self._on_redaction)
        tools_menu.addAction(self._action_redaction)
        
        self._action_convert = QAction("Format-&Konvertierung...", self)
        self._action_convert.triggered.connect(self._on_convert)
        tools_menu.addAction(self._action_convert)
        
        tools_menu.addSeparator()
        
        self._action_text_pool = QAction("Text-&Pooler...", self)
        self._action_text_pool.triggered.connect(self._on_text_pool)
        tools_menu.addAction(self._action_text_pool)
        
        self._action_code_analysis = QAction("&Code-Analyse (.py)...", self)
        self._action_code_analysis.triggered.connect(self._on_code_analysis)
        tools_menu.addAction(self._action_code_analysis)
        
        self._action_form_builder = QAction("&Formular-Builder...", self)
        self._action_form_builder.triggered.connect(self._on_form_builder)
        tools_menu.addAction(self._action_form_builder)
        
        self._action_pdf_marker = QAction("PDF-&Marker (M/D/K)...", self)
        self._action_pdf_marker.triggered.connect(self._on_pdf_marker)
        tools_menu.addAction(self._action_pdf_marker)
        
        self._action_pdf_pages = QAction("PDF-Seiten &verwalten...", self)
        self._action_pdf_pages.triggered.connect(self._on_pdf_pages)
        tools_menu.addAction(self._action_pdf_pages)
        
        self._action_pdf_annotate = QAction("PDF-&Annotationen...", self)
        self._action_pdf_annotate.triggered.connect(self._on_pdf_annotate)
        tools_menu.addAction(self._action_pdf_annotate)

        self._action_signature_overlay = QAction("PDF-Signatur &einbetten...", self)
        self._action_signature_overlay.triggered.connect(self._on_signature_overlay)
        tools_menu.addAction(self._action_signature_overlay)

        tools_menu.addSeparator()
        
        self._action_image_tools = QAction("&Bild-Werkzeuge...", self)
        self._action_image_tools.triggered.connect(self._on_image_tools)
        tools_menu.addAction(self._action_image_tools)
        
        self._action_sqlite_viewer = QAction("SQLite-&Viewer...", self)
        self._action_sqlite_viewer.triggered.connect(self._on_sqlite_viewer)
        tools_menu.addAction(self._action_sqlite_viewer)
        
        self._action_pyinstaller = QAction("Python &Kompilieren...", self)
        self._action_pyinstaller.triggered.connect(self._on_pyinstaller)
        tools_menu.addAction(self._action_pyinstaller)
        
        # === Hilfe-Menü ===
        help_menu = menubar.addMenu("&Hilfe")
        
        self._action_about = QAction("Über DokuZen", self)
        self._action_about.triggered.connect(self._on_about)
        help_menu.addAction(self._action_about)
    
    def _setup_toolbar(self):
        """Erstellt die Toolbar."""
        toolbar = QToolBar("Hauptwerkzeuge")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Import-Button
        self._btn_import = QAction("Importieren", self)
        self._btn_import.setToolTip("Dateien zur Bibliothek hinzufügen (Ctrl+I)")
        self._btn_import.triggered.connect(self._on_import)
        toolbar.addAction(self._btn_import)
        
        # Neues Thema
        self._btn_new_theme = QAction("Neues Thema", self)
        self._btn_new_theme.setToolTip("Neues Thema erstellen (Ctrl+N)")
        self._btn_new_theme.triggered.connect(self._on_new_theme)
        toolbar.addAction(self._btn_new_theme)
        
        toolbar.addSeparator()
        
        # Suchfeld
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Suchen...")
        self._search_box.setToolTip("Dokumente in der Bibliothek durchsuchen (Ctrl+F)")
        self._search_box.setAccessibleName("Dokumente durchsuchen")
        self._search_box.setAccessibleDescription(
            "Filtert die angezeigten Dokumente beim Eingeben. Mit Ctrl+F fokussieren."
        )
        self._search_box.setMaximumWidth(250)
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self._search_box)
        
        toolbar.addSeparator()
        
        # Aktualisieren
        self._btn_refresh = QAction("Aktualisieren", self)
        self._btn_refresh.setToolTip("Ansicht aktualisieren (F5)")
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
        self._status_theme = QLabel("Thema: -")
        self._status_docs = QLabel("Dokumente: 0")
        self._status_filter = QLabel("Filter: Alle")
        
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
        self._status_theme.setText(f"Thema: {theme or '-'}")
        
        docs = self._library.get_documents()
        self._status_docs.setText(f"Dokumente: {len(docs)}")
    
    # === Event Handler ===
    
    def _on_import(self):
        """Importiert Dateien."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien importieren",
            "",
            "Alle unterstützten (*.pdf *.doc *.docx *.txt *.py *.log *.json);;"
            "PDF-Dateien (*.pdf);;"
            "Word-Dokumente (*.doc *.docx);;"
            "Textdateien (*.txt *.log *.py *.json);;"
            "Alle Dateien (*.*)"
        )
        
        if files:
            success, failed = self._library.add_documents(files)
            self._statusbar.showMessage(
                f"{success} Datei(en) importiert, {failed} übersprungen", 3000
            )
            self._document_panel.refresh()
            self._update_statusbar()
    
    def _on_import_folder(self):
        """Importiert einen ganzen Ordner."""
        folder = QFileDialog.getExistingDirectory(self, "Ordner importieren")
        if folder:
            folder_path = Path(folder)
            files = []
            for ext in self._library.SUPPORTED_EXTENSIONS:
                files.extend(folder_path.glob(f"*{ext}"))
            
            if files:
                success, failed = self._library.add_documents([str(f) for f in files])
                self._statusbar.showMessage(
                    f"{success} Datei(en) importiert, {failed} übersprungen", 3000
                )
                self._document_panel.refresh()
                self._update_statusbar()
            else:
                self._statusbar.showMessage("Keine unterstützten Dateien gefunden", 3000)
    
    def _on_export_pdf(self):
        """Exportiert Sammel-PDF."""
        self._statusbar.showMessage("Funktion noch nicht implementiert", 3000)
    
    def _on_settings(self):
        """Öffnet Einstellungen."""
        from gui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()
    
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
        self._statusbar.showMessage("Aktualisiert", 1500)
    
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
        import os
        import subprocess
        
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
            self._statusbar.showMessage(f"Datei nicht gefunden: {normalized}", 5000)
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
            f"Startup-Import: {success} Datei(en) importiert, {failed} übersprungen",
            4000,
        )
        return resolved

    def _show_path_in_preview(self, path: str) -> None:
        """Zeigt eine Datei direkt in der Vorschau an."""
        self._preview_panel.show_document(path)
        self._statusbar.showMessage(f"Vorschau geladen: {Path(path).name}", 3000)

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
            self._statusbar.showMessage("Keine existierenden PDF-Dateien für --merge gefunden", 5000)
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
            "PDF-Annotationen",
            "PDF-Annotationen können über die Vorschau hinzugefügt werden:\n\n"
            "• Rechtsklick auf PDF → Annotieren\n"
            "• Marker, Kommentare, Stempel\n"
            "• Freitext-Overlays\n"
            "• Formen (Rechteck, Kreis, Linie)\n\n"
            "Oder nutzen Sie die PDF-Werkstatt für erweiterte Optionen."
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
            "Über DokuZen",
            "<h2>DokuZen</h2>"
            "<p>Version 1.0.0</p>"
            "<p>Dokumenten- und Dateiverwaltungssuite</p>"
            "<p>Vereint 22 Text-, PDF- und Datei-Tools in einer Anwendung.</p>"
            "<hr>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Dokumentenbibliothek mit Themen</li>"
            "<li>PDF-Werkstatt (OCR, Schwärzung, Merge)</li>"
            "<li>Konvertierung (Word, Text, PDF)</li>"
            "<li>Formular-Builder</li>"
            "<li>Entwickler-Tools</li>"
            "</ul>"
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
                f"{success} Datei(en) importiert, {failed} übersprungen", 3000
            )
            self._document_panel.refresh()
            self._update_statusbar()
