#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - OCR Dialog
============================
Dialog für Texterkennung (OCR).
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QWidget,
    QPushButton, QLabel, QFileDialog, QProgressBar,
    QMessageBox, QFormLayout, QComboBox, QCheckBox,
    QLineEdit, QTextEdit, QSpinBox, QListWidget,
    QAbstractItemView, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal

from utils.logger import LoggerMixin
from core.ocr import OCREngine, OCRResult, OCRPageResult


class OCRWorker(QThread):
    """Worker-Thread für OCR-Operationen."""
    
    progress = Signal(int, int)  # current, total
    page_done = Signal(int, str, float)  # page_num, text, confidence
    finished = Signal(bool, str)  # success, message
    
    def __init__(self, engine: OCREngine, pdf_path: str, language: str):
        super().__init__()
        self.engine = engine
        self.pdf_path = pdf_path
        self.language = language
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        # BUGSWEEP-33 REVIEW-NOTIZ (NICHT auto-gefixt — Engine-Änderung nötig, User-Entscheidung):
        # recognize_pdf() verarbeitet ALLE Seiten in einem blockierenden Aufruf; der _cancelled-Check
        # greift erst in der Ergebnis-Schleife danach -> "Abbrechen" überspringt nur noch das Emittieren,
        # die teure OCR ist schon gelaufen. Echter Abbruch bräuchte seitenweise OCR mit Cancel-Callback
        # in der Engine. (Ebenso: Einzelbild-OCR _start_image_ocr läuft synchron im GUI-Thread -> Freeze.)
        try:
            results = self.engine.recognize_pdf(self.pdf_path, self.language)
            
            total = len(results)
            for i, result in enumerate(results):
                if self._cancelled:
                    self.finished.emit(False, "Abgebrochen")
                    return
                
                self.progress.emit(i + 1, total)
                self.page_done.emit(result.page_num, result.text, result.confidence)
            
            self.finished.emit(True, f"{total} Seiten verarbeitet")
            
        except Exception as e:
            self.finished.emit(False, str(e))


