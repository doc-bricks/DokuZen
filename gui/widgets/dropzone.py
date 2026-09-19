#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Smart Dropzone Widget
===============================
Visuelles, interaktives Drag & Drop Widget für Dateien und Ordner mit automatischer Erkennung.
"""

from pathlib import Path
from typing import List
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QMenu
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QFont, QCursor, QAction

from translator import tr


class SmartDropzoneWidget(QFrame):
    """
    Interaktive Dropzone mit animierter Rückmeldung, Format-Chips und barrierefreier Tastaturnavigation.
    """

    files_dropped = Signal(list)  # Emittiert Liste von Dateipfaden (Dateien und/oder Ordner)
    browse_requested = Signal()

    STYLE_NORMAL = """
        QFrame#SmartDropzone {
            border: 2px dashed #0078d4;
            border-radius: 10px;
            background-color: rgba(0, 120, 212, 0.04);
            padding: 16px;
        }
        QFrame#SmartDropzone:hover {
            border: 2px dashed #106ebe;
            background-color: rgba(0, 120, 212, 0.08);
        }
    """

    STYLE_DRAG_OVER = """
        QFrame#SmartDropzone {
            border: 2px dashed #107c41;
            border-radius: 10px;
            background-color: rgba(16, 124, 65, 0.12);
            padding: 16px;
        }
    """

    STYLE_FOCUS = """
        QFrame#SmartDropzone:focus {
            border: 2px solid #005a9e;
            background-color: rgba(0, 120, 212, 0.10);
        }
    """

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self.setObjectName("SmartDropzone")
        self._compact = compact
        self._is_drag_over = False

        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.setAccessibleName(tr("Smart Ingest Dropzone"))
        self.setAccessibleDescription(
            tr("Ziehen Sie Dateien oder Ordner hierher oder drücken Sie die Eingabetaste zum Durchsuchen.")
        )

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6 if self._compact else 10)

        # Icon / Symbol
        self.icon_label = QLabel("📥")
        icon_font = QFont()
        icon_font.setPointSize(24 if self._compact else 36)
        self.icon_label.setFont(icon_font)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # Haupttext
        self.title_label = QLabel(tr("Dateien oder Ordner hierher ziehen"))
        title_font = QFont()
        title_font.setPointSize(11 if self._compact else 13)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Untertext / Hinweis
        self.subtitle_label = QLabel(tr("Oder klicken / Eingabe drücken zum Durchsuchen"))
        sub_font = QFont()
        sub_font.setPointSize(9 if self._compact else 10)
        self.subtitle_label.setFont(sub_font)
        self.subtitle_label.setStyleSheet("color: #666666;")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label)

        # Format-Badges / Chips
        if not self._compact:
            chips_layout = QHBoxLayout()
            chips_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chips_layout.setSpacing(6)

            chips = [
                ("PDF", "#d83b01"),
                ("Office/Word", "#0078d4"),
                ("Bilder", "#107c41"),
                ("Text & Markdown", "#5c2d91"),
                ("Ordner", "#008272"),
            ]

            chip_style = (
                "QLabel { "
                "  background-color: rgba(0,0,0,0.06); "
                "  border-radius: 4px; "
                "  padding: 3px 8px; "
                "  font-size: 10px; "
                "  font-weight: bold; "
                "}"
            )

            for text, color in chips:
                badge = QLabel(tr(text))
                badge.setStyleSheet(chip_style + f" QLabel {{ color: {color}; }}")
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chips_layout.addWidget(badge)

            layout.addLayout(chips_layout)

    def _apply_style(self):
        if self._is_drag_over:
            self.setStyleSheet(self.STYLE_DRAG_OVER)
        else:
            self.setStyleSheet(self.STYLE_NORMAL + self.STYLE_FOCUS)

    def set_compact_mode(self, compact: bool):
        """Schaltet zwischen Standard- und Kompaktmodus um."""
        self._compact = compact
        self._setup_ui()
        self._apply_style()

    # === Maus & Tastatur Interaktion ===

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_browse_menu(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._show_browse_menu(self.mapToGlobal(self.rect().center()))
            event.accept()
        else:
            super().keyPressEvent(event)

    def _show_browse_menu(self, pos):
        """Öffnet ein Auswahlmenü für Dateien oder Ordner."""
        menu = QMenu(self)
        action_files = QAction(tr("Dateien auswählen..."), self)
        action_files.triggered.connect(self._browse_files)
        menu.addAction(action_files)

        action_folder = QAction(tr("Ordner auswählen..."), self)
        action_folder.triggered.connect(self._browse_folder)
        menu.addAction(action_folder)

        menu.exec(pos)

    def _browse_files(self):
        """Öffnet den Dateiauswahldialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Dateien für Smart Ingest auswählen"),
            "",
            tr("Alle unterstützten Dateien (*.pdf *.docx *.doc *.txt *.md *.png *.jpg *.jpeg *.tiff *.bmp *.xlsx *.csv *.html);;PDF-Dokumente (*.pdf);;Alle Dateien (*.*)")
        )
        if files:
            self.files_dropped.emit(files)

    def _browse_folder(self):
        """Öffnet den Ordnerauswahldialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("Ordner für Smart Ingest auswählen")
        )
        if folder:
            self.files_dropped.emit([folder])

    # === Drag & Drop Ereignisse ===

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._is_drag_over = True
            self._apply_style()
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self._apply_style()
        event.accept()

    def dropEvent(self, event):
        self._is_drag_over = False
        self._apply_style()

        if event.mimeData().hasUrls():
            paths: List[str] = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            if paths:
                self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
