#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für den optionalen PDF-Beschnitt im DokuZen-Export."""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    temp_dir = tempfile.mkdtemp(prefix="dokuzen_crop_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture()
def multipage_pdf(tmp_dir) -> Path:
    pdf_path = tmp_dir / "multi.pdf"
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 120), "DokuZen Crop Test")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_crop_document_margins_reduces_visible_rect(multipage_pdf):
    from core.pdf.crop import POINTS_PER_MM, crop_document_margins

    doc = fitz.open(str(multipage_pdf))
    try:
        original_width = doc[0].rect.width
        original_height = doc[0].rect.height

        assert crop_document_margins(doc, margin_mm=5) is True

        expected_delta = 2 * 5 * POINTS_PER_MM
        assert doc.page_count == 2
        assert doc[0].rect.width == pytest.approx(original_width - expected_delta, abs=0.2)
        assert doc[0].rect.height == pytest.approx(original_height - expected_delta, abs=0.2)
    finally:
        doc.close()


def test_crop_document_margins_rejects_too_large_margin(tmp_dir):
    from core.pdf.crop import crop_document_margins

    pdf_path = tmp_dir / "tiny.pdf"
    doc = fitz.open()
    doc.new_page(width=50, height=50)
    doc.save(str(pdf_path))
    doc.close()

    doc = fitz.open(str(pdf_path))
    try:
        original_rect = fitz.Rect(doc[0].rect)
        assert crop_document_margins(doc, margin_mm=20) is False
        assert doc[0].rect == original_rect
    finally:
        doc.close()


def test_pdf_marker_dialog_offers_crop_option():
    source = (
        PROJECT_ROOT / "gui" / "dialogs" / "pdf_marker_dialog.py"
    ).read_text(encoding="utf-8")

    assert "Seitenränder beschneiden" in source
    assert "_crop_margin_mm" in source
    assert "crop_document_margins(new_doc" in source
