#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Smart Ingest Dialog
=============================
Zentraler Dialog für Formaterkennung, Konvertierungsvorbereitung und Batch-Ingest.
"""

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from translator import tr
from core.library.manager import LibraryManager
from core.ingest import (
    SmartIngestService, IngestCandidate, IngestAction, FileType, IngestSummary
)
from gui.widgets.dropzone import SmartDropzoneWidget


class SmartIngestDialog(QDialog):
    """
    Dialog zur Erkennung, Voransicht und gesteuerten Aufnahme von Dateien in die Bibliothek.
    """

    ingest_finished = Signal(object)  # Emittiert IngestSummary

    ACTION_DISPLAY_NAMES = {
        IngestAction.ADD_DIRECT: tr("Direkt importieren"),
        IngestAction.CONVERT_TO_PDF: tr("In PDF konvertieren"),
        IngestAction.SKIP_DUPLICATE: tr("Überspringen (Duplikat)"),
        IngestAction.UNSUPPORTED: tr("Nicht unterstützt"),
    }

    FILE_TYPE_DISPLAY = {
        FileType.PDF: tr("PDF-Dokument"),
        FileType.OFFICE: tr("Office / Word"),
        FileType.TEXT_MARKDOWN: tr("Text / Markdown"),
        FileType.IMAGE: tr("Bild"),
        FileType.SPREADSHEET: tr("Tabelle / CSV"),
        FileType.WEB_HTML: tr("HTML-Webseite"),
        FileType.CODE: tr("Code / Daten"),
        FileType.FOLDER: tr("Ordner"),
        FileType.UNSUPPORTED: tr("Unbekannt"),
    }

    def __init__(
        self,
        parent=None,
        library_manager: Optional[LibraryManager] = None,
        initial_paths: Optional[List[str]] = None,
        initial_theme: Optional[str] = None
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Smart Ingest & Formaterkennung"))
        self.resize(850, 600)
        self.setMinimumSize(700, 480)

        self.library = library_manager
        self.service = SmartIngestService(self.library) if self.library else None
        self._candidates: List[IngestCandidate] = []
        self._initial_theme = initial_theme

        self._setup_ui()

        if initial_paths:
            self.add_paths(initial_paths)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header: Titel & Themen-Auswahl
        top_bar = QHBoxLayout()

        header_label = QLabel(tr("Dokumente erkennen, vorbereiten und importieren"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        header_label.setFont(title_font)
        top_bar.addWidget(header_label)

        top_bar.addStretch()

        theme_lbl = QLabel(tr("Zielthema:"))
        theme_lbl.setFont(QFont("", 9, QFont.Weight.Bold))
        top_bar.addWidget(theme_lbl)

        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(160)
        self._populate_themes()
        top_bar.addWidget(self.theme_combo)

        layout.addLayout(top_bar)

        # Kompakte Dropzone
        self.dropzone = SmartDropzoneWidget(self, compact=True)
        self.dropzone.files_dropped.connect(self.add_paths)
        layout.addWidget(self.dropzone)

        # Kandidatentabelle
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tr("Dateiname"),
            tr("Format"),
            tr("Aktion"),
            tr("Größe"),
            tr("Status")
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Werkzeugleiste unter der Tabelle
        tb_layout = QHBoxLayout()

        self.btn_add_files = QPushButton(tr("Dateien hinzufügen..."))
        self.btn_add_files.clicked.connect(self._on_add_files)
        tb_layout.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton(tr("Ordner hinzufügen..."))
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        tb_layout.addWidget(self.btn_add_folder)

        self.btn_remove = QPushButton(tr("Auswahl entfernen"))
        self.btn_remove.clicked.connect(self._on_remove_selected)
        tb_layout.addWidget(self.btn_remove)

        self.btn_clear = QPushButton(tr("Alle leeren"))
        self.btn_clear.clicked.connect(self._on_clear_all)
        tb_layout.addWidget(self.btn_clear)

        tb_layout.addStretch()

        self.lbl_count = QLabel(tr("0 Dateien bereit"))
        tb_layout.addWidget(self.lbl_count)

        layout.addLayout(tb_layout)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Optionen
        opts_layout = QHBoxLayout()

        self.chk_auto_convert = QCheckBox(tr("Nicht-PDFs automatisch in PDF konvertieren"))
        self.chk_auto_convert.setChecked(True)
        self.chk_auto_convert.toggled.connect(self._on_options_changed)
        opts_layout.addWidget(self.chk_auto_convert)

        self.chk_skip_dupes = QCheckBox(tr("Duplikate überspringen"))
        self.chk_skip_dupes.setChecked(True)
        self.chk_skip_dupes.toggled.connect(self._on_options_changed)
        opts_layout.addWidget(self.chk_skip_dupes)

        self.chk_recursive = QCheckBox(tr("Ordner rekursiv durchsuchen"))
        self.chk_recursive.setChecked(True)
        opts_layout.addWidget(self.chk_recursive)

        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # Fortschrittsbalken & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setVisible(False)
        layout.addWidget(self.lbl_status)

        # Buttons unten
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_start = QPushButton(tr("Import starten"))
        self.btn_start.setDefault(True)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #0078d4; color: white; padding: 6px 18px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #106ebe; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )
        self.btn_start.clicked.connect(self._on_start_ingest)
        btn_box.addWidget(self.btn_start)

        self.btn_close = QPushButton(tr("Schließen"))
        self.btn_close.clicked.connect(self.close)
        btn_box.addWidget(self.btn_close)

        layout.addLayout(btn_box)

    def _populate_themes(self):
        """Füllt die Themen-Auswahl."""
        self.theme_combo.clear()
        if not self.library:
            return

        themes = self.library.themes.get_all_themes()
        curr_theme = self._initial_theme or self.library.themes.get_current_theme()

        for t in themes:
            name = t.name if hasattr(t, "name") else str(t)
            self.theme_combo.addItem(name, name)

        if curr_theme:
            theme_str = curr_theme.name if hasattr(curr_theme, "name") else str(curr_theme)
            idx = self.theme_combo.findText(theme_str)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)

    def add_paths(self, paths: List[str]):
        """Scannt Pfade und fügt sie der Kandidatentabelle hinzu."""
        if not self.service or not paths:
            return

        selected_theme = self.theme_combo.currentText() or None
        recursive = self.chk_recursive.isChecked()
        auto_convert = self.chk_auto_convert.isChecked()

        new_candidates = self.service.prepare_candidates(
            paths,
            recursive=recursive,
            auto_convert=auto_convert,
            theme=selected_theme
        )

        existing_paths = {c.path for c in self._candidates}
        added_count = 0
        for cand in new_candidates:
            if cand.path not in existing_paths:
                self._candidates.append(cand)
                existing_paths.add(cand.path)
                added_count += 1

        self._refresh_table()

    def _refresh_table(self):
        """Aktualisiert die Darstellung der Kandidatentabelle."""
        self.table.setRowCount(len(self._candidates))

        for row, cand in enumerate(self._candidates):
            # Spalte 0: Name
            item_name = QTableWidgetItem(cand.name)
            item_name.setToolTip(cand.path)
            self.table.setItem(row, 0, item_name)

            # Spalte 1: Format
            fmt_desc = self.FILE_TYPE_DISPLAY.get(cand.file_type, cand.file_type.value)
            item_fmt = QTableWidgetItem(fmt_desc)
            self.table.setItem(row, 1, item_fmt)

            # Spalte 2: Aktion (ComboBox)
            combo_action = QComboBox()
            for act in [
                IngestAction.ADD_DIRECT,
                IngestAction.CONVERT_TO_PDF,
                IngestAction.SKIP_DUPLICATE,
                IngestAction.UNSUPPORTED
            ]:
                combo_action.addItem(self.ACTION_DISPLAY_NAMES[act], act)

            # Gewählte Aktion einstellen
            idx = combo_action.findData(cand.selected_action)
            if idx >= 0:
                combo_action.setCurrentIndex(idx)
            combo_action.currentIndexChanged.connect(
                lambda idx, r=row: self._on_row_action_changed(r, idx)
            )
            self.table.setCellWidget(row, 2, combo_action)

            # Spalte 3: Größe
            item_size = QTableWidgetItem(cand.size_human)
            self.table.setItem(row, 3, item_size)

            # Spalte 4: Status
            status_text = tr("Bereit")
            if cand.is_duplicate and cand.selected_action == IngestAction.SKIP_DUPLICATE:
                status_text = tr("Duplikat")
            elif cand.file_type == FileType.UNSUPPORTED:
                status_text = tr("Nicht unterstützt")
            item_status = QTableWidgetItem(status_text)
            self.table.setItem(row, 4, item_status)

        self._update_summary_label()

    def _on_row_action_changed(self, row: int, combo_index: int):
        """Aktualisiert die gewählte Aktion für einen Kandidaten."""
        if 0 <= row < len(self._candidates):
            widget = self.table.cellWidget(row, 2)
            if isinstance(widget, QComboBox):
                selected_action = widget.currentData()
                self._candidates[row].selected_action = selected_action

    def _on_options_changed(self):
        """Reagiert auf Änderungen an den Checkboxen."""
        auto_convert = self.chk_auto_convert.isChecked()
        skip_dupes = self.chk_skip_dupes.isChecked()

        for cand in self._candidates:
            if skip_dupes and cand.is_duplicate:
                cand.selected_action = IngestAction.SKIP_DUPLICATE
            elif auto_convert and self.service and self.service.detector.is_convertible_to_pdf(cand.path):
                cand.selected_action = IngestAction.CONVERT_TO_PDF
            elif cand.file_type != FileType.UNSUPPORTED:
                cand.selected_action = IngestAction.ADD_DIRECT
            else:
                cand.selected_action = IngestAction.UNSUPPORTED

        self._refresh_table()

    def _update_summary_label(self):
        count = len(self._candidates)
        self.lbl_count.setText(f"{count} {tr('Datei(en) gelistet')}")
        self.btn_start.setEnabled(count > 0)

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Dateien hinzufügen"),
            "",
            tr("Alle unterstützten Dateien (*.pdf *.docx *.doc *.txt *.md *.png *.jpg *.jpeg *.tiff *.bmp *.xlsx *.csv *.html);;Alle Dateien (*.*)")
        )
        if files:
            self.add_paths(files)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("Ordner hinzufügen")
        )
        if folder:
            self.add_paths([folder])

    def _on_remove_selected(self):
        selected_rows = sorted(
            {idx.row() for idx in self.table.selectedIndexes()},
            reverse=True
        )
        for r in selected_rows:
            if 0 <= r < len(self._candidates):
                self._candidates.pop(r)
        self._refresh_table()

    def _on_clear_all(self):
        self._candidates.clear()
        self._refresh_table()

    def _on_start_ingest(self):
        """Führt den Ingest-Prozess durch."""
        if not self.service or not self._candidates:
            return

        selected_theme = self.theme_combo.currentText() or None
        self.btn_start.setEnabled(False)
        self.btn_add_files.setEnabled(False)
        self.btn_add_folder.setEnabled(False)
        self.btn_remove.setEnabled(False)
        self.btn_clear.setEnabled(False)

        total = len(self._candidates)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText(tr("Verarbeitung läuft..."))

        def on_progress(idx, total_count, candidate, result):
            self.progress_bar.setValue(idx)
            row = idx - 1
            if 0 <= row < self.table.rowCount():
                if result.success:
                    if result.action_performed == IngestAction.SKIP_DUPLICATE:
                        st = tr("Übersprungen")
                        color = QColor("#888888")
                    elif result.action_performed == IngestAction.CONVERT_TO_PDF:
                        st = tr("Konvertiert & importiert")
                        color = QColor("#008800")
                    else:
                        st = tr("Erfolgreich importiert")
                        color = QColor("#008800")
                else:
                    st = f"{tr('Fehler')}: {result.error or 'Unbekannt'}"
                    color = QColor("#cc0000")

                item = QTableWidgetItem(st)
                item.setForeground(color)
                self.table.setItem(row, 4, item)

        summary = self.service.ingest_batch(
            self._candidates,
            theme=selected_theme,
            progress_callback=on_progress
        )

        self.lbl_status.setText(
            f"{tr('Abgeschlossen')}: {summary.added_count} {tr('importiert')}, "
            f"{summary.converted_count} {tr('konvertiert')}, "
            f"{summary.skipped_count} {tr('übersprungen')}, "
            f"{summary.failed_count} {tr('Fehler')}"
        )

        self.btn_close.setText(tr("Fertig"))
        self.btn_close.setDefault(True)
        self.btn_close.setFocus()

        self.ingest_finished.emit(summary)
