#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermetische Regressionstests für FormBuilder AcroForm-Resilienz:
- Background-PDF Overlay-Unterstützung
- Datentyp-Resilienz in _draw_field und fill_form (booleans, ints, floats, None)
- AcroForm Feld-Attribute (read_only, required, max_length)
- Defensive Deserialisierung von FormField und FormTemplate bei schema-drift und JSON-Nulls
- Case-Insensitive Page-Sizes in create_template
- Ausführliche Metadaten in extract_form_fields
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from core.forms.builder import (
    FieldType,
    FormBuilder,
    FormField,
    FormTemplate,
)


class TestFormBuilderResilience20261011(unittest.TestCase):
    def setUp(self):
        self.builder = FormBuilder()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_draw_field_and_generate_pdf_with_non_string_types(self):
        """generate_pdf() darf bei booleans, ints, floats oder None in fill_data nicht abstürzen."""
        tpl = FormTemplate(name="TypeSafetyTest", page_size=(210, 297))
        tpl.add_field(FormField(FieldType.CHECKBOX, "newsletter", 20, 20, 40, 8))
        tpl.add_field(FormField(FieldType.RADIO, "gender_opt", 20, 35, 40, 8))
        tpl.add_field(FormField(FieldType.TEXT, "zip_code", 20, 50, 60, 8))
        tpl.add_field(FormField(FieldType.TEXTAREA, "notes", 20, 65, 80, 20))
        tpl.add_field(FormField(FieldType.DATE, "event_date", 20, 90, 40, 8))
        tpl.add_field(FormField(FieldType.DROPDOWN, "rating", 20, 105, 40, 8, options=["1", "2", "3"]))

        pdf_path = os.path.join(self.temp_dir.name, "type_safety.pdf")
        fill_data = {
            "newsletter": True,     # boolean
            "gender_opt": 1,        # int truthy
            "zip_code": 80331,      # int
            "notes": None,          # None
            "event_date": "2026-10-11",
            "rating": 3             # int option
        }

        success = self.builder.generate_pdf(tpl, pdf_path, fill_data=fill_data)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(pdf_path))

        doc = fitz.open(pdf_path)
        try:
            widgets = {w.field_name: w for w in doc[0].widgets()}
            self.assertEqual(widgets["newsletter"].field_value, "Yes")
            self.assertEqual(widgets["zip_code"].field_value, "80331")
        finally:
            doc.close()

    def test_generate_pdf_with_background_pdf_overlay(self):
        """Wenn background_pdf gesetzt ist, wird das PDF auf die Hintergrundseite gerendert."""
        # 1. Erstelle Background-PDF mit spezifischem Inhalt
        bg_path = os.path.join(self.temp_dir.name, "background.pdf")
        bg_doc = fitz.open()
        bg_page = bg_doc.new_page(width=595, height=842)
        bg_page.draw_rect(fitz.Rect(50, 50, 200, 200), color=(1, 0, 0), fill=(0.95, 0.95, 0.95))
        bg_page.insert_text(fitz.Point(60, 80), "OFFICIAL BACKGROUND HEADER", fontsize=14)
        bg_doc.save(bg_path)
        bg_doc.close()

        # 2. Template mit background_pdf konfigurieren
        tpl = FormTemplate(name="BgTest", page_size=(210, 297), background_pdf=bg_path)
        tpl.add_field(FormField(FieldType.TEXT, "applicant_name", 30, 40, 80, 8, label="Applicant"))

        out_path = os.path.join(self.temp_dir.name, "output_with_bg.pdf")
        success = self.builder.generate_pdf(tpl, out_path, fill_data={"applicant_name": "Lukas Geiger"})
        self.assertTrue(success)

        # 3. Überprüfe, dass Background-Text und Widget vorhanden sind
        res_doc = fitz.open(out_path)
        try:
            self.assertEqual(len(res_doc), 1)
            page_text = res_doc[0].get_text()
            self.assertIn("OFFICIAL BACKGROUND HEADER", page_text)
            widgets = list(res_doc[0].widgets())
            self.assertEqual(len(widgets), 1)
            self.assertEqual(widgets[0].field_name, "applicant_name")
            self.assertEqual(widgets[0].field_value, "Lukas Geiger")
        finally:
            res_doc.close()

    def test_field_attributes_read_only_required_max_length(self):
        """AcroForm-Flags read_only, required und text_maxlen werden im Widget abgebildet."""
        tpl = FormTemplate(name="FlagsTest", page_size=(210, 297))
        tpl.add_field(FormField(
            FieldType.TEXT, "protected_field", 20, 20, 80, 8,
            read_only=True, required=True, max_length=15, default_value="LOCKED"
        ))
        tpl.add_field(FormField(
            FieldType.CHECKBOX, "req_checkbox", 20, 35, 40, 8,
            required=True
        ))

        pdf_path = os.path.join(self.temp_dir.name, "flags_test.pdf")
        self.builder.generate_pdf(tpl, pdf_path)

        fields = self.builder.extract_form_fields(pdf_path)
        fields_map = {f["name"]: f for f in fields}

        # protected_field must have read_only and required set
        self.assertTrue(fields_map["protected_field"]["read_only"])
        self.assertTrue(fields_map["protected_field"]["required"])

        # Check PyMuPDF direct properties
        doc = fitz.open(pdf_path)
        try:
            w_text = [w for w in doc[0].widgets() if w.field_name == "protected_field"][0]
            self.assertTrue(bool(w_text.field_flags & getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)))
            self.assertTrue(bool(w_text.field_flags & getattr(fitz, "PDF_FIELD_IS_REQUIRED", 2)))
            self.assertEqual(w_text.text_maxlen, 15)
        finally:
            doc.close()

    def test_fill_form_checkbox_and_type_coercion(self):
        """fill_form() unterstützt CheckBoxes mit booleans/strings und wandelt non-strings sauber um."""
        tpl = FormTemplate(name="FillTest", page_size=(210, 297))
        tpl.add_field(FormField(FieldType.CHECKBOX, "is_active", 20, 20, 30, 8))
        tpl.add_field(FormField(FieldType.TEXT, "amount", 20, 35, 40, 8))
        tpl.add_field(FormField(FieldType.TEXT, "comment", 20, 50, 40, 8, default_value="init"))

        pdf_path = os.path.join(self.temp_dir.name, "fill_test.pdf")
        self.builder.generate_pdf(tpl, pdf_path)

        out_path = os.path.join(self.temp_dir.name, "filled_result.pdf")
        ok = self.builder.fill_form(pdf_path, out_path, {
            "is_active": True,
            "amount": 1250,
            "comment": "Updated Note"
        })
        self.assertTrue(ok)

        doc = fitz.open(out_path)
        try:
            w_map = {w.field_name: w for w in doc[0].widgets()}
            self.assertEqual(w_map["amount"].field_value, "1250")
            self.assertEqual(w_map["is_active"].field_value, "Yes")
            self.assertEqual(w_map["comment"].field_value, "Updated Note")
        finally:
            doc.close()

    def test_form_field_from_dict_null_and_drift_resilience(self):
        """FormField.from_dict fängt explizite nulls, abweichendes Casing und Typfehler resilient ab."""
        corrupt_dict = {
            "field_type": "TEXT",       # uppercase
            "name": "resilient_field",
            "x": "25.5",               # string number
            "y": None,                 # null
            "width": 80,
            "height": 10,
            "label": None,             # null
            "default_value": None,     # null
            "required": None,          # null
            "options": None,           # null
            "font_size": None,         # null
            "max_length": None,        # null
            "read_only": None          # null
        }
        field = FormField.from_dict(corrupt_dict)
        self.assertEqual(field.field_type, FieldType.TEXT)
        self.assertEqual(field.x, 25.5)
        self.assertEqual(field.y, 0.0)
        self.assertEqual(field.label, "")
        self.assertEqual(field.default_value, "")
        self.assertEqual(field.options, [])
        self.assertEqual(field.font_size, 10)
        self.assertEqual(field.max_length, 0)
        self.assertFalse(field.read_only)
        self.assertFalse(field.required)

    def test_form_template_from_dict_and_load_exceptions(self):
        """FormTemplate.from_dict und load() behandeln fehlerhafte JSON-Strukturen und fehlende Pfade."""
        corrupt_tpl_dict = {
            "name": None,
            "page_size": None,
            "fields": None,
            "background_pdf": None,
            "title": None,
            "author": None
        }
        tpl = FormTemplate.from_dict(corrupt_tpl_dict)
        self.assertEqual(tpl.name, "Vorlage")
        self.assertEqual(tpl.page_size, (210.0, 297.0))
        self.assertEqual(len(tpl.fields), 0)

        # Nicht-existierende Datei
        with self.assertRaises(ValueError):
            FormTemplate.load(os.path.join(self.temp_dir.name, "nonexistent.json"))

        # Ungültiges JSON
        bad_json = os.path.join(self.temp_dir.name, "bad.json")
        with open(bad_json, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        with self.assertRaises(ValueError):
            FormTemplate.load(bad_json)

    def test_create_template_case_insensitive_page_sizes(self):
        """create_template() normalisiert die Seitengröße unabhängig von Groß-/Kleinschreibung."""
        tpl_a5 = self.builder.create_template("DocA5", page_size="a5")
        self.assertEqual(tpl_a5.page_size, (148, 210))

        tpl_letter = self.builder.create_template("DocLetter", page_size="letter")
        self.assertEqual(tpl_letter.page_size, (216, 279))

        tpl_unknown = self.builder.create_template("DocUnknown", page_size="unknown_format")
        self.assertEqual(tpl_unknown.page_size, (210, 297))

    def test_extract_form_fields_exposes_rich_metadata(self):
        """extract_form_fields liefert options, read_only und required zurück."""
        tpl = FormTemplate(name="ExtractTest", page_size=(210, 297))
        tpl.add_field(FormField(
            FieldType.DROPDOWN, "category", 20, 20, 60, 8,
            options=["Privat", "Geschäftlich"], default_value="Privat", required=True
        ))

        pdf_path = os.path.join(self.temp_dir.name, "extract_test.pdf")
        self.builder.generate_pdf(tpl, pdf_path)

        fields = self.builder.extract_form_fields(pdf_path)
        self.assertEqual(len(fields), 1)
        f = fields[0]
        self.assertEqual(f["name"], "category")
        self.assertEqual(f["options"], ["Privat", "Geschäftlich"])
        self.assertTrue(f["required"])
        self.assertFalse(f["read_only"])


if __name__ == "__main__":
    unittest.main()
