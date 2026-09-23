#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF-Annotationen-Dialog
====================================
Dialog zur Verwaltung und Erstellung von PDF-Annotationen:
Marker, Notizen/Kommentare, Freitext, Stempel und Formen.
"""

from pathlib import Path
import shutil
from typing import Optional, List, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QPushButton, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QFileDialog,
    QMessageBox, QWidget, QComboBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QRadioButton, QButtonGroup, QTextEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal

from utils.logger import LoggerMixin
from translator import tr
from core.pdf.annotations import (
    PDFAnnotator,
    AnnotationType,
    StampType,
    AnnotationColor,
    Annotation,
    PYMUPDF_AVAILABLE
)

if PYMUPDF_AVAILABLE:
    import fitz


class PDFAnnotationDialog(QDialog, LoggerMixin):
    """
    Dialog zur Bearbeitung und Erstellung von PDF-Annotationen.
    """

    annotations_changed = Signal(str)

    COLOR_PRESETS = {
        "Gelb": AnnotationColor.yellow(),
        "Grün": AnnotationColor.green(),
        "Rot": AnnotationColor.red(),
        "Blau": AnnotationColor.blue(),
        "Orange": AnnotationColor.orange(),
        "Lila": AnnotationColor.purple(),
        "Schwarz": AnnotationColor(0.0, 0.0, 0.0),
    }

    STAMP_OPTIONS = [
        ("Genehmigt", StampType.APPROVED),
        ("Vertraulich", StampType.CONFIDENTIAL),
        ("Entwurf", StampType.DRAFT),
        ("Final", StampType.FINAL),
        ("Abgelehnt", StampType.NOT_APPROVED),
        ("Streng geheim", StampType.TOP_SECRET),
        ("Zur Prüfung", StampType.FOR_COMMENT),
        ("Abgelaufen", StampType.EXPIRED),
    ]

    STAMP_POSITIONS = [
        "Oben rechts",
        "Oben links",
        "Mitte",
        "Unten rechts",
        "Unten links",
        "Benutzerdefiniert",
    ]

    def __init__(self, parent=None, pdf_path: Optional[str] = None):
        super().__init__(parent)
        self._annotator = PDFAnnotator()
        self._current_doc_pages = 0
        self._page_width = 595.0
        self._page_height = 842.0
        self._loaded_annotations: List[Annotation] = []

        self._setup_ui()

        if pdf_path and Path(pdf_path).exists():
            self._input_path.setText(str(Path(pdf_path).resolve()))
            self._load_document()
        else:
            self._update_controls_state()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Erstellt die Benutzeroberfläche und Barrierefreiheits-Attribute."""
        self.setWindowTitle(tr("PDF-Annotationen verwalten"))
        self.setMinimumSize(740, 700)
        self.resize(800, 760)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Nicht-Verfügbarkeits-Warnung wenn fitz fehlt
        if not PYMUPDF_AVAILABLE:
            warn_lbl = QLabel(tr("PyMuPDF ist nicht verfügbar. PDF-Annotationen erfordern PyMuPDF."))
            warn_lbl.setStyleSheet("color: #d9534f; font-weight: bold; padding: 6px; background: #fdf7f7; border: 1px solid #ebccd1; border-radius: 4px;")
            main_layout.addWidget(warn_lbl)

        # --- Gruppe 1: Datei & Seite ---
        doc_group = QGroupBox(tr("PDF-Dokument"))
        doc_layout = QVBoxLayout(doc_group)

        file_row = QHBoxLayout()
        lbl_file = QLabel(tr("Eingabe-PDF:"))
        lbl_file.setFixedWidth(85)
        file_row.addWidget(lbl_file)

        self._input_path = QLineEdit()
        self._input_path.setPlaceholderText(tr("PDF auswählen …"))
        self._input_path.setToolTip(tr("Pfad zur zu annotierenden PDF-Datei."))
        self._input_path.setAccessibleName(tr("Eingabe-PDF"))
        self._input_path.setAccessibleDescription(tr("Pfad zur zu annotierenden PDF-Datei."))
        self._input_path.textChanged.connect(self._on_input_path_changed)
        file_row.addWidget(self._input_path)

        self._btn_browse_input = QPushButton("…")
        self._btn_browse_input.setFixedWidth(32)
        self._btn_browse_input.setToolTip(tr("PDF-Datei auswählen"))
        self._btn_browse_input.setAccessibleName(tr("PDF durchsuchen"))
        self._btn_browse_input.setAccessibleDescription(tr("Öffnet Dateidialog zur Auswahl einer PDF-Datei."))
        self._btn_browse_input.clicked.connect(self._browse_input_file)
        file_row.addWidget(self._btn_browse_input)
        doc_layout.addLayout(file_row)

        # Seiten-Steuerung & Info
        page_row = QHBoxLayout()
        lbl_page = QLabel(tr("Seite:"))
        lbl_page.setFixedWidth(85)
        page_row.addWidget(lbl_page)

        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, 1)
        self._page_spin.setValue(1)
        self._page_spin.setToolTip(tr("Zielseite für Annotationen (1-basiert)."))
        self._page_spin.setAccessibleName(tr("Zielseite"))
        self._page_spin.setAccessibleDescription(tr("Wählt die aktive Seite im Dokument aus."))
        self._page_spin.valueChanged.connect(self._on_page_changed)
        page_row.addWidget(self._page_spin)

        self._lbl_page_info = QLabel("—")
        self._lbl_page_info.setStyleSheet("color: #666;")
        page_row.addWidget(self._lbl_page_info)
        page_row.addStretch()
        doc_layout.addLayout(page_row)

        # Speicherziel: In-Place vs. Neue Datei
        dest_row = QHBoxLayout()
        self._output_group = QButtonGroup(self)
        self._radio_inplace = QRadioButton(tr("Originaldatei direkt aktualisieren"))
        self._radio_inplace.setChecked(True)
        self._radio_inplace.setToolTip(tr("Änderungen direkt in die Quelldatei schreiben."))
        self._radio_inplace.setAccessibleName(tr("In-Place speichern"))
        self._radio_inplace.setAccessibleDescription(tr("Schreibt Annotationen direkt in die geöffnete PDF-Datei."))
        self._output_group.addButton(self._radio_inplace)
        dest_row.addWidget(self._radio_inplace)

        self._radio_new_file = QRadioButton(tr("In neue Datei speichern"))
        self._radio_new_file.setToolTip(tr("Annotationen in eine neue separate PDF-Datei schreiben."))
        self._radio_new_file.setAccessibleName(tr("In neue Datei speichern"))
        self._radio_new_file.setAccessibleDescription(tr("Erstellt eine neue Datei mit den hinzugefügten Annotationen."))
        self._output_group.addButton(self._radio_new_file)
        dest_row.addWidget(self._radio_new_file)
        self._radio_inplace.toggled.connect(self._on_output_mode_changed)

        self._output_path = QLineEdit()
        self._output_path.setPlaceholderText(tr("Ausgabe-PDF auswählen …"))
        self._output_path.setEnabled(False)
        self._output_path.setToolTip(tr("Zielpfad für die neue annotierte PDF-Datei."))
        self._output_path.setAccessibleName(tr("Ausgabe-PDF"))
        self._output_path.setAccessibleDescription(tr("Pfad der neuen Zieldatei."))
        dest_row.addWidget(self._output_path)

        self._btn_browse_output = QPushButton("…")
        self._btn_browse_output.setFixedWidth(32)
        self._btn_browse_output.setEnabled(False)
        self._btn_browse_output.setToolTip(tr("Ausgabepfad wählen"))
        self._btn_browse_output.setAccessibleName(tr("Ausgabepfad durchsuchen"))
        self._btn_browse_output.setAccessibleDescription(tr("Öffnet Dateidialog zum Festlegen des Ausgabepfads."))
        self._btn_browse_output.clicked.connect(self._browse_output_file)
        dest_row.addWidget(self._btn_browse_output)
        doc_layout.addLayout(dest_row)

        main_layout.addWidget(doc_group)

        # --- Gruppe 2: Vorhandene Annotationen ---
        existing_group = QGroupBox(tr("Vorhandene Annotationen"))
        existing_layout = QVBoxLayout(existing_group)

        filter_row = QHBoxLayout()
        self._check_current_page_only = QCheckBox(tr("Nur aktuelle Seite anzeigen"))
        self._check_current_page_only.setChecked(True)
        self._check_current_page_only.setToolTip(tr("Filtert die Tabelle auf die aktuell ausgewählte Seite."))
        self._check_current_page_only.setAccessibleName(tr("Nur aktuelle Seite filtern"))
        self._check_current_page_only.setAccessibleDescription(tr("Beschränkt die Anzeige der Annotationen auf die aktive Seite."))
        self._check_current_page_only.toggled.connect(self._refresh_annotations_table)
        filter_row.addWidget(self._check_current_page_only)

        self._lbl_annot_count = QLabel("0 Annotationen")
        self._lbl_annot_count.setStyleSheet("color: #666;")
        filter_row.addStretch()
        filter_row.addWidget(self._lbl_annot_count)
        existing_layout.addLayout(filter_row)

        self._table_annots = QTableWidget()
        self._table_annots.setColumnCount(5)
        self._table_annots.setHorizontalHeaderLabels([
            tr("Index"), tr("Typ"), tr("Seite"), tr("Inhalt / Text"), tr("Position")
        ])
        self._table_annots.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table_annots.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_annots.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_annots.setToolTip(tr("Liste der im Dokument vorhandenen Annotationen."))
        self._table_annots.setAccessibleName(tr("Annotationstabelle"))
        self._table_annots.setAccessibleDescription(tr("Zeigt alle ausgelesenen Annotationen mit Typ und Position an."))
        existing_layout.addWidget(self._table_annots)

        annot_btns_row = QHBoxLayout()
        self._btn_delete_selected = QPushButton(tr("Ausgewählte löschen"))
        self._btn_delete_selected.setToolTip(tr("Löscht die markierte Annotation aus dem Dokument."))
        self._btn_delete_selected.setAccessibleName(tr("Ausgewählte Annotation löschen"))
        self._btn_delete_selected.setAccessibleDescription(tr("Entfernt die in der Tabelle ausgewählte Annotation."))
        self._btn_delete_selected.clicked.connect(self._delete_selected_annotation)
        annot_btns_row.addWidget(self._btn_delete_selected)

        self._btn_delete_page = QPushButton(tr("Alle auf dieser Seite löschen"))
        self._btn_delete_page.setToolTip(tr("Löscht alle Annotationen auf der aktuell ausgewählten Seite."))
        self._btn_delete_page.setAccessibleName(tr("Alle Annotationen der Seite löschen"))
        self._btn_delete_page.setAccessibleDescription(tr("Entfernt alle Annotationen der aktiven Seite."))
        self._btn_delete_page.clicked.connect(self._delete_page_annotations)
        annot_btns_row.addWidget(self._btn_delete_page)

        self._btn_delete_all = QPushButton(tr("Alle im Dokument löschen"))
        self._btn_delete_all.setToolTip(tr("Löscht sämtliche Annotationen aus dem gesamten Dokument."))
        self._btn_delete_all.setAccessibleName(tr("Alle Annotationen im Dokument löschen"))
        self._btn_delete_all.setAccessibleDescription(tr("Entfernt alle Annotationen aus allen Seiten."))
        self._btn_delete_all.clicked.connect(self._delete_all_annotations)
        annot_btns_row.addWidget(self._btn_delete_all)
        existing_layout.addLayout(annot_btns_row)

        main_layout.addWidget(existing_group)

        # --- Gruppe 3: Neue Annotation hinzufügen ---
        add_group = QGroupBox(tr("Annotation hinzufügen"))
        add_layout = QVBoxLayout(add_group)

        self._tab_widget = QTabWidget()

        # Tab 1: Text-Marker
        tab_marker = QWidget()
        form_marker = QFormLayout(tab_marker)

        self._combo_marker_type = QComboBox()
        self._combo_marker_type.addItem(tr("Highlight (Gelb)"), "highlight")
        self._combo_marker_type.addItem(tr("Unterstreichen"), "underline")
        self._combo_marker_type.addItem(tr("Durchstreichen"), "strikeout")
        self._combo_marker_type.addItem(tr("Wellenlinie"), "squiggly")
        self._combo_marker_type.setToolTip(tr("Wählt die Art der Textmarkierung aus."))
        self._combo_marker_type.setAccessibleName(tr("Marker-Typ"))
        self._combo_marker_type.setAccessibleDescription(tr("Legt fest, ob Text hervorgehoben, unterstrichen oder durchgestrichen wird."))
        form_marker.addRow(tr("Marker-Typ:"), self._combo_marker_type)

        self._combo_marker_color = QComboBox()
        for cname in self.COLOR_PRESETS:
            self._combo_marker_color.addItem(tr(cname), cname)
        self._combo_marker_color.setToolTip(tr("Farbe des Markers."))
        self._combo_marker_color.setAccessibleName(tr("Marker-Farbe"))
        self._combo_marker_color.setAccessibleDescription(tr("Wählt die Farbe für die Markierung."))
        form_marker.addRow(tr("Farbe:"), self._combo_marker_color)

        self._marker_search_text = QLineEdit()
        self._marker_search_text.setPlaceholderText(tr("Suchtext im Dokument eingeben …"))
        self._marker_search_text.setToolTip(tr("Wenn Text eingegeben ist, werden alle Treffer auf der Seite markiert."))
        self._marker_search_text.setAccessibleName(tr("Suchtext für Markierung"))
        self._marker_search_text.setAccessibleDescription(tr("Sucht nach Begriffen auf der Seite zur automatischen Markierung."))
        form_marker.addRow(tr("Suchtext (auf Seite markieren):"), self._marker_search_text)

        marker_coord_row = QHBoxLayout()
        self._marker_x = QDoubleSpinBox()
        self._marker_x.setRange(0, 2000)
        self._marker_x.setValue(72.0)
        self._marker_y = QDoubleSpinBox()
        self._marker_y.setRange(0, 2000)
        self._marker_y.setValue(100.0)
        self._marker_w = QDoubleSpinBox()
        self._marker_w.setRange(1, 2000)
        self._marker_w.setValue(200.0)
        self._marker_h = QDoubleSpinBox()
        self._marker_h.setRange(1, 1000)
        self._marker_h.setValue(20.0)
        marker_coord_row.addWidget(QLabel("X:"))
        marker_coord_row.addWidget(self._marker_x)
        marker_coord_row.addWidget(QLabel("Y:"))
        marker_coord_row.addWidget(self._marker_y)
        marker_coord_row.addWidget(QLabel("B:"))
        marker_coord_row.addWidget(self._marker_w)
        marker_coord_row.addWidget(QLabel("H:"))
        marker_coord_row.addWidget(self._marker_h)
        form_marker.addRow(tr("Oder manuelle Koordinaten:"), marker_coord_row)

        self._marker_comment = QLineEdit()
        self._marker_comment.setPlaceholderText(tr("Optionaler Notiztext zum Marker"))
        self._marker_comment.setToolTip(tr("Optionaler Tooltip/Kommentar zur Markierung."))
        self._marker_comment.setAccessibleName(tr("Marker-Kommentar"))
        self._marker_comment.setAccessibleDescription(tr("Zusätzlicher Textinhalt für die Markierung."))
        form_marker.addRow(tr("Inhalt / Notiz:"), self._marker_comment)

        self._tab_widget.addTab(tab_marker, tr("Text-Marker"))

        # Tab 2: Notiz (Sticky Note)
        tab_note = QWidget()
        form_note = QFormLayout(tab_note)

        note_pos_row = QHBoxLayout()
        self._note_x = QDoubleSpinBox()
        self._note_x.setRange(0, 2000)
        self._note_x.setValue(72.0)
        self._note_y = QDoubleSpinBox()
        self._note_y.setRange(0, 2000)
        self._note_y.setValue(72.0)
        note_pos_row.addWidget(QLabel("X:"))
        note_pos_row.addWidget(self._note_x)
        note_pos_row.addWidget(QLabel("Y:"))
        note_pos_row.addWidget(self._note_y)
        form_note.addRow(tr("Position (X, Y):"), note_pos_row)

        self._note_author = QLineEdit("DokuZen")
        self._note_author.setToolTip(tr("Name des Autors für die Notiz."))
        self._note_author.setAccessibleName(tr("Notiz-Autor"))
        self._note_author.setAccessibleDescription(tr("Autorname der Sticky Note."))
        form_note.addRow(tr("Autor:"), self._note_author)

        self._note_text = QTextEdit()
        self._note_text.setMaximumHeight(70)
        self._note_text.setPlaceholderText(tr("Kommentartext eingeben …"))
        self._note_text.setToolTip(tr("Inhalt der Notiz."))
        self._note_text.setAccessibleName(tr("Notiztext"))
        self._note_text.setAccessibleDescription(tr("Textinhalt der Sticky Note."))
        form_note.addRow(tr("Notiztext:"), self._note_text)

        self._tab_widget.addTab(tab_note, tr("Notiz"))

        # Tab 3: Freitext
        tab_freetext = QWidget()
        form_freetext = QFormLayout(tab_freetext)

        ft_pos_row = QHBoxLayout()
        self._ft_x = QDoubleSpinBox()
        self._ft_x.setRange(0, 2000)
        self._ft_x.setValue(72.0)
        self._ft_y = QDoubleSpinBox()
        self._ft_y.setRange(0, 2000)
        self._ft_y.setValue(150.0)
        self._ft_w = QDoubleSpinBox()
        self._ft_w.setRange(20, 2000)
        self._ft_w.setValue(250.0)
        self._ft_h = QDoubleSpinBox()
        self._ft_h.setRange(10, 1000)
        self._ft_h.setValue(35.0)
        ft_pos_row.addWidget(QLabel("X:"))
        ft_pos_row.addWidget(self._ft_x)
        ft_pos_row.addWidget(QLabel("Y:"))
        ft_pos_row.addWidget(self._ft_y)
        ft_pos_row.addWidget(QLabel("B:"))
        ft_pos_row.addWidget(self._ft_w)
        ft_pos_row.addWidget(QLabel("H:"))
        ft_pos_row.addWidget(self._ft_h)
        form_freetext.addRow(tr("Position & Größe:"), ft_pos_row)

        self._ft_text = QLineEdit()
        self._ft_text.setPlaceholderText(tr("Freitext eingeben …"))
        self._ft_text.setToolTip(tr("Text der Freitextbox."))
        self._ft_text.setAccessibleName(tr("Freitext-Inhalt"))
        self._ft_text.setAccessibleDescription(tr("Inhalt der freischwebenden Textbox."))
        form_freetext.addRow(tr("Inhalt / Text:"), self._ft_text)

        ft_style_row = QHBoxLayout()
        self._ft_fontsize = QSpinBox()
        self._ft_fontsize.setRange(6, 72)
        self._ft_fontsize.setValue(12)
        ft_style_row.addWidget(QLabel(tr("Schriftgröße:")))
        ft_style_row.addWidget(self._ft_fontsize)

        self._ft_color = QComboBox()
        for cname in ["Schwarz", "Rot", "Blau", "Grün"]:
            self._ft_color.addItem(tr(cname), cname)
        ft_style_row.addWidget(QLabel(tr("Textfarbe:")))
        ft_style_row.addWidget(self._ft_color)

        self._ft_border = QCheckBox(tr("Rahmen anzeigen"))
        self._ft_border.setChecked(False)
        ft_style_row.addWidget(self._ft_border)
        form_freetext.addRow(tr("Darstellung:"), ft_style_row)

        self._tab_widget.addTab(tab_freetext, tr("Freitext"))

        # Tab 4: Stempel
        tab_stamp = QWidget()
        form_stamp = QFormLayout(tab_stamp)

        self._combo_stamp_type = QComboBox()
        for label, stype in self.STAMP_OPTIONS:
            self._combo_stamp_type.addItem(tr(label), stype)
        self._combo_stamp_type.setToolTip(tr("Vordefinierter Stempel."))
        self._combo_stamp_type.setAccessibleName(tr("Stempel-Typ"))
        self._combo_stamp_type.setAccessibleDescription(tr("Wählt den Standard-Stempeltext."))
        form_stamp.addRow(tr("Stempel-Typ:"), self._combo_stamp_type)

        self._combo_stamp_pos = QComboBox()
        for pos_name in self.STAMP_POSITIONS:
            self._combo_stamp_pos.addItem(tr(pos_name), pos_name)
        self._combo_stamp_pos.currentIndexChanged.connect(self._on_stamp_pos_preset_changed)
        self._combo_stamp_pos.setToolTip(tr("Automatische Platzierung auf der Seite."))
        self._combo_stamp_pos.setAccessibleName(tr("Stempel-Positionierung"))
        self._combo_stamp_pos.setAccessibleDescription(tr("Wählt die vordefinierte Position des Stempels."))
        form_stamp.addRow(tr("Position / Platzierung:"), self._combo_stamp_pos)

        stamp_coord_row = QHBoxLayout()
        self._stamp_x = QDoubleSpinBox()
        self._stamp_x.setRange(0, 2000)
        self._stamp_x.setValue(380.0)
        self._stamp_y = QDoubleSpinBox()
        self._stamp_y.setRange(0, 2000)
        self._stamp_y.setValue(40.0)
        self._stamp_w = QDoubleSpinBox()
        self._stamp_w.setRange(20, 1000)
        self._stamp_w.setValue(180.0)
        self._stamp_h = QDoubleSpinBox()
        self._stamp_h.setRange(10, 500)
        self._stamp_h.setValue(50.0)
        stamp_coord_row.addWidget(QLabel("X:"))
        stamp_coord_row.addWidget(self._stamp_x)
        stamp_coord_row.addWidget(QLabel("Y:"))
        stamp_coord_row.addWidget(self._stamp_y)
        stamp_coord_row.addWidget(QLabel("B:"))
        stamp_coord_row.addWidget(self._stamp_w)
        stamp_coord_row.addWidget(QLabel("H:"))
        stamp_coord_row.addWidget(self._stamp_h)
        form_stamp.addRow(tr("Koordinaten:"), stamp_coord_row)

        self._tab_widget.addTab(tab_stamp, tr("Stempel"))

        # Tab 5: Formen
        tab_shape = QWidget()
        form_shape = QFormLayout(tab_shape)

        self._combo_shape_type = QComboBox()
        self._combo_shape_type.addItem(tr("Rechteck"), "rect")
        self._combo_shape_type.addItem(tr("Kreis"), "circle")
        self._combo_shape_type.addItem(tr("Linie"), "line")
        self._combo_shape_type.setToolTip(tr("Art der geometrischen Form."))
        self._combo_shape_type.setAccessibleName(tr("Form-Typ"))
        self._combo_shape_type.setAccessibleDescription(tr("Wählt zwischen Rechteck, Kreis oder Linie."))
        form_shape.addRow(tr("Form:"), self._combo_shape_type)

        shape_coord_row = QHBoxLayout()
        self._shape_x = QDoubleSpinBox()
        self._shape_x.setRange(0, 2000)
        self._shape_x.setValue(72.0)
        self._shape_y = QDoubleSpinBox()
        self._shape_y.setRange(0, 2000)
        self._shape_y.setValue(200.0)
        self._shape_w = QDoubleSpinBox()
        self._shape_w.setRange(1, 2000)
        self._shape_w.setValue(150.0)
        self._shape_h = QDoubleSpinBox()
        self._shape_h.setRange(1, 1000)
        self._shape_h.setValue(80.0)
        shape_coord_row.addWidget(QLabel("X:"))
        shape_coord_row.addWidget(self._shape_x)
        shape_coord_row.addWidget(QLabel("Y:"))
        shape_coord_row.addWidget(self._shape_y)
        shape_coord_row.addWidget(QLabel("B:"))
        shape_coord_row.addWidget(self._shape_w)
        shape_coord_row.addWidget(QLabel("H:"))
        shape_coord_row.addWidget(self._shape_h)
        form_shape.addRow(tr("Koordinaten:"), shape_coord_row)

        shape_style_row = QHBoxLayout()
        self._shape_width = QDoubleSpinBox()
        self._shape_width.setRange(0.5, 20.0)
        self._shape_width.setValue(1.5)
        shape_style_row.addWidget(QLabel(tr("Linienbreite:")))
        shape_style_row.addWidget(self._shape_width)

        self._shape_color = QComboBox()
        for cname in self.COLOR_PRESETS:
            self._shape_color.addItem(tr(cname), cname)
        shape_style_row.addWidget(QLabel(tr("Linienfarbe:")))
        shape_style_row.addWidget(self._shape_color)

        self._shape_fill = QComboBox()
        self._shape_fill.addItem(tr("Keine (Transparent)"), "none")
        for cname in ["Hellgelb", "Hellblau", "Hellrot", "Hellgrün"]:
            self._shape_fill.addItem(tr(cname), cname)
        shape_style_row.addWidget(QLabel(tr("Füllfarbe:")))
        shape_style_row.addWidget(self._shape_fill)
        form_shape.addRow(tr("Stil:"), shape_style_row)

        self._tab_widget.addTab(tab_shape, tr("Formen"))

        add_layout.addWidget(self._tab_widget)

        self._btn_add_annot = QPushButton(tr("Annotation hinzufügen"))
        self._btn_add_annot.setStyleSheet("font-weight: bold; padding: 6px;")
        self._btn_add_annot.setToolTip(tr("Wendet die oben konfigurierte Annotation auf das Dokument an."))
        self._btn_add_annot.setAccessibleName(tr("Annotation hinzufügen"))
        self._btn_add_annot.setAccessibleDescription(tr("Fügt die konfigurierte Annotation zur gewählten Seite hinzu."))
        self._btn_add_annot.clicked.connect(self._add_current_annotation)
        add_layout.addWidget(self._btn_add_annot)

        main_layout.addWidget(add_group)

        # --- Gruppe 4: Status & Buttons ---
        bottom_row = QHBoxLayout()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #2b542c; font-weight: bold;")
        bottom_row.addWidget(self._status_label)
        bottom_row.addStretch()

        self._btn_close = QPushButton(tr("Schließen"))
        self._btn_close.setToolTip(tr("Schließt den Dialog."))
        self._btn_close.setAccessibleName(tr("Schließen"))
        self._btn_close.setAccessibleDescription(tr("Schließt das Dialogfenster."))
        self._btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(self._btn_close)
        main_layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Dokument-Laden & Aktualisierung
    # ------------------------------------------------------------------

    def _browse_input_file(self):
        """Öffnet Dateidialog für Eingabe-PDF."""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Eingabe-PDF auswählen"), "", tr("PDF-Dateien (*.pdf)")
        )
        if path:
            self._input_path.setText(path)
            self._load_document()

    def _browse_output_file(self):
        """Öffnet Dateidialog für Ausgabe-PDF."""
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Ausgabe-PDF festlegen"), "", tr("PDF-Dateien (*.pdf)")
        )
        if path:
            self._output_path.setText(path)

    def _on_input_path_changed(self):
        """Wird ausgelöst, wenn der Nutzer den Pfad ändert."""
        path = self._input_path.text().strip()
        if Path(path).is_file():
            self._load_document()
        else:
            self._current_doc_pages = 0
            self._lbl_page_info.setText("—")
            self._page_spin.setRange(1, 1)
            self._loaded_annotations.clear()
            self._refresh_annotations_table()
            self._update_controls_state()

    def _on_output_mode_changed(self):
        """Aktiviert/Deaktiviert Eingabefelder für neues Ausgabedokument."""
        is_new_file = self._radio_new_file.isChecked()
        self._output_path.setEnabled(is_new_file)
        self._btn_browse_output.setEnabled(is_new_file)

    def _load_document(self):
        """Liest Metadaten und vorhandene Annotationen aus."""
        path = self._input_path.text().strip()
        if not path or not Path(path).is_file() or not PYMUPDF_AVAILABLE:
            self._update_controls_state()
            return

        try:
            doc = fitz.open(path)
            self._current_doc_pages = len(doc)
            if self._current_doc_pages > 0:
                first_page = doc[0]
                self._page_width = float(first_page.rect.width)
                self._page_height = float(first_page.rect.height)
                self._page_spin.setRange(1, self._current_doc_pages)
                self._update_page_info()
            doc.close()
        except Exception as e:
            self.logger.error(f"Fehler beim Öffnen von {path}: {e}")
            self._current_doc_pages = 0

        self._load_annotations()
        self._update_controls_state()

    def _on_page_changed(self):
        """Aktualisiert Seiteninformationen und Tabelle."""
        self._update_page_info()
        self._refresh_annotations_table()

    def _update_page_info(self):
        """Aktualisiert das Seiten-Info-Label."""
        if self._current_doc_pages > 0:
            cur = self._page_spin.value()
            path = self._input_path.text().strip()
            if PYMUPDF_AVAILABLE and Path(path).is_file():
                try:
                    doc = fitz.open(path)
                    p = doc[cur - 1]
                    self._page_width = float(p.rect.width)
                    self._page_height = float(p.rect.height)
                    doc.close()
                except Exception:
                    pass
            self._lbl_page_info.setText(
                f"{tr('Seite')} {cur} {tr('von')} {self._current_doc_pages} "
                f"({int(self._page_width)} × {int(self._page_height)} pt)"
            )
        else:
            self._lbl_page_info.setText("—")

    def _update_controls_state(self):
        """Aktiviert oder deaktiviert Aktionsbuttons."""
        has_doc = self._current_doc_pages > 0 and PYMUPDF_AVAILABLE
        self._btn_add_annot.setEnabled(has_doc)
        self._btn_delete_selected.setEnabled(has_doc)
        self._btn_delete_page.setEnabled(has_doc)
        self._btn_delete_all.setEnabled(has_doc)

    def _get_target_file(self) -> Optional[str]:
        """Ermittelt den effektiven Zieldateipfad."""
        src = self._input_path.text().strip()
        if not src or not Path(src).is_file():
            return None

        if self._radio_inplace.isChecked():
            return src

        dst = self._output_path.text().strip()
        if not dst:
            QMessageBox.warning(self, tr("Fehlender Pfad"), tr("Bitte Ausgabepfad angeben."))
            return None
        if not Path(dst).exists():
            shutil.copy2(src, dst)
        return dst

    # ------------------------------------------------------------------
    # Vorhandene Annotationen anzeigen & löschen
    # ------------------------------------------------------------------

    def _load_annotations(self):
        """Liest alle Annotationen aus dem Quelldokument aus."""
        src = self._input_path.text().strip()
        if not src or not Path(src).is_file() or not PYMUPDF_AVAILABLE:
            self._loaded_annotations = []
        else:
            self._loaded_annotations = self._annotator.get_annotations(src)

        self._refresh_annotations_table()

    def _refresh_annotations_table(self):
        """Aktualisiert die Tabellenansicht der vorhandenen Annotationen."""
        self._table_annots.setRowCount(0)
        current_page_idx = self._page_spin.value() - 1
        only_current = self._check_current_page_only.isChecked()

        filtered = [
            (idx, ann) for idx, ann in enumerate(self._loaded_annotations)
            if not only_current or ann.page_index == current_page_idx
        ]

        self._lbl_annot_count.setText(f"{len(filtered)} {tr('Annotationen')}")
        self._table_annots.setRowCount(len(filtered))

        for row, (idx, ann) in enumerate(filtered):
            # Index
            item_idx = QTableWidgetItem(str(idx + 1))
            item_idx.setData(Qt.ItemDataRole.UserRole, (ann.page_index, idx))
            self._table_annots.setItem(row, 0, item_idx)

            # Typ
            type_str = ann.type.value if hasattr(ann.type, "value") else str(ann.type)
            self._table_annots.setItem(row, 1, QTableWidgetItem(type_str.upper()))

            # Seite
            self._table_annots.setItem(row, 2, QTableWidgetItem(f"{ann.page_index + 1}"))

            # Inhalt / Autor
            content_display = ann.content or ann.author or "—"
            self._table_annots.setItem(row, 3, QTableWidgetItem(content_display))

            # Position
            rect_display = f"({int(ann.rect[0])}, {int(ann.rect[1])}, {int(ann.rect[2])}, {int(ann.rect[3])})"
            self._table_annots.setItem(row, 4, QTableWidgetItem(rect_display))

    def _delete_selected_annotation(self):
        """Löscht die aktuell markierte Annotation."""
        selected_rows = self._table_annots.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, tr("Hinweis"), tr("Keine Annotation ausgewählt."))
            return

        row = selected_rows[0].row()
        item = self._table_annots.item(row, 0)
        if not item:
            return

        page_idx, _ = item.data(Qt.ItemDataRole.UserRole)
        target = self._get_target_file()
        if not target:
            return

        # Ermittle den relativen Index auf der Seite
        page_annots = [a for a in self._loaded_annotations if a.page_index == page_idx]
        annot_obj = self._loaded_annotations[int(item.text()) - 1]
        try:
            annot_idx_on_page = page_annots.index(annot_obj)
        except ValueError:
            annot_idx_on_page = 0

        success = self._annotator.remove_annotation(target, target, page_idx, annot_idx_on_page)
        if success:
            self._status_label.setText(tr("Annotation(en) erfolgreich gelöscht"))
            self._load_annotations()
            self.annotations_changed.emit(target)
        else:
            QMessageBox.critical(self, tr("Fehler"), tr("Annotation konnte nicht gelöscht werden."))

    def _delete_page_annotations(self):
        """Löscht alle Annotationen auf der aktuellen Seite."""
        target = self._get_target_file()
        if not target:
            return

        cur_page = self._page_spin.value()
        res = QMessageBox.question(
            self,
            tr("Bestätigen"),
            f"{tr('Wollen Sie wirklich alle Annotationen auf dieser Seite löschen?')} ({tr('Seite')} {cur_page})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self._annotator.remove_all_annotations(target, target, page_index=cur_page - 1)
            self._status_label.setText(tr("Annotation(en) erfolgreich gelöscht"))
            self._load_annotations()
            self.annotations_changed.emit(target)

    def _delete_all_annotations(self):
        """Löscht sämtliche Annotationen im gesamten Dokument."""
        target = self._get_target_file()
        if not target:
            return

        res = QMessageBox.question(
            self,
            tr("Bestätigen"),
            tr("Wollen Sie wirklich alle Annotationen im gesamten Dokument löschen?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self._annotator.remove_all_annotations(target, target, page_index=None)
            self._status_label.setText(tr("Annotation(en) erfolgreich gelöscht"))
            self._load_annotations()
            self.annotations_changed.emit(target)

    # ------------------------------------------------------------------
    # Neue Annotation hinzufügen
    # ------------------------------------------------------------------

    def _on_stamp_pos_preset_changed(self):
        """Setzt Standardkoordinaten für Stempel nach gewähltem Preset."""
        preset = self._combo_stamp_pos.currentData()
        w = self._stamp_w.value()
        h = self._stamp_h.value()
        pw = self._page_width
        ph = self._page_height

        if preset == "Oben rechts":
            self._stamp_x.setValue(max(0.0, pw - w - 40.0))
            self._stamp_y.setValue(40.0)
        elif preset == "Oben links":
            self._stamp_x.setValue(40.0)
            self._stamp_y.setValue(40.0)
        elif preset == "Mitte":
            self._stamp_x.setValue(max(0.0, (pw - w) / 2.0))
            self._stamp_y.setValue(max(0.0, (ph - h) / 2.0))
        elif preset == "Unten rechts":
            self._stamp_x.setValue(max(0.0, pw - w - 40.0))
            self._stamp_y.setValue(max(0.0, ph - h - 40.0))
        elif preset == "Unten links":
            self._stamp_x.setValue(40.0)
            self._stamp_y.setValue(max(0.0, ph - h - 40.0))

    def _add_current_annotation(self):
        """Fügt die im aktuellen Tab konfigurierte Annotation hinzu."""
        target = self._get_target_file()
        if not target:
            return

        page_idx = self._page_spin.value() - 1
        current_tab = self._tab_widget.currentIndex()
        success = False

        if current_tab == 0:
            # Text-Marker
            mtype = self._combo_marker_type.currentData()
            color = self.COLOR_PRESETS.get(self._combo_marker_color.currentData(), AnnotationColor.yellow())
            search_text = self._marker_search_text.text().strip()
            comment = self._marker_comment.text().strip()

            rects: List[Tuple[float, float, float, float]] = []
            if search_text and PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(target)
                    page = doc[page_idx]
                    found = page.search_for(search_text)
                    doc.close()
                    rects = [tuple(r) for r in found]
                except Exception as e:
                    self.logger.error(f"Suchfehler: {e}")

            if not rects:
                x = self._marker_x.value()
                y = self._marker_y.value()
                w = self._marker_w.value()
                h = self._marker_h.value()
                rects = [(x, y, x + w, y + h)]

            for r in rects:
                if mtype == "highlight":
                    success = self._annotator.add_highlight(target, target, page_idx, r, color, comment)
                elif mtype == "underline":
                    success = self._annotator.add_underline(target, target, page_idx, r, color)
                elif mtype == "strikeout":
                    success = self._annotator.add_strikeout(target, target, page_idx, r, color)
                elif mtype == "squiggly":
                    success = self._annotator.add_squiggly(target, target, page_idx, r, color)

        elif current_tab == 1:
            # Notiz
            pos = (self._note_x.value(), self._note_y.value())
            author = self._note_author.text().strip()
            text = self._note_text.toPlainText().strip()
            if not text:
                text = tr("Notiz")
            success = self._annotator.add_text_note(target, target, page_idx, pos, text, author=author)

        elif current_tab == 2:
            # Freitext
            x = self._ft_x.value()
            y = self._ft_y.value()
            w = self._ft_w.value()
            h = self._ft_h.value()
            rect = (x, y, x + w, y + h)
            text = self._ft_text.text().strip() or "Freitext"
            fontsize = self._ft_fontsize.value()
            col_name = self._ft_color.currentData()
            text_color = self.COLOR_PRESETS.get(col_name, AnnotationColor(0.0, 0.0, 0.0))
            bg_color = AnnotationColor(1.0, 1.0, 0.8) if self._ft_border.isChecked() else None
            success = self._annotator.add_freetext(
                target, target, page_idx, rect, text, fontsize=fontsize,
                color=text_color, bg_color=bg_color
            )

        elif current_tab == 3:
            # Stempel
            stype = self._combo_stamp_type.currentData()
            x = self._stamp_x.value()
            y = self._stamp_y.value()
            w = self._stamp_w.value()
            h = self._stamp_h.value()
            rect = (x, y, x + w, y + h)
            success = self._annotator.add_stamp(target, target, page_idx, rect, stamp_type=stype)

        elif current_tab == 4:
            # Formen
            shape = self._combo_shape_type.currentData()
            x = self._shape_x.value()
            y = self._shape_y.value()
            w = self._shape_w.value()
            h = self._shape_h.value()
            rect = (x, y, x + w, y + h)
            width = self._shape_width.value()
            stroke_color = self.COLOR_PRESETS.get(self._shape_color.currentData(), AnnotationColor.red())

            fill_val = self._shape_fill.currentData()
            fill_color = None
            if fill_val == "Hellgelb":
                fill_color = AnnotationColor(1.0, 1.0, 0.7)
            elif fill_val == "Hellblau":
                fill_color = AnnotationColor(0.8, 0.9, 1.0)
            elif fill_val == "Hellrot":
                fill_color = AnnotationColor(1.0, 0.8, 0.8)
            elif fill_val == "Hellgrün":
                fill_color = AnnotationColor(0.8, 1.0, 0.8)

            if shape == "rect":
                success = self._annotator.add_rect(target, target, page_idx, rect, stroke_color, fill_color, width)
            elif shape == "circle":
                success = self._annotator.add_circle(target, target, page_idx, rect, stroke_color, fill_color, width)
            elif shape == "line":
                start = (x, y)
                end = (x + w, y + h)
                success = self._annotator.add_line(target, target, page_idx, start, end, stroke_color, width)

        if success:
            self._status_label.setText(tr("Annotation erfolgreich hinzugefügt"))
            self._load_annotations()
            self.annotations_changed.emit(target)
        else:
            QMessageBox.critical(self, tr("Fehler"), tr("Annotation konnte nicht hinzugefügt werden."))
