#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: PDF-Marker darf keine leeren Export-PDFs speichern."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog, PageThumbnail


class _UncheckedBox:
    def isChecked(self):
        return False


def _make_pdf(path: Path, page_count: int = 2) -> None:
    doc = fitz.open()
    try:
        for index in range(page_count):
            page = doc.new_page()
            page.insert_text((72, 72), f"Seite {index + 1}")
        doc.save(path)
    finally:
        doc.close()


def test_delete_all_pages_warns_before_empty_pdf_save(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    _make_pdf(input_pdf, page_count=2)

    dialog = PDFMarkerDialog.__new__(PDFMarkerDialog)
    dialog._pdf_path = str(input_pdf)
    dialog._page_count = 2
    dialog._thumbnails = [PageThumbnail(0), PageThumbnail(1)]
    dialog._crop_pages = _UncheckedBox()
    dialog._add_page_numbers = _UncheckedBox()
    for thumbnail in dialog._thumbnails:
        thumbnail.set_marker("d")

    messages = []
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output_pdf), "PDF-Dateien (*.pdf)"),
    )
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: messages.append(("warning", args[2])),
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args: messages.append(("critical", args[2])),
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args: messages.append(("information", args[2])),
    )

    dialog._delete_marked()

    assert ("warning", "Es muss mindestens eine Seite im Export verbleiben.") in messages
    assert not any(kind == "critical" for kind, _message in messages)
    assert not output_pdf.exists()