class OCRDialog(QDialog, LoggerMixin):
    """
    OCR-Dialog für Texterkennung.
    
    Features:
    - Einzelbild-OCR
    - PDF-OCR (alle Seiten)
    - Sprachauswahl
    - Ergebnisvorschau
    - Export als TXT
    """
    
    # Verfügbare Sprachen
    LANGUAGES = {
        "Deutsch": "deu",
        "Englisch": "eng",
        "Deutsch + Englisch": "deu+eng",
        "Französisch": "fra",
        "Spanisch": "spa",
        "Italienisch": "ita",
        "Niederländisch": "nld",
        "Polnisch": "pol",
        "Russisch": "rus",
        "Chinesisch (vereinfacht)": "chi_sim",
        "Japanisch": "jpn",
    }
    
    def __init__(self, parent=None, initial_file: str = None):
        super().__init__(parent)
        
        self._engine = OCREngine()
        self._worker: Optional[OCRWorker] = None
        self._results: List[OCRPageResult] = []
        self._initial_file = initial_file
        
        self._setup_ui()
        
        if initial_file:
            self._input_path.setText(initial_file)

    def closeEvent(self, event):
        # BUGSWEEP-33: laufenden OCRWorker abbrechen + abwarten, sonst QThread-Zerstoerung bei
        # laufendem Thread -> Crash. (cancel() greift engine-bedingt erst nach der aktuellen
        # recognize_pdf-Verarbeitung — REVIEW-NOTIZ unten; wait() garantiert dennoch Crash-Freiheit.)
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        super().closeEvent(event)

    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Texterkennung (OCR)")
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Status
        if not self._engine.is_available:
            warning = QLabel("⚠️ Tesseract ist nicht installiert oder nicht gefunden!")
            warning.setStyleSheet("color: red; font-weight: bold; padding: 10px;")
            layout.addWidget(warning)
        
        # Splitter für Einstellungen und Ergebnis
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Oberer Bereich: Einstellungen
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # Eingabe
        input_group = QGroupBox("Eingabe (Bild oder PDF)")
        input_layout = QHBoxLayout(input_group)
        
        self._input_path = QLineEdit()
        self._input_path.setPlaceholderText("Bild oder PDF wählen...")
        input_layout.addWidget(self._input_path)
        
        btn_browse = QPushButton("Durchsuchen...")
        btn_browse.clicked.connect(self._on_browse_input)
        input_layout.addWidget(btn_browse)
        
        settings_layout.addWidget(input_group)
        
        # Optionen
        options_group = QGroupBox("OCR-Einstellungen")
        options_layout = QFormLayout(options_group)
        
        self._language = QComboBox()
        self._language.addItems(list(self.LANGUAGES.keys()))
        self._language.setCurrentText("Deutsch + Englisch")
        options_layout.addRow("Sprache:", self._language)
        
        settings_layout.addWidget(options_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._btn_start = QPushButton("OCR starten")
        self._btn_start.setStyleSheet("font-weight: bold; padding: 8px;")
        self._btn_start.clicked.connect(self._on_start_ocr)
        btn_layout.addWidget(self._btn_start)
        
        self._btn_cancel = QPushButton("Abbrechen")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._btn_cancel)
        
        btn_layout.addStretch()
        settings_layout.addLayout(btn_layout)
        
        # Fortschritt
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        settings_layout.addWidget(self._progress)
        
        self._status = QLabel("")
        settings_layout.addWidget(self._status)
        
        splitter.addWidget(settings_widget)
        
        # Unterer Bereich: Ergebnis
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        result_group = QGroupBox("Erkannter Text")
        result_inner = QVBoxLayout(result_group)
        
        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setStyleSheet("font-family: Consolas, monospace;")
        result_inner.addWidget(self._result_text)
        
        # Export-Buttons
        export_layout = QHBoxLayout()
        
        btn_copy = QPushButton("In Zwischenablage")
        btn_copy.clicked.connect(self._on_copy)
        export_layout.addWidget(btn_copy)
        
        btn_save = QPushButton("Als TXT speichern...")
        btn_save.clicked.connect(self._on_save)
        export_layout.addWidget(btn_save)
        
        export_layout.addStretch()
        result_inner.addLayout(export_layout)
        
        result_layout.addWidget(result_group)
        splitter.addWidget(result_widget)
        
        # Splitter-Größen
        splitter.setSizes([200, 400])
        
        # Schließen
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        close_layout.addWidget(btn_close)
        layout.addLayout(close_layout)
    
    def _on_browse_input(self):
        """Öffnet Datei-Dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei wählen", "",
            "Alle unterstützten (*.pdf *.png *.jpg *.jpeg *.tiff *.bmp);;"
            "PDF-Dateien (*.pdf);;"
            "Bilder (*.png *.jpg *.jpeg *.tiff *.bmp)"
        )
        if path:
            self._input_path.setText(path)
    
    def _on_start_ocr(self):
        """Startet OCR."""
        input_path = self._input_path.text().strip()
        
        if not input_path:
            QMessageBox.warning(self, "Fehler", "Bitte Datei auswählen.")
            return
        
        if not Path(input_path).exists():
            QMessageBox.warning(self, "Fehler", "Datei nicht gefunden.")
            return
        
        if not self._engine.is_available:
            QMessageBox.critical(self, "Fehler", "Tesseract ist nicht verfügbar.")
            return
        
        # Sprache
        lang_name = self._language.currentText()
        language = self.LANGUAGES.get(lang_name, "deu+eng")
        
        self._result_text.clear()
        self._results.clear()
        
        ext = Path(input_path).suffix.lower()
        
        if ext == ".pdf":
            self._start_pdf_ocr(input_path, language)
        else:
            self._start_image_ocr(input_path, language)
    
    def _start_image_ocr(self, path: str, language: str):
        """OCR für Einzelbild."""
        self._status.setText("Verarbeite Bild...")
        self._btn_start.setEnabled(False)
        
        result = self._engine.recognize_image(path, language)
        
        self._btn_start.setEnabled(True)
        
        if result.success:
            self._result_text.setText(result.text)
            self._status.setText(f"Fertig - Konfidenz: {result.confidence:.1f}%")
        else:
            self._status.setText(f"Fehler: {result.error}")
            QMessageBox.critical(self, "Fehler", result.error)
    
    def _start_pdf_ocr(self, path: str, language: str):
        """OCR für PDF (im Thread)."""
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        
        self._worker = OCRWorker(self._engine, path, language)
        self._worker.progress.connect(self._on_progress)
        self._worker.page_done.connect(self._on_page_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
    
    def _on_progress(self, current: int, total: int):
        """Aktualisiert Fortschritt."""
        self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._status.setText(f"Seite {current} von {total}...")
    
    def _on_page_done(self, page_num: int, text: str, confidence: float):
        """Eine Seite wurde verarbeitet."""
        current_text = self._result_text.toPlainText()
        if current_text:
            current_text += "\n\n"
        current_text += f"=== Seite {page_num} (Konfidenz: {confidence:.1f}%) ===\n\n"
        current_text += text
        self._result_text.setText(current_text)
    
    def _on_finished(self, success: bool, message: str):
        """OCR abgeschlossen."""
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._progress.setVisible(False)
        self._status.setText(message)
        
        if not success:
            QMessageBox.warning(self, "OCR", message)
        
        self._worker = None
    
    def _on_cancel(self):
        """Bricht OCR ab."""
        if self._worker:
            self._worker.cancel()
    
    def _on_copy(self):
        """Kopiert Text in Zwischenablage."""
        text = self._result_text.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self._status.setText("In Zwischenablage kopiert!")
    
    def _on_save(self):
        """Speichert Text als TXT."""
        text = self._result_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "Fehler", "Kein Text zum Speichern.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Text speichern", "", "Textdateien (*.txt)"
        )
        if path:
            # BUGSWEEP-33: Schreibfehler (schreibgeschuetzt/voll/ungueltig) abfangen statt
            # unbehandelter Exception aus dem Slot.
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self._status.setText(f"Gespeichert: {path}")
            except OSError as e:
                QMessageBox.critical(self, "Fehler", f"Konnte nicht speichern:\n{e}")
