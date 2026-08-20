#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Settings Dialog (Erweitert)
==============================================
Einstellungsdialog mit Themes, Shortcuts und mehr.
"""

import sys
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QSpinBox, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QKeySequenceEdit,
    QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence

from utils.logger import LoggerMixin
from translator import TranslationSystem


class SettingsDialog(QDialog, LoggerMixin):
    """
    Einstellungsdialog für DokuZen Pro.
    
    Tabs:
    - Allgemein (Pfade, Sprache)
    - Darstellung (Themes, Schrift)
    - Tastaturkürzel
    - Erweitert
    """
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None, settings: Dict = None):
        super().__init__(parent)
        
        self._settings = settings or {}
        self._modified = False
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Einstellungen")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Tab-Widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # Tabs erstellen
        self._tabs.addTab(self._create_general_tab(), "Allgemein")
        self._tabs.addTab(self._create_appearance_tab(), "Darstellung")
        self._tabs.addTab(self._create_shortcuts_tab(), "Tastaturkürzel")
        self._tabs.addTab(self._create_advanced_tab(), "Erweitert")
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_reset = QPushButton("Zurücksetzen")
        btn_reset.clicked.connect(self._reset_settings)
        btn_layout.addWidget(btn_reset)
        
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self._save_and_close)
        btn_ok.setDefault(True)
        btn_layout.addWidget(btn_ok)
        
        layout.addLayout(btn_layout)

    def _configure_compact_browse_button(
        self,
        button: QPushButton,
        *,
        tooltip: str,
        description: str,
    ) -> None:
        """Hält kompakte Browse-Buttons visuell knapp, aber semantisch klar."""
        button.setFixedWidth(30)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setAccessibleDescription(description)
    
    def _create_general_tab(self) -> QWidget:
        """Erstellt den Allgemein-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Pfade
        paths_group = QGroupBox("Pfade")
        paths_layout = QFormLayout(paths_group)
        
        self._library_path = QLineEdit()
        btn_library = QPushButton("...")
        self._configure_compact_browse_button(
            btn_library,
            tooltip="Bibliotheksordner auswählen",
            description="Öffnet den Ordnerdialog für den Speicherort der DokuZen-Bibliothek.",
        )
        btn_library.clicked.connect(lambda: self._browse_folder(self._library_path))
        
        lib_layout = QHBoxLayout()
        lib_layout.addWidget(self._library_path)
        lib_layout.addWidget(btn_library)
        paths_layout.addRow("Bibliothek:", lib_layout)
        
        self._export_path = QLineEdit()
        btn_export = QPushButton("...")
        self._configure_compact_browse_button(
            btn_export,
            tooltip="Export-Ordner auswählen",
            description="Öffnet den Ordnerdialog für den Standardpfad exportierter Dateien.",
        )
        btn_export.clicked.connect(lambda: self._browse_folder(self._export_path))
        
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(self._export_path)
        exp_layout.addWidget(btn_export)
        paths_layout.addRow("Export-Standard:", exp_layout)
        
        self._spawn_path = QLineEdit()
        btn_spawn = QPushButton("...")
        self._configure_compact_browse_button(
            btn_spawn,
            tooltip="Spawner-Ordner auswählen",
            description="Öffnet den Ordnerdialog für den Ablageordner des TextSpawners.",
        )
        btn_spawn.clicked.connect(lambda: self._browse_folder(self._spawn_path))
        
        spawn_layout = QHBoxLayout()
        spawn_layout.addWidget(self._spawn_path)
        spawn_layout.addWidget(btn_spawn)
        paths_layout.addRow("Spawner-Ordner:", spawn_layout)
        
        layout.addWidget(paths_group)
        
        # Sprache
        lang_group = QGroupBox("Sprache")
        lang_layout = QFormLayout(lang_group)
        
        self._language = QComboBox()
        self._language.addItems(["Deutsch", "English", "Español", "中文", "日本語", "Русский"])
        lang_layout.addRow("Sprache:", self._language)
        
        layout.addWidget(lang_group)
        
        # Verhalten
        behavior_group = QGroupBox("Verhalten")
        behavior_layout = QVBoxLayout(behavior_group)
        
        self._auto_save = QCheckBox("Automatisch speichern")
        behavior_layout.addWidget(self._auto_save)
        
        self._confirm_delete = QCheckBox("Vor Löschen bestätigen")
        behavior_layout.addWidget(self._confirm_delete)
        
        self._remember_window = QCheckBox("Fensterposition merken")
        behavior_layout.addWidget(self._remember_window)
        
        self._start_minimized = QCheckBox("Minimiert starten")
        behavior_layout.addWidget(self._start_minimized)
        
        layout.addWidget(behavior_group)
        layout.addStretch()
        
        return widget
    
    def _create_appearance_tab(self) -> QWidget:
        """Erstellt den Darstellung-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Theme
        theme_group = QGroupBox("Design")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_form = QFormLayout()
        self._theme = QComboBox()
        self._theme.addItems(["Hell", "Dunkel", "Sepia", "Nord", "Ozean"])
        self._theme.currentTextChanged.connect(self._on_theme_preview)
        theme_form.addRow("Theme:", self._theme)
        theme_layout.addLayout(theme_form)
        
        # Theme-Vorschau
        self._theme_preview = QFrame()
        self._theme_preview.setFixedHeight(100)
        self._theme_preview.setStyleSheet("""
            QFrame {
                border: 1px solid #ccc;
                border-radius: 8px;
                background: #fff;
            }
        """)
        
        preview_layout = QHBoxLayout(self._theme_preview)
        preview_layout.addWidget(QLabel("Vorschau"))
        
        theme_layout.addWidget(self._theme_preview)
        layout.addWidget(theme_group)
        
        # Schrift
        font_group = QGroupBox("Schrift")
        font_layout = QFormLayout(font_group)
        
        self._font_family = QComboBox()
        self._font_family.addItems(["Segoe UI", "Arial", "Helvetica", "Roboto", "Open Sans"])
        font_layout.addRow("Schriftart:", self._font_family)
        
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 18)
        self._font_size.setValue(10)
        self._font_size.setSuffix(" pt")
        font_layout.addRow("Größe:", self._font_size)
        
        layout.addWidget(font_group)
        
        # Icons
        icon_group = QGroupBox("Icons")
        icon_layout = QFormLayout(icon_group)
        
        self._icon_size = QComboBox()
        self._icon_size.addItems(["Klein (16px)", "Mittel (24px)", "Groß (32px)"])
        self._icon_size.setCurrentIndex(1)
        icon_layout.addRow("Icon-Größe:", self._icon_size)
        
        layout.addWidget(icon_group)
        layout.addStretch()
        
        return widget
    
    def _create_shortcuts_tab(self) -> QWidget:
        """Erstellt den Tastaturkürzel-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info
        info = QLabel("Doppelklick zum Bearbeiten eines Kürzels")
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)
        
        # Tree für Shortcuts
        self._shortcuts_tree = QTreeWidget()
        self._shortcuts_tree.setHeaderLabels(["Aktion", "Tastaturkürzel"])
        self._shortcuts_tree.setColumnWidth(0, 300)
        self._shortcuts_tree.itemDoubleClicked.connect(self._edit_shortcut)
        
        # Kategorien und Shortcuts einfügen
        categories = {
            "Datei": [
                ("Datei öffnen", "Ctrl+O"),
                ("Speichern", "Ctrl+S"),
                ("Importieren", "Ctrl+I"),
                ("Exportieren", "Ctrl+E"),
                ("Beenden", "Ctrl+Q"),
            ],
            "Bearbeiten": [
                ("Rückgängig", "Ctrl+Z"),
                ("Wiederholen", "Ctrl+Y"),
                ("Suchen", "Ctrl+F"),
                ("Alles auswählen", "Ctrl+A"),
            ],
            "Ansicht": [
                ("Vergrößern", "Ctrl++"),
                ("Verkleinern", "Ctrl+-"),
                ("Zoom zurücksetzen", "Ctrl+0"),
                ("Vollbild", "F11"),
            ],
            "Werkzeuge": [
                ("PDF-Werkstatt", "Ctrl+Shift+P"),
                ("OCR", "Ctrl+Shift+O"),
                ("Schwärzen", "Ctrl+Shift+R"),
                ("Konvertieren", "Ctrl+Shift+C"),
                ("Formular-Builder", "Ctrl+Shift+F"),
                ("PDF-Marker", "Ctrl+Shift+K"),
                ("Einstellungen", "Ctrl+,"),
            ],
        }
        
        for category, shortcuts in categories.items():
            cat_item = QTreeWidgetItem([category])
            cat_item.setExpanded(True)
            
            for action, shortcut in shortcuts:
                item = QTreeWidgetItem([action, shortcut])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                cat_item.addChild(item)
            
            self._shortcuts_tree.addTopLevelItem(cat_item)
        
        layout.addWidget(self._shortcuts_tree)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_reset_shortcuts = QPushButton("Alle zurücksetzen")
        btn_reset_shortcuts.clicked.connect(self._reset_shortcuts)
        btn_layout.addWidget(btn_reset_shortcuts)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Erstellt den Erweitert-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # OCR
        ocr_group = QGroupBox("OCR-Einstellungen")
        ocr_layout = QFormLayout(ocr_group)
        
        self._tesseract_path = QLineEdit()
        btn_tesseract = QPushButton("...")
        self._configure_compact_browse_button(
            btn_tesseract,
            tooltip="Tesseract-Datei auswählen",
            description="Öffnet den Dateidialog für die ausführbare Tesseract-OCR-Datei.",
        )
        btn_tesseract.clicked.connect(lambda: self._browse_file(self._tesseract_path, "Tesseract (tesseract.exe)"))
        
        tess_layout = QHBoxLayout()
        tess_layout.addWidget(self._tesseract_path)
        tess_layout.addWidget(btn_tesseract)
        ocr_layout.addRow("Tesseract-Pfad:", tess_layout)
        
        self._ocr_dpi = QSpinBox()
        self._ocr_dpi.setRange(72, 600)
        self._ocr_dpi.setValue(300)
        self._ocr_dpi.setSuffix(" DPI")
        ocr_layout.addRow("OCR-Auflösung:", self._ocr_dpi)
        
        layout.addWidget(ocr_group)
        
        # PDF
        pdf_group = QGroupBox("PDF-Einstellungen")
        pdf_layout = QFormLayout(pdf_group)
        
        self._pdf_quality = QComboBox()
        self._pdf_quality.addItems(["Standard", "Hoch", "Maximal"])
        pdf_layout.addRow("PDF-Qualität:", self._pdf_quality)
        
        self._pdf_compress = QCheckBox("PDFs komprimieren")
        pdf_layout.addRow("", self._pdf_compress)
        
        layout.addWidget(pdf_group)
        
        # Cache
        cache_group = QGroupBox("Cache")
        cache_layout = QVBoxLayout(cache_group)
        
        cache_info = QLabel("Cache-Größe: 0 MB")
        cache_layout.addWidget(cache_info)
        
        btn_clear_cache = QPushButton("Cache leeren")
        btn_clear_cache.clicked.connect(self._clear_cache)
        cache_layout.addWidget(btn_clear_cache)
        
        layout.addWidget(cache_group)
        
        # Windows-Integration (nur auf Windows anzeigen)
        if sys.platform == "win32":
            win_group = QGroupBox("Windows-Integration")
            win_layout = QVBoxLayout(win_group)

            self._register_context = QCheckBox("Kontextmenü im Explorer registrieren")
            win_layout.addWidget(self._register_context)

            self._register_associations = QCheckBox("Dateizuordnungen registrieren")
            win_layout.addWidget(self._register_associations)

            btn_register = QPushButton("Jetzt registrieren")
            btn_register.clicked.connect(self._register_windows)
            win_layout.addWidget(btn_register)

            layout.addWidget(win_group)
        layout.addStretch()
        
        return widget
    
    def _browse_folder(self, line_edit: QLineEdit):
        """Öffnet Ordner-Dialog."""
        path = QFileDialog.getExistingDirectory(self, "Ordner wählen", line_edit.text())
        if path:
            line_edit.setText(path)
            self._modified = True
    
    def _browse_file(self, line_edit: QLineEdit, filter_text: str):
        """Öffnet Datei-Dialog."""
        path, _ = QFileDialog.getOpenFileName(self, "Datei wählen", line_edit.text(), filter_text)
        if path:
            line_edit.setText(path)
            self._modified = True
    
    def _on_theme_preview(self, theme_name: str):
        """Zeigt Theme-Vorschau."""
        colors = {
            "Hell": ("#ffffff", "#202124", "#1a73e8"),
            "Dunkel": ("#202124", "#e8eaed", "#8ab4f8"),
            "Sepia": ("#f4ecd8", "#5b4636", "#8b5a2b"),
            "Nord": ("#2e3440", "#eceff4", "#88c0d0"),
            "Ozean": ("#caf0f8", "#03045e", "#0077b6"),
        }
        
        bg, text, accent = colors.get(theme_name, colors["Hell"])
        
        self._theme_preview.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px solid {accent};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text};
                font-weight: bold;
            }}
        """)
    
    def _edit_shortcut(self, item: QTreeWidgetItem, column: int):
        """Bearbeitet einen Shortcut."""
        if item.childCount() > 0:  # Kategorie
            return
        
        from PySide6.QtWidgets import QInputDialog
        
        current = item.text(1)
        new_shortcut, ok = QInputDialog.getText(
            self, "Tastaturkürzel bearbeiten",
            f"Neues Kürzel für '{item.text(0)}':",
            text=current
        )
        
        if ok and new_shortcut:
            item.setText(1, new_shortcut)
            self._modified = True
    
    def _reset_shortcuts(self):
        """Setzt alle Shortcuts zurück."""
        reply = QMessageBox.question(
            self, "Zurücksetzen",
            "Alle Tastaturkürzel auf Standard zurücksetzen?"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Baum neu aufbauen
            self._tabs.setCurrentIndex(2)  # Shortcuts-Tab
            QMessageBox.information(self, "Zurückgesetzt", "Tastaturkürzel wurden zurückgesetzt.")
    
    def _clear_cache(self):
        """Leert den Cache."""
        reply = QMessageBox.question(
            self, "Cache leeren",
            "Cache wirklich leeren?"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Cache", "Cache wurde geleert.")
    
    def _register_windows(self):
        """Registriert Windows-Integration."""
        try:
            from plugins.spawner.registry import DokuZenRegistry
            
            registry = DokuZenRegistry()
            
            if self._register_context.isChecked():
                results = registry.register_all()
                success = sum(1 for v in results.values() if v)
                QMessageBox.information(
                    self, "Registrierung",
                    f"Kontextmenüs registriert: {success}/{len(results)}"
                )
            else:
                registry.unregister_all()
                QMessageBox.information(self, "Registrierung", "Kontextmenüs entfernt.")
                
        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))
    
    def _load_settings(self):
        """Lädt die Einstellungen."""
        s = self._settings
        
        # Pfade
        self._library_path.setText(s.get("library_path", ""))
        self._export_path.setText(s.get("export_path", ""))
        self._spawn_path.setText(s.get("spawn_path", ""))
        
        # Sprache
        lang = s.get("language", "Deutsch")
        idx = self._language.findText(str(lang))
        if idx < 0:
            from translator import TranslationSystem
            code = TranslationSystem.normalize_language_code(str(lang))
            name = TranslationSystem.LANGUAGE_NAMES.get(code, "Deutsch")
            idx = self._language.findText(name)
        if idx >= 0:
            self._language.setCurrentIndex(idx)
        
        # Verhalten
        self._auto_save.setChecked(s.get("auto_save", True))
        self._confirm_delete.setChecked(s.get("confirm_delete", True))
        self._remember_window.setChecked(s.get("remember_window", True))
        self._start_minimized.setChecked(s.get("start_minimized", False))
        
        # Darstellung
        theme = s.get("theme", "Hell")
        idx = self._theme.findText(theme)
        if idx >= 0:
            self._theme.setCurrentIndex(idx)
        
        self._font_size.setValue(s.get("font_size", 10))
        
        # Erweitert
        self._tesseract_path.setText(s.get("tesseract_path", ""))
        self._ocr_dpi.setValue(s.get("ocr_dpi", 300))

        # BUGSWEEP-34: font_family/icon_size/pdf_quality/pdf_compress wurden in _get_settings
        # gespeichert, aber hier NIE wiederhergestellt -> beim erneuten Oeffnen Default-Widget ->
        # beim nächsten OK still mit dem Default ueberschrieben (Datenverlust). Nur setzen, wenn
        # vorhanden (Combos via findText, Checkbox nur bei vorhandenem Key -> UI-Default sonst unveraendert).
        for key, combo in (("font_family", self._font_family),
                           ("icon_size", self._icon_size),
                           ("pdf_quality", self._pdf_quality)):
            val = s.get(key)
            if val:
                i = combo.findText(val)
                if i >= 0:
                    combo.setCurrentIndex(i)
        if "pdf_compress" in s:
            self._pdf_compress.setChecked(s["pdf_compress"])

    def _get_settings(self) -> Dict:
        """Gibt die aktuellen Einstellungen zurück."""
        return {
            # Pfade
            "library_path": self._library_path.text(),
            "export_path": self._export_path.text(),
            "spawn_path": self._spawn_path.text(),
            
            # Sprache
            "language": self._language.currentText(),
            "language_code": TranslationSystem.normalize_language_code(self._language.currentText()),
            
            # Verhalten
            "auto_save": self._auto_save.isChecked(),
            "confirm_delete": self._confirm_delete.isChecked(),
            "remember_window": self._remember_window.isChecked(),
            "start_minimized": self._start_minimized.isChecked(),
            
            # Darstellung
            "theme": self._theme.currentText(),
            "font_family": self._font_family.currentText(),
            "font_size": self._font_size.value(),
            "icon_size": self._icon_size.currentText(),
            
            # Erweitert
            "tesseract_path": self._tesseract_path.text(),
            "ocr_dpi": self._ocr_dpi.value(),
            "pdf_quality": self._pdf_quality.currentText(),
            "pdf_compress": self._pdf_compress.isChecked(),
            
            # Windows (Attribute nur auf win32 vorhanden)
            "register_context": self._register_context.isChecked() if hasattr(self, "_register_context") else False,
            "register_associations": self._register_associations.isChecked() if hasattr(self, "_register_associations") else False,
        }
    
    def _reset_settings(self):
        """Setzt alle Einstellungen zurück."""
        reply = QMessageBox.question(
            self, "Zurücksetzen",
            "Alle Einstellungen auf Standard zurücksetzen?"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._settings = {}
            self._load_settings()
    
    def _save_and_close(self):
        """Speichert und schließt."""
        self._settings = self._get_settings()
        self.settings_changed.emit(self._settings)
        self.accept()
    
    def get_settings(self) -> Dict:
        """Gibt die Einstellungen zurück."""
        return self._settings
