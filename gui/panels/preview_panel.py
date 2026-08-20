#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Preview Panel
===============================
Zeigt eine Vorschau des ausgewählten Dokuments.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QScrollArea,
    QStackedWidget, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage

from utils.logger import LoggerMixin
from translator import tr


class PreviewPanel(QWidget, LoggerMixin):
    """
    Panel zur Vorschau von Dokumenten.
    
    Unterstützt:
    - Textdateien (.txt, .py, .log, .json, .xml, .md, .csv)
    - Bilder (.jpg, .png, .gif, .bmp)
    - PDF (erste Seite als Bild - via PyMuPDF)
    """
    
    # Unterstützte Text-Erweiterungen
    TEXT_EXTENSIONS = {".txt", ".py", ".log", ".json", ".xml", ".md", ".csv", ".html", ".css", ".js"}
    
    # Unterstützte Bild-Erweiterungen
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_path: Optional[str] = None
        self._setup_ui()
        
        self.logger.debug("PreviewPanel erstellt")
    
    def _setup_ui(self):
        """Erstellt die UI-Elemente."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header
        header_layout = QHBoxLayout()
        self._header_label = QLabel(f"<b>{tr('Vorschau')}</b>")
        header_layout.addWidget(self._header_label)
        
        header_layout.addStretch()
        
        # Öffnen-Button
        self._btn_open = QPushButton(tr("Öffnen"))
        self._btn_open.setFixedWidth(70)
        self._btn_open.clicked.connect(self._open_external)
        self._btn_open.setEnabled(False)
        header_layout.addWidget(self._btn_open)
        
        layout.addLayout(header_layout)
        
        # Stacked Widget für verschiedene Vorschau-Typen
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        
        # Seite 0: Kein Dokument
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        self._empty_label = QLabel(tr("Kein Dokument ausgewählt"))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #888;")
        empty_layout.addWidget(self._empty_label)
        self._stack.addWidget(self._empty_widget)
        
        # Seite 1: Text-Vorschau
        self._text_widget = QTextEdit()
        self._text_widget.setReadOnly(True)
        self._text_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._text_widget.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        self._stack.addWidget(self._text_widget)
        
        # Seite 2: Bild-Vorschau
        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_scroll.setWidget(self._image_label)
        self._stack.addWidget(self._image_scroll)
        
        # Seite 3: Nicht unterstützt
        self._unsupported_widget = QWidget()
        unsupported_layout = QVBoxLayout(self._unsupported_widget)
        self._unsupported_label = QLabel(tr("Vorschau nicht verfügbar"))
        self._unsupported_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._unsupported_label.setStyleSheet("color: #888;")
        unsupported_layout.addWidget(self._unsupported_label)
        
        self._unsupported_info = QLabel(tr("Doppelklick zum Öffnen"))
        self._unsupported_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._unsupported_info.setStyleSheet("color: #aaa; font-size: 9pt;")
        unsupported_layout.addWidget(self._unsupported_info)
        
        self._stack.addWidget(self._unsupported_widget)
        
        # Initial: Leer
        self._stack.setCurrentIndex(0)
    
    def show_document(self, path: str):
        """
        Zeigt die Vorschau für ein Dokument.
        
        Args:
            path: Pfad zum Dokument
        """
        self._current_path = path
        file_path = Path(path)
        
        if not file_path.exists():
            self._show_error(f"Datei nicht gefunden:\n{path}")
            return
        
        self._btn_open.setEnabled(True)
        self._header_label.setText(f"<b>{file_path.name}</b>")
        
        ext = file_path.suffix.lower()
        
        if ext in self.TEXT_EXTENSIONS:
            self._show_text(file_path)
        elif ext in self.IMAGE_EXTENSIONS:
            self._show_image(file_path)
        elif ext == ".pdf":
            self._show_pdf(file_path)
        else:
            self._show_unsupported(ext)
    
    def retranslate_ui(self):
        """Aktualisiert alle UI-Texte im PreviewPanel dynamisch."""
        if hasattr(self, "_btn_open"):
            self._btn_open.setText(tr("Öffnen"))
        if hasattr(self, "_empty_label"):
            self._empty_label.setText(tr("Kein Dokument ausgewählt"))
        if hasattr(self, "_unsupported_info"):
            self._unsupported_info.setText(tr("Doppelklick zum Öffnen"))
            
        if self._current_path:
            self.show_document(self._current_path)
        else:
            if hasattr(self, "_header_label"):
                self._header_label.setText(f"<b>{tr('Vorschau')}</b>")
            if hasattr(self, "_unsupported_label"):
                self._unsupported_label.setText(tr("Vorschau nicht verfügbar"))

    def clear(self):
        """Leert die Vorschau."""
        self._current_path = None
        self._btn_open.setEnabled(False)
        self._header_label.setText(f"<b>{tr('Vorschau')}</b>")
        self._stack.setCurrentIndex(0)
    
    def _show_text(self, path: Path):
        """Zeigt Text-Vorschau."""
        try:
            # Versuche verschiedene Encodings
            content = None
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(path, "r", encoding=encoding) as f:
                        content = f.read(50000)  # Max 50KB
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                self._show_error(tr("Encoding nicht erkannt"))
                return
            
            # Syntax-Highlighting basierend auf Erweiterung
            if path.suffix.lower() == ".py":
                self._text_widget.setPlainText(content)
            elif path.suffix.lower() in {".json", ".xml", ".html"}:
                self._text_widget.setPlainText(content)
            else:
                self._text_widget.setPlainText(content)
            
            self._stack.setCurrentIndex(1)
            
        except Exception as e:
            self._show_error(f"{tr('Fehler beim Lesen')}:\n{e}")
    
    def _show_image(self, path: Path):
        """Zeigt Bild-Vorschau."""
        try:
            pixmap = QPixmap(str(path))
            
            if pixmap.isNull():
                self._show_error(tr("Bild konnte nicht geladen werden"))
                return
            
            # Skalieren wenn zu groß
            max_size = QSize(800, 800)
            if pixmap.width() > max_size.width() or pixmap.height() > max_size.height():
                pixmap = pixmap.scaled(
                    max_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            self._image_label.setPixmap(pixmap)
            self._stack.setCurrentIndex(2)
            
        except Exception as e:
            self._show_error(f"{tr('Fehler beim Laden')}:\n{e}")
    
    def _show_pdf(self, path: Path):
        """Zeigt PDF-Vorschau (erste Seite) mit PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            try:
                if doc.page_count > 0:
                    page = doc[0]

                    # Seite rendern (100 DPI für Vorschau)
                    mat = fitz.Matrix(100/72, 100/72)
                    pix = page.get_pixmap(matrix=mat)

                    # PyMuPDF Pixmap zu QImage konvertieren
                    qimg = QImage(pix.samples, pix.width, pix.height,
                                  pix.stride, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)

                    # Skalieren
                    max_size = QSize(600, 800)
                    if pixmap.width() > max_size.width() or pixmap.height() > max_size.height():
                        pixmap = pixmap.scaled(
                            max_size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )

                    self._image_label.setPixmap(pixmap)
                    self._stack.setCurrentIndex(2)
                else:
                    self._show_unsupported(".pdf")
            finally:
                doc.close()

        except ImportError:
            # PyMuPDF nicht installiert
            self._unsupported_label.setText(
                f"{tr('PDF-Vorschau nicht verfügbar')}\n\n"
                f"{tr('Installieren Sie PyMuPDF')}:\n"
                "pip install PyMuPDF"
            )
            self._stack.setCurrentIndex(3)
        except Exception as e:
            self._show_error(f"{tr('PDF-Fehler')}:\n{e}")
    
    def _show_unsupported(self, ext: str):
        """Zeigt Meldung für nicht unterstützte Formate."""
        self._unsupported_label.setText(
            f"{tr('Vorschau für')} {ext.upper()} {tr('nicht verfügbar')}"
        )
        self._stack.setCurrentIndex(3)
    
    def _show_error(self, message: str):
        """Zeigt Fehlermeldung."""
        self._unsupported_label.setText(message)
        self._stack.setCurrentIndex(3)
    
    def _open_external(self):
        """Öffnet das Dokument extern."""
        if self._current_path:
            import os
            import sys
            import subprocess
            
            if sys.platform == "win32":
                os.startfile(self._current_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self._current_path], check=False, timeout=30)
            else:
                subprocess.run(["xdg-open", self._current_path], check=False, timeout=30)
