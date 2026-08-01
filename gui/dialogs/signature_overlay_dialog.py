#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Signatur-Overlay-Dialog
=======================================
Bild (PNG/JPG) als Unterschrift auf einer PDF-Seite platzieren.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QPushButton, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QFileDialog,
    QMessageBox, QWidget, QComboBox
)
from PySide6.QtCore import Qt

from utils.logger import LoggerMixin
from core.pdf.signature import SignatureOverlay, PYMUPDF_AVAILABLE


# Voreingestellte Positionen (werden beim Anwenden auf die tatsächliche
# Seitengröße skaliert; Werte in PDF-Punkten, Basis A4 595 × 842)
_PRESETS = {
    "Unten links (Standard)": {"x": 50.0, "y_from_bottom": 100.0},
    "Unten Mitte":             {"x": None,  "y_from_bottom": 100.0},   # x wird berechnet
    "Unten rechts":            {"x": None,  "y_from_bottom": 100.0},   # x wird berechnet
    "Benutzerdefiniert":       None,
}


class SignatureOverlayDialog(QDialog, LoggerMixin):
    """
    Dialog zum Einbetten einer Signatur-Grafik (PNG/JPG) in ein PDF.

    Der Nutzer wählt:
    - Eingabe-PDF und Signatur-Bild
    - Zielseite (1-basiert)
    - Voreingestellte oder manuelle Position
    - Breite und Höhe (in PDF-Punkten; A4 = ca. 595 × 842 pt)
    - Ob das Seitenverhältnis des Bildes beibehalten werden soll
    - Ausgabe-PDF
    """

    def __init__(self, parent=None, pdf_path: Optional[str] = None):
        super().__init__(parent)
        self._setup_ui()
        if pdf_path:
            self._input_pdf.setText(pdf_path)
            self._update_page_count()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Erstellt alle Bedienelemente."""
        self.setWindowTitle("Signatur-Overlay einbetten")
        self.setMinimumSize(540, 560)
        self.resize(580, 600)

        layout = QVBoxLayout(self)

        # --- Dateien ---
        files_group = QGroupBox("Dateien")
        files_form = QFormLayout(files_group)

        # Eingabe-PDF
        pdf_row = QHBoxLayout()
        self._input_pdf = QLineEdit()
        self._input_pdf.setPlaceholderText("PDF auswählen …")
        self._input_pdf.textChanged.connect(self._update_page_count)
        pdf_row.addWidget(self._input_pdf)
        btn_pdf = QPushButton("…")
        btn_pdf.setFixedWidth(30)
        btn_pdf.clicked.connect(self._browse_input_pdf)
        pdf_row.addWidget(btn_pdf)
        files_form.addRow("Eingabe-PDF:", pdf_row)

        # Signatur-Bild
        sig_row = QHBoxLayout()
        self._input_sig = QLineEdit()
        self._input_sig.setPlaceholderText("Signaturbild (PNG / JPG) auswählen …")
        sig_row.addWidget(self._input_sig)
        btn_sig = QPushButton("…")
        btn_sig.setFixedWidth(30)
        btn_sig.clicked.connect(self._browse_signature)
        sig_row.addWidget(btn_sig)
        files_form.addRow("Signatur-Bild:", sig_row)

        # Zielseite
        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, 9999)
        self._page_spin.setValue(1)
        self._page_count_label = QLabel("(PDF noch nicht geladen)")
        page_row = QHBoxLayout()
        page_row.addWidget(self._page_spin)
        page_row.addWidget(self._page_count_label)
        page_row.addStretch()
        files_form.addRow("Zielseite:", page_row)

        layout.addWidget(files_group)

        # --- Position & Größe ---
        pos_group = QGroupBox("Position & Größe  (1 Punkt ≈ 1/72 Zoll; A4 ≈ 595 × 842 pt)")
        pos_form = QFormLayout(pos_group)

        # Voreinstellung
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(list(_PRESETS.keys()))
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        pos_form.addRow("Voreinstellung:", self._preset_combo)

        # X
        self._x_spin = QDoubleSpinBox()
        self._x_spin.setRange(0.0, 5000.0)
        self._x_spin.setValue(50.0)
        self._x_spin.setSuffix(" pt")
        self._x_spin.setDecimals(1)
        pos_form.addRow("X (von links):", self._x_spin)

        # Y
        self._y_auto_check = QCheckBox("Automatisch (50 pt vom unteren Seitenrand)")
        self._y_auto_check.setChecked(True)
        self._y_auto_check.stateChanged.connect(self._on_y_auto_changed)
        pos_form.addRow("Y (von oben):", self._y_auto_check)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setRange(0.0, 5000.0)
        self._y_spin.setValue(720.0)
        self._y_spin.setSuffix(" pt")
        self._y_spin.setDecimals(1)
        self._y_spin.setEnabled(False)
        pos_form.addRow("", self._y_spin)

        # Breite
        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(10.0, 2000.0)
        self._width_spin.setValue(200.0)
        self._width_spin.setSuffix(" pt")
        self._width_spin.setDecimals(1)
        pos_form.addRow("Breite:", self._width_spin)

        # Höhe
        self._height_spin = QDoubleSpinBox()
        self._height_spin.setRange(5.0, 2000.0)
        self._height_spin.setValue(80.0)
        self._height_spin.setSuffix(" pt")
        self._height_spin.setDecimals(1)
        pos_form.addRow("Höhe:", self._height_spin)

        # Seitenverhältnis
        self._aspect_check = QCheckBox("Seitenverhältnis des Bildes beibehalten")
        self._aspect_check.setChecked(True)
        pos_form.addRow("", self._aspect_check)

        self._detect_existing_check = QCheckBox("Vorher prüfen, ob bereits eine Signatur vorhanden ist")
        self._detect_existing_check.setChecked(True)
        pos_form.addRow("", self._detect_existing_check)

        layout.addWidget(pos_group)

        # --- Ausgabe ---
        output_group = QGroupBox("Ausgabe")
        output_form = QFormLayout(output_group)

        out_row = QHBoxLayout()
        self._output_pdf = QLineEdit()
        self._output_pdf.setPlaceholderText("Ausgabe-PDF …")
        out_row.addWidget(self._output_pdf)
        btn_out = QPushButton("…")
        btn_out.setFixedWidth(30)
        btn_out.clicked.connect(self._browse_output_pdf)
        out_row.addWidget(btn_out)
        output_form.addRow("Ausgabe-PDF:", out_row)

        layout.addWidget(output_group)

        # --- Hinweis ---
        hint = QLabel(
            "Hinweis: PNG-Bilder mit transparentem Hintergrund werden "
            "korrekt übertragen. Das Original-PDF bleibt unverändert."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        layout.addWidget(hint)

        layout.addStretch()

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        self._btn_apply = QPushButton("Signatur einbetten")
        self._btn_apply.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self._btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self._btn_apply)
        layout.addLayout(btn_row)

        # Initialen Preset-Zustand anwenden
        self._on_preset_changed(self._preset_combo.currentText())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_input_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Eingabe-PDF wählen", "", "PDF-Dateien (*.pdf)"
        )
        if path:
            self._input_pdf.setText(path)
            # Auto-Ausgabe vorbelegen
            stem = Path(path).stem
            parent = Path(path).parent
            self._output_pdf.setText(str(parent / f"{stem}_signiert.pdf"))

    def _browse_signature(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Signaturbild wählen", "",
            "Bildformate (*.png *.jpg *.jpeg);;PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if path:
            self._input_sig.setText(path)

    def _browse_output_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Ausgabe-PDF wählen", "", "PDF-Dateien (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self._output_pdf.setText(path)

    def _update_page_count(self):
        """Aktualisiert die Seitenanzahl-Anzeige nach PDF-Auswahl."""
        pdf_path = self._input_pdf.text().strip()
        if not pdf_path or not Path(pdf_path).is_file():
            self._page_count_label.setText("(PDF noch nicht geladen)")
            return
        if not PYMUPDF_AVAILABLE:
            return
        try:
            import fitz
            doc = fitz.open(pdf_path)
            count = doc.page_count
            doc.close()
            self._page_count_label.setText(f"von {count} Seite(n)")
            self._page_spin.setMaximum(count)
        except Exception:
            self._page_count_label.setText("(Fehler beim Lesen)")

    def _on_y_auto_changed(self, state: int):
        """Aktiviert/Deaktiviert den Y-Spinner je nach Auto-Checkbox."""
        self._y_spin.setEnabled(not self._y_auto_check.isChecked())

    def _on_preset_changed(self, preset_name: str):
        """Reagiert auf Voreinstellungs-Wechsel."""
        is_custom = preset_name == "Benutzerdefiniert"
        self._x_spin.setEnabled(is_custom)
        self._y_auto_check.setEnabled(is_custom)
        self._y_spin.setEnabled(is_custom and not self._y_auto_check.isChecked())

        if not is_custom:
            preset = _PRESETS.get(preset_name)
            if preset and preset.get("x") is not None:
                self._x_spin.setValue(preset["x"])

    def _resolve_position(
        self, page_width: float, page_height: float, sig_width: float, sig_height: float
    ):
        """
        Berechnet x, y aus der gewählten Voreinstellung und der Seitengröße.

        Returns:
            Tuple (x, y) in PDF-Punkten
        """
        preset_name = self._preset_combo.currentText()
        y_from_bottom = 100.0  # Standard-Abstand vom Seitenrand

        if preset_name == "Benutzerdefiniert":
            x = self._x_spin.value()
            y = None if self._y_auto_check.isChecked() else self._y_spin.value()
            return x, y

        preset = _PRESETS.get(preset_name, {})
        bottom_offset = preset.get("y_from_bottom", y_from_bottom) if preset else y_from_bottom
        y = page_height - sig_height - bottom_offset

        if preset_name == "Unten links (Standard)":
            x = 50.0
        elif preset_name == "Unten Mitte":
            x = (page_width - sig_width) / 2.0
        elif preset_name == "Unten rechts":
            x = page_width - sig_width - 50.0
        else:
            x = 50.0

        return x, y

    def _on_apply(self):
        """Führt das Einbetten durch."""
        pdf_path = self._input_pdf.text().strip()
        sig_path = self._input_sig.text().strip()
        output_path = self._output_pdf.text().strip()

        # Eingabe-Validierung
        if not pdf_path:
            QMessageBox.warning(self, "Fehler", "Bitte eine Eingabe-PDF auswählen.")
            return
        if not Path(pdf_path).is_file():
            QMessageBox.warning(self, "Fehler", f"PDF nicht gefunden:\n{pdf_path}")
            return
        if not sig_path:
            QMessageBox.warning(self, "Fehler", "Bitte ein Signaturbild auswählen.")
            return
        if not Path(sig_path).is_file():
            QMessageBox.warning(self, "Fehler", f"Signaturbild nicht gefunden:\n{sig_path}")
            return
        if not output_path:
            QMessageBox.warning(self, "Fehler", "Bitte einen Ausgabepfad angeben.")
            return

        page_index = self._page_spin.value() - 1  # 1-basiert → 0-basiert
        width = self._width_spin.value()
        height = self._height_spin.value()
        keep_aspect = self._aspect_check.isChecked()

        # Tatsächliche Bildgröße und Seiten-Rect für Positions-Berechnung
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_rect = doc[page_index].rect if page_index < doc.page_count else fitz.Rect(0, 0, 595, 842)
            doc.close()
        except Exception:
            page_rect = None

        page_w = page_rect.width if page_rect else 595.0
        page_h = page_rect.height if page_rect else 842.0

        x, y = self._resolve_position(page_w, page_h, width, height)

        # Signatur einbetten
        self._btn_apply.setEnabled(False)
        self._btn_apply.setText("Einbetten …")

        overlay = SignatureOverlay()
        result = overlay.embed_signature_checked(
            pdf_path=pdf_path,
            signature_path=sig_path,
            output_path=output_path,
            page_index=page_index,
            x=x,
            y=y,
            width=width,
            height=height,
            keep_aspect=keep_aspect,
            skip_if_present=self._detect_existing_check.isChecked(),
        )

        self._btn_apply.setEnabled(True)
        self._btn_apply.setText("Signatur einbetten")

        if result.success and result.skipped_existing:
            QMessageBox.information(
                self, "Signatur bereits vorhanden",
                "Auf der Zielseite wurde bereits ein Signaturhinweis erkannt.\n"
                "Das PDF wurde ohne zusätzliches Overlay übernommen.\n\n"
                f"Datei: {output_path}"
            )
            self.accept()
        elif result.success:
            QMessageBox.information(
                self, "Erfolg",
                f"Signatur wurde erfolgreich eingebettet.\n\nDatei: {output_path}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Fehler",
                "Signatur konnte nicht eingebettet werden.\n"
                "Bitte Protokoll (logs/dokuzen.log) prüfen."
            )
