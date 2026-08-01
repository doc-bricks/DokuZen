#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Form Builder Core
====================================
Erstellt und bearbeitet PDF-Formulare.
"""

# BUGSWEEP-30: reportlab ist optional (try/except unten). Ohne diese __future__-Direktive wird die
# Annotation `c: canvas.Canvas` (FormBuilder._draw_field) bereits bei Klassendefinition ausgewertet
# -> NameError, wenn reportlab fehlt -> das ganze Modul (inkl. FormTemplate) ist unimportierbar.
# PEP 563 macht alle Annotationen zu Strings (lazy) -> Modul laedt auch ohne reportlab.
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import black, white, gray
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class FieldType(Enum):
    """Feldtypen für Formulare."""
    TEXT = "text"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    DATE = "date"
    SIGNATURE = "signature"
    LABEL = "label"


@dataclass
class FormField:
    """Repräsentiert ein Formularfeld."""
    field_type: FieldType
    name: str
    x: float  # Position in mm
    y: float
    width: float
    height: float
    label: str = ""
    default_value: str = ""
    required: bool = False
    options: List[str] = field(default_factory=list)  # Für Dropdown/Radio
    font_size: int = 10
    max_length: int = 0
    read_only: bool = False
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dictionary."""
        return {
            "field_type": self.field_type.value,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label,
            "default_value": self.default_value,
            "required": self.required,
            "options": self.options,
            "font_size": self.font_size,
            "max_length": self.max_length,
            "read_only": self.read_only
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FormField':
        """Erstellt aus Dictionary."""
        return cls(
            field_type=FieldType(data["field_type"]),
            name=data["name"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            label=data.get("label", ""),
            default_value=data.get("default_value", ""),
            required=data.get("required", False),
            options=data.get("options", []),
            font_size=data.get("font_size", 10),
            max_length=data.get("max_length", 0),
            read_only=data.get("read_only", False)
        )


@dataclass
class FormTemplate:
    """Formular-Vorlage."""
    name: str
    page_size: Tuple[float, float] = (210, 297)  # A4 in mm
    fields: List[FormField] = field(default_factory=list)
    background_pdf: Optional[str] = None
    title: str = ""
    author: str = ""
    
    def add_field(self, field: FormField):
        """Fügt ein Feld hinzu."""
        self.fields.append(field)
    
    def remove_field(self, name: str):
        """Entfernt ein Feld."""
        self.fields = [f for f in self.fields if f.name != name]
    
    def get_field(self, name: str) -> Optional[FormField]:
        """Findet ein Feld nach Name."""
        for f in self.fields:
            if f.name == name:
                return f
        return None
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dictionary."""
        return {
            "name": self.name,
            "page_size": list(self.page_size),
            "fields": [f.to_dict() for f in self.fields],
            "background_pdf": self.background_pdf,
            "title": self.title,
            "author": self.author
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FormTemplate':
        """Erstellt aus Dictionary."""
        template = cls(
            name=data["name"],
            page_size=tuple(data.get("page_size", [210, 297])),
            background_pdf=data.get("background_pdf"),
            title=data.get("title", ""),
            author=data.get("author", "")
        )
        for fd in data.get("fields", []):
            template.add_field(FormField.from_dict(fd))
        return template
    
    def save(self, filepath: str):
        """Speichert Template als JSON."""
        # BUGSWEEP-30: atomar schreiben (tmp + replace) — sonst hinterlaesst ein Crash/OneDrive-Lock
        # mitten im json.dump eine halbe/korrupte Template-JSON (persistence.py macht es bereits so).
        target = Path(filepath)
        tmp = target.with_name(target.name + ".tmp")
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        tmp.replace(target)
    
    @classmethod
    def load(cls, filepath: str) -> 'FormTemplate':
        """Lädt Template aus JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                raise ValueError(f"Ungültige JSON-Datei: {filepath}: {e}")
        return cls.from_dict(data)


class FormBuilder(LoggerMixin):
    """
    Erstellt PDF-Formulare.
    
    Features:
    - Verschiedene Feldtypen
    - Vorlagen speichern/laden
    - PDF mit Formularfeldern generieren
    - Hintergrund-PDF verwenden
    """
    
    PAGE_SIZES = {
        "A4": (210, 297),
        "A5": (148, 210),
        "Letter": (216, 279),
        "Legal": (216, 356)
    }
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            self.logger.warning("reportlab nicht verfügbar")
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht verfügbar")
    
    def create_template(self, name: str, page_size: str = "A4") -> FormTemplate:
        """Erstellt eine neue Vorlage."""
        size = self.PAGE_SIZES.get(page_size, self.PAGE_SIZES["A4"])
        return FormTemplate(name=name, page_size=size)
    
    def generate_pdf(self, template: FormTemplate, output_path: str,
                     fill_data: Dict[str, str] = None) -> bool:
        """
        Generiert PDF aus Template.
        
        Args:
            template: Formular-Vorlage
            output_path: Ausgabepfad
            fill_data: Optionale Felddaten zum Ausfüllen
            
        Returns:
            True bei Erfolg
        """
        if not REPORTLAB_AVAILABLE:
            self.logger.error("reportlab nicht verfügbar")
            return False
        
        fill_data = fill_data or {}
        
        try:
            # Seitengröße
            width_mm, height_mm = template.page_size
            page_size = (width_mm * mm, height_mm * mm)
            
            c = canvas.Canvas(output_path, pagesize=page_size)
            
            # Titel setzen
            if template.title:
                c.setTitle(template.title)
            if template.author:
                c.setAuthor(template.author)
            
            # Felder zeichnen
            for field in template.fields:
                self._draw_field(c, field, height_mm, fill_data.get(field.name, ""))
            
            c.save()
            
            # Formularfelder hinzufügen (interaktiv)
            if PYMUPDF_AVAILABLE:
                self._add_interactive_fields(output_path, template, fill_data)
            
            self.logger.info(f"PDF erstellt: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"PDF-Generierung fehlgeschlagen: {e}")
            return False
    
    def _draw_field(self, c: canvas.Canvas, field: FormField, 
                    page_height: float, value: str):
        """Zeichnet ein Feld auf das Canvas."""
        x = field.x * mm
        y = (page_height - field.y - field.height) * mm  # Y von oben
        w = field.width * mm
        h = field.height * mm
        
        c.setFont("Helvetica", field.font_size)
        
        if field.field_type == FieldType.LABEL:
            # Nur Text
            c.drawString(x, y + h - field.font_size, field.label or field.default_value)
        
        elif field.field_type == FieldType.TEXT:
            # Rahmen zeichnen
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            # Label
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, field.label)
                c.setFont("Helvetica", field.font_size)
            
            # Wert
            if value:
                c.drawString(x + 2, y + 4, value[:int(w/5)])
        
        elif field.field_type == FieldType.TEXTAREA:
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, field.label)
        
        elif field.field_type == FieldType.CHECKBOX:
            # Checkbox-Rahmen
            box_size = min(h, 12)
            c.rect(x, y + (h - box_size) / 2, box_size, box_size)
            
            # Häkchen wenn checked
            if value.lower() in ['true', '1', 'yes', 'ja', 'x']:
                c.line(x + 2, y + (h - box_size) / 2 + box_size / 2,
                       x + box_size / 2, y + (h - box_size) / 2 + 2)
                c.line(x + box_size / 2, y + (h - box_size) / 2 + 2,
                       x + box_size - 2, y + (h - box_size) / 2 + box_size - 2)
            
            # Label
            if field.label:
                c.drawString(x + box_size + 4, y + (h - field.font_size) / 2 + 2, field.label)
        
        elif field.field_type == FieldType.DROPDOWN:
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            # Pfeil
            c.line(x + w - 10, y + h/2 + 3, x + w - 5, y + h/2 - 2)
            c.line(x + w - 5, y + h/2 - 2, x + w - 2, y + h/2 + 3)
            
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, field.label)
        
        elif field.field_type == FieldType.DATE:
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            # Placeholder
            c.setFillColor(gray)
            c.drawString(x + 2, y + 4, "TT.MM.JJJJ")
            c.setFillColor(black)
            
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, field.label)
        
        elif field.field_type == FieldType.SIGNATURE:
            c.setStrokeColor(gray)
            c.setDash(3, 2)
            c.rect(x, y, w, h)
            c.setDash()
            
            c.setFont("Helvetica", 8)
            c.drawString(x + 2, y + 4, "Unterschrift")
            
            if field.label:
                c.drawString(x, y + h + 2, field.label)
    
    def _add_interactive_fields(self, pdf_path: str, template: FormTemplate,
                                 fill_data: Dict[str, str]):
        """Fügt interaktive Formularfelder hinzu."""
        doc = fitz.open(pdf_path)
        try:
            page = doc[0]

            page_height = template.page_size[1]

            for field in template.fields:
                if field.field_type in [FieldType.LABEL]:
                    continue  # Labels sind nicht interaktiv

                # Rechteck berechnen (PDF-Koordinaten: Y von unten)
                x = field.x * 72 / 25.4  # mm zu points
                y = (page_height - field.y - field.height) * 72 / 25.4
                w = field.width * 72 / 25.4
                h = field.height * 72 / 25.4

                rect = fitz.Rect(x, y, x + w, y + h)

                try:
                    if field.field_type == FieldType.TEXT:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                        widget.field_name = field.name
                        widget.rect = rect
                        widget.field_value = fill_data.get(field.name, field.default_value)
                        page.add_widget(widget)

                    elif field.field_type == FieldType.CHECKBOX:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                        widget.field_name = field.name
                        widget.rect = rect
                        page.add_widget(widget)

                    elif field.field_type == FieldType.DROPDOWN:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_LISTBOX
                        widget.field_name = field.name
                        widget.rect = rect
                        widget.choice_values = field.options
                        page.add_widget(widget)

                except Exception as e:
                    self.logger.debug(f"Widget-Fehler für {field.name}: {e}")

            doc.saveIncr()
        finally:
            doc.close()
    
    def extract_form_fields(self, pdf_path: str) -> List[Dict]:
        """Extrahiert Formularfelder aus einem PDF."""
        if not PYMUPDF_AVAILABLE:
            return []
        
        fields = []
        
        try:
            doc = fitz.open(pdf_path)
            try:
                for page_num, page in enumerate(doc):
                    for widget in page.widgets():
                        field_info = {
                            "page": page_num + 1,
                            "name": widget.field_name,
                            "type": widget.field_type_string,
                            "value": widget.field_value,
                            "rect": list(widget.rect),
                            "flags": widget.field_flags
                        }
                        fields.append(field_info)
            finally:
                doc.close()

        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren: {e}")
        
        return fields
    
    def fill_form(self, pdf_path: str, output_path: str, 
                  data: Dict[str, str]) -> bool:
        """Füllt ein PDF-Formular aus."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        try:
            doc = fitz.open(pdf_path)
            try:
                for page in doc:
                    for widget in page.widgets():
                        if widget.field_name in data:
                            widget.field_value = data[widget.field_name]
                            widget.update()

                doc.save(output_path)
            finally:
                doc.close()

            self.logger.info(f"Formular ausgefüllt: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Fehler beim Ausfüllen: {e}")
            return False


# === Standard-Templates ===

def create_contact_form() -> FormTemplate:
    """Erstellt ein Kontaktformular-Template."""
    template = FormTemplate(name="Kontaktformular", title="Kontaktformular")
    
    template.add_field(FormField(
        FieldType.LABEL, "title", 20, 20, 100, 10,
        label="Kontaktformular", font_size=16
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "name", 20, 40, 80, 8,
        label="Name", required=True
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "email", 110, 40, 80, 8,
        label="E-Mail", required=True
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "phone", 20, 60, 80, 8,
        label="Telefon"
    ))
    
    template.add_field(FormField(
        FieldType.DROPDOWN, "subject", 110, 60, 80, 8,
        label="Betreff",
        options=["Anfrage", "Beschwerde", "Lob", "Sonstiges"]
    ))
    
    template.add_field(FormField(
        FieldType.TEXTAREA, "message", 20, 80, 170, 60,
        label="Nachricht"
    ))
    
    template.add_field(FormField(
        FieldType.CHECKBOX, "newsletter", 20, 150, 100, 8,
        label="Newsletter abonnieren"
    ))
    
    template.add_field(FormField(
        FieldType.DATE, "date", 20, 170, 50, 8,
        label="Datum"
    ))
    
    template.add_field(FormField(
        FieldType.SIGNATURE, "signature", 100, 160, 90, 30,
        label="Unterschrift"
    ))
    
    return template


def create_registration_form() -> FormTemplate:
    """Erstellt ein Anmeldeformular-Template."""
    template = FormTemplate(name="Anmeldeformular", title="Anmeldung")
    
    template.add_field(FormField(
        FieldType.LABEL, "title", 20, 15, 170, 12,
        label="Anmeldeformular", font_size=18
    ))
    
    # Persönliche Daten
    template.add_field(FormField(
        FieldType.LABEL, "section1", 20, 35, 100, 8,
        label="Persönliche Daten", font_size=12
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "firstname", 20, 50, 80, 8,
        label="Vorname", required=True
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "lastname", 110, 50, 80, 8,
        label="Nachname", required=True
    ))
    
    template.add_field(FormField(
        FieldType.DATE, "birthdate", 20, 70, 50, 8,
        label="Geburtsdatum"
    ))
    
    # Adresse
    template.add_field(FormField(
        FieldType.LABEL, "section2", 20, 95, 100, 8,
        label="Adresse", font_size=12
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "street", 20, 110, 120, 8,
        label="Straße"
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "zip", 150, 110, 40, 8,
        label="PLZ"
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "city", 20, 130, 80, 8,
        label="Stadt"
    ))
    
    template.add_field(FormField(
        FieldType.TEXT, "country", 110, 130, 80, 8,
        label="Land", default_value="Deutschland"
    ))
    
    return template
