#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFMerger.rotate_pages und In-Place- sowie Verzeichnis-Operationen.
"""

import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pdf.merger import PDFMerger, MergeItem, PYMUPDF_AVAILABLE

if not PYMUPDF_AVAILABLE:
    pytest.skip("PyMuPDF nicht verfügbar", allow_module_level=True)

import fitz


def _create_sample_pdf(path: Path, page_count: int = 2) -> None:
    doc = fitz.open()
    for i in range(page_count):
        p = doc.new_page(width=595, height=842)
        p.insert_text((50, 50), f"Page {i + 1}")
    doc.save(str(path))
    doc.close()


def test_rotate_pages_in_place_all_pages():
    """In-Place-Rotation (input_path == output_path) schlägt nicht mehr mit 'save to original must be incremental' fehl."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "sample.pdf"
        _create_sample_pdf(pdf_path, 2)

        merger = PDFMerger()
        res = merger.rotate_pages(str(pdf_path), str(pdf_path), 90)
        assert res.success is True
        assert res.page_count == 2
        assert res.error is None

        # Verifiziere Rotation auf Platte
        doc = fitz.open(str(pdf_path))
        assert doc.page_count == 2
        assert doc[0].rotation == 90
        assert doc[1].rotation == 90
        doc.close()

        # Zweite In-Place-Rotation (90 + 90 = 180 Grad)
        res2 = merger.rotate_pages(str(pdf_path), str(pdf_path), 90)
        assert res2.success is True
        doc2 = fitz.open(str(pdf_path))
        assert doc2[0].rotation == 180
        assert doc2[1].rotation == 180
        doc2.close()


def test_rotate_pages_in_place_subset():
    """In-Place-Rotation für eine Einzelseite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "sample.pdf"
        _create_sample_pdf(pdf_path, 2)

        merger = PDFMerger()
        # Nur Seite 1 (1-basiert) rotieren
        res = merger.rotate_pages(str(pdf_path), str(pdf_path), 90, pages=[1])
        assert res.success is True

        doc = fitz.open(str(pdf_path))
        assert doc[0].rotation == 90
        assert doc[1].rotation == 0
        doc.close()


def test_rotate_pages_creates_parent_directory():
    """rotate_pages erstellt Zielverzeichnisse automatisch, wenn sie nicht existieren."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "sample.pdf"
        _create_sample_pdf(input_path, 1)

        output_path = Path(tmpdir) / "sub" / "nested" / "rotated.pdf"
        assert not output_path.parent.exists()

        merger = PDFMerger()
        res = merger.rotate_pages(str(input_path), str(output_path), 90)
        assert res.success is True
        assert output_path.exists()

        doc = fitz.open(str(output_path))
        assert doc[0].rotation == 90
        doc.close()


def test_merge_creates_parent_directory():
    """merge / merge_files erstellt Zielverzeichnisse automatisch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "sample.pdf"
        _create_sample_pdf(input_path, 1)

        output_path = Path(tmpdir) / "merged_dir" / "out.pdf"
        assert not output_path.parent.exists()

        merger = PDFMerger()
        res = merger.merge_files([str(input_path)], str(output_path))
        assert res.success is True
        assert output_path.exists()

        doc = fitz.open(str(output_path))
        assert doc.page_count == 1
        doc.close()
