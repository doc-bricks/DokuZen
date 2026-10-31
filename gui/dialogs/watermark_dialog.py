#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF-Wasserzeichen-Dialog
=====================================
Dialog zum Konfigurieren und Einbetten von Text- und Bild-Wasserzeichen
in PDF-Dokumente mit flexibler Platzierung, Rotation, Deckkraft und Seitenbereichen.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.pdf.watermark import (
    PDFWatermarker,
    WatermarkLayer,
    WatermarkOptions,
    WatermarkPosition,
    WatermarkType,
    parse_color,
    PYMUPDF_AVAILABLE,
)
from translator import tr
from utils.logger import LoggerMixin


class WatermarkDialog(QDialog, LoggerMixin):
    """
    Dialog zum Einbetten von Text- und Bild-Wasserzeichen in PDFs.
    """

    def __init__(self, parent: Optional[QWidget] = None, pdf_path: Optional[str] = None):
        super().__init__(parent)
        self._watermarker = PDFWatermarker()
        self._setup_ui()

        if pdf_path:
            self._input_pdf.setText(pdf_path)
            self._on_input_pdf_changed(pdf_path)

    def _setup_ui(self) -> None:
        """Erstellt alle UI-Elemente und Layouts."""
        self.setWindowTitle(tr("PDF-Wasserzeichen verwalten"))
        self.setAccessibleName("PDF-Wasserzeichen verwalten")
        self.setAccessibleDescription("Dialog zum Hinzufügen von Text- oder Bild-Wasserzeichen in PDF-Dateien.")
        self.setMinimumSize(560, 680)
        self.resize(600, 720)

        main_layout = QVBoxLayout(self)

        # === 1. Dateien-Gruppe ===
        files_group = QGroupBox(tr("Dateien"), self)
        files_form = QFormLayout(files_group)

        # Eingabe-PDF
        input_row = QHBoxLayout()
        self._input_pdf = QLineEdit(self)
        self._input_pdf.setPlaceholderText(tr("PDF auswählen …"))
        self._input_pdf.setAccessibleName("Eingabe-PDF")
        self._input_pdf.setAccessibleDescription("Pfad zur PDF-Datei, auf die das Wasserzeichen angewendet werden soll.")
        self._input_pdf.setToolTip("Pfad zur zu bearbeitenden PDF-Datei.")
        self._input_pdf.textChanged.connect(self._on_input_pdf_changed)
        input_row.addWidget(self._input_pdf)

        btn_browse_input = QPushButton(tr("Durchsuchen..."), self)
        btn_browse_input.setAccessibleName("Eingabe-PDF durchsuchen")
        btn_browse_input.setAccessibleDescription("Öffnet einen Dateidialog zur Auswahl der Eingabe-PDF.")
        btn_browse_input.setToolTip("PDF-Datei auf der Festplatte auswählen.")
        btn_browse_input.clicked.connect(self._browse_input_pdf)
        input_row.addWidget(btn_browse_input)
        files_form.addRow(tr("Eingabe-PDF:"), input_row)

        # Speichermodus
        mode_row = QHBoxLayout()
        self._radio_inplace = QRadioButton(tr("In-Place speichern (Quelldatei überschreiben)"), self)
        self._radio_inplace.setAccessibleName("In-Place speichern")
        self._radio_inplace.setAccessibleDescription("Schreibt das Wasserzeichen direkt in die vorhandene PDF-Datei.")
        self._radio_inplace.setToolTip("Überschreibt die Original-PDF sicher via atomarem Schreiben.")
        self._radio_inplace.setChecked(True)
        self._radio_inplace.toggled.connect(self._toggle_output_mode)
        mode_row.addWidget(self._radio_inplace)

        self._radio_new_file = QRadioButton(tr("Neue Datei speichern"), self)
        self._radio_new_file.setAccessibleName("Neue Datei speichern")
        self._radio_new_file.setAccessibleDescription("Speichert das Ergebnis in einer neuen separaten PDF-Datei.")
        self._radio_new_file.setToolTip("Erstellt eine neue Kopie mit Wasserzeichen.")
        mode_row.addWidget(self._radio_new_file)
        files_form.addRow(tr("Speichermodus:"), mode_row)

        # Ausgabepfad
        output_row = QHBoxLayout()
        self._output_pdf = QLineEdit(self)
        self._output_pdf.setPlaceholderText(tr("Ausgabepfad wählen …"))
        self._output_pdf.setAccessibleName("Ausgabe-PDF")
        self._output_pdf.setAccessibleDescription("Zielpfad für die neue PDF-Datei mit Wasserzeichen.")
        self._output_pdf.setToolTip("Dateipfad der neuen PDF-Datei.")
        self._output_pdf.setEnabled(False)
        output_row.addWidget(self._output_pdf)

        self._btn_browse_output = QPushButton(tr("Durchsuchen..."), self)
        self._btn_browse_output.setAccessibleName("Ausgabe-PDF durchsuchen")
        self._btn_browse_output.setAccessibleDescription("Öffnet Dateidialog zum Festlegen des Ausgabepfads.")
        self._btn_browse_output.setToolTip("Speicherort für die neue PDF-Datei wählen.")
        self._btn_browse_output.setEnabled(False)
        self._btn_browse_output.clicked.connect(self._browse_output_pdf)
        output_row.addWidget(self._btn_browse_output)
        files_form.addRow(tr("Ausgabe-PDF:"), output_row)

        main_layout.addWidget(files_group)

        # === 2. Wasserzeichen-Typ ===
        type_group = QGroupBox(tr("Wasserzeichen-Typ:"), self)
        type_layout = QHBoxLayout(type_group)

        self._radio_text = QRadioButton(tr("Text-Wasserzeichen"), self)
        self._radio_text.setChecked(True)
        self._radio_text.setAccessibleName("Text-Wasserzeichen auswählen")
        self._radio_text.setAccessibleDescription("Verwendet frei konfigurierbaren Text oder Stempel als Wasserzeichen.")
        self._radio_text.setToolTip("Aktiviert Text-Wasserzeichen.")
        self._radio_text.toggled.connect(self._toggle_watermark_type)
        type_layout.addWidget(self._radio_text)

        self._radio_image = QRadioButton(tr("Bild-Wasserzeichen"), self)
        self._radio_image.setAccessibleName("Bild-Wasserzeichen auswählen")
        self._radio_image.setAccessibleDescription("Verwendet eine Bilddatei (z. B. Logo-PNG mit Transparenz) als Wasserzeichen.")
        self._radio_image.setToolTip("Aktiviert Bild-Wasserzeichen.")
        type_layout.addWidget(self._radio_image)

        main_layout.addWidget(type_group)

        # === 3. Text-Einstellungen ===
        self._text_group = QGroupBox(tr("Text-Wasserzeichen"), self)
        text_form = QFormLayout(self._text_group)

        self._edit_text = QLineEdit(tr("ENTWURF"), self)
        self._edit_text.setAccessibleName("Wasserzeichen-Text")
        self._edit_text.setAccessibleDescription("Text, der als Wasserzeichen über die PDF gelegt wird.")
        self._edit_text.setToolTip("Geben Sie den gewünschten Wasserzeichen-Text ein.")
        text_form.addRow(tr("Wasserzeichen-Text:"), self._edit_text)

        # Schnellvorlagen (Presets)
        presets_row = QHBoxLayout()
        for preset_label in ("ENTWURF", "VERTRAULICH", "KOPIE", "GEHEIM", "DRAFT"):
            btn_preset = QPushButton(preset_label, self)
            btn_preset.setAccessibleName(f"Vorlage {preset_label}")
            btn_preset.setAccessibleDescription(f"Übernimmt '{preset_label}' als Wasserzeichen-Text.")
            btn_preset.setToolTip(f"Setzt den Text auf '{preset_label}'.")
            btn_preset.clicked.connect(lambda _, p=preset_label: self._set_preset_text(p))
            presets_row.addWidget(btn_preset)
        text_form.addRow(tr("Schnellauswahl (Vorlagen):"), presets_row)

        # Schriftgröße & Auto
        font_row = QHBoxLayout()
        self._spin_fontsize = QSpinBox(self)
        self._spin_fontsize.setRange(10, 160)
        self._spin_fontsize.setValue(48)
        self._spin_fontsize.setAccessibleName("Schriftgröße")
        self._spin_fontsize.setAccessibleDescription("Schriftgröße des Wasserzeichens in Punkten.")
        self._spin_fontsize.setToolTip("Schriftgröße einstellen.")
        font_row.addWidget(self._spin_fontsize)

        self._chk_auto_font = QCheckBox(tr("Automatisch anpassen"), self)
        self._chk_auto_font.setAccessibleName("Schriftgröße automatisch anpassen")
        self._chk_auto_font.setAccessibleDescription("Passt die Schriftgröße automatisch an die Seitenbreite an.")
        self._chk_auto_font.toggled.connect(self._toggle_auto_font)
        font_row.addWidget(self._chk_auto_font)
        text_form.addRow(tr("Schriftgröße:"), font_row)

        # Farbe
        self._combo_color = QComboBox(self)
        self._combo_color.addItem(tr("Grau"), "gray")
        self._combo_color.addItem(tr("Rot"), "red")
        self._combo_color.addItem(tr("Blau"), "blue")
        self._combo_color.addItem(tr("Schwarz"), "black")
        self._combo_color.setAccessibleName("Farbe")
        self._combo_color.setAccessibleDescription("Farbe des Text-Wasserzeichens.")
        self._combo_color.setToolTip("Wählen Sie die Textfarbe.")
        text_form.addRow(tr("Farbe:"), self._combo_color)

        # Winkel
        angle_row = QHBoxLayout()
        self._spin_angle = QSpinBox(self)
        self._spin_angle.setRange(-90, 90)
        self._spin_angle.setValue(45)
        self._spin_angle.setAccessibleName("Winkel (Grad)")
        self._spin_angle.setAccessibleDescription("Rotationswinkel des Wasserzeichens in Grad (-90 bis +90).")
        self._spin_angle.setToolTip("Rotationswinkel des Wasserzeichens.")
        angle_row.addWidget(self._spin_angle)

        btn_angle_0 = QPushButton("0°", self)
        btn_angle_0.setToolTip("Horizontal ausrichten.")
        btn_angle_0.clicked.connect(lambda: self._spin_angle.setValue(0))
        angle_row.addWidget(btn_angle_0)

        btn_angle_45 = QPushButton("45°", self)
        btn_angle_45.setToolTip("Diagonal von unten links nach oben rechts.")
        btn_angle_45.clicked.connect(lambda: self._spin_angle.setValue(45))
        angle_row.addWidget(btn_angle_45)

        btn_angle_neg45 = QPushButton("-45°", self)
        btn_angle_neg45.setToolTip("Diagonal von oben links nach unten rechts.")
        btn_angle_neg45.clicked.connect(lambda: self._spin_angle.setValue(-45))
        angle_row.addWidget(btn_angle_neg45)
        text_form.addRow(tr("Winkel (Grad):"), angle_row)

        main_layout.addWidget(self._text_group)

        # === 4. Bild-Einstellungen ===
        self._image_group = QGroupBox(tr("Bild-Wasserzeichen"), self)
        image_form = QFormLayout(self._image_group)
        self._image_group.setVisible(False)

        img_row = QHBoxLayout()
        self._edit_image_path = QLineEdit(self)
        self._edit_image_path.setPlaceholderText(tr("Bilddatei (PNG/JPG) auswählen …"))
        self._edit_image_path.setAccessibleName("Bilddatei")
        self._edit_image_path.setAccessibleDescription("Pfad zur Bilddatei für das Wasserzeichen.")
        self._edit_image_path.setToolTip("Bilddatei auswählen.")
        img_row.addWidget(self._edit_image_path)

        btn_browse_img = QPushButton(tr("Durchsuchen..."), self)
        btn_browse_img.setAccessibleName("Bilddatei durchsuchen")
        btn_browse_img.setAccessibleDescription("Öffnet einen Dateidialog zur Auswahl des Wasserzeichen-Bildes.")
        btn_browse_img.setToolTip("Bild auf Festplatte wählen.")
        btn_browse_img.clicked.connect(self._browse_image_file)
        img_row.addWidget(btn_browse_img)
        image_form.addRow(tr("Bilddatei:"), img_row)

        self._spin_img_scale = QSpinBox(self)
        self._spin_img_scale.setRange(10, 100)
        self._spin_img_scale.setValue(50)
        self._spin_img_scale.setSuffix(" %")
        self._spin_img_scale.setAccessibleName("Bild-Skalierung")
        self._spin_img_scale.setAccessibleDescription("Breite des Bildes im Verhältnis zur Seitenbreite in Prozent.")
        self._spin_img_scale.setToolTip("Größe des Bildes im Verhältnis zur Seite.")
        image_form.addRow(tr("Größe:"), self._spin_img_scale)

        main_layout.addWidget(self._image_group)

        # === 5. Gemeinsame Erscheinungsbild-Gruppe ===
        common_group = QGroupBox(tr("Darstellung"), self)
        common_form = QFormLayout(common_group)

        # Deckkraft
        opacity_row = QHBoxLayout()
        self._slider_opacity = QSlider(Qt.Orientation.Horizontal, self)
        self._slider_opacity.setRange(5, 100)
        self._slider_opacity.setValue(25)
        self._slider_opacity.setAccessibleName("Deckkraft")
        self._slider_opacity.setAccessibleDescription("Regler für die Deckkraft des Wasserzeichens von 5 bis 100 Prozent.")
        self._slider_opacity.setToolTip("Transparenz des Wasserzeichens einstellen.")
        self._lbl_opacity = QLabel("25 %", self)
        self._slider_opacity.valueChanged.connect(lambda v: self._lbl_opacity.setText(f"{v} %"))
        opacity_row.addWidget(self._slider_opacity)
        opacity_row.addWidget(self._lbl_opacity)
        common_form.addRow(tr("Deckkraft (Transparenz):"), opacity_row)

        # Position
        self._combo_pos = QComboBox(self)
        self._combo_pos.addItem(tr("Zentriert"), "center")
        self._combo_pos.addItem(tr("Oben links"), "top_left")
        self._combo_pos.addItem(tr("Oben rechts"), "top_right")
        self._combo_pos.addItem(tr("Unten links"), "bottom_left")
        self._combo_pos.addItem(tr("Unten rechts"), "bottom_right")
        self._combo_pos.addItem(tr("Gekachelt (Mehrfach)"), "tiled")
        self._combo_pos.setAccessibleName("Position")
        self._combo_pos.setAccessibleDescription("Platzierung des Wasserzeichens auf der PDF-Seite.")
        self._combo_pos.setToolTip("Wählen Sie die Position auf der Seite.")
        common_form.addRow(tr("Position:"), self._combo_pos)

        # Ebene
        self._combo_layer = QComboBox(self)
        self._combo_layer.addItem(tr("Vordergrund (über Text)"), "foreground")
        self._combo_layer.addItem(tr("Hintergrund (unter Text)"), "background")
        self._combo_layer.setAccessibleName("Ebene")
        self._combo_layer.setAccessibleDescription("Ebene des Wasserzeichens: im Vordergrund oder im Hintergrund.")
        self._combo_layer.setToolTip("Ebene des Wasserzeichens festlegen.")
        common_form.addRow(tr("Ebene:"), self._combo_layer)

        # Seitenbereich
        pages_row = QHBoxLayout()
        self._combo_pages = QComboBox(self)
        self._combo_pages.addItem(tr("Alle Seiten"), "all")
        self._combo_pages.addItem(tr("Nur erste Seite"), "first")
        self._combo_pages.addItem(tr("Gerade Seiten"), "even")
        self._combo_pages.addItem(tr("Ungerade Seiten"), "odd")
        self._combo_pages.addItem(tr("Bereich (z. B. 1-3, 5):"), "custom")
        self._combo_pages.setAccessibleName("Seitenbereich")
        self._combo_pages.setAccessibleDescription("Bestimmt, auf welchen Seiten das Wasserzeichen eingefügt wird.")
        self._combo_pages.currentIndexChanged.connect(self._toggle_custom_pages)
        pages_row.addWidget(self._combo_pages)

        self._edit_custom_pages = QLineEdit(self)
        self._edit_custom_pages.setPlaceholderText("1-3, 5")
        self._edit_custom_pages.setEnabled(False)
        self._edit_custom_pages.setAccessibleName("Benutzerdefinierter Seitenbereich")
        self._edit_custom_pages.setAccessibleDescription("Geben Sie Seitenzahlen und Bereiche ein (z. B. 1-3, 5).")
        pages_row.addWidget(self._edit_custom_pages)
        common_form.addRow(tr("Seiten:"), pages_row)

        main_layout.addWidget(common_group)

        # === 6. Dialog-Buttons ===
        btn_layout = QHBoxLayout()
        self._btn_apply = QPushButton(tr("Wasserzeichen anwenden"), self)
        self._btn_apply.setDefault(True)
        self._btn_apply.setAccessibleName("Wasserzeichen anwenden")
        self._btn_apply.setAccessibleDescription("Fügt das Wasserzeichen in die PDF-Datei ein.")
        self._btn_apply.clicked.connect(self._apply_watermark)
        btn_layout.addWidget(self._btn_apply)

        btn_cancel = QPushButton(tr("Abbrechen"), self)
        btn_cancel.setAccessibleName("Abbrechen")
        btn_cancel.setAccessibleDescription("Schließt das Fenster ohne Änderungen.")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # UI-Ereignisse & Hilfsmethoden
    # ------------------------------------------------------------------

    def _toggle_output_mode(self, checked: bool) -> None:
        """Aktiviert/Deaktiviert das Ausgabefeld je nach In-Place-Einstellung."""
        is_inplace = self._radio_inplace.isChecked()
        self._output_pdf.setEnabled(not is_inplace)
        self._btn_browse_output.setEnabled(not is_inplace)

    def _toggle_watermark_type(self, checked: bool) -> None:
        """Schaltet zwischen Text- und Bild-Optionen um."""
        is_text = self._radio_text.isChecked()
        self._text_group.setVisible(is_text)
        self._image_group.setVisible(not is_text)

    def _toggle_auto_font(self, checked: bool) -> None:
        """Deaktiviert manuelles Schriftgrößen-Feld bei Auto-Check."""
        self._spin_fontsize.setEnabled(not checked)

    def _toggle_custom_pages(self, index: int) -> None:
        """Aktiviert das Bereichsfeld, wenn 'Bereich' ausgewählt ist."""
        is_custom = (self._combo_pages.currentData() == "custom")
        self._edit_custom_pages.setEnabled(is_custom)

    def _set_preset_text(self, text: str) -> None:
        """Setzt den Wasserzeichen-Text auf eine Vorlage."""
        self._edit_text.setText(text)

    def _on_input_pdf_changed(self, text: str) -> None:
        """Aktualisiert Standard-Zieldatei bei Änderung der Eingabedatei."""
        if not text or not self._radio_new_file.isChecked():
            return
        p = Path(text)
        if p.suffix.lower() == ".pdf":
            default_out = str(p.with_stem(f"{p.stem}_watermarked"))
            self._output_pdf.setText(default_out)

    def _browse_input_pdf(self) -> None:
        """Öffnet Dateidialog für Eingabe-PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("PDF-Dateien"),
            self._input_pdf.text() or "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self._input_pdf.setText(file_path)
            self._on_input_pdf_changed(file_path)

    def _browse_output_pdf(self) -> None:
        """Öffnet Dateidialog für Ausgabe-PDF."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Speichern unter"),
            self._output_pdf.text() or "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self._output_pdf.setText(file_path)

    def _browse_image_file(self) -> None:
        """Öffnet Dateidialog für Bilddatei."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Bilddatei auswählen"),
            self._edit_image_path.text() or "",
            "Images (*.png *.jpg *.jpeg *.svg *.bmp)",
        )
        if file_path:
            self._edit_image_path.setText(file_path)

    def _apply_watermark(self) -> None:
        """Validiert Eingaben und wendet das Wasserzeichen an."""
        src = self._input_pdf.text().strip()
        if not src:
            QMessageBox.warning(self, tr("Hinweis"), tr("Bitte wählen Sie eine Eingabe-PDF aus."))
            return

        if not os.path.exists(src):
            QMessageBox.critical(self, tr("Fehler"), tr("Eingabedatei nicht gefunden."))
            return

        if self._radio_inplace.isChecked():
            dst = src
        else:
            dst = self._output_pdf.text().strip()
            if not dst:
                QMessageBox.warning(self, tr("Hinweis"), tr("Bitte geben Sie einen Ausgabepfad an."))
                return

        # Optionen zusammenstellen
        is_image = self._radio_image.isChecked()
        wm_type = WatermarkType.IMAGE if is_image else WatermarkType.TEXT

        # Seitenbereich
        pages_mode = self._combo_pages.currentData()
        if pages_mode == "custom":
            pages_spec = self._edit_custom_pages.text().strip()
            if not pages_spec:
                QMessageBox.warning(self, tr("Hinweis"), tr("Bitte geben Sie einen Seitenbereich an."))
                return
        else:
            pages_spec = str(pages_mode)

        # Ebene
        layer_str = str(self._combo_layer.currentData())
        layer = WatermarkLayer.BACKGROUND if layer_str == "background" else WatermarkLayer.FOREGROUND

        # Position
        pos_str = str(self._combo_pos.currentData())
        pos_map = {
            "center": WatermarkPosition.CENTER,
            "top_left": WatermarkPosition.TOP_LEFT,
            "top_right": WatermarkPosition.TOP_RIGHT,
            "bottom_left": WatermarkPosition.BOTTOM_LEFT,
            "bottom_right": WatermarkPosition.BOTTOM_RIGHT,
            "tiled": WatermarkPosition.TILED,
        }
        pos = pos_map.get(pos_str, WatermarkPosition.CENTER)

        # Farbe & Schriftgröße
        color_val = self._combo_color.currentData()
        parsed_color = parse_color(color_val)
        font_size = None if self._chk_auto_font.isChecked() else float(self._spin_fontsize.value())
        opacity = float(self._slider_opacity.value()) / 100.0
        angle = float(self._spin_angle.value())

        options = WatermarkOptions(
            watermark_type=wm_type,
            text=self._edit_text.text().strip() or "ENTWURF",
            image_path=self._edit_image_path.text().strip() if is_image else None,
            font_size=font_size,
            color=parsed_color,
            opacity=opacity,
            angle=angle,
            position=pos,
            layer=layer,
            pages=pages_spec,
            scale=float(self._spin_img_scale.value()) / 100.0,
        )

        res = self._watermarker.apply_to_pdf(src, dst, options)

        if res.success:
            QMessageBox.information(
                self,
                tr("Erfolg"),
                f"{tr('Wasserzeichen erfolgreich angewendet')}.\n{res.pages_watermarked} / {res.total_pages} {tr('Seiten')}.",
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                tr("Fehler"),
                res.error or tr("Wasserzeichen-Verarbeitung fehlgeschlagen."),
            )


__all__ = ["WatermarkDialog"]
