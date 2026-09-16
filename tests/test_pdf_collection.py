#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Tests for Collection / Binder PDF Exporter
========================================================
Testet das Kernmodul core/pdf/collection.py.
"""

from pathlib import Path
import pytest

import fitz  # PyMuPDF
from PIL import Image

from core.pdf.collection import (
    CollectionExporter,
    CollectionExportOptions,
    CollectionExportResult,
    export_collection_pdf,
)


@pytest.fixture
def make_pdf(tmp_path):
    """Erzeugt eine Test-PDF mit angegebener Seitenzahl."""
    def _creator(name: str, pages: int = 2) -> str:
        p = tmp_path / name
        doc = fitz.open()
        for i in range(pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 100), f"Dokument: {name} - Seite {i + 1}", fontsize=18)
        doc.save(str(p))
        doc.close()
        return str(p)
    return _creator


@pytest.fixture
def make_image(tmp_path):
    """Erzeugt ein einfaches Testbild."""
    def _creator(name: str, width: int = 300, height: int = 200) -> str:
        p = tmp_path / name
        img = Image.new("RGB", (width, height), color=(73, 109, 137))
        img.save(str(p))
        return str(p)
    return _creator


@pytest.fixture
def make_text(tmp_path):
    """Erzeugt eine Textdatei."""
    def _creator(name: str, lines: int = 30) -> str:
        p = tmp_path / name
        content = "\n".join([f"Zeile {i + 1}: Dies ist Testinhalt fuer {name}" for i in range(lines)])
        p.write_text(content, encoding="utf-8")
        return str(p)
    return _creator


def test_export_collection_single_pdf(tmp_path, make_pdf):
    pdf1 = make_pdf("bericht_a.pdf", pages=3)
    out_pdf = tmp_path / "sammel_1.pdf"

    res = export_collection_pdf([pdf1], out_pdf)

    assert res.success is True
    assert res.total_pages == 3
    assert res.document_count == 1
    assert Path(out_pdf).exists()

    doc = fitz.open(str(out_pdf))
    assert len(doc) == 3
    toc = doc.get_toc()
    assert len(toc) == 1
    assert toc[0][1] == "bericht a"
    assert toc[0][2] == 1
    doc.close()


def test_export_collection_multiple_pdfs_with_bookmarks(tmp_path, make_pdf):
    pdf1 = make_pdf("kapitel_1.pdf", pages=2)
    pdf2 = make_pdf("kapitel_2.pdf", pages=3)
    out_pdf = tmp_path / "sammel_multi.pdf"

    res = export_collection_pdf([pdf1, pdf2], out_pdf)

    assert res.success is True
    assert res.total_pages == 5
    assert res.document_count == 2

    doc = fitz.open(str(out_pdf))
    assert len(doc) == 5
    toc = doc.get_toc()
    assert len(toc) == 2
    assert toc[0][1] == "kapitel 1"
    assert toc[0][2] == 1  # startet auf Seite 1
    assert toc[1][1] == "kapitel 2"
    assert toc[1][2] == 3  # startet auf Seite 3 (nach 2 Seiten von pdf1)
    doc.close()


def test_export_collection_mixed_formats(tmp_path, make_pdf, make_image, make_text):
    pdf_file = make_pdf("dokument.pdf", pages=2)
    img_file = make_image("diagramm.png", width=400, height=300)
    txt_file = make_text("notizen.txt", lines=15)
    out_pdf = tmp_path / "sammel_gemischt.pdf"

    res = export_collection_pdf([pdf_file, img_file, txt_file], out_pdf)

    assert res.success is True
    assert res.document_count == 3
    assert res.total_pages >= 4  # 2 PDF + 1 Bild + min. 1 Text
    assert len(res.skipped_files) == 0

    doc = fitz.open(str(out_pdf))
    assert len(doc) == res.total_pages
    toc = doc.get_toc()
    assert len(toc) == 3
    doc.close()


def test_export_collection_with_page_numbers(tmp_path, make_pdf):
    pdf1 = make_pdf("doc1.pdf", pages=2)
    pdf2 = make_pdf("doc2.pdf", pages=2)
    out_pdf = tmp_path / "sammel_numbered.pdf"

    opts = CollectionExportOptions(
        add_page_numbers=True,
        page_number_pattern="Seite {page} / {total}",
    )
    res = export_collection_pdf([pdf1, pdf2], out_pdf, options=opts)

    assert res.success is True
    assert res.total_pages == 4

    doc = fitz.open(str(out_pdf))
    assert len(doc) == 4
    # Prüfe, ob Seitenzahlen eingefügt wurden
    for i, page in enumerate(doc):
        text = page.get_text()
        assert f"Seite {i + 1} / 4" in text
    doc.close()


def test_export_collection_empty_documents_error(tmp_path):
    out_pdf = tmp_path / "empty.pdf"
    res = export_collection_pdf([], out_pdf)

    assert res.success is False
    assert "Keine Dokumente" in (res.error or "")
    assert not out_pdf.exists()


def test_export_collection_missing_file_handling(tmp_path, make_pdf):
    valid_pdf = make_pdf("real.pdf", pages=1)
    fake_pdf = tmp_path / "non_existent.pdf"
    out_pdf = tmp_path / "partial.pdf"

    res = export_collection_pdf([str(fake_pdf), valid_pdf], out_pdf)

    assert res.success is True
    assert res.document_count == 1
    assert res.total_pages == 1
    assert str(fake_pdf) in res.skipped_files
    assert out_pdf.exists()


def test_export_collection_all_files_missing(tmp_path):
    fake1 = tmp_path / "fake1.pdf"
    fake2 = tmp_path / "fake2.pdf"
    out_pdf = tmp_path / "fail.pdf"

    res = export_collection_pdf([str(fake1), str(fake2)], out_pdf)

    assert res.success is False
    assert not out_pdf.exists()


def test_dialog_reorder_and_filter(make_pdf):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from gui.dialogs.collection_export_dialog import CollectionExportDialog

    _ = QApplication.instance() or QApplication([])

    pdf1 = make_pdf("alpha.pdf", pages=1)
    pdf2 = make_pdf("beta.pdf", pages=1)

    dialog = CollectionExportDialog(None, initial_documents=[pdf1, pdf2])
    assert dialog._list_widget.count() == 2

    # Zweites Item auswählen und nach oben schieben
    dialog._list_widget.setCurrentRow(1)
    dialog._move_up()

    first_data = dialog._list_widget.item(0).data(Qt.ItemDataRole.UserRole)
    second_data = dialog._list_widget.item(1).data(Qt.ItemDataRole.UserRole)
    assert first_data == str(Path(pdf2).resolve())
    assert second_data == str(Path(pdf1).resolve())

    # Erstes Item abwählen
    dialog._list_widget.item(0).setCheckState(Qt.CheckState.Unchecked)
    checked = dialog._get_checked_paths()
    assert len(checked) == 1
    assert checked[0] == str(Path(pdf1).resolve())

    dialog.close()


def test_dialog_export_execution(monkeypatch, tmp_path, make_pdf):
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from gui.dialogs.collection_export_dialog import CollectionExportDialog

    _ = QApplication.instance() or QApplication([])

    p1 = make_pdf("part1.pdf", pages=2)
    p2 = make_pdf("part2.pdf", pages=2)
    out_target = tmp_path / "gui_sammel.pdf"

    dialog = CollectionExportDialog(None, initial_documents=[p1, p2], current_theme="Projekt")

    # Mocke Dateidialog und Nachfrage zum Öffnen
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(out_target), "PDF-Dateien (*.pdf)"),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    dialog._on_export()

    assert out_target.exists()
    assert dialog.exported_file == str(out_target)

    doc = fitz.open(str(out_target))
    assert len(doc) == 4
    toc = doc.get_toc()
    assert len(toc) == 2
    doc.close()
    dialog.close()
