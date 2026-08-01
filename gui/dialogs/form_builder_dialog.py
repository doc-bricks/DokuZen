#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Form Builder Dialog
======================================
Visueller Editor für PDF-Formulare.
"""

from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QSplitter, QWidget,
    QComboBox, QLineEdit, QSpinBox, QCheckBox,
    QFormLayout, QTabWidget, QScrollArea, QFrame,
    QToolBar, QGraphicsView, QGraphicsScene, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QAction, QPainter

from utils.logger import LoggerMixin
from core.forms.builder import (
    FormBuilder, FormTemplate, FormField, FieldType,
    create_contact_form, create_registration_form
)


class FieldItem(QGraphicsRectItem):
    """Grafisches Element für ein Formularfeld."""
    
    def __init__(self, field: FormField, scale: float = 2.0):
        # Skalierung: mm zu Pixel
        x = field.x * scale
        y = field.y * scale
        w = field.width * scale
        h = field.height * scale
        
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        
        self.field = field
        self.scale_factor = scale
        
        # Styling nach Feldtyp
        colors = {
            FieldType.TEXT: QColor(200, 220, 255),
            FieldType.TEXTAREA: QColor(200, 220, 255),
            FieldType.CHECKBOX: QColor(220, 255, 220),
            FieldType.RADIO: QColor(220, 255, 220),
            FieldType.DROPDOWN: QColor(255, 255, 200),
            FieldType.DATE: QColor(255, 220, 200),
            FieldType.SIGNATURE: QColor(255, 200, 255),
            FieldType.LABEL: QColor(240, 240, 240),
        }
        
        color = colors.get(field.field_type, QColor(200, 200, 200))
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Interaktiv
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
    
    def update_from_field(self):
        """Aktualisiert Position/Größe aus Feld."""
        self.setPos(self.field.x * self.scale_factor, 
                    self.field.y * self.scale_factor)
        self.setRect(0, 0, 
                     self.field.width * self.scale_factor,
                     self.field.height * self.scale_factor)
    
    def sync_to_field(self):
        """Synchronisiert Position zu Feld."""
        self.field.x = self.pos().x() / self.scale_factor
        self.field.y = self.pos().y() / self.scale_factor


class FormCanvas(QGraphicsView):
    """Canvas für die Formular-Vorschau."""
    
    field_selected = Signal(object)  # FormField oder None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        
        self._template: Optional[FormTemplate] = None
        self._field_items: List[FieldItem] = []
        self._scale = 2.0  # mm zu Pixel
        
        # Styling
        self.setBackgroundBrush(QBrush(QColor(128, 128, 128)))
        # BUGSWEEP-34: scoped Enum + QPainter-Import. `self.renderHints().Antialiasing` greift einen
        # Enum-Wert über die Flags-Instanz ab -> in PySide6 6.4+ falsch/AttributeError (Canvas-Konstruktion
        # bzw. Dialog oeffnet ggf. nicht). Korrekt: QPainter.RenderHint.Antialiasing.
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    def set_template(self, template: FormTemplate):
        """Setzt das Template."""
        self._template = template
        self._rebuild()
    
    def _rebuild(self):
        """Baut die Szene neu auf."""
        self._scene.clear()
        self._field_items.clear()
        
        if not self._template:
            return
        
        # Seitenhintergrund
        w = self._template.page_size[0] * self._scale
        h = self._template.page_size[1] * self._scale
        
        page = self._scene.addRect(0, 0, w, h, 
                                   QPen(Qt.GlobalColor.black),
                                   QBrush(Qt.GlobalColor.white))
        
        # Felder hinzufügen
        for field in self._template.fields:
            item = FieldItem(field, self._scale)
            self._scene.addItem(item)
            self._field_items.append(item)
        
        self._scene.setSceneRect(-10, -10, w + 20, h + 20)
    
    def add_field(self, field: FormField):
        """Fügt ein Feld hinzu."""
        item = FieldItem(field, self._scale)
        self._scene.addItem(item)
        self._field_items.append(item)
    
    def remove_selected(self):
        """Entfernt ausgewählte Felder."""
        for item in self._scene.selectedItems():
            if isinstance(item, FieldItem):
                if self._template:
                    self._template.remove_field(item.field.name)
                self._scene.removeItem(item)
                self._field_items.remove(item)
    
    def get_selected_field(self) -> Optional[FormField]:
        """Gibt das ausgewählte Feld zurück."""
        for item in self._scene.selectedItems():
            if isinstance(item, FieldItem):
                return item.field
        return None
    
    def sync_all_positions(self):
        """Synchronisiert alle Positionen."""
        for item in self._field_items:
            item.sync_to_field()
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        field = self.get_selected_field()
        self.field_selected.emit(field)


class FormBuilderDialog(QDialog, LoggerMixin):
    """
    Visueller Formular-Editor.
    
    Features:
    - Felder hinzufügen/bearbeiten
    - Drag & Drop Positionierung
    - Vorlagen speichern/laden
    - PDF exportieren
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._builder = FormBuilder()
        self._template: Optional[FormTemplate] = None
        self._field_counter = 0
        
        self._setup_ui()
        self._new_template()
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Formular-Builder")
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)
        
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QToolBar()
        
        action_new = QAction("Neu", self)
        action_new.triggered.connect(self._new_template)
        toolbar.addAction(action_new)
        
        action_open = QAction("Öffnen...", self)
        action_open.triggered.connect(self._open_template)
        toolbar.addAction(action_open)
        
        action_save = QAction("Speichern...", self)
        action_save.triggered.connect(self._save_template)
        toolbar.addAction(action_save)
        
        toolbar.addSeparator()
        
        action_export = QAction("PDF exportieren...", self)
        action_export.triggered.connect(self._export_pdf)
        toolbar.addAction(action_export)
        
        toolbar.addSeparator()
        
        # Template-Vorlagen
        toolbar.addWidget(QLabel(" Vorlage: "))
        self._template_combo = QComboBox()
        self._template_combo.addItems(["Leer", "Kontaktformular", "Anmeldeformular"])
        self._template_combo.currentTextChanged.connect(self._on_template_selected)
        toolbar.addWidget(self._template_combo)
        
        layout.addWidget(toolbar)
        
        # Hauptbereich
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Links: Feld-Toolbox
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Feld hinzufügen
        add_group = QGroupBox("Feld hinzufügen")
        add_layout = QVBoxLayout(add_group)
        
        for field_type in FieldType:
            btn = QPushButton(field_type.value.capitalize())
            btn.clicked.connect(lambda checked, ft=field_type: self._add_field(ft))
            add_layout.addWidget(btn)
        
        left_layout.addWidget(add_group)
        
        # Aktionen
        action_group = QGroupBox("Aktionen")
        action_layout = QVBoxLayout(action_group)
        
        btn_delete = QPushButton("Ausgewähltes löschen")
        btn_delete.clicked.connect(self._delete_selected)
        action_layout.addWidget(btn_delete)
        
        btn_duplicate = QPushButton("Duplizieren")
        btn_duplicate.clicked.connect(self._duplicate_selected)
        action_layout.addWidget(btn_duplicate)
        
        left_layout.addWidget(action_group)
        left_layout.addStretch()
        
        splitter.addWidget(left_widget)
        
        # Mitte: Canvas
        self._canvas = FormCanvas()
        self._canvas.field_selected.connect(self._on_field_selected)
        splitter.addWidget(self._canvas)
        
        # Rechts: Eigenschaften
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Template-Eigenschaften
        template_group = QGroupBox("Formular")
        template_layout = QFormLayout(template_group)
        
        self._template_name = QLineEdit()
        self._template_name.textChanged.connect(self._on_template_name_changed)
        template_layout.addRow("Name:", self._template_name)
        
        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["A4", "A5", "Letter", "Legal"])
        self._page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        template_layout.addRow("Seitengröße:", self._page_size_combo)
        
        right_layout.addWidget(template_group)
        
        # Feld-Eigenschaften
        self._field_group = QGroupBox("Feld-Eigenschaften")
        self._field_group.setEnabled(False)
        field_layout = QFormLayout(self._field_group)
        
        self._field_name = QLineEdit()
        self._field_name.textChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Name:", self._field_name)
        
        self._field_label = QLineEdit()
        self._field_label.textChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Label:", self._field_label)
        
        self._field_x = QSpinBox()
        self._field_x.setRange(0, 500)
        self._field_x.valueChanged.connect(self._on_field_property_changed)
        field_layout.addRow("X (mm):", self._field_x)
        
        self._field_y = QSpinBox()
        self._field_y.setRange(0, 500)
        self._field_y.valueChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Y (mm):", self._field_y)
        
        self._field_width = QSpinBox()
        self._field_width.setRange(5, 200)
        self._field_width.valueChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Breite:", self._field_width)
        
        self._field_height = QSpinBox()
        self._field_height.setRange(5, 100)
        self._field_height.valueChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Höhe:", self._field_height)
        
        self._field_required = QCheckBox()
        self._field_required.stateChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Pflichtfeld:", self._field_required)
        
        self._field_default = QLineEdit()
        self._field_default.textChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Standardwert:", self._field_default)
        
        self._field_options = QLineEdit()
        self._field_options.setPlaceholderText("Option1, Option2, ...")
        self._field_options.textChanged.connect(self._on_field_property_changed)
        field_layout.addRow("Optionen:", self._field_options)
        
        right_layout.addWidget(self._field_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
        # Splitter-Größen
        splitter.setSizes([150, 650, 300])
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _new_template(self):
        """Erstellt ein neues Template."""
        self._template = self._builder.create_template("Neues Formular")
        self._template_name.setText(self._template.name)
        self._canvas.set_template(self._template)
        self._field_counter = 0
    
    def _on_template_selected(self, name: str):
        """Lädt ein Vorlagen-Template."""
        if name == "Kontaktformular":
            self._template = create_contact_form()
        elif name == "Anmeldeformular":
            self._template = create_registration_form()
        else:
            self._template = self._builder.create_template("Neues Formular")
        
        self._template_name.setText(self._template.name)
        self._canvas.set_template(self._template)
    
    def _open_template(self):
        """Öffnet ein gespeichertes Template."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Vorlage öffnen", "",
            "Formular-Vorlagen (*.json)"
        )
        if path:
            try:
                self._template = FormTemplate.load(path)
                self._template_name.setText(self._template.name)
                self._canvas.set_template(self._template)
            except Exception as e:
                QMessageBox.critical(self, "Fehler", str(e))
    
    def _save_template(self):
        """Speichert das Template."""
        if not self._template:
            return
        
        self._canvas.sync_all_positions()
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Vorlage speichern", f"{self._template.name}.json",
            "Formular-Vorlagen (*.json)"
        )
        if path:
            try:
                self._template.save(path)
                QMessageBox.information(self, "Gespeichert", f"Vorlage gespeichert:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", str(e))
    
    def _export_pdf(self):
        """Exportiert als PDF."""
        if not self._template:
            return
        
        self._canvas.sync_all_positions()
        
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF exportieren", f"{self._template.name}.pdf",
            "PDF-Dateien (*.pdf)"
        )
        if path:
            if self._builder.generate_pdf(self._template, path):
                QMessageBox.information(self, "Exportiert", f"PDF erstellt:\n{path}")
            else:
                QMessageBox.critical(self, "Fehler", "PDF-Export fehlgeschlagen")
    
    def _add_field(self, field_type: FieldType):
        """Fügt ein neues Feld hinzu."""
        if not self._template:
            return
        
        self._field_counter += 1
        name = f"{field_type.value}_{self._field_counter}"
        
        field = FormField(
            field_type=field_type,
            name=name,
            x=20,
            y=20 + (self._field_counter - 1) * 15,
            width=80 if field_type != FieldType.CHECKBOX else 100,
            height=8 if field_type != FieldType.TEXTAREA else 30,
            label=f"Feld {self._field_counter}"
        )
        
        self._template.add_field(field)
        self._canvas.add_field(field)
    
    def _delete_selected(self):
        """Löscht ausgewähltes Feld."""
        self._canvas.remove_selected()
        self._field_group.setEnabled(False)
    
    def _duplicate_selected(self):
        """Dupliziert ausgewähltes Feld."""
        field = self._canvas.get_selected_field()
        if field and self._template:
            self._field_counter += 1
            
            new_field = FormField(
                field_type=field.field_type,
                name=f"{field.field_type.value}_{self._field_counter}",
                x=field.x + 10,
                y=field.y + 10,
                width=field.width,
                height=field.height,
                label=field.label,
                default_value=field.default_value,
                required=field.required,
                options=list(field.options)
            )
            
            self._template.add_field(new_field)
            self._canvas.add_field(new_field)
    
    def _on_field_selected(self, field: Optional[FormField]):
        """Zeigt Eigenschaften des ausgewählten Felds."""
        self._field_group.setEnabled(field is not None)
        
        if field:
            self._current_field = field
            
            # Blockiere Signals während Update
            for widget in [self._field_name, self._field_label, self._field_x,
                           self._field_y, self._field_width, self._field_height,
                           self._field_required, self._field_default, self._field_options]:
                widget.blockSignals(True)
            
            self._field_name.setText(field.name)
            self._field_label.setText(field.label)
            self._field_x.setValue(int(field.x))
            self._field_y.setValue(int(field.y))
            self._field_width.setValue(int(field.width))
            self._field_height.setValue(int(field.height))
            self._field_required.setChecked(field.required)
            self._field_default.setText(field.default_value)
            self._field_options.setText(", ".join(field.options))
            
            # Options nur für Dropdown/Radio aktivieren
            self._field_options.setEnabled(
                field.field_type in [FieldType.DROPDOWN, FieldType.RADIO]
            )
            
            for widget in [self._field_name, self._field_label, self._field_x,
                           self._field_y, self._field_width, self._field_height,
                           self._field_required, self._field_default, self._field_options]:
                widget.blockSignals(False)
        else:
            self._current_field = None
    
    def _on_field_property_changed(self):
        """Aktualisiert Feld-Eigenschaften."""
        if not hasattr(self, '_current_field') or not self._current_field:
            return
        
        field = self._current_field
        field.name = self._field_name.text()
        field.label = self._field_label.text()
        field.x = self._field_x.value()
        field.y = self._field_y.value()
        field.width = self._field_width.value()
        field.height = self._field_height.value()
        field.required = self._field_required.isChecked()
        field.default_value = self._field_default.text()
        
        options_text = self._field_options.text()
        if options_text:
            field.options = [o.strip() for o in options_text.split(',')]
        
        # Canvas aktualisieren
        for item in self._canvas._field_items:
            if item.field == field:
                item.update_from_field()
                break
    
    def _on_template_name_changed(self, name: str):
        """Aktualisiert Template-Namen."""
        if self._template:
            self._template.name = name
    
    def _on_page_size_changed(self, size_name: str):
        """Ändert die Seitengröße."""
        if self._template:
            size = FormBuilder.PAGE_SIZES.get(size_name, (210, 297))
            self._template.page_size = size
            self._canvas.set_template(self._template)
