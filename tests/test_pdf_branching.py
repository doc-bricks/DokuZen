#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Tests for PDF Branching & Marker Persistence
"""

import json
from pathlib import Path
import pytest
import fitz

from core.pdf.branching import (
    generate_branch_path,
    split_at_page,
    merge_branches,
    merge_with_branch,
    save_marker_file,
    load_marker_file,
)


@pytest.fixture
def sample_pdf(tmp_path):
    """Erstellt eine Test-PDF-Datei mit 5 Seiten."""
    pdf_path = tmp_path / "test_doc.pdf"
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f"Seite {i + 1}", fontsize=20)
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_generate_branch_path(tmp_path):
    orig = tmp_path / "doc.pdf"
    orig.touch()

    p1 = generate_branch_path(str(orig), "branch_auszug")
    assert p1.endswith("doc_branch_auszug.pdf")

    # Create the file so counter collision occurs
    Path(p1).touch()
    p2 = generate_branch_path(str(orig), "branch_auszug")
    assert p2.endswith("doc_branch_auszug_1.pdf")


def test_split_at_page(sample_pdf):
    part1, part2 = split_at_page(sample_pdf, 2)

    assert Path(part1).exists()
    assert Path(part2).exists()

    doc1 = fitz.open(part1)
    doc2 = fitz.open(part2)
    doc_orig = fitz.open(sample_pdf)

    assert len(doc1) == 2
    assert len(doc2) == 3
    assert len(doc_orig) == 5

    doc1.close()
    doc2.close()
    doc_orig.close()


def test_split_at_page_invalid(sample_pdf):
    with pytest.raises(ValueError):
        split_at_page(sample_pdf, 0)

    with pytest.raises(ValueError):
        split_at_page(sample_pdf, 5)


def test_merge_branches(sample_pdf, tmp_path):
    out_pdf = str(tmp_path / "merged_branch.pdf")
    items = [
        (sample_pdf, [1, 3]),
        (sample_pdf, [5]),
    ]

    success = merge_branches(items, out_pdf)
    assert success
    assert Path(out_pdf).exists()

    doc = fitz.open(out_pdf)
    assert len(doc) == 3
    doc.close()


def test_merge_branches_with_crop_and_numbers(sample_pdf, tmp_path):
    out_pdf = str(tmp_path / "merged_styled.pdf")
    items = [
        (sample_pdf, [1, 2]),
    ]
    success = merge_branches(
        items,
        out_pdf,
        crop_margin_mm=5.0,
        add_page_numbers=True,
    )
    assert success
    assert Path(out_pdf).exists()
    doc = fitz.open(out_pdf)
    assert len(doc) == 2
    # Check that text was inserted on page (e.g. Seite 1 / 2)
    page_text = doc[0].get_text()
    assert "Seite 1 / 2" in page_text
    doc.close()


def test_merge_with_branch_helper(sample_pdf, tmp_path):
    out_pdf = str(tmp_path / "helper_merged.pdf")
    success = merge_with_branch(
        sample_pdf,
        [sample_pdf],
        out_pdf,
        main_pages=[1],
    )
    assert success
    assert Path(out_pdf).exists()
    doc = fitz.open(out_pdf)
    assert len(doc) == 6  # 1 page from main + 5 from branch
    doc.close()


def test_save_and_load_marker_file(sample_pdf, tmp_path):
    markers = {0: 'm', 2: 'd', 4: 'k'}
    marker_path = save_marker_file(sample_pdf, markers)

    assert Path(marker_path).exists()
    loaded = load_marker_file(marker_path)

    assert loaded == {0: 'm', 2: 'd', 4: 'k'}


def test_pdf_marker_dialog_buttons(sample_pdf):
    from PySide6.QtWidgets import QApplication
    from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog

    app = QApplication.instance() or QApplication([])
    dialog = PDFMarkerDialog(pdf_path=sample_pdf)

    assert hasattr(dialog, "_split_at_selected_page")
    assert hasattr(dialog, "_merge_branches")
    assert hasattr(dialog, "_save_markers_file")
    assert hasattr(dialog, "_load_markers_file")

    dialog.close()


def test_pdf_marker_dialog_merge_flow(sample_pdf, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog

    app = QApplication.instance() or QApplication([])
    dialog = PDFMarkerDialog(pdf_path=sample_pdf)

    merged_target = tmp_path / "dialog_merged.pdf"

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([sample_pdf], "PDF-Dateien (*.pdf)"),
    )
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(merged_target), "PDF-Dateien (*.pdf)"),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    dialog._merge_branches()
    assert merged_target.exists()
    doc = fitz.open(str(merged_target))
    assert len(doc) == 10  # 5 from main + 5 from branch
    doc.close()

    dialog.close()


def test_pdf_marker_dialog_merge_no_doc_warns(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog

    app = QApplication.instance() or QApplication([])
    dialog = PDFMarkerDialog(pdf_path=None)

    warned = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: warned.append(args[2]),
    )

    dialog._merge_branches()
    assert "Bitte zuerst ein Dokument laden." in warned
    dialog.close()
