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


class FieldType(str, Enum):
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
        """Erstellt aus Dictionary mit defensiver Validierung."""
        ft_raw = data.get("field_type", "text")
        if isinstance(ft_raw, FieldType):
            field_type = ft_raw
        elif isinstance(ft_raw, str):
            try:
                field_type = FieldType(ft_raw.lower())
            except ValueError:
                field_type = FieldType.TEXT
        else:
            field_type = FieldType.TEXT

        raw_opts = data.get("options")
        options = [str(o) for o in raw_opts] if isinstance(raw_opts, (list, tuple)) else []

        raw_def = data.get("default_value")
        default_val = str(raw_def) if raw_def is not None else ""

        raw_lbl = data.get("label")
        lbl = str(raw_lbl) if raw_lbl is not None else ""

        try:
            x_val = float(data.get("x", 0.0))
        except (ValueError, TypeError):
            x_val = 0.0

        try:
            y_val = float(data.get("y", 0.0))
        except (ValueError, TypeError):
            y_val = 0.0

        try:
            w_val = float(data.get("width", 10.0))
        except (ValueError, TypeError):
            w_val = 10.0

        try:
            h_val = float(data.get("height", 10.0))
        except (ValueError, TypeError):
            h_val = 10.0

        try:
            fs_val = int(data.get("font_size", 10) or 10)
        except (ValueError, TypeError):
            fs_val = 10

        try:
            ml_val = int(data.get("max_length", 0) or 0)
        except (ValueError, TypeError):
            ml_val = 0

        return cls(
            field_type=field_type,
            name=str(data.get("name") or "field"),
            x=x_val,
            y=y_val,
            width=w_val,
            height=h_val,
            label=lbl,
            default_value=default_val,
            required=bool(data.get("required", False)),
            options=options,
            font_size=fs_val,
            max_length=ml_val,
            read_only=bool(data.get("read_only", False))
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
        """Erstellt aus Dictionary mit defensiven Fallbacks."""
        if not isinstance(data, dict):
            raise ValueError(f"Ungültige Template-Struktur (Dictionary erwartet): {type(data)}")

        raw_size = data.get("page_size")
        if isinstance(raw_size, (list, tuple)) and len(raw_size) >= 2:
            try:
                page_size = (float(raw_size[0]), float(raw_size[1]))
            except (ValueError, TypeError):
                page_size = (210.0, 297.0)
        else:
            page_size = (210.0, 297.0)

        bg_raw = data.get("background_pdf")
        bg_pdf = str(bg_raw) if bg_raw else None

        template = cls(
            name=str(data.get("name") or "Vorlage"),
            page_size=page_size,
            background_pdf=bg_pdf,
            title=str(data.get("title") or ""),
            author=str(data.get("author") or "")
        )
        raw_fields = data.get("fields")
        if isinstance(raw_fields, list):
            for fd in raw_fields:
                if isinstance(fd, dict):
                    template.add_field(FormField.from_dict(fd))
        return template
    
    def save(self, filepath: str):
        """Speichert Template als JSON."""
        # BUGSWEEP-30: atomar schreiben (tmp + replace) — sonst hinterlaesst ein Crash/OneDrive-Lock
        # mitten im json.dump eine halbe/korrupte Template-JSON (persistence.py macht es bereits so).
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        tmp.replace(target)
    
    @classmethod
    def load(cls, filepath: str) -> 'FormTemplate':
        """Lädt Template aus JSON."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
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
        lookup = {k.lower(): v for k, v in self.PAGE_SIZES.items()}
        size = lookup.get(str(page_size).strip().lower(), self.PAGE_SIZES["A4"])
        return FormTemplate(name=name, page_size=size)
    
    def generate_pdf(self, template: FormTemplate, output_path: str,
                     fill_data: Optional[Dict[str, Any]] = None) -> bool:
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
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        has_bg = False
        bg_file = None
        if template.background_pdf:
            bg_candidate = Path(template.background_pdf)
            if bg_candidate.is_file():
                has_bg = True
                bg_file = bg_candidate
            else:
                self.logger.warning(f"Hintergrund-PDF nicht gefunden: {template.background_pdf}")

        # Wenn Hintergrund-PDF vorhanden ist, zeichnen wir den Canvas temporär und legen ihn darüber
        canvas_target = str(target_path.with_name(target_path.stem + ".tmp_canvas.pdf")) if has_bg else str(target_path)
        
        try:
            # Seitengröße
            width_mm, height_mm = template.page_size
            page_size = (width_mm * mm, height_mm * mm)
            
            c = canvas.Canvas(canvas_target, pagesize=page_size)
            
            # Titel setzen
            if template.title:
                c.setTitle(str(template.title))
            if template.author:
                c.setAuthor(str(template.author))
            
            # Felder zeichnen
            for field in template.fields:
                val = fill_data.get(field.name, field.default_value)
                self._draw_field(c, field, height_mm, val)
            
            c.save()

            if has_bg and PYMUPDF_AVAILABLE:
                # Hintergrund-PDF laden und Canvas darüberlegen
                bg_doc = fitz.open(str(bg_file))
                fg_doc = fitz.open(canvas_target)
                try:
                    if len(bg_doc) > 0 and len(fg_doc) > 0:
                        bg_page = bg_doc[0]
                        bg_page.show_pdf_page(bg_page.rect, fg_doc, 0)
                    bg_doc.save(str(target_path))
                finally:
                    bg_doc.close()
                    fg_doc.close()
                    try:
                        Path(canvas_target).unlink(missing_ok=True)
                    except Exception:
                        pass
            
            # Formularfelder hinzufügen (interaktiv)
            if PYMUPDF_AVAILABLE:
                self._add_interactive_fields(str(target_path), template, fill_data)
            
            self.logger.info(f"PDF erstellt: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"PDF-Generierung fehlgeschlagen: {e}")
            if has_bg:
                try:
                    Path(canvas_target).unlink(missing_ok=True)
                except Exception:
                    pass
            return False
    
    def _draw_field(self, c: canvas.Canvas, field: FormField, 
                    page_height: float, value: Any):
        """Zeichnet ein Feld auf das Canvas."""
        x = field.x * mm
        y = (page_height - field.y - field.height) * mm  # Y von oben
        w = field.width * mm
        h = field.height * mm
        
        c.setFont("Helvetica", field.font_size)
        
        ft_val = field.field_type.value if hasattr(field.field_type, "value") else str(field.field_type).lower()

        val_str = ""
        val_bool = False
        if value is not None:
            if isinstance(value, bool):
                val_bool = value
                val_str = "true" if value else "false"
            elif isinstance(value, (int, float)):
                val_bool = (value == 1)
                val_str = str(value)
            else:
                val_str = str(value)
                val_bool = val_str.strip().lower() in ['true', '1', 'yes', 'ja', 'x']

        if ft_val == FieldType.LABEL.value:
            # Nur Text
            lbl_text = str(field.label or field.default_value or "")
            c.drawString(x, y + h - field.font_size, lbl_text)
        
        elif ft_val == FieldType.TEXT.value:
            # Rahmen zeichnen
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            # Label
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, str(field.label))
                c.setFont("Helvetica", field.font_size)
            
            # Wert
            if val_str:
                c.drawString(x + 2, y + 4, val_str[:int(w/5)])
        
        elif ft_val == FieldType.TEXTAREA.value:
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, str(field.label))
                c.setFont("Helvetica", field.font_size)
            if val_str:
                c.setFont("Helvetica", field.font_size)
                lines = val_str.split("\n")
                line_y = y + h - field.font_size - 4
                for line in lines:
                    if line_y < y + 4:
                        break
                    c.drawString(x + 4, line_y, line[:int(w / 5)])
                    line_y -= (field.font_size + 2)
        
        elif ft_val == FieldType.CHECKBOX.value:
            # Checkbox-Rahmen
            box_size = min(h, 12)
            c.rect(x, y + (h - box_size) / 2, box_size, box_size)
            
            # Häkchen wenn checked
            if val_bool:
                c.line(x + 2, y + (h - box_size) / 2 + box_size / 2,
                       x + box_size / 2, y + (h - box_size) / 2 + 2)
                c.line(x + box_size / 2, y + (h - box_size) / 2 + 2,
                       x + box_size - 2, y + (h - box_size) / 2 + box_size - 2)
            
            # Label
            if field.label:
                c.drawString(x + box_size + 4, y + (h - field.font_size) / 2 + 2, str(field.label))

        elif ft_val == FieldType.RADIO.value:
            c.setStrokeColor(gray)
            radius = min(h, 12) / 2
            c.circle(x + radius, y + h / 2, radius)
            if val_bool:
                c.setFillColor(black)
                c.circle(x + radius, y + h / 2, radius / 2, fill=1)
                c.setFillColor(black)
            if field.label:
                c.drawString(x + radius * 2 + 4, y + (h - field.font_size) / 2 + 2, str(field.label))
        
        elif ft_val == FieldType.DROPDOWN.value:
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            # Pfeil
            c.line(x + w - 10, y + h/2 + 3, x + w - 5, y + h/2 - 2)
            c.line(x + w - 5, y + h/2 - 2, x + w - 2, y + h/2 + 3)
            
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, str(field.label))
                c.setFont("Helvetica", field.font_size)
            if val_str:
                c.drawString(x + 2, y + 4, val_str[:int((w - 12) / 5)])
        
        elif ft_val == FieldType.DATE.value:
            c.setStrokeColor(gray)
            c.rect(x, y, w, h)
            
            if val_str:
                c.setFont("Helvetica", field.font_size)
                c.drawString(x + 2, y + 4, val_str)
            else:
                # Placeholder
                c.setFillColor(gray)
                c.drawString(x + 2, y + 4, "TT.MM.JJJJ")
                c.setFillColor(black)
            
            if field.label:
                c.setFont("Helvetica", 8)
                c.drawString(x, y + h + 2, str(field.label))
        
        elif ft_val == FieldType.SIGNATURE.value:
            c.setStrokeColor(gray)
            c.setDash(3, 2)
            c.rect(x, y, w, h)
            c.setDash()
            
            c.setFont("Helvetica", 8)
            c.drawString(x + 2, y + 4, "Unterschrift")
            
            if field.label:
                c.drawString(x, y + h + 2, str(field.label))
    
    def _add_interactive_fields(self, pdf_path: str, template: FormTemplate,
                                 fill_data: Dict[str, Any]):
        """Fügt interaktive Formularfelder hinzu."""
        doc = fitz.open(pdf_path)
        try:
            if len(doc) == 0:
                return
            page = doc[0]

            scale = 72.0 / 25.4  # mm zu points

            for field in template.fields:
                ft_val = field.field_type.value if hasattr(field.field_type, "value") else str(field.field_type).lower()

                if ft_val == FieldType.LABEL.value:
                    continue  # Labels sind nicht interaktiv

                # Rechteck berechnen: PyMuPDF-Koordinaten (Ursprung oben links, Y wächst nach unten)
                x = field.x * scale
                y = field.y * scale
                w = field.width * scale
                h = field.height * scale

                rect = fitz.Rect(x, y, x + w, y + h)

                raw_val = fill_data.get(field.name, field.default_value)
                val_str = "" if raw_val is None else str(raw_val)
                val_bool = False
                if raw_val is not None:
                    if isinstance(raw_val, bool):
                        val_bool = raw_val
                    else:
                        val_bool = str(raw_val).strip().lower() in ['true', '1', 'yes', 'ja', 'x']

                try:
                    if ft_val == FieldType.TEXT.value:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                        widget.field_name = field.name
                        widget.rect = rect
                        widget.field_value = val_str
                        if field.max_length and field.max_length > 0:
                            widget.text_maxlen = int(field.max_length)
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        page.add_widget(widget)

                    elif ft_val == FieldType.TEXTAREA.value:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                        widget.field_name = field.name
                        widget.rect = rect
                        widget.field_flags |= getattr(fitz, "PDF_TX_FIELD_IS_MULTILINE", 4096)
                        if field.max_length and field.max_length > 0:
                            widget.text_maxlen = int(field.max_length)
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        widget.field_value = val_str
                        page.add_widget(widget)

                    elif ft_val == FieldType.DATE.value:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                        widget.field_name = field.name
                        widget.rect = rect
                        widget.text_format = getattr(fitz, "PDF_WIDGET_TX_FORMAT_DATE", 3)
                        widget.field_value = val_str
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        page.add_widget(widget)

                    elif ft_val == FieldType.CHECKBOX.value:
                        widget = fitz.Widget()
                        widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                        widget.field_name = field.name
                        widget.rect = rect
                        if val_bool:
                            widget.field_value = True
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        page.add_widget(widget)

                    elif ft_val == FieldType.RADIO.value:
                        widget = fitz.Widget()
                        widget.field_type = getattr(fitz, "PDF_WIDGET_TYPE_RADIOBUTTON", 5)
                        widget.field_name = field.name
                        widget.rect = rect
                        if val_bool:
                            widget.field_value = True
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        page.add_widget(widget)

                    elif ft_val == FieldType.DROPDOWN.value:
                        widget = fitz.Widget()
                        widget.field_type = getattr(fitz, "PDF_WIDGET_TYPE_COMBOBOX", fitz.PDF_WIDGET_TYPE_LISTBOX)
                        widget.field_name = field.name
                        widget.rect = rect
                        widget.choice_values = [str(opt) for opt in (field.options or [])]
                        if val_str:
                            widget.field_value = val_str
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        page.add_widget(widget)

                    elif ft_val == FieldType.SIGNATURE.value:
                        widget = fitz.Widget()
                        widget.field_type = getattr(fitz, "PDF_WIDGET_TYPE_SIGNATURE", 6)
                        widget.field_name = field.name
                        widget.rect = rect
                        if field.read_only:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
                        if field.required:
                            widget.field_flags |= getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)
                        page.add_widget(widget)

                except Exception as e:
                    self.logger.debug(f"Widget-Fehler für {field.name}: {e}")

            tmp_replace = False
            tmp_out = None
            try:
                doc.saveIncr()
            except Exception:
                tmp_out = Path(pdf_path).with_name(Path(pdf_path).name + ".tmp_incr")
                doc.save(str(tmp_out))
                tmp_replace = True
        finally:
            doc.close()
            if tmp_replace and tmp_out:
                try:
                    tmp_out.replace(pdf_path)
                except Exception:
                    pass
    
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
                        flags = widget.field_flags or 0
                        field_info = {
                            "page": page_num + 1,
                            "name": widget.field_name,
                            "type": widget.field_type_string,
                            "value": widget.field_value,
                            "rect": list(widget.rect),
                            "flags": flags,
                            "read_only": bool(flags & getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)),
                            "required": bool(flags & getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)),
                            "options": list(widget.choice_values or []) if hasattr(widget, "choice_values") else []
                        }
                        fields.append(field_info)
            finally:
                doc.close()

        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren: {e}")
        
        return fields
    
    def fill_form(self, pdf_path: str, output_path: str, 
                  data: Dict[str, Any]) -> bool:
        """Füllt ein PDF-Formular aus."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        tmp_replace = False
        tmp = None
        try:
            doc = fitz.open(pdf_path)
            try:
                for page in doc:
                    for widget in page.widgets():
                        if widget.field_name in data:
                            val = data[widget.field_name]
                            if widget.field_type in (fitz.PDF_WIDGET_TYPE_CHECKBOX, getattr(fitz, "PDF_WIDGET_TYPE_RADIOBUTTON", 5)):
                                if isinstance(val, bool):
                                    widget.field_value = val
                                else:
                                    widget.field_value = str(val).strip().lower() in ['true', '1', 'yes', 'ja', 'x']
                            else:
                                widget.field_value = str(val) if val is not None else ""
                            try:
                                widget.update()
                            except Exception as e:
                                self.logger.debug(f"Widget update warning für {widget.field_name}: {e}")

                is_same = False
                try:
                    is_same = Path(pdf_path).resolve() == Path(output_path).resolve()
                except Exception:
                    pass

                if is_same:
                    try:
                        doc.saveIncr()
                    except Exception:
                        tmp = Path(output_path).with_name(Path(output_path).name + ".tmp_fill")
                        doc.save(str(tmp))
                        tmp_replace = True
                else:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    doc.save(output_path)
            finally:
                doc.close()
                if tmp_replace and tmp:
                    try:
                        tmp.replace(output_path)
                    except Exception:
                        pass

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
