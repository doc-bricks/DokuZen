#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrations- und Regressionstests für PDFAnnotator, PDFMarginCropper,
PDFPageNumberer und RedactionApplier.

Prüft:
- Auflösung und Einbetten aller vordefinierten StampType-Werte ohne FileNotFoundError
- Auflösung von Strings und Integer-IDs als Stempel
- In-Place-Bearbeitung (pdf_path == output_path) für alle Annotationsmethoden
- In-Place-Bearbeitung für PDFMarginCropper, PDFPageNumberer und RedactionApplier
"""

import shutil
import tempfile
from pathlib import Path

import pytest

try:
    import pymupdf as fitz
    FITZ_AVAILABLE = True
except ImportError:
    try:
        import fitz
        FITZ_AVAILABLE = True
    except ImportError:
        FITZ_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not FITZ_AVAILABLE,
    reason="PyMuPDF (fitz) nicht installiert",
)


@pytest.fixture()
def tmp_dir():
    """Temporäres Verzeichnis für Tests."""
    d = tempfile.mkdtemp(prefix="dokuzen_annot_real_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def test_pdf(tmp_dir) -> Path:
    """Erzeugt ein minimales PDF mit 2 Seiten und Text."""
    pdf_path = tmp_dir / "annot_test.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 100), "DokuZen Test Dokument Seite 1 - Vertraulich")
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 100), "DokuZen Test Dokument Seite 2")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestPDFAnnotatorStamps:
    """Verifiziert das fehlerfreie Hinzufügen von Stempeln."""

    @pytest.mark.parametrize("stamp_type", [
        "APPROVED",
        "EXPERIMENTAL",
        "NOT_APPROVED",
        "AS_IS",
        "EXPIRED",
        "NOT_FOR_PUBLIC",
        "CONFIDENTIAL",
        "FINAL",
        "SOLD",
        "DRAFT",
        "FOR_COMMENT",
        "TOP_SECRET",
    ])
    def test_add_all_stamp_types_enum(self, test_pdf, tmp_dir, stamp_type):
        from core.pdf.annotations import PDFAnnotator, StampType, AnnotationType

        annotator = PDFAnnotator()
        out = tmp_dir / f"stamp_{stamp_type.lower()}.pdf"
        enum_val = getattr(StampType, stamp_type)

        ok = annotator.add_stamp(
            pdf_path=str(test_pdf),
            output_path=str(out),
            page_index=0,
            rect=(100, 100, 300, 180),
            stamp_type=enum_val,
        )

        assert ok is True
        assert out.is_file()

        annots = annotator.get_annotations(str(out))
        assert len(annots) == 1
        assert annots[0].type == AnnotationType.STAMP
        assert annots[0].page_index == 0

    def test_add_stamp_with_int_id(self, test_pdf, tmp_dir):
        from core.pdf.annotations import PDFAnnotator, AnnotationType

        annotator = PDFAnnotator()
        out = tmp_dir / "stamp_int.pdf"

        ok = annotator.add_stamp(
            pdf_path=str(test_pdf),
            output_path=str(out),
            page_index=0,
            rect=(100, 100, 300, 180),
            stamp_type=0,  # STAMP_Approved
        )

        assert ok is True
        assert out.is_file()
        annots = annotator.get_annotations(str(out))
        assert len(annots) == 1
        assert annots[0].type == AnnotationType.STAMP

    def test_add_stamp_with_string_name(self, test_pdf, tmp_dir):
        from core.pdf.annotations import PDFAnnotator, AnnotationType

        annotator = PDFAnnotator()
        out = tmp_dir / "stamp_str.pdf"

        ok = annotator.add_stamp(
            pdf_path=str(test_pdf),
            output_path=str(out),
            page_index=0,
            rect=(100, 100, 300, 180),
            stamp_type="Confidential",
        )

        assert ok is True
        assert out.is_file()
        annots = annotator.get_annotations(str(out))
        assert len(annots) == 1
        assert annots[0].type == AnnotationType.STAMP


class TestPDFAnnotatorInPlace:
    """Verifiziert In-Place-Operationen auf PDFAnnotator."""

    def test_add_highlight_in_place(self, test_pdf):
        from core.pdf.annotations import PDFAnnotator, AnnotationColor, AnnotationType

        annotator = PDFAnnotator()
        ok = annotator.add_highlight(
            pdf_path=str(test_pdf),
            output_path=str(test_pdf),
            page_index=0,
            rect=(50, 90, 200, 110),
            color=AnnotationColor.yellow(),
            content="Wichtiger Hinweis",
        )

        assert ok is True
        annots = annotator.get_annotations(str(test_pdf))
        assert len(annots) == 1
        assert annots[0].type == AnnotationType.HIGHLIGHT
        assert annots[0].content == "Wichtiger Hinweis"

    def test_add_stamp_in_place(self, test_pdf):
        from core.pdf.annotations import PDFAnnotator, StampType, AnnotationType

        annotator = PDFAnnotator()
        ok = annotator.add_stamp(
            pdf_path=str(test_pdf),
            output_path=str(test_pdf),
            page_index=0,
            rect=(100, 100, 300, 180),
            stamp_type=StampType.APPROVED,
        )

        assert ok is True
        annots = annotator.get_annotations(str(test_pdf))
        assert len(annots) == 1
        assert annots[0].type == AnnotationType.STAMP

    def test_chained_in_place_annotations_and_removal(self, test_pdf):
        from core.pdf.annotations import PDFAnnotator, StampType, AnnotationColor, AnnotationType

        annotator = PDFAnnotator()

        # 1. Text Note
        assert annotator.add_text_note(str(test_pdf), str(test_pdf), 0, (50, 50), "Notiz", "Tester")
        # 2. Rect
        assert annotator.add_rect(str(test_pdf), str(test_pdf), 0, (60, 60, 120, 120))
        # 3. Circle
        assert annotator.add_circle(str(test_pdf), str(test_pdf), 0, (70, 70, 130, 130))
        # 4. Stamp
        assert annotator.add_stamp(str(test_pdf), str(test_pdf), 0, (100, 100, 300, 180), StampType.FINAL)

        annots = annotator.get_annotations(str(test_pdf))
        assert len(annots) == 4

        # Remove single annotation in place
        assert annotator.remove_annotation(str(test_pdf), str(test_pdf), 0, 0)
        annots_after = annotator.get_annotations(str(test_pdf))
        assert len(annots_after) == 3

        # Remove all annotations in place
        assert annotator.remove_all_annotations(str(test_pdf), str(test_pdf))
        annots_final = annotator.get_annotations(str(test_pdf))
        assert len(annots_final) == 0


class TestOtherModulesInPlace:
    """Verifiziert In-Place-Operationen in MarginCropper, PageNumberer und Redaction."""

    def test_crop_margins_in_place(self, test_pdf):
        from core.pdf.crop import PDFMarginCropper

        cropper = PDFMarginCropper()
        ok = cropper.crop_pdf_margins(str(test_pdf), str(test_pdf), margin_mm=2.0)
        assert ok is True
        assert test_pdf.is_file()

        doc = fitz.open(str(test_pdf))
        p = doc[0]
        assert p.rect.width < 595
        doc.close()

    def test_add_page_numbers_in_place(self, test_pdf):
        from core.pdf.page_numbers import PDFPageNumberer

        numberer = PDFPageNumberer()
        ok = numberer.add_to_pdf(str(test_pdf), str(test_pdf), pattern="Test Seite {page}/{total}")
        assert ok is True
        assert test_pdf.is_file()

        doc = fitz.open(str(test_pdf))
        txt = doc[0].get_text()
        assert "Test Seite 1/2" in txt
        doc.close()

    def test_redact_pdf_in_place(self, test_pdf):
        from core.redaction.detector import redact_pdf

        ok = redact_pdf(str(test_pdf), str(test_pdf))
        assert ok is True
        assert test_pdf.is_file()

        doc = fitz.open(str(test_pdf))
        assert doc.page_count == 2
        doc.close()
