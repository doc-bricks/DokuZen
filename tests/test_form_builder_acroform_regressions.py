#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regressionstests für FormBuilder AcroForm-Generierung, Koordinatenausrichtung,
vollständige Feldtypen (Textarea, Date, Signature, Radio), Checkbox-Werte und In-Place-Speichern.
"""

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
    FormBuilder,
    FormTemplate,
    FormField,
    FieldType,
    create_contact_form,
    create_registration_form,
)


class TestFormBuilderAcroformRegressions(unittest.TestCase):
    def setUp(self):
        self.builder = FormBuilder()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_coordinate_alignment_with_drawn_box(self):
        """Interactive widget rect must align with the visual drawn box at the top of the page."""
        tpl = FormTemplate(name="CoordTest", page_size=(210, 297))
        # Field at y=30mm from top, height 10mm
        field = FormField(FieldType.TEXT, "first_field", 20, 30, 80, 10, label="First Field")
        tpl.add_field(field)

        pdf_path = os.path.join(self.temp_dir.name, "coord_test.pdf")
        success = self.builder.generate_pdf(tpl, pdf_path)
        self.assertTrue(success)

        doc = fitz.open(pdf_path)
        try:
            page = doc[0]
            widgets = list(page.widgets())
            self.assertEqual(len(widgets), 1)
            w = widgets[0]

            # In PyMuPDF, y=0 is top. 30mm = 30 * 72 / 25.4 = 85.039 points from top.
            expected_y0 = 30.0 * 72.0 / 25.4
            expected_y1 = 40.0 * 72.0 / 25.4
            expected_x0 = 20.0 * 72.0 / 25.4
            expected_x1 = 100.0 * 72.0 / 25.4

            self.assertAlmostEqual(w.rect.y0, expected_y0, delta=1.0)
            self.assertAlmostEqual(w.rect.y1, expected_y1, delta=1.0)
            self.assertAlmostEqual(w.rect.x0, expected_x0, delta=1.0)
            self.assertAlmostEqual(w.rect.x1, expected_x1, delta=1.0)

            # Check that it matches the drawn rectangle in drawings
            drawings = page.get_drawings()
            rect_drawings = [d["rect"] for d in drawings if abs(d["rect"].width - (expected_x1 - expected_x0)) < 2.0]
            self.assertTrue(len(rect_drawings) >= 1)
            self.assertAlmostEqual(w.rect.y0, rect_drawings[0].y0, delta=1.0)
        finally:
            doc.close()

    def test_all_interactive_widget_types_created(self):
        """All non-label field types (TEXT, TEXTAREA, DATE, CHECKBOX, RADIO, DROPDOWN, SIGNATURE) must create widgets."""
        tpl = FormTemplate(name="AllTypes", page_size=(210, 297))
        tpl.add_field(FormField(FieldType.LABEL, "lbl", 20, 10, 100, 10, label="Header"))
        tpl.add_field(FormField(FieldType.TEXT, "txt", 20, 30, 80, 8, label="Text"))
        tpl.add_field(FormField(FieldType.TEXTAREA, "area", 20, 50, 80, 25, label="Area"))
        tpl.add_field(FormField(FieldType.DATE, "dt", 20, 80, 40, 8, label="Date"))
        tpl.add_field(FormField(FieldType.CHECKBOX, "cb", 20, 100, 40, 8, label="Agree", default_value="yes"))
        tpl.add_field(FormField(FieldType.RADIO, "rad", 20, 120, 40, 8, label="Option 1", default_value="true"))
        tpl.add_field(FormField(FieldType.DROPDOWN, "drop", 20, 140, 60, 8, label="Select", options=["Opt1", "Opt2"], default_value="Opt1"))
        tpl.add_field(FormField(FieldType.SIGNATURE, "sig", 20, 160, 80, 20, label="Sign"))

        pdf_path = os.path.join(self.temp_dir.name, "all_types.pdf")
        success = self.builder.generate_pdf(tpl, pdf_path)
        self.assertTrue(success)

        doc = fitz.open(pdf_path)
        try:
            page = doc[0]
            widgets_by_name = {w.field_name: w for w in page.widgets()}

            # 7 interactive widgets (label excluded)
            self.assertEqual(len(widgets_by_name), 7)
            self.assertIn("txt", widgets_by_name)
            self.assertIn("area", widgets_by_name)
            self.assertIn("dt", widgets_by_name)
            self.assertIn("cb", widgets_by_name)
            self.assertIn("rad", widgets_by_name)
            self.assertIn("drop", widgets_by_name)
            self.assertIn("sig", widgets_by_name)

            # TEXTAREA should be multiline text
            self.assertEqual(widgets_by_name["area"].field_type, fitz.PDF_WIDGET_TYPE_TEXT)
            self.assertTrue(bool(widgets_by_name["area"].field_flags & getattr(fitz, "PDF_TX_FIELD_IS_MULTILINE", 4096)))

            # CHECKBOX should be checked ('Yes')
            self.assertEqual(widgets_by_name["cb"].field_type, fitz.PDF_WIDGET_TYPE_CHECKBOX)
            self.assertEqual(widgets_by_name["cb"].field_value, "Yes")

            # DROPDOWN should be ComboBox and have Opt1 selected
            self.assertEqual(widgets_by_name["drop"].field_type, getattr(fitz, "PDF_WIDGET_TYPE_COMBOBOX", 3))
            self.assertEqual(widgets_by_name["drop"].field_value, "Opt1")

            # SIGNATURE should be signature type
            self.assertEqual(widgets_by_name["sig"].field_type, getattr(fitz, "PDF_WIDGET_TYPE_SIGNATURE", 6))
        finally:
            doc.close()

    def test_contact_form_has_all_interactive_fields(self):
        """create_contact_form() must produce all 8 interactive widgets aligned with content."""
        tpl = create_contact_form()
        pdf_path = os.path.join(self.temp_dir.name, "contact.pdf")
        success = self.builder.generate_pdf(tpl, pdf_path, fill_data={
            "name": "Erika Mustermann",
            "message": "Erste Zeile\nZweite Zeile",
            "newsletter": "ja",
            "date": "08.09.2026",
            "subject": "Lob"
        })
        self.assertTrue(success)

        extracted = self.builder.extract_form_fields(pdf_path)
        names = {f["name"] for f in extracted}
        self.assertIn("name", names)
        self.assertIn("email", names)
        self.assertIn("phone", names)
        self.assertIn("subject", names)
        self.assertIn("message", names)
        self.assertIn("newsletter", names)
        self.assertIn("date", names)
        self.assertIn("signature", names)
        self.assertEqual(len(names), 8)

    def test_in_place_fill_form(self):
        """fill_form() must work when output_path is the same as pdf_path."""
        tpl = FormTemplate(name="InPlaceTest", page_size=(210, 297))
        tpl.add_field(FormField(FieldType.TEXT, "username", 20, 20, 80, 8))
        tpl.add_field(FormField(FieldType.CHECKBOX, "active", 20, 40, 20, 8))

        pdf_path = os.path.join(self.temp_dir.name, "inplace.pdf")
        self.builder.generate_pdf(tpl, pdf_path)

        # In-place fill
        ok = self.builder.fill_form(pdf_path, pdf_path, {"username": "Dr. Doku", "active": "true"})
        self.assertTrue(ok)

        # Verify updated values
        extracted = {f["name"]: f["value"] for f in self.builder.extract_form_fields(pdf_path)}
        self.assertEqual(extracted["username"], "Dr. Doku")
        self.assertEqual(extracted["active"], "Yes")

    def test_template_save_creates_parent_dir(self):
        """FormTemplate.save() creates missing parent directories."""
        tpl = create_registration_form()
        target = Path(self.temp_dir.name) / "sub" / "folder" / "reg.json"
        tpl.save(str(target))
        self.assertTrue(target.exists())

        loaded = FormTemplate.load(str(target))
        self.assertEqual(loaded.name, "Anmeldeformular")
        self.assertEqual(len(loaded.fields), len(tpl.fields))


if __name__ == "__main__":
    unittest.main()
