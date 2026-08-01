#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Workshop Dialog
=====================================
Zentraler Dialog für PDF-Operationen.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox,
    QFormLayout, QSpinBox, QComboBox, QCheckBox, QLineEdit,
    QAbstractItemView, QSplitter, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon

from utils.logger import LoggerMixin
from core.pdf import PDFReader, PDFMerger, MergeItem, PDFSecurity
from core.pdf.page_ranges import parse_page_range_notation


class PDFWorkshopDialog(QDialog, LoggerMixin):
    """
    PDF-Werkstatt - Zentraler Dialog für alle PDF-Operationen.
    
    Tabs:
    - Zusammenführen
    - Aufteilen
    - Seiten extrahieren
    - Entsperren
    - Verschlüsseln
    - Info
    """
    
    def __init__(self, parent=None, initial_files: List[str] = None):
        super().__init__(parent)
        
        self._initial_files = initial_files or []
        self._setup_ui()
        
        # Initiale Dateien laden
        if self._initial_files:
            self._add_files_to_merge(self._initial_files)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("PDF-Werkstatt")
        self.setMinimumSize(700, 500)
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Tab-Widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # Tabs erstellen
        self._tabs.addTab(self._create_merge_tab(), "Zusammenführen")
        self._tabs.addTab(self._create_split_tab(), "Aufteilen")
        self._tabs.addTab(self._create_extract_tab(), "Seiten extrahieren")
        self._tabs.addTab(self._create_unlock_tab(), "Entsperren")
        self._tabs.addTab(self._create_encrypt_tab(), "Verschlüsseln")
        self._tabs.addTab(self._create_info_tab(), "PDF-Info")
        
        # Fortschrittsbalken
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
        
        # Schließen-Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
    
    # === Merge Tab ===
    
    def _create_merge_tab(self) -> QWidget:
        """Erstellt den Zusammenführen-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Dateiliste
        list_group = QGroupBox("PDF-Dateien (Reihenfolge durch Drag & Drop ändern)")
        list_layout = QVBoxLayout(list_group)
        
        self._merge_list = QListWidget()
        self._merge_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._merge_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        list_layout.addWidget(self._merge_list)
        
        # Buttons für Liste
        btn_row = QHBoxLayout()
        
        btn_add = QPushButton("Hinzufügen...")
        btn_add.clicked.connect(self._on_merge_add)
        btn_row.addWidget(btn_add)
        
        btn_remove = QPushButton("Entfernen")
        btn_remove.clicked.connect(self._on_merge_remove)
        btn_row.addWidget(btn_remove)
        
        btn_up = QPushButton("↑")
        btn_up.setFixedWidth(30)
        btn_up.clicked.connect(self._on_merge_up)
        btn_row.addWidget(btn_up)
        
        btn_down = QPushButton("↓")
        btn_down.setFixedWidth(30)
        btn_down.clicked.connect(self._on_merge_down)
        btn_row.addWidget(btn_down)
        
        btn_row.addStretch()
        list_layout.addLayout(btn_row)
        
        layout.addWidget(list_group)
        
        # Ausgabe
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Ausgabedatei:"))
        
        self._merge_output = QLineEdit()
        self._merge_output.setPlaceholderText("Ziel-PDF wählen...")
        output_layout.addWidget(self._merge_output)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._on_merge_browse_output)
        output_layout.addWidget(btn_browse)
        
        layout.addLayout(output_layout)
        
        # Zusammenführen-Button
        btn_merge = QPushButton("PDFs zusammenführen")
        btn_merge.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_merge.clicked.connect(self._on_merge_execute)
        layout.addWidget(btn_merge)
        
        return widget
    
    def _add_files_to_merge(self, files: List[str]):
        """Fügt Dateien zur Merge-Liste hinzu."""
        for f in files:
            if f.lower().endswith('.pdf'):
                item = QListWidgetItem(Path(f).name)
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setToolTip(f)
                self._merge_list.addItem(item)
    
    def _on_merge_add(self):
        """Fügt PDFs zur Liste hinzu."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "PDFs hinzufügen", "", "PDF-Dateien (*.pdf)"
        )
        self._add_files_to_merge(files)
    
    def _on_merge_remove(self):
        """Entfernt ausgewählte PDFs."""
        for item in self._merge_list.selectedItems():
            self._merge_list.takeItem(self._merge_list.row(item))
    
    def _on_merge_up(self):
        """Verschiebt Auswahl nach oben."""
        row = self._merge_list.currentRow()
        if row > 0:
            item = self._merge_list.takeItem(row)
            self._merge_list.insertItem(row - 1, item)
            self._merge_list.setCurrentRow(row - 1)
    
    def _on_merge_down(self):
        """Verschiebt Auswahl nach unten."""
        row = self._merge_list.currentRow()
        if row < self._merge_list.count() - 1:
            item = self._merge_list.takeItem(row)
            self._merge_list.insertItem(row + 1, item)
            self._merge_list.setCurrentRow(row + 1)
    
    def _on_merge_browse_output(self):
        """Wählt Ausgabedatei."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Ausgabe-PDF", "", "PDF-Dateien (*.pdf)"
        )
        if path:
            if not path.lower().endswith('.pdf'):
                path += '.pdf'
            self._merge_output.setText(path)
    
    def _on_merge_execute(self):
        """Führt PDFs zusammen."""
        if self._merge_list.count() < 2:
            QMessageBox.warning(self, "Fehler", "Mindestens 2 PDFs erforderlich.")
            return
        
        output = self._merge_output.text().strip()
        if not output:
            QMessageBox.warning(self, "Fehler", "Bitte Ausgabedatei angeben.")
            return
        
        # Dateien sammeln
        items = []
        for i in range(self._merge_list.count()):
            path = self._merge_list.item(i).data(Qt.ItemDataRole.UserRole)
            items.append(MergeItem(path=path))
        
        # Zusammenführen
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate
        
        merger = PDFMerger()
        result = merger.merge(items, output)
        
        self._progress.setVisible(False)
        
        if result.success:
            QMessageBox.information(
                self, "Erfolg",
                f"PDF erstellt: {result.output_path}\n{result.page_count} Seiten"
            )
        else:
            QMessageBox.critical(self, "Fehler", f"Fehler: {result.error}")
    
    # === Split Tab ===
    
    def _create_split_tab(self) -> QWidget:
        """Erstellt den Aufteilen-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Eingabe
        input_group = QGroupBox("Eingabe-PDF")
        input_layout = QHBoxLayout(input_group)
        
        self._split_input = QLineEdit()
        self._split_input.setPlaceholderText("PDF zum Aufteilen wählen...")
        input_layout.addWidget(self._split_input)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._on_split_browse_input)
        input_layout.addWidget(btn_browse)
        
        layout.addWidget(input_group)
        
        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QFormLayout(options_group)
        
        self._split_pages = QSpinBox()
        self._split_pages.setRange(1, 100)
        self._split_pages.setValue(1)
        options_layout.addRow("Seiten pro Datei:", self._split_pages)
        
        layout.addWidget(options_group)
        
        # Ausgabe
        output_group = QGroupBox("Ausgabe-Verzeichnis")
        output_layout = QHBoxLayout(output_group)
        
        self._split_output = QLineEdit()
        output_layout.addWidget(self._split_output)
        
        btn_browse_out = QPushButton("...")
        btn_browse_out.setFixedWidth(30)
        btn_browse_out.clicked.connect(self._on_split_browse_output)
        output_layout.addWidget(btn_browse_out)
        
        layout.addWidget(output_group)
        
        # Button
        btn_split = QPushButton("PDF aufteilen")
        btn_split.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_split.clicked.connect(self._on_split_execute)
        layout.addWidget(btn_split)
        
        layout.addStretch()
        return widget
    
    def _on_split_browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF wählen", "", "PDF (*.pdf)")
        if path:
            self._split_input.setText(path)
    
    def _on_split_browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Ausgabe-Verzeichnis")
        if path:
            self._split_output.setText(path)
    
    def _on_split_execute(self):
        input_path = self._split_input.text().strip()
        output_dir = self._split_output.text().strip()
        
        if not input_path or not output_dir:
            QMessageBox.warning(self, "Fehler", "Bitte Ein- und Ausgabe angeben.")
            return
        
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        
        merger = PDFMerger()
        results = merger.split(input_path, output_dir, self._split_pages.value())
        
        self._progress.setVisible(False)
        
        success_count = sum(1 for r in results if r.success)
        QMessageBox.information(
            self, "Fertig",
            f"{success_count} Dateien erstellt in:\n{output_dir}"
        )

    # === Extract Tab ===
    
    def _create_extract_tab(self) -> QWidget:
        """Erstellt den Seiten-Extrahieren-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Eingabe
        input_group = QGroupBox("Eingabe-PDF")
        input_layout = QHBoxLayout(input_group)
        
        self._extract_input = QLineEdit()
        input_layout.addWidget(self._extract_input)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._on_extract_browse_input)
        input_layout.addWidget(btn_browse)
        
        layout.addWidget(input_group)
        
        # Seiten
        pages_group = QGroupBox("Seiten (z.B. 1,3,5-10)")
        pages_layout = QVBoxLayout(pages_group)
        
        self._extract_pages = QLineEdit()
        self._extract_pages.setPlaceholderText("1,2,3 oder 1-5 oder 1,3,5-10")
        pages_layout.addWidget(self._extract_pages)
        
        self._extract_info = QLabel("Seitenanzahl: -")
        pages_layout.addWidget(self._extract_info)
        
        layout.addWidget(pages_group)
        
        # Ausgabe
        output_group = QGroupBox("Ausgabe-PDF")
        output_layout = QHBoxLayout(output_group)
        
        self._extract_output = QLineEdit()
        output_layout.addWidget(self._extract_output)
        
        btn_browse_out = QPushButton("...")
        btn_browse_out.setFixedWidth(30)
        btn_browse_out.clicked.connect(self._on_extract_browse_output)
        output_layout.addWidget(btn_browse_out)
        
        layout.addWidget(output_group)
        
        # Button
        btn_extract = QPushButton("Seiten extrahieren")
        btn_extract.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_extract.clicked.connect(self._on_extract_execute)
        layout.addWidget(btn_extract)
        
        layout.addStretch()
        return widget
    
    def _on_extract_browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF wählen", "", "PDF (*.pdf)")
        if path:
            self._extract_input.setText(path)
            # Info aktualisieren
            with PDFReader() as reader:
                if reader.open(path):
                    self._extract_info.setText(f"Seitenanzahl: {reader.page_count}")
    
    def _on_extract_browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ausgabe-PDF", "", "PDF (*.pdf)")
        if path:
            self._extract_output.setText(path)
    
    def _parse_page_range(self, text: str) -> List[int]:
        """Parst Seitenangaben wie '1,3,5-10'. Gibt [] bei ungültigem Input zurück."""
        return parse_page_range_notation(text)
    
    def _on_extract_execute(self):
        input_path = self._extract_input.text().strip()
        output_path = self._extract_output.text().strip()
        pages_text = self._extract_pages.text().strip()
        
        if not all([input_path, output_path, pages_text]):
            QMessageBox.warning(self, "Fehler", "Bitte alle Felder ausfüllen.")
            return
        
        pages = self._parse_page_range(pages_text)
        if not pages:
            QMessageBox.warning(self, "Fehler", "Ungültige Seitenangabe.")
            return
        
        merger = PDFMerger()
        result = merger.extract_pages(input_path, output_path, pages)
        
        if result.success:
            QMessageBox.information(self, "Erfolg", f"Erstellt: {result.output_path}")
        else:
            QMessageBox.critical(self, "Fehler", result.error)
    
    # === Unlock Tab ===
    
    def _create_unlock_tab(self) -> QWidget:
        """Erstellt den Entsperren-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info
        info = QLabel(
            "Entfernt Passwortschutz und Einschränkungen von PDFs.\n"
            "Funktioniert bei PDFs mit nur Owner-Passwort auch ohne Kennwort."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info)
        
        # Eingabe
        input_group = QGroupBox("Geschützte PDF")
        input_layout = QHBoxLayout(input_group)
        
        self._unlock_input = QLineEdit()
        input_layout.addWidget(self._unlock_input)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._on_unlock_browse_input)
        input_layout.addWidget(btn_browse)
        
        layout.addWidget(input_group)
        
        # Passwort (optional)
        pw_group = QGroupBox("Passwort (falls bekannt)")
        pw_layout = QHBoxLayout(pw_group)
        
        self._unlock_password = QLineEdit()
        self._unlock_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._unlock_password.setPlaceholderText("Optional - leer lassen wenn unbekannt")
        pw_layout.addWidget(self._unlock_password)
        
        layout.addWidget(pw_group)
        
        # Ausgabe
        output_group = QGroupBox("Entsperrte PDF")
        output_layout = QHBoxLayout(output_group)
        
        self._unlock_output = QLineEdit()
        output_layout.addWidget(self._unlock_output)
        
        btn_browse_out = QPushButton("...")
        btn_browse_out.setFixedWidth(30)
        btn_browse_out.clicked.connect(self._on_unlock_browse_output)
        output_layout.addWidget(btn_browse_out)
        
        layout.addWidget(output_group)
        
        # Button
        btn_unlock = QPushButton("PDF entsperren")
        btn_unlock.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_unlock.clicked.connect(self._on_unlock_execute)
        layout.addWidget(btn_unlock)
        
        layout.addStretch()
        return widget
    
    def _on_unlock_browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF wählen", "", "PDF (*.pdf)")
        if path:
            self._unlock_input.setText(path)
            # Auto-Ausgabe
            stem = Path(path).stem
            parent = Path(path).parent
            self._unlock_output.setText(str(parent / f"{stem}_entsperrt.pdf"))
    
    def _on_unlock_browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ausgabe-PDF", "", "PDF (*.pdf)")
        if path:
            self._unlock_output.setText(path)
    
    def _on_unlock_execute(self):
        input_path = self._unlock_input.text().strip()
        output_path = self._unlock_output.text().strip()
        password = self._unlock_password.text()
        
        if not input_path or not output_path:
            QMessageBox.warning(self, "Fehler", "Bitte Ein- und Ausgabe angeben.")
            return
        
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        
        security = PDFSecurity()
        result = security.unlock(input_path, output_path, password)
        
        self._progress.setVisible(False)
        
        if result.success:
            QMessageBox.information(self, "Erfolg", f"PDF entsperrt:\n{result.output_path}")
        else:
            QMessageBox.critical(self, "Fehler", f"Konnte nicht entsperren:\n{result.error}")
    
    # === Encrypt Tab ===
    
    def _create_encrypt_tab(self) -> QWidget:
        """Erstellt den Verschlüsseln-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Eingabe
        input_group = QGroupBox("Eingabe-PDF")
        input_layout = QHBoxLayout(input_group)
        
        self._encrypt_input = QLineEdit()
        input_layout.addWidget(self._encrypt_input)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._on_encrypt_browse_input)
        input_layout.addWidget(btn_browse)
        
        layout.addWidget(input_group)
        
        # Passwort
        pw_group = QGroupBox("Passwort")
        pw_layout = QFormLayout(pw_group)
        
        self._encrypt_password = QLineEdit()
        self._encrypt_password.setEchoMode(QLineEdit.EchoMode.Password)
        pw_layout.addRow("Passwort:", self._encrypt_password)
        
        self._encrypt_password2 = QLineEdit()
        self._encrypt_password2.setEchoMode(QLineEdit.EchoMode.Password)
        pw_layout.addRow("Bestätigen:", self._encrypt_password2)
        
        self._encrypt_method = QComboBox()
        self._encrypt_method.addItems(["AES-256 (empfohlen)", "AES-128", "RC4-128"])
        pw_layout.addRow("Methode:", self._encrypt_method)
        
        layout.addWidget(pw_group)
        
        # Ausgabe
        output_group = QGroupBox("Ausgabe-PDF")
        output_layout = QHBoxLayout(output_group)
        
        self._encrypt_output = QLineEdit()
        output_layout.addWidget(self._encrypt_output)
        
        btn_browse_out = QPushButton("...")
        btn_browse_out.setFixedWidth(30)
        btn_browse_out.clicked.connect(self._on_encrypt_browse_output)
        output_layout.addWidget(btn_browse_out)
        
        layout.addWidget(output_group)
        
        # Button
        btn_encrypt = QPushButton("PDF verschlüsseln")
        btn_encrypt.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_encrypt.clicked.connect(self._on_encrypt_execute)
        layout.addWidget(btn_encrypt)
        
        layout.addStretch()
        return widget
    
    def _on_encrypt_browse_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF wählen", "", "PDF (*.pdf)")
        if path:
            self._encrypt_input.setText(path)
    
    def _on_encrypt_browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ausgabe-PDF", "", "PDF (*.pdf)")
        if path:
            self._encrypt_output.setText(path)
    
    def _on_encrypt_execute(self):
        input_path = self._encrypt_input.text().strip()
        output_path = self._encrypt_output.text().strip()
        pw1 = self._encrypt_password.text()
        pw2 = self._encrypt_password2.text()
        
        if not all([input_path, output_path, pw1]):
            QMessageBox.warning(self, "Fehler", "Bitte alle Felder ausfüllen.")
            return
        
        if pw1 != pw2:
            QMessageBox.warning(self, "Fehler", "Passwörter stimmen nicht überein.")
            return
        
        from core.pdf.security import EncryptionMethod
        methods = {
            0: EncryptionMethod.AES_256,
            1: EncryptionMethod.AES_128,
            2: EncryptionMethod.RC4_128
        }
        method = methods.get(self._encrypt_method.currentIndex(), EncryptionMethod.AES_256)
        
        security = PDFSecurity()
        result = security.encrypt(input_path, output_path, user_password=pw1, method=method)
        
        if result.success:
            QMessageBox.information(self, "Erfolg", f"PDF verschlüsselt:\n{result.output_path}")
        else:
            QMessageBox.critical(self, "Fehler", result.error)
    
    # === Info Tab ===
    
    def _create_info_tab(self) -> QWidget:
        """Erstellt den Info-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Eingabe
        input_layout = QHBoxLayout()
        
        self._info_input = QLineEdit()
        self._info_input.setPlaceholderText("PDF auswählen...")
        input_layout.addWidget(self._info_input)
        
        btn_browse = QPushButton("PDF wählen...")
        btn_browse.clicked.connect(self._on_info_browse)
        input_layout.addWidget(btn_browse)
        
        layout.addLayout(input_layout)
        
        # Info-Anzeige
        self._info_text = QTextEdit()
        self._info_text.setReadOnly(True)
        self._info_text.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self._info_text)
        
        return widget
    
    def _on_info_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF wählen", "", "PDF (*.pdf)")
        if path:
            self._info_input.setText(path)
            self._show_pdf_info(path)
    
    def _show_pdf_info(self, path: str):
        """Zeigt PDF-Informationen an."""
        with PDFReader() as reader:
            if not reader.open(path):
                self._info_text.setText("Fehler beim Öffnen der PDF.")
                return

            info = reader.get_info()
        
        if not info:
            self._info_text.setText("Keine Informationen verfügbar.")
            return
        
        # Formatierte Ausgabe
        lines = [
            f"Datei: {Path(path).name}",
            f"Pfad: {path}",
            "",
            f"Seitenanzahl: {info.page_count}",
            f"Dateigröße: {info.file_size / 1024:.1f} KB",
            "",
            f"Verschlüsselt: {'Ja' if info.is_encrypted else 'Nein'}",
            f"Gesperrt: {'Ja' if info.is_locked else 'Nein'}",
            f"Hat Text: {'Ja' if info.has_text else 'Nein (evtl. Scan)'}",
            f"Hat Bilder: {'Ja' if info.has_images else 'Nein'}",
            "",
            "=== Metadaten ===",
            f"Titel: {info.metadata.title or '-'}",
            f"Autor: {info.metadata.author or '-'}",
            f"Betreff: {info.metadata.subject or '-'}",
            f"Ersteller: {info.metadata.creator or '-'}",
            f"Erzeuger: {info.metadata.producer or '-'}",
        ]
        
        if info.metadata.creation_date:
            lines.append(f"Erstellt: {info.metadata.creation_date}")
        if info.metadata.modification_date:
            lines.append(f"Geändert: {info.metadata.modification_date}")
        
        self._info_text.setText("\n".join(lines))
