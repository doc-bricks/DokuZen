#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für optionale Seitenzahlen im DokuZen-PDF-Export."""

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
    temp_dir = tempfile.mkdtemp(prefix="dokuzen_page_numbers_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture()
def multipage_pdf(tmp_dir) -> Path:
    pdf_path = tmp_dir / "multi.pdf"
    doc = fitz.open()
    for _ in range(3):
        doc.new_page(width=595, height=842)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _page_texts(pdf_path: Path):
    doc = fitz.open(str(pdf_path))
    try:
        return [page.get_text() for page in doc]
    finally:
        doc.close()


def test_add_page_numbers_writes_page_labels(multipage_pdf, tmp_dir):
    from core.pdf.page_numbers import add_page_numbers

    output = tmp_dir / "numbered.pdf"
    assert add_page_numbers(str(multipage_pdf), str(output)) is True

    texts = _page_texts(output)
    assert "Seite 1 / 3" in texts[0]
    assert "Seite 2 / 3" in texts[1]
    assert "Seite 3 / 3" in texts[2]


def test_add_page_numbers_to_document_keeps_page_count(multipage_pdf):
    from core.pdf.page_numbers import add_page_numbers_to_document

    doc = fitz.open(str(multipage_pdf))
    try:
        assert add_page_numbers_to_document(doc) is True
        assert doc.page_count == 3
    finally:
        doc.close()


def test_pdf_marker_dialog_offers_page_number_export_option():
    source = (
        PROJECT_ROOT / "gui" / "dialogs" / "pdf_marker_dialog.py"
    ).read_text(encoding="utf-8")

    assert "Seitenzahlen einfügen" in source
    assert "add_page_numbers_to_document(new_doc)" in source
