#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Redaction Dialog
==================================
Dialog zum Schwärzen sensibler Daten.
"""

from pathlib import Path
from typing import List, Optional, Set

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QWidget,
    QPushButton, QLabel, QFileDialog, QProgressBar,
    QMessageBox, QFormLayout, QCheckBox, QLineEdit,
    QTextEdit, QListWidget, QListWidgetItem, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from utils.logger import LoggerMixin
from core.redaction import (
    RedactionDetector, RedactionApplier, Match, SensitiveType,
    extract_page_text_and_char_rects
)
from core.pdf import PDFReader


class RedactionDialog(QDialog, LoggerMixin):
    """
    Dialog zum Schwärzen von PDFs.
    
    Features:
    - Automatische Erkennung (Email, Telefon, IBAN, etc.)
    - Blacklist-Wörter laden
    - Whitelist (Ausnahmen)
    - Vorschau der Treffer
    - Selektive Schwärzung
    """
    
    def __init__(self, parent=None, initial_file: str = None):
        super().__init__(parent)
        
        self._detector = RedactionDetector()
        self._applier = RedactionApplier()
        self._matches: List[Match] = []
        self._initial_file = initial_file
        
        self._setup_ui()
        
        if initial_file:
            self._input_path.setText(initial_file)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("PDF Schwärzen")
        self.setMinimumSize(700, 500)
        self.resize(900, 650)
        
        layout = QVBoxLayout(self)
        
        # Hauptsplitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Oberer Bereich: Einstellungen
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # Eingabe
        input_group = QGroupBox("PDF-Datei")
        input_layout = QHBoxLayout(input_group)
        
        self._input_path = QLineEdit()
        self._input_path.setPlaceholderText("PDF zum Schwärzen wählen...")
        input_layout.addWidget(self._input_path)
        
        btn_browse = QPushButton("Durchsuchen...")
        btn_browse.clicked.connect(self._on_browse_input)
        input_layout.addWidget(btn_browse)
        
        settings_layout.addWidget(input_group)
        
        # Erkennungsoptionen
        detect_group = QGroupBox("Automatische Erkennung")
        detect_layout = QVBoxLayout(detect_group)
        
        # Checkboxen für Typen
        types_layout = QHBoxLayout()
        
        self._chk_email = QCheckBox("E-Mail-Adressen")
        self._chk_email.setChecked(True)
        types_layout.addWidget(self._chk_email)
        
        self._chk_phone = QCheckBox("Telefonnummern")
        self._chk_phone.setChecked(True)
        types_layout.addWidget(self._chk_phone)
        
        self._chk_iban = QCheckBox("IBAN")
        self._chk_iban.setChecked(True)
        types_layout.addWidget(self._chk_iban)
        
        self._chk_date = QCheckBox("Datumsangaben")
        self._chk_date.setChecked(False)
        types_layout.addWidget(self._chk_date)
        
        types_layout.addStretch()
        detect_layout.addLayout(types_layout)
        
        # Blacklist
        blacklist_layout = QHBoxLayout()
        
        self._blacklist_path = QLineEdit()
        self._blacklist_path.setPlaceholderText("Optional: Blacklist-Datei (ein Wort pro Zeile)")
        blacklist_layout.addWidget(self._blacklist_path)
        
        btn_blacklist = QPushButton("...")
        btn_blacklist.setFixedWidth(30)
        btn_blacklist.clicked.connect(self._on_browse_blacklist)
        blacklist_layout.addWidget(btn_blacklist)
        
        detect_layout.addLayout(blacklist_layout)
        
        # Zusätzliche Wörter
        extra_layout = QHBoxLayout()
        extra_layout.addWidget(QLabel("Zusätzliche Wörter:"))
        
        self._extra_words = QLineEdit()
        self._extra_words.setPlaceholderText("Kommagetrennt: Name1, Name2, Firma XY")
        extra_layout.addWidget(self._extra_words)
        
        detect_layout.addLayout(extra_layout)
        
        settings_layout.addWidget(detect_group)
        
        # Scan-Button
        btn_scan = QPushButton("PDF scannen")
        btn_scan.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_scan.clicked.connect(self._on_scan)
        settings_layout.addWidget(btn_scan)
        
        splitter.addWidget(settings_widget)
        
        # Unterer Bereich: Ergebnisse
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        result_group = QGroupBox("Gefundene sensible Daten (zum Schwärzen auswählen)")
        result_inner = QVBoxLayout(result_group)
        
        # Tabelle
        self._result_table = QTableWidget()
        self._result_table.setColumnCount(5)
        self._result_table.setHorizontalHeaderLabels(["", "Seite", "Typ", "Text", "Konfidenz"])
        self._result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._result_table.setColumnWidth(0, 30)
        self._result_table.setColumnWidth(1, 50)
        self._result_table.setColumnWidth(2, 100)
        self._result_table.setColumnWidth(4, 80)
        self._result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        result_inner.addWidget(self._result_table)
        
        # Auswahl-Buttons
        select_layout = QHBoxLayout()
        
        btn_select_all = QPushButton("Alle auswählen")
        btn_select_all.clicked.connect(self._on_select_all)
        select_layout.addWidget(btn_select_all)
        
        btn_select_none = QPushButton("Keine auswählen")
        btn_select_none.clicked.connect(self._on_select_none)
        select_layout.addWidget(btn_select_none)
        
        self._status = QLabel("")
        select_layout.addWidget(self._status)
        
        select_layout.addStretch()
        result_inner.addLayout(select_layout)
        
        result_layout.addWidget(result_group)
        splitter.addWidget(result_widget)
        
        # Splitter-Größen
        splitter.setSizes([250, 350])
        
        # Fortschritt
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        
        self._btn_redact = QPushButton("Ausgewählte schwärzen...")
        self._btn_redact.setStyleSheet("font-weight: bold; padding: 8px;")
        self._btn_redact.setEnabled(False)
        self._btn_redact.clicked.connect(self._on_redact)
        btn_layout.addWidget(self._btn_redact)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _on_browse_input(self):
        """Wählt PDF aus."""
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF wählen", "", "PDF-Dateien (*.pdf)"
        )
        if path:
            self._input_path.setText(path)
    
    def _on_browse_blacklist(self):
        """Wählt Blacklist-Datei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Blacklist wählen", "", "Textdateien (*.txt)"
        )
        if path:
            self._blacklist_path.setText(path)
    
    def _on_scan(self):
        """Scannt PDF nach sensiblen Daten."""
        input_path = self._input_path.text().strip()
        
        if not input_path or not Path(input_path).exists():
            QMessageBox.warning(self, "Fehler", "Bitte gültige PDF auswählen.")
            return
        
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setText("Scanne...")
        
        # Detector konfigurieren
        self._detector.clear_blacklist()
        
        # Blacklist laden
        blacklist_path = self._blacklist_path.text().strip()
        if blacklist_path and Path(blacklist_path).exists():
            self._detector.load_blacklist(blacklist_path)
        
        # Extra-Wörter hinzufügen
        extra = self._extra_words.text().strip()
        if extra:
            words = [w.strip() for w in extra.split(",") if w.strip()]
            self._detector.add_to_blacklist(words)
        
        # PDF lesen und scannen
        try:
            import fitz
            doc = fitz.open(input_path)
            try:
                self._matches.clear()

                for i, page in enumerate(doc):
                    text, char_rects = extract_page_text_and_char_rects(page)
                    matches = self._detector.detect(text, page=i+1, char_rects=char_rects)

                    # Nach aktivierten Typen filtern
                    filtered = []
                    for m in matches:
                        if m.type == SensitiveType.EMAIL and self._chk_email.isChecked():
                            filtered.append(m)
                        elif m.type == SensitiveType.PHONE and self._chk_phone.isChecked():
                            filtered.append(m)
                        elif m.type == SensitiveType.IBAN and self._chk_iban.isChecked():
                            filtered.append(m)
                        elif m.type == SensitiveType.DATE and self._chk_date.isChecked():
                            filtered.append(m)
                        elif m.type == SensitiveType.CUSTOM:
                            filtered.append(m)

                    self._matches.extend(filtered)
            finally:
                doc.close()

        except Exception as e:
            self._progress.setVisible(False)
            QMessageBox.critical(self, "Fehler", f"Scan fehlgeschlagen: {e}")
            return
        
        self._progress.setVisible(False)
        self._update_table()
        
        count = len(self._matches)
        self._status.setText(f"{count} Treffer gefunden")
        self._btn_redact.setEnabled(count > 0)
    
    def _update_table(self):
        """Aktualisiert die Ergebnis-Tabelle."""
        self._result_table.setRowCount(len(self._matches))
        
        type_names = {
            SensitiveType.EMAIL: "E-Mail",
            SensitiveType.PHONE: "Telefon",
            SensitiveType.IBAN: "IBAN",
            SensitiveType.DATE: "Datum",
            SensitiveType.CUSTOM: "Blacklist",
            SensitiveType.NAME: "Name",
            SensitiveType.ADDRESS: "Adresse",
        }
        
        for row, match in enumerate(self._matches):
            # Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self._result_table.setItem(row, 0, chk)
            
            # Seite
            self._result_table.setItem(row, 1, QTableWidgetItem(str(match.page)))
            
            # Typ
            type_name = type_names.get(match.type, str(match.type))
            self._result_table.setItem(row, 2, QTableWidgetItem(type_name))
            
            # Text
            text_item = QTableWidgetItem(match.text)
            text_item.setToolTip(match.text)
            self._result_table.setItem(row, 3, text_item)
            
            # Konfidenz
            conf_item = QTableWidgetItem(f"{match.confidence:.0f}%")
            self._result_table.setItem(row, 4, conf_item)
    
    def _on_select_all(self):
        """Wählt alle Treffer aus."""
        for row in range(self._result_table.rowCount()):
            item = self._result_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
    
    def _on_select_none(self):
        """Hebt Auswahl auf."""
        for row in range(self._result_table.rowCount()):
            item = self._result_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
    
    def _get_selected_matches(self) -> List[Match]:
        """Gibt ausgewählte Treffer zurück."""
        selected = []
        for row in range(self._result_table.rowCount()):
            item = self._result_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(self._matches[row])
        return selected
    
    def _on_redact(self):
        """Schwärzt ausgewählte Treffer."""
        selected = self._get_selected_matches()
        
        if not selected:
            QMessageBox.warning(self, "Fehler", "Keine Treffer ausgewählt.")
            return
        
        input_path = self._input_path.text().strip()
        
        # Ausgabepfad
        stem = Path(input_path).stem
        parent = Path(input_path).parent
        default_output = str(parent / f"{stem}_geschwärzt.pdf")
        
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Geschwärzte PDF speichern", default_output, "PDF (*.pdf)"
        )
        
        if not output_path:
            return

        # BUGSWEEP-34: Ueberschreiben der Quell-PDF verhindern — schreibt redact_pdf nicht atomar in
        # die noch geöffnete Datei, droht Korruption der EINZIGEN sensiblen Original-PDF.
        if Path(output_path).resolve() == Path(input_path).resolve():
            QMessageBox.warning(
                self, "Ungültiges Ziel",
                "Die geschwärzte PDF darf die Originaldatei nicht überschreiben.\n"
                "Bitte einen anderen Dateinamen wählen."
            )
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setText("Schwärze...")
        
        success = self._applier.redact_pdf(input_path, output_path, selected)
        
        self._progress.setVisible(False)
        
        if success:
            # P0-Fix (Review 2026-07-23): redact_pdf() meldete bisher "Erfolg",
            # auch wenn einzelne Treffer (z.B. IBANs mit Leerzeichen) im PDF
            # nicht gefunden und daher NICHT geschwaerzt wurden. Statistik
            # auswerten statt dem Nutzer eine falsche Sicherheit vorzutaeuschen.
            stats = getattr(self._applier, "last_redaction_stats", None) or {}
            missed = stats.get("missed", 0)
            if missed:
                self._status.setText(f"Teilweise geschwärzt: {missed} Treffer nicht gefunden")
                QMessageBox.warning(
                    self, "Unvollständig geschwärzt",
                    f"PDF gespeichert:\n{output_path}\n\n"
                    f"{stats.get('redacted', 0)} von {stats.get('total', len(selected))} "
                    "Stellen wurden geschwärzt.\n"
                    f"{missed} Stelle(n) konnten im PDF nicht lokalisiert werden "
                    "(z.B. Text mit Zeilenumbruch oder ungewöhnlichen Leerzeichen wie "
                    "bei IBANs) und sind im Ergebnis noch UNGESCHWÄRZT.\n\n"
                    "Bitte die Ausgabedatei manuell prüfen, bevor sie weitergegeben wird."
                )
            else:
                self._status.setText(f"Geschwärzt: {len(selected)} Stellen")
                QMessageBox.information(
                    self, "Erfolg",
                    f"PDF geschwärzt:\n{output_path}\n\n{len(selected)} Stellen geschwärzt."
                )
        else:
            self._status.setText("Fehler beim Schwärzen")
            QMessageBox.critical(self, "Fehler", "Schwärzung fehlgeschlagen.")
