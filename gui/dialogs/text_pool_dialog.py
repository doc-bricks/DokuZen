#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Text Pool Dialog
===================================
Dialog zum Zusammenführen und Bearbeiten von Texten.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QWidget,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter,
    QComboBox, QCheckBox, QLineEdit, QAbstractItemView,
    QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt

from utils.logger import LoggerMixin


class TextPoolDialog(QDialog, LoggerMixin):
    """
    Dialog zum Zusammenführen von Textdateien.
    
    Features:
    - Dateien per Drag & Drop hinzufügen
    - Reihenfolge ändern
    - Vorschau des kombinierten Texts
    - Verschiedene Trennzeichen
    - Export als TXT, MD, PDF
    """
    
    SEPARATORS = {
        "Leerzeile": "\n\n",
        "Doppelte Leerzeile": "\n\n\n",
        "Horizontale Linie": "\n\n---\n\n",
        "Dateiname-Header": "header",  # Speziell behandelt
        "Seitenumbruch (PDF)": "\n\n<!-- pagebreak -->\n\n",
        "Kein Trenner": "\n",
    }
    
    def __init__(self, parent=None, initial_files: List[str] = None):
        super().__init__(parent)
        
        self._files: List[str] = []
        self._initial_files = initial_files or []
        
        self._setup_ui()
        
        if self._initial_files:
            self._add_files(self._initial_files)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Text-Pooler")
        self.setMinimumSize(700, 500)
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Hauptsplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Linke Seite: Dateiliste
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_group = QGroupBox("Textdateien (Reihenfolge per Drag & Drop)")
        list_layout = QVBoxLayout(list_group)
        
        self._file_list = QListWidget()
        self._file_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._file_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._file_list.model().rowsMoved.connect(self._update_preview)
        list_layout.addWidget(self._file_list)
        
        # Buttons
        btn_row = QHBoxLayout()
        
        btn_add = QPushButton("Hinzufügen...")
        btn_add.clicked.connect(self._on_add_files)
        btn_row.addWidget(btn_add)
        
        btn_remove = QPushButton("Entfernen")
        btn_remove.clicked.connect(self._on_remove_files)
        btn_row.addWidget(btn_remove)
        
        btn_up = QPushButton("↑")
        btn_up.setFixedWidth(30)
        btn_up.clicked.connect(self._on_move_up)
        btn_row.addWidget(btn_up)
        
        btn_down = QPushButton("↓")
        btn_down.setFixedWidth(30)
        btn_down.clicked.connect(self._on_move_down)
        btn_row.addWidget(btn_down)
        
        btn_row.addStretch()
        list_layout.addLayout(btn_row)
        
        left_layout.addWidget(list_group)
        
        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QFormLayout(options_group)
        
        self._separator_combo = QComboBox()
        self._separator_combo.addItems(list(self.SEPARATORS.keys()))
        self._separator_combo.setCurrentText("Horizontale Linie")
        self._separator_combo.currentTextChanged.connect(self._update_preview)
        options_layout.addRow("Trenner:", self._separator_combo)
        
        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(["UTF-8", "Latin-1", "CP1252", "Auto-Erkennung"])
        options_layout.addRow("Encoding:", self._encoding_combo)
        
        self._chk_strip = QCheckBox("Leerzeilen am Anfang/Ende entfernen")
        self._chk_strip.setChecked(True)
        self._chk_strip.stateChanged.connect(self._update_preview)
        options_layout.addRow(self._chk_strip)
        
        left_layout.addWidget(options_group)
        
        splitter.addWidget(left_widget)
        
        # Rechte Seite: Vorschau
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_group = QGroupBox("Vorschau")
        preview_layout = QVBoxLayout(preview_group)
        
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet("font-family: Consolas, monospace;")
        preview_layout.addWidget(self._preview)
        
        # Info
        self._info_label = QLabel("")
        preview_layout.addWidget(self._info_label)
        
        right_layout.addWidget(preview_group)
        
        splitter.addWidget(right_widget)
        
        # Splitter-Größen
        splitter.setSizes([350, 550])
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        
        btn_save_txt = QPushButton("Als TXT speichern...")
        btn_save_txt.clicked.connect(lambda: self._on_save("txt"))
        btn_layout.addWidget(btn_save_txt)
        
        btn_save_md = QPushButton("Als MD speichern...")
        btn_save_md.clicked.connect(lambda: self._on_save("md"))
        btn_layout.addWidget(btn_save_md)
        
        btn_copy = QPushButton("In Zwischenablage")
        btn_copy.clicked.connect(self._on_copy)
        btn_layout.addWidget(btn_copy)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _add_files(self, files: List[str]):
        """Fügt Dateien zur Liste hinzu."""
        for f in files:
            path = Path(f)
            if path.exists() and path.suffix.lower() in ['.txt', '.md', '.py', '.log', '.json', '.xml', '.csv', '.html']:
                item = QListWidgetItem(path.name)
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(str(path))
                self._file_list.addItem(item)
                self._files.append(str(path))
        
        self._update_preview()
    
    def _on_add_files(self):
        """Dialog zum Hinzufügen von Dateien."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Textdateien hinzufügen", "",
            "Textdateien (*.txt *.md *.py *.log *.json *.xml *.csv *.html);;"
            "Alle Dateien (*.*)"
        )
        if files:
            self._add_files(files)
    
    def _on_remove_files(self):
        """Entfernt ausgewählte Dateien."""
        for item in self._file_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self._files:
                self._files.remove(path)
            self._file_list.takeItem(self._file_list.row(item))
        
        self._update_preview()
    
    def _on_move_up(self):
        """Verschiebt Auswahl nach oben."""
        row = self._file_list.currentRow()
        if row > 0:
            item = self._file_list.takeItem(row)
            self._file_list.insertItem(row - 1, item)
            self._file_list.setCurrentRow(row - 1)
            self._update_preview()
    
    def _on_move_down(self):
        """Verschiebt Auswahl nach unten."""
        row = self._file_list.currentRow()
        if row < self._file_list.count() - 1:
            item = self._file_list.takeItem(row)
            self._file_list.insertItem(row + 1, item)
            self._file_list.setCurrentRow(row + 1)
            self._update_preview()
    
    def _on_selection_changed(self):
        """Reagiert auf Änderung der Auswahl."""
        pass
    
    def _get_file_order(self) -> List[str]:
        """Gibt die Dateien in aktueller Reihenfolge zurück."""
        files = []
        for i in range(self._file_list.count()):
            path = self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
            files.append(path)
        return files
    
    def _read_file(self, filepath: str) -> str:
        """Liest eine Datei mit passendem Encoding."""
        encoding = self._encoding_combo.currentText()
        
        if encoding == "Auto-Erkennung":
            # Versuche verschiedene Encodings
            # BUGSWEEP-34: cp1252 VOR latin-1 — latin-1 dekodiert jedes Byte (wirft nie
            # UnicodeDecodeError), sonst wuerde cp1252 nie erreicht (Mojibake bei Windows-Dateien).
            for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
                try:
                    with open(filepath, 'r', encoding=enc) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            return f"[Fehler: Konnte {Path(filepath).name} nicht lesen]"
        else:
            enc_map = {"UTF-8": "utf-8", "Latin-1": "latin-1", "CP1252": "cp1252"}
            try:
                with open(filepath, 'r', encoding=enc_map.get(encoding, 'utf-8')) as f:
                    return f.read()
            except Exception as e:
                return f"[Fehler: {e}]"
    
    def _get_combined_text(self) -> str:
        """Kombiniert alle Texte."""
        files = self._get_file_order()
        
        if not files:
            return ""
        
        separator_name = self._separator_combo.currentText()
        separator = self.SEPARATORS.get(separator_name, "\n\n")
        use_header = separator == "header"
        
        if use_header:
            separator = "\n\n"
        
        texts = []
        
        for filepath in files:
            content = self._read_file(filepath)
            
            if self._chk_strip.isChecked():
                content = content.strip()
            
            if use_header:
                filename = Path(filepath).name
                header = f"# {filename}\n\n"
                content = header + content
            
            texts.append(content)
        
        return separator.join(texts)
    
    def _update_preview(self):
        """Aktualisiert die Vorschau."""
        text = self._get_combined_text()
        self._preview.setText(text)
        
        # Info aktualisieren
        file_count = self._file_list.count()
        char_count = len(text)
        word_count = len(text.split())
        line_count = text.count('\n') + 1 if text else 0
        
        self._info_label.setText(
            f"{file_count} Dateien | {char_count:,} Zeichen | "
            f"{word_count:,} Wörter | {line_count:,} Zeilen"
        )
    
    def _on_copy(self):
        """Kopiert in Zwischenablage."""
        text = self._get_combined_text()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "Kopiert", "Text wurde in die Zwischenablage kopiert.")
    
    def _on_save(self, format: str):
        """Speichert den kombinierten Text."""
        text = self._get_combined_text()
        
        if not text:
            QMessageBox.warning(self, "Fehler", "Keine Texte zum Speichern.")
            return
        
        if format == "txt":
            path, _ = QFileDialog.getSaveFileName(
                self, "Als TXT speichern", "", "Textdateien (*.txt)"
            )
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Als Markdown speichern", "", "Markdown (*.md)"
            )
        
        if path:
            try:
                # BUGSWEEP-34: atomar (tmp + replace) — sonst hinterlaesst ein Schreibfehler/Absturz
                # mitten im write eine halbe/getrunkte Zieldatei (Datenverlust bei gleichnamigem Ziel).
                tmp = Path(str(path) + ".tmp")
                with open(tmp, 'w', encoding='utf-8') as f:
                    f.write(text)
                tmp.replace(path)
                QMessageBox.information(self, "Gespeichert", f"Datei gespeichert:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")
    
    # === Drag & Drop ===
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()  # BUGSWEEP-34: Nicht-Datei-Drops sauber ablehnen
    
    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(url.toLocalFile())
        if files:
            self._add_files(files)
