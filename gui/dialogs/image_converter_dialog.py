#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Image Converter Dialog
=========================================
Dialog für Bildkonvertierung und ICO-Erstellung.
"""

from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QProgressBar, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap

from utils.logger import LoggerMixin
from core.converter.image_tools import ImageConverter, IcoBuilder, ImageProcessor, ImageFormat


class ConversionWorker(QThread):
    """Worker-Thread für Bildkonvertierung."""
    
    progress = Signal(int, int)  # current, total
    finished = Signal(dict)  # results
    
    def __init__(self, files: List[str], output_dir: str, 
                 target_format: str, resize: tuple = None, quality: int = 85):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.target_format = target_format
        self.resize = resize
        self.quality = quality
        self._cancelled = False

    def cancel(self):
        # BUGSWEEP-33: erlaubt closeEvent, eine laufende Batch-Konvertierung abzubrechen.
        self._cancelled = True

    def run(self):
        converter = ImageConverter()
        results = {}

        # BUGSWEEP-33: Ausgabeverzeichnis sicherstellen (sonst schlaegt jedes save fehl -> "0/N"
        # ohne klare Ursache).
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        for i, file in enumerate(self.files):
            if self._cancelled:
                break
            self.progress.emit(i + 1, len(self.files))

            out_name = Path(file).stem + "." + self.target_format
            out_path = str(Path(self.output_dir) / out_name)
            # BUGSWEEP-33 REVIEW-NOTIZ (NICHT auto-gefixt — UX-Entscheidung): waehlt der Nutzer das
            # Quellverzeichnis als Ausgabe und dasselbe Format, ist out_path == input -> Original wird
            # ohne Rückfrage ueberschrieben (gilt analog für convert_dialog). Saubere Lösung:
            # Guard out_path==input (skip/umbenennen) oder Overwrite-Abfrage.

            results[file] = converter.convert(
                file, out_path,
                resize=self.resize,
                quality=self.quality
            )

        self.finished.emit(results)


class ImageConverterDialog(QDialog, LoggerMixin):
    """
    Dialog für Bildkonvertierung und ICO-Erstellung.
    
    Tabs:
    - Konvertieren (Batch)
    - ICO erstellen
    - Favicon-Paket
    """
    
    def __init__(self, parent=None, initial_files: List[str] = None):
        super().__init__(parent)
        
        self._converter = ImageConverter()
        self._ico_builder = IcoBuilder()
        self._processor = ImageProcessor()
        
        self._worker: Optional[ConversionWorker] = None
        
        self._setup_ui()
        
        if initial_files:
            for f in initial_files:
                self._file_list.addItem(f)

    def closeEvent(self, event):
        # BUGSWEEP-33: laufende Konvertierung abbrechen + abwarten, sonst QThread-Zerstoerung bei
        # laufendem Thread -> Crash, und _on_finished feuert ggf. auf bereits zerstoerte Widgets.
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        super().closeEvent(event)

    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Bild-Werkzeuge")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # Tab: Konvertieren
        self._tabs.addTab(self._create_convert_tab(), "Konvertieren")
        
        # Tab: ICO erstellen
        self._tabs.addTab(self._create_ico_tab(), "ICO erstellen")
        
        # Tab: Favicon-Paket
        self._tabs.addTab(self._create_favicon_tab(), "Favicon-Paket")
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _create_convert_tab(self) -> QWidget:
        """Erstellt den Konvertieren-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Dateien
        files_group = QGroupBox("Dateien")
        files_layout = QVBoxLayout(files_group)
        
        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        files_layout.addWidget(self._file_list)
        
        file_buttons = QHBoxLayout()
        
        btn_add = QPushButton("Hinzufügen...")
        btn_add.clicked.connect(self._add_files)
        file_buttons.addWidget(btn_add)
        
        btn_remove = QPushButton("Entfernen")
        btn_remove.clicked.connect(self._remove_files)
        file_buttons.addWidget(btn_remove)
        
        btn_clear = QPushButton("Alle löschen")
        btn_clear.clicked.connect(lambda: self._file_list.clear())
        file_buttons.addWidget(btn_clear)
        
        file_buttons.addStretch()
        files_layout.addLayout(file_buttons)
        
        layout.addWidget(files_group)
        
        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QFormLayout(options_group)
        
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG", "JPEG", "WEBP", "GIF", "BMP", "TIFF"])
        options_layout.addRow("Zielformat:", self._format_combo)
        
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(85)
        self._quality_spin.setSuffix(" %")
        options_layout.addRow("Qualität:", self._quality_spin)
        
        # Größe
        size_layout = QHBoxLayout()
        
        self._resize_check = QCheckBox("Größe ändern:")
        size_layout.addWidget(self._resize_check)
        
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 10000)
        self._width_spin.setValue(800)
        self._width_spin.setEnabled(False)
        size_layout.addWidget(self._width_spin)
        
        size_layout.addWidget(QLabel("x"))
        
        self._height_spin = QSpinBox()
        self._height_spin.setRange(1, 10000)
        self._height_spin.setValue(600)
        self._height_spin.setEnabled(False)
        size_layout.addWidget(self._height_spin)
        
        size_layout.addStretch()
        options_layout.addRow("", size_layout)
        
        self._resize_check.toggled.connect(self._width_spin.setEnabled)
        self._resize_check.toggled.connect(self._height_spin.setEnabled)
        
        # Ausgabe
        out_layout = QHBoxLayout()
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("Ausgabeverzeichnis wählen...")
        out_layout.addWidget(self._output_dir)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._browse_output)
        out_layout.addWidget(btn_browse)
        
        options_layout.addRow("Ausgabe:", out_layout)
        
        layout.addWidget(options_group)
        
        # Fortschritt
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
        
        # Konvertieren-Button
        btn_convert = QPushButton("Konvertieren")
        btn_convert.clicked.connect(self._start_conversion)
        layout.addWidget(btn_convert)
        
        return widget
    
    def _create_ico_tab(self) -> QWidget:
        """Erstellt den ICO-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Quelldatei
        source_group = QGroupBox("Quelldatei")
        source_layout = QHBoxLayout(source_group)
        
        self._ico_source = QLineEdit()
        self._ico_source.setPlaceholderText("PNG oder Bild wählen (min. 256x256 empfohlen)...")
        source_layout.addWidget(self._ico_source)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._browse_ico_source)
        source_layout.addWidget(btn_browse)
        
        layout.addWidget(source_group)
        
        # Vorschau
        preview_group = QGroupBox("Vorschau")
        preview_layout = QVBoxLayout(preview_group)
        
        self._ico_preview = QLabel()
        self._ico_preview.setFixedSize(256, 256)
        self._ico_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ico_preview.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")
        preview_layout.addWidget(self._ico_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(preview_group)
        
        # Größen
        sizes_group = QGroupBox("Größen")
        sizes_layout = QVBoxLayout(sizes_group)
        
        self._preset_combo = QComboBox()
        self._preset_combo.addItems([
            "Standard (16, 32, 48, 256)",
            "Minimal (16, 32)",
            "Vollständig (16, 24, 32, 48, 64, 128, 256)",
            "Web/Favicon (16, 32, 180, 192)"
        ])
        sizes_layout.addWidget(self._preset_combo)
        
        layout.addWidget(sizes_group)
        
        # Erstellen
        btn_create = QPushButton("ICO erstellen...")
        btn_create.clicked.connect(self._create_ico)
        layout.addWidget(btn_create)
        
        layout.addStretch()
        
        return widget
    
    def _create_favicon_tab(self) -> QWidget:
        """Erstellt den Favicon-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info
        info = QLabel(
            "Erstellt ein komplettes Favicon-Paket für Websites:\n"
            "• favicon.ico (16x16, 32x32)\n"
            "• favicon-16x16.png, favicon-32x32.png\n"
            "• apple-touch-icon.png (180x180)\n"
            "• android-chrome-192x192.png, android-chrome-512x512.png\n"
            "• site.webmanifest"
        )
        info.setStyleSheet("background: #e8f4fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        # Quelldatei
        source_group = QGroupBox("Quelldatei")
        source_layout = QHBoxLayout(source_group)
        
        self._favicon_source = QLineEdit()
        self._favicon_source.setPlaceholderText("PNG-Bild wählen (min. 512x512 empfohlen)...")
        source_layout.addWidget(self._favicon_source)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._browse_favicon_source)
        source_layout.addWidget(btn_browse)
        
        layout.addWidget(source_group)
        
        # Ausgabe
        output_group = QGroupBox("Ausgabeverzeichnis")
        output_layout = QHBoxLayout(output_group)
        
        self._favicon_output = QLineEdit()
        output_layout.addWidget(self._favicon_output)
        
        btn_browse_out = QPushButton("...")
        btn_browse_out.setFixedWidth(30)
        btn_browse_out.clicked.connect(self._browse_favicon_output)
        output_layout.addWidget(btn_browse_out)
        
        layout.addWidget(output_group)
        
        # Erstellen
        btn_create = QPushButton("Favicon-Paket erstellen")
        btn_create.clicked.connect(self._create_favicon_package)
        layout.addWidget(btn_create)
        
        layout.addStretch()
        
        return widget
    
    def _add_files(self):
        """Fügt Dateien hinzu."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Bilder hinzufügen", "",
            "Bilder (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tiff)"
        )
        for f in files:
            self._file_list.addItem(f)
    
    def _remove_files(self):
        """Entfernt ausgewählte Dateien."""
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))
    
    def _browse_output(self):
        """Wählt Ausgabeverzeichnis."""
        path = QFileDialog.getExistingDirectory(self, "Ausgabeverzeichnis")
        if path:
            self._output_dir.setText(path)
    
    def _browse_ico_source(self):
        """Wählt ICO-Quelldatei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild wählen", "",
            "Bilder (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if path:
            self._ico_source.setText(path)
            self._update_ico_preview(path)
    
    def _browse_favicon_source(self):
        """Wählt Favicon-Quelldatei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild wählen", "",
            "PNG-Bilder (*.png)"
        )
        if path:
            self._favicon_source.setText(path)
    
    def _browse_favicon_output(self):
        """Wählt Favicon-Ausgabeverzeichnis."""
        path = QFileDialog.getExistingDirectory(self, "Ausgabeverzeichnis")
        if path:
            self._favicon_output.setText(path)
    
    def _update_ico_preview(self, path: str):
        """Aktualisiert ICO-Vorschau."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self._ico_preview.setPixmap(scaled)
    
    def _start_conversion(self):
        """Startet die Konvertierung."""
        # BUGSWEEP-33: Mehrfachstart verhindern — sonst wird self._worker mit einem neuen QThread
        # ueberschrieben, die Referenz auf den noch laufenden alten geht verloren -> GC -> Crash.
        if self._worker and self._worker.isRunning():
            return
        if self._file_list.count() == 0:
            QMessageBox.warning(self, "Keine Dateien", "Bitte fügen Sie Dateien hinzu.")
            return
        
        output_dir = self._output_dir.text()
        if not output_dir:
            QMessageBox.warning(self, "Kein Ausgabeordner", "Bitte wählen Sie ein Ausgabeverzeichnis.")
            return
        
        # Dateien sammeln
        files = [self._file_list.item(i).text() for i in range(self._file_list.count())]
        
        # Format
        format_map = {
            "PNG": "png", "JPEG": "jpg", "WEBP": "webp",
            "GIF": "gif", "BMP": "bmp", "TIFF": "tiff"
        }
        target_format = format_map[self._format_combo.currentText()]
        
        # Größe
        resize = None
        if self._resize_check.isChecked():
            resize = (self._width_spin.value(), self._height_spin.value())
        
        # Worker starten
        self._progress.setVisible(True)
        self._progress.setRange(0, len(files))
        
        self._worker = ConversionWorker(
            files, output_dir, target_format,
            resize, self._quality_spin.value()
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
    
    def _on_progress(self, current: int, total: int):
        """Fortschritt-Update."""
        self._progress.setValue(current)
    
    def _on_finished(self, results: dict):
        """Konvertierung abgeschlossen."""
        self._progress.setVisible(False)
        
        success = sum(1 for v in results.values() if v)
        total = len(results)
        
        QMessageBox.information(
            self, "Fertig",
            f"Konvertierung abgeschlossen:\n{success}/{total} erfolgreich"
        )
    
    def _create_ico(self):
        """Erstellt ICO-Datei."""
        source = self._ico_source.text()
        if not source:
            QMessageBox.warning(self, "Keine Datei", "Bitte wählen Sie eine Quelldatei.")
            return
        
        # Preset zu Größen
        presets = {
            0: "standard",
            1: "minimal",
            2: "full",
            3: "web"
        }
        preset = presets[self._preset_combo.currentIndex()]
        
        # Ausgabe
        default_name = Path(source).stem + ".ico"
        output, _ = QFileDialog.getSaveFileName(
            self, "ICO speichern", default_name,
            "ICO-Dateien (*.ico)"
        )
        
        if not output:
            return
        
        if self._ico_builder.create_ico(source, output, preset=preset):
            QMessageBox.information(self, "Erfolg", f"ICO erstellt:\n{output}")
        else:
            QMessageBox.critical(self, "Fehler", "ICO-Erstellung fehlgeschlagen.")
    
    def _create_favicon_package(self):
        """Erstellt Favicon-Paket."""
        source = self._favicon_source.text()
        output = self._favicon_output.text()
        
        if not source:
            QMessageBox.warning(self, "Keine Datei", "Bitte wählen Sie eine Quelldatei.")
            return
        
        if not output:
            QMessageBox.warning(self, "Kein Ordner", "Bitte wählen Sie ein Ausgabeverzeichnis.")
            return
        
        files = self._ico_builder.create_favicon_package(source, output)
        
        if files:
            file_list = "\n".join(f"• {name}" for name in files.keys())
            QMessageBox.information(
                self, "Erfolg",
                f"Favicon-Paket erstellt:\n\n{file_list}"
            )
        else:
            QMessageBox.critical(self, "Fehler", "Favicon-Erstellung fehlgeschlagen.")
