#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Collection / Binder PDF Export Dialog
===================================================
Interaktiver Dialog zur Zusammenstellung, Sortierung und Erstellung
eines einheitlichen Sammel-PDFs aus mehreren Dokumenten und Medien.
"""

import os
from pathlib import Path
import subprocess
import sys
from typing import List, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.pdf.collection import (
    CollectionExporter,
    CollectionExportOptions,
    export_collection_pdf,
)
from translator import tr
from utils.logger import LoggerMixin


class CollectionExportDialog(QDialog, LoggerMixin):
    """
    Dialog zur Erstellung eines Sammel-PDFs.

    Funktionen:
    - Dokumentenliste mit Sortierung (Nach oben / Nach unten)
    - Dynamisches Hinzufügen / Entfernen von Dateien
    - Inhaltsverzeichnis / Bookmarks aktivieren
    - Fortlaufende Seitennummerierung mit Formatvorlage
    - Fortschrittsrückmeldung und Direkt-Öffnen
    """

    SUPPORTED_FILTER = (
        "Unterstützte Dokumente (*.pdf *.png *.jpg *.jpeg *.bmp *.webp *.tiff *.txt *.md *.log *.docx);;"
        "PDF-Dateien (*.pdf);;"
        "Bilder (*.png *.jpg *.jpeg *.bmp *.webp *.tiff);;"
        "Textdateien (*.txt *.md *.log);;"
        "Alle Dateien (*.*)"
    )

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_documents: Optional[Sequence[str]] = None,
        current_theme: Optional[str] = None,
    ):
        super().__init__(parent)
        self.logger.debug("CollectionExportDialog wird initialisiert...")

        self._initial_documents = list(initial_documents or [])
        self._current_theme = current_theme or ""
        self._exported_file: Optional[str] = None

        self._setup_ui()
        if self._initial_documents:
            self._add_files(self._initial_documents)
        self._update_stats()

    def _setup_ui(self):
        """Erstellt die Oberfläche."""
        self.setWindowTitle(tr("Sammel-PDF erstellen"))
        self.setMinimumSize(720, 520)
        self.resize(800, 580)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # 1. Dokumenten-Bereich
        docs_group = QGroupBox(tr("Dokumente in der Sammelmappe"))
        docs_layout = QHBoxLayout(docs_group)

        self._list_widget = QListWidget()
        self._list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list_widget.setAccessibleName(tr("Dokumentenliste für Sammel-PDF"))
        self._list_widget.setAccessibleDescription(
            tr("Liste der Dokumente, die in das Sammel-PDF eingebunden werden. Mit Checkboxen abwählbar.")
        )
        self._list_widget.itemChanged.connect(self._on_item_changed)
        docs_layout.addWidget(self._list_widget, stretch=1)

        # Buttons rechts von der Liste
        btn_box = QVBoxLayout()
        btn_box.setSpacing(6)

        self._btn_add = QPushButton(tr("Dateien hinzufügen..."))
        self._btn_add.setToolTip(tr("Weitere Dokumente oder Bilder zur Mappe hinzufügen"))
        self._btn_add.clicked.connect(self._on_add_files_clicked)
        btn_box.addWidget(self._btn_add)

        self._btn_remove = QPushButton(tr("Entfernen"))
        self._btn_remove.setToolTip(tr("Markierte Dokumente aus der Liste entfernen"))
        self._btn_remove.clicked.connect(self._remove_selected)
        btn_box.addWidget(self._btn_remove)

        btn_box.addSpacing(10)

        self._btn_up = QPushButton(tr("Nach oben"))
        self._btn_up.setToolTip(tr("Verschiebt das gewählte Dokument eine Position nach oben"))
        self._btn_up.clicked.connect(self._move_up)
        btn_box.addWidget(self._btn_up)

        self._btn_down = QPushButton(tr("Nach unten"))
        self._btn_down.setToolTip(tr("Verschiebt das gewählte Dokument eine Position nach unten"))
        self._btn_down.clicked.connect(self._move_down)
        btn_box.addWidget(self._btn_down)

        btn_box.addSpacing(10)

        self._btn_select_all = QPushButton(tr("Alle auswählen"))
        self._btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_box.addWidget(self._btn_select_all)

        self._btn_deselect_all = QPushButton(tr("Keine auswählen"))
        self._btn_deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        btn_box.addWidget(self._btn_deselect_all)

        btn_box.addStretch()
        docs_layout.addLayout(btn_box)
        main_layout.addWidget(docs_group, stretch=1)

        # 2. Optionen
        options_group = QGroupBox(tr("Export-Optionen"))
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)

        self._check_bookmarks = QCheckBox(tr("Inhaltsverzeichnis / Lesezeichen erstellen (Bookmarks)"))
        self._check_bookmarks.setChecked(True)
        self._check_bookmarks.setToolTip(
            tr("Erstellt ein anklickbares PDF-Inhaltsverzeichnis mit Links zu den Startseiten der Dokumente.")
        )
        self._check_bookmarks.setAccessibleName(tr("Lesezeichen erstellen"))
        self._check_bookmarks.setAccessibleDescription(
            tr("Aktiviert das Inhaltsverzeichnis im PDF-Reader.")
        )
        options_layout.addWidget(self._check_bookmarks)

        num_layout = QHBoxLayout()
        self._check_numbers = QCheckBox(tr("Fortlaufende Seitenzahlen hinzufügen"))
        self._check_numbers.setChecked(False)
        self._check_numbers.setToolTip(
            tr("Bettet am unteren Seitenrand fortlaufende Seitennummern ein.")
        )
        self._check_numbers.setAccessibleName(tr("Fortlaufende Seitenzahlen"))
        self._check_numbers.toggled.connect(self._on_numbers_toggled)
        num_layout.addWidget(self._check_numbers)

        self._label_pattern = QLabel(f"{tr('Muster')}:")
        self._label_pattern.setEnabled(False)
        num_layout.addWidget(self._label_pattern)

        self._combo_pattern = QComboBox()
        self._combo_pattern.setEnabled(False)
        self._combo_pattern.addItem("Seite {page} / {total}", "Seite {page} / {total}")
        self._combo_pattern.addItem("{page} / {total}", "{page} / {total}")
        self._combo_pattern.addItem("Seite {page}", "Seite {page}")
        self._combo_pattern.addItem("{page}", "{page}")
        num_layout.addWidget(self._combo_pattern)
        num_layout.addStretch()
        options_layout.addLayout(num_layout)

        main_layout.addWidget(options_group)

        # 3. Status- & Aktionsbereich
        self._label_stats = QLabel("")
        main_layout.addWidget(self._label_stats)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)  # Unbestimmter Modus während des Exports
        main_layout.addWidget(self._progress)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self._btn_cancel = QPushButton(tr("Abbrechen"))
        self._btn_cancel.clicked.connect(self.reject)
        action_layout.addWidget(self._btn_cancel)

        self._btn_export = QPushButton(tr("Sammel-PDF exportieren..."))
        self._btn_export.setDefault(True)
        self._btn_export.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self._btn_export.clicked.connect(self._on_export)
        action_layout.addWidget(self._btn_export)

        main_layout.addLayout(action_layout)

    def _add_files(self, paths: Sequence[str]):
        """Fügt Dateien zur Liste hinzu."""
        existing_paths = {
            self._list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list_widget.count())
        }

        for path_str in paths:
            if not path_str or path_str in existing_paths:
                continue
            p = Path(path_str)
            if not p.exists() or not p.is_file():
                continue

            item = QListWidgetItem()
            item.setText(f"{p.name}   ({p.parent})")
            item.setData(Qt.ItemDataRole.UserRole, str(p.resolve()))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._list_widget.addItem(item)
            existing_paths.add(str(p.resolve()))

        self._update_stats()

    def _on_add_files_clicked(self):
        """Öffnet Dateiauswahl zum Hinzufügen weiterer Dokumente."""
        start_dir = ""
        if self._list_widget.count() > 0:
            first_item_path = self._list_widget.item(0).data(Qt.ItemDataRole.UserRole)
            if first_item_path:
                start_dir = str(Path(first_item_path).parent)

        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Dokumente zur Sammelmappe hinzufügen"),
            start_dir,
            self.SUPPORTED_FILTER,
        )
        if files:
            self._add_files(files)

    def _remove_selected(self):
        """Entfernt markierte Einträge aus der Liste."""
        selected_items = self._list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self._list_widget.row(item)
            self._list_widget.takeItem(row)
        self._update_stats()

    def _move_up(self):
        """Verschiebt gewählte Zeile nach oben."""
        current_row = self._list_widget.currentRow()
        if current_row > 0:
            item = self._list_widget.takeItem(current_row)
            self._list_widget.insertItem(current_row - 1, item)
            self._list_widget.setCurrentRow(current_row - 1)

    def _move_down(self):
        """Verschiebt gewählte Zeile nach unten."""
        current_row = self._list_widget.currentRow()
        if 0 <= current_row < self._list_widget.count() - 1:
            item = self._list_widget.takeItem(current_row)
            self._list_widget.insertItem(current_row + 1, item)
            self._list_widget.setCurrentRow(current_row + 1)

    def _set_all_checked(self, checked: bool):
        """Aktiviert oder deaktiviert alle Checkboxen."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self._list_widget.count()):
            self._list_widget.item(i).setCheckState(state)
        self._update_stats()

    def _on_item_changed(self, item: QListWidgetItem):
        """Aktualisiert Statistik bei Checkbox-Änderung."""
        self._update_stats()

    def _on_numbers_toggled(self, checked: bool):
        """Aktiviert/Deaktiviert das Format-Dropdown für Seitenzahlen."""
        self._label_pattern.setEnabled(checked)
        self._combo_pattern.setEnabled(checked)

    def _get_checked_paths(self) -> List[str]:
        """Gibt alle aktiv ausgewählten Dokumentpfade in Listenreihenfolge zurück."""
        paths = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                p = item.data(Qt.ItemDataRole.UserRole)
                if p:
                    paths.append(p)
        return paths

    def _update_stats(self):
        """Aktualisiert die Status- und Zählerzeile."""
        total = self._list_widget.count()
        active = len(self._get_checked_paths())
        if total == 0:
            self._label_stats.setText(tr("Keine Dokumente in der Liste."))
            self._btn_export.setEnabled(False)
        else:
            self._label_stats.setText(
                f"{active} {tr('von')} {total} {tr('Dokument(en) für Sammel-PDF aktiviert.')}"
            )
            self._btn_export.setEnabled(active > 0)

    def _on_export(self):
        """Führt den Export der Sammel-PDF durch."""
        checked_paths = self._get_checked_paths()
        if not checked_paths:
            QMessageBox.warning(
                self,
                tr("Keine Dokumente"),
                tr("Bitte aktivieren Sie mindestens ein Dokument für den Export."),
            )
            return

        # Zieldateiname vorschlagen
        default_dir = str(Path(checked_paths[0]).parent)
        theme_suffix = f"_{self._current_theme}" if self._current_theme else ""
        default_filename = f"Sammel-PDF{theme_suffix}.pdf"
        default_path = str(Path(default_dir) / default_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Sammel-PDF speichern"),
            default_path,
            "PDF-Dateien (*.pdf)",
        )
        if not save_path:
            return

        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        # UI sperren und Fortschritt zeigen
        self._progress.setVisible(True)
        self._btn_export.setEnabled(False)
        self._btn_cancel.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)

        opts = CollectionExportOptions(
            add_bookmarks=self._check_bookmarks.isChecked(),
            add_page_numbers=self._check_numbers.isChecked(),
            page_number_pattern=self._combo_pattern.currentData() or "Seite {page} / {total}",
            title=f"Sammel-PDF {self._current_theme}".strip(),
        )

        try:
            result = export_collection_pdf(checked_paths, save_path, options=opts)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._progress.setVisible(False)
            self._btn_export.setEnabled(True)
            self._btn_cancel.setEnabled(True)

            if not result.success:
                QMessageBox.critical(
                    self,
                    tr("Export fehlgeschlagen"),
                    result.error or tr("Ein unbekannter Fehler ist aufgetreten."),
                )
                return

            self._exported_file = result.output_path

            # Erfolgsmeldung mit Option zum Öffnen
            info_msg = (
                f"{tr('Sammel-PDF erfolgreich erstellt:')}\n"
                f"{result.output_path}\n\n"
                f"• {tr('Seiten gesamt:')} {result.total_pages}\n"
                f"• {tr('Eingebundene Dokumente:')} {result.document_count}"
            )
            if result.skipped_files:
                info_msg += f"\n• {tr('Übersprungene Dateien:')} {len(result.skipped_files)}"

            info_msg += f"\n\n{tr('Möchten Sie das Dokument jetzt öffnen?')}"

            reply = QMessageBox.question(
                self,
                tr("Export erfolgreich"),
                info_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._open_document(result.output_path)

            self.accept()

        except Exception as exc:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._progress.setVisible(False)
            self._btn_export.setEnabled(True)
            self._btn_cancel.setEnabled(True)
            self.logger.error("Unerwarteter Fehler beim Sammel-PDF-Export: %s", exc, exc_info=True)
            QMessageBox.critical(self, tr("Fehler"), str(exc))

    def _open_document(self, doc_path: str):
        """Öffnet das erstellte Dokument im Standard-PDF-Viewer."""
        p = Path(doc_path)
        if not p.exists():
            return
        try:
            if sys.platform == "win32":
                os.startfile(doc_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", doc_path], check=False, timeout=30)
            else:
                subprocess.run(["xdg-open", doc_path], check=False, timeout=30)
        except Exception as exc:
            self.logger.warning("Dokument konnte nicht extern geöffnet werden: %s", exc)

    @property
    def exported_file(self) -> Optional[str]:
        """Gibt den Pfad der erstellten Datei zurück (falls exportiert)."""
        return self._exported_file
