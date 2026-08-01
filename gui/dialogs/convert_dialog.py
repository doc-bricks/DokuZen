#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Convert Dialog
================================
Dialog zur Format-Konvertierung.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QWidget,
    QPushButton, QLabel, QFileDialog, QProgressBar,
    QMessageBox, QFormLayout, QComboBox, QLineEdit,
    QListWidget, QListWidgetItem, QRadioButton,
    QButtonGroup, QAbstractItemView
)
from PySide6.QtCore import Qt

from utils.logger import LoggerMixin
from core.converter import FormatConverter, ConversionResult, OutputFormat


class ConvertDialog(QDialog, LoggerMixin):
    """
    Dialog zur Format-Konvertierung.
    
    Features:
    - Einzeldatei-Konvertierung
    - Batch-Konvertierung
    - Verschiedene Zielformate
    - Fortschrittsanzeige
    """
    
    # Format-Optionen mit Beschreibungen
    FORMATS = {
        OutputFormat.PDF: ("PDF", "Portable Document Format"),
        OutputFormat.TXT: ("TXT", "Reiner Text"),
        OutputFormat.DOCX: ("DOCX", "Microsoft Word"),
        OutputFormat.HTML: ("HTML", "Webseite"),
        OutputFormat.MD: ("MD", "Markdown"),
    }
    
    # Unterstützte Eingabe-Erweiterungen
    INPUT_EXTENSIONS = "*.pdf *.docx *.doc *.txt *.md *.html *.jpg *.jpeg *.png *.gif *.bmp *.tiff"
    
    def __init__(self, parent=None, initial_files: List[str] = None):
        super().__init__(parent)
        
        self._converter = FormatConverter()
        self._initial_files = initial_files or []
        
        self._setup_ui()
        
        if self._initial_files:
            self._add_files(self._initial_files)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Format-Konvertierung")
        self.setMinimumSize(600, 450)
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Modus-Auswahl
        mode_group = QGroupBox("Modus")
        mode_layout = QHBoxLayout(mode_group)
        
        self._mode_group = QButtonGroup()
        
        self._radio_single = QRadioButton("Einzeldatei")
        self._radio_single.setChecked(True)
        self._radio_single.toggled.connect(self._on_mode_changed)
        self._mode_group.addButton(self._radio_single)
        mode_layout.addWidget(self._radio_single)
        
        self._radio_batch = QRadioButton("Stapelverarbeitung")
        self._radio_batch.toggled.connect(self._on_mode_changed)
        self._mode_group.addButton(self._radio_batch)
        mode_layout.addWidget(self._radio_batch)
        
        mode_layout.addStretch()
        layout.addWidget(mode_group)
        
        # Einzeldatei-Bereich
        self._single_widget = QWidget()
        single_layout = QVBoxLayout(self._single_widget)
        single_layout.setContentsMargins(0, 0, 0, 0)
        
        input_group = QGroupBox("Eingabedatei")
        input_layout = QHBoxLayout(input_group)
        
        self._single_input = QLineEdit()
        self._single_input.setPlaceholderText("Datei zum Konvertieren wählen...")
        input_layout.addWidget(self._single_input)
        
        btn_browse = QPushButton("Durchsuchen...")
        btn_browse.clicked.connect(self._on_browse_single)
        input_layout.addWidget(btn_browse)
        
        single_layout.addWidget(input_group)
        
        output_group = QGroupBox("Ausgabedatei")
        output_layout = QHBoxLayout(output_group)
        
        self._single_output = QLineEdit()
        self._single_output.setPlaceholderText("Ausgabepfad...")
        output_layout.addWidget(self._single_output)
        
        btn_browse_out = QPushButton("...")
        btn_browse_out.setFixedWidth(30)
        btn_browse_out.clicked.connect(self._on_browse_single_output)
        output_layout.addWidget(btn_browse_out)
        
        single_layout.addWidget(output_group)
        layout.addWidget(self._single_widget)
        
        # Batch-Bereich
        self._batch_widget = QWidget()
        self._batch_widget.setVisible(False)
        batch_layout = QVBoxLayout(self._batch_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        
        files_group = QGroupBox("Dateien zur Konvertierung")
        files_layout = QVBoxLayout(files_group)
        
        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        files_layout.addWidget(self._file_list)
        
        btn_row = QHBoxLayout()
        
        btn_add = QPushButton("Hinzufügen...")
        btn_add.clicked.connect(self._on_add_files)
        btn_row.addWidget(btn_add)
        
        btn_remove = QPushButton("Entfernen")
        btn_remove.clicked.connect(self._on_remove_files)
        btn_row.addWidget(btn_remove)
        
        btn_clear = QPushButton("Alle entfernen")
        btn_clear.clicked.connect(self._on_clear_files)
        btn_row.addWidget(btn_clear)
        
        btn_row.addStretch()
        files_layout.addLayout(btn_row)
        
        batch_layout.addWidget(files_group)
        
        # Ausgabeverzeichnis
        outdir_group = QGroupBox("Ausgabeverzeichnis")
        outdir_layout = QHBoxLayout(outdir_group)
        
        self._batch_output = QLineEdit()
        outdir_layout.addWidget(self._batch_output)
        
        btn_browse_dir = QPushButton("...")
        btn_browse_dir.setFixedWidth(30)
        btn_browse_dir.clicked.connect(self._on_browse_batch_output)
        outdir_layout.addWidget(btn_browse_dir)
        
        batch_layout.addWidget(outdir_group)
        layout.addWidget(self._batch_widget)
        
        # Zielformat
        format_group = QGroupBox("Zielformat")
        format_layout = QFormLayout(format_group)
        
        self._format_combo = QComboBox()
        for fmt, (name, desc) in self.FORMATS.items():
            self._format_combo.addItem(f"{name} - {desc}", fmt)
        format_layout.addRow("Format:", self._format_combo)
        
        layout.addWidget(format_group)
        
        # Fortschritt
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
        
        self._status = QLabel("")
        layout.addWidget(self._status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._btn_convert = QPushButton("Konvertieren")
        self._btn_convert.setStyleSheet("font-weight: bold; padding: 8px;")
        self._btn_convert.clicked.connect(self._on_convert)
        btn_layout.addWidget(self._btn_convert)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _on_mode_changed(self):
        """Schaltet zwischen Einzel- und Batch-Modus."""
        is_single = self._radio_single.isChecked()
        self._single_widget.setVisible(is_single)
        self._batch_widget.setVisible(not is_single)
    
    def _on_browse_single(self):
        """Wählt Einzeldatei aus."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei wählen", "",
            f"Alle unterstützten ({self.INPUT_EXTENSIONS})"
        )
        if path:
            self._single_input.setText(path)
            # Auto-Output generieren
            fmt = self._format_combo.currentData()
            if fmt:
                out_path = str(Path(path).with_suffix(f".{fmt.value}"))
                self._single_output.setText(out_path)
    
    def _on_browse_single_output(self):
        """Wählt Ausgabedatei."""
        fmt = self._format_combo.currentData()
        ext = fmt.value if fmt else "pdf"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Speichern unter", "", f"{ext.upper()}-Dateien (*.{ext})"
        )
        if path:
            self._single_output.setText(path)
    
    def _add_files(self, files: List[str]):
        """Fügt Dateien zur Batch-Liste hinzu."""
        for f in files:
            if Path(f).exists():
                item = QListWidgetItem(Path(f).name)
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setToolTip(f)
                self._file_list.addItem(item)
    
    def _on_add_files(self):
        """Fügt Dateien hinzu."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Dateien wählen", "",
            f"Alle unterstützten ({self.INPUT_EXTENSIONS})"
        )
        self._add_files(files)
    
    def _on_remove_files(self):
        """Entfernt ausgewählte Dateien."""
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))
    
    def _on_clear_files(self):
        """Entfernt alle Dateien."""
        self._file_list.clear()
    
    def _on_browse_batch_output(self):
        """Wählt Ausgabeverzeichnis."""
        path = QFileDialog.getExistingDirectory(self, "Ausgabeverzeichnis")
        if path:
            self._batch_output.setText(path)
    
    def _on_convert(self):
        """Führt Konvertierung durch."""
        fmt = self._format_combo.currentData()
        
        if not fmt:
            QMessageBox.warning(self, "Fehler", "Bitte Format auswählen.")
            return
        
        if self._radio_single.isChecked():
            self._convert_single(fmt)
        else:
            self._convert_batch(fmt)
    
    def _convert_single(self, fmt: OutputFormat):
        """Einzeldatei konvertieren."""
        input_path = self._single_input.text().strip()
        output_path = self._single_output.text().strip()
        
        if not input_path:
            QMessageBox.warning(self, "Fehler", "Bitte Eingabedatei wählen.")
            return
        
        if not output_path:
            QMessageBox.warning(self, "Fehler", "Bitte Ausgabedatei angeben.")
            return
        
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setText("Konvertiere...")

        # BUGSWEEP-33 REVIEW-NOTIZ (NICHT auto-gefixt — Architektur/UX, User-Entscheidung): convert()
        # laeuft hier synchron im GUI-Thread -> bei grossen/vielen Dateien friert das UI ein (anders
        # als image_converter_dialog, das einen QThread nutzt). Zudem In-Place-Overwrite möglich
        # (output_path == input bei gleichem Ziel-Ordner+Format -> Originalverlust ohne Rückfrage).
        # Saubere Lösung: Worker-QThread (Progress via Signal) + Overwrite-Guard.
        result = self._converter.convert(input_path, output_path, fmt)
        
        self._progress.setVisible(False)
        
        if result.success:
            self._status.setText(f"Fertig: {Path(output_path).name}")
            QMessageBox.information(
                self, "Erfolg",
                f"Konvertierung erfolgreich:\n{result.output_path}"
            )
        else:
            self._status.setText(f"Fehler: {result.error}")
            QMessageBox.critical(self, "Fehler", f"Konvertierung fehlgeschlagen:\n{result.error}")
    
    def _convert_batch(self, fmt: OutputFormat):
        """Stapelkonvertierung."""
        if self._file_list.count() == 0:
            QMessageBox.warning(self, "Fehler", "Keine Dateien ausgewählt.")
            return
        
        output_dir = self._batch_output.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Fehler", "Bitte Ausgabeverzeichnis angeben.")
            return
        
        # Dateien sammeln
        files = []
        for i in range(self._file_list.count()):
            path = self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
            files.append(path)
        
        self._progress.setVisible(True)
        self._progress.setRange(0, len(files))
        
        # Ausgabeverzeichnis erstellen
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        error_count = 0
        
        for i, input_path in enumerate(files):
            self._progress.setValue(i)
            self._status.setText(f"Konvertiere {i+1}/{len(files)}...")
            
            # Ausgabepfad
            output_name = Path(input_path).stem + f".{fmt.value}"
            output_path = str(Path(output_dir) / output_name)
            
            result = self._converter.convert(input_path, output_path, fmt)
            
            if result.success:
                success_count += 1
            else:
                error_count += 1
                self.logger.warning(f"Konvertierung fehlgeschlagen: {input_path} - {result.error}")
        
        self._progress.setValue(len(files))
        self._progress.setVisible(False)
        
        self._status.setText(f"Fertig: {success_count} erfolgreich, {error_count} Fehler")
        
        QMessageBox.information(
            self, "Stapelverarbeitung abgeschlossen",
            f"Konvertierung abgeschlossen:\n\n"
            f"Erfolgreich: {success_count}\n"
            f"Fehler: {error_count}\n\n"
            f"Ausgabe: {output_dir}"
        )
