#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für das PDF-Wasserzeichen-Modul (core/pdf/watermark.py) in DokuZen.

Validiert:
1. Text-Wasserzeichen mit verschiedenen Winkeln, Farben, Deckkräften und Schriftgrößen.
2. Bild-Wasserzeichen mit PNG-Transparenz und Skalierung.
3. Verschiedene Positionen (Center, Top-Left, Bottom-Right, Tiled/Gekachelt).
4. Vordergrund- vs. Hintergrund-Ebene.
5. Seitenbereichs-Filterung (all, first, even, odd, benutzerdefinierte Bereiche).
6. Sicheres In-Place-Überschreiben via atomarer temporärer Datei.
7. Fehlerbehandlung bei nicht existierenden oder ungültigen Eingabedateien.
"""

import os
from pathlib import Path
import pytest
from PIL import Image

import fitz

from core.pdf.watermark import (
    PDFWatermarker,
    WatermarkOptions,
    WatermarkType,
    WatermarkPosition,
    WatermarkLayer,
    WatermarkResult,
    add_watermark_to_document,
    add_watermark_to_pdf,
    parse_color,
)


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Erstellt ein Test-PDF mit 4 Seiten und Textinhalt."""
    pdf_path = tmp_path / "sample_multipage.pdf"
    doc = fitz.open()
    for i in range(4):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text(fitz.Point(100, 100), f"Seite {i + 1} Originaltext", fontsize=14)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_logo(tmp_path) -> Path:
    """Erstellt ein Test-PNG mit Transparenz (Alpha-Kanal)."""
    logo_path = tmp_path / "watermark_logo.png"
    img = Image.new("RGBA", (150, 150), (220, 20, 60, 140))
    img.save(str(logo_path))
    return logo_path


def test_parse_color():
    """Testet das Parsen von Farbnamen, Hex-Werten und RGB-Tuples."""
    assert parse_color("gray") == (0.6, 0.6, 0.6)
    assert parse_color("red") == (0.85, 0.15, 0.15)
    assert parse_color("blue") == (0.15, 0.35, 0.85)
    assert parse_color("#000000") == (0.0, 0.0, 0.0)
    assert parse_color("#ffffff") == (1.0, 1.0, 1.0)
    assert parse_color((0.2, 0.4, 0.6)) == (0.2, 0.4, 0.6)
    # Werte im 255-Bereich
    assert parse_color((255, 0, 0)) == (1.0, 0.0, 0.0)
    # Fallback bei ungültigen Eingaben
    assert parse_color("unknown_color") == (0.6, 0.6, 0.6)


def test_resolve_target_pages():
    """Testet die Auflösung von Seitenbereichen in 0-basierte Indizes."""
    wm = PDFWatermarker()
    assert wm.resolve_target_pages(4, "all") == [0, 1, 2, 3]
    assert wm.resolve_target_pages(4, "first") == [0]
    assert wm.resolve_target_pages(4, "even") == [1, 3]  # 2. und 4. Seite (0-basiert: 1, 3)
    assert wm.resolve_target_pages(4, "odd") == [0, 2]   # 1. und 3. Seite (0-basiert: 0, 2)
    assert wm.resolve_target_pages(4, "1, 3-4") == [0, 2, 3]
    assert wm.resolve_target_pages(4, "2-3") == [1, 2]
    assert wm.resolve_target_pages(0, "all") == []


def test_apply_text_watermark_default(sample_pdf, tmp_path):
    """Testet das Standard-Text-Wasserzeichen ('ENTWURF' diagonal auf allen Seiten)."""
    out_pdf = tmp_path / "watermarked_default.pdf"
    res = add_watermark_to_pdf(sample_pdf, out_pdf)

    assert res.success is True
    assert res.pages_watermarked == 4
    assert res.total_pages == 4
    assert out_pdf.exists()

    doc = fitz.open(str(out_pdf))
    assert len(doc) == 4
    for page in doc:
        text = page.get_text()
        assert "ENTWURF" in text
    doc.close()


def test_apply_text_watermark_custom_options(sample_pdf, tmp_path):
    """Testet benutzerdefinierten Text, Farbe, Winkel, Position und Ebene."""
    out_pdf = tmp_path / "watermarked_custom.pdf"
    opts = WatermarkOptions(
        text="VERTRAULICH",
        font_size=60.0,
        color=(0.9, 0.1, 0.1),
        opacity=0.35,
        angle=30.0,
        position=WatermarkPosition.CENTER,
        layer=WatermarkLayer.FOREGROUND,
        pages="first",
    )
    res = PDFWatermarker().apply_to_pdf(sample_pdf, out_pdf, opts)

    assert res.success is True
    assert res.pages_watermarked == 1

    doc = fitz.open(str(out_pdf))
    # Seite 1 hat das Wasserzeichen
    assert "VERTRAULICH" in doc[0].get_text()
    # Seite 2 hat es nicht
    assert "VERTRAULICH" not in doc[1].get_text()
    doc.close()


def test_apply_tiled_watermark(sample_pdf, tmp_path):
    """Testet gekachelte/wiederholende Wasserzeichen über die gesamte Seite."""
    out_pdf = tmp_path / "watermarked_tiled.pdf"
    opts = WatermarkOptions(
        text="KOPIE",
        position=WatermarkPosition.TILED,
        angle=45.0,
        pages="all",
    )
    res = PDFWatermarker().apply_to_pdf(sample_pdf, out_pdf, opts)

    assert res.success is True
    assert res.pages_watermarked == 4

    doc = fitz.open(str(out_pdf))
    # Da es gekachelt ist, muss 'KOPIE' mehrfach im Text der Seite vorkommen
    count_page0 = doc[0].get_text().count("KOPIE")
    assert count_page0 >= 4, f"Erwartete mindestens 4 Wiederholungen, gefunden: {count_page0}"
    doc.close()


def test_apply_image_watermark(sample_pdf, sample_logo, tmp_path):
    """Testet Bild-Wasserzeichen mit Skalierung."""
    out_pdf = tmp_path / "watermarked_image.pdf"
    opts = WatermarkOptions(
        watermark_type=WatermarkType.IMAGE,
        image_path=str(sample_logo),
        scale=0.4,
        position=WatermarkPosition.BOTTOM_RIGHT,
        pages="1-2",
    )
    res = PDFWatermarker().apply_to_pdf(sample_pdf, out_pdf, opts)

    assert res.success is True
    assert res.pages_watermarked == 2

    doc = fitz.open(str(out_pdf))
    # Seite 0 und 1 haben Bilder
    assert len(doc[0].get_images()) >= 1
    assert len(doc[1].get_images()) >= 1
    # Seite 2 und 3 haben keine neuen Bilder
    assert len(doc[2].get_images()) == 0
    doc.close()


def test_apply_watermark_in_place(sample_pdf):
    """Testet das In-Place-Schreiben in dieselbe Quelldatei."""
    opts = WatermarkOptions(text="INPLACE_CHECK", pages="1")
    res = PDFWatermarker().apply_to_pdf(sample_pdf, sample_pdf, opts)

    assert res.success is True
    assert res.pages_watermarked == 1

    doc = fitz.open(str(sample_pdf))
    assert "INPLACE_CHECK" in doc[0].get_text()
    doc.close()


def test_apply_watermark_error_handling(tmp_path):
    """Testet Fehlerbehandlung bei fehlenden Dateien und ungültigen Formaten."""
    wm = PDFWatermarker()

    # Nicht existierende Datei
    res_missing = wm.apply_to_pdf(tmp_path / "non_existent.pdf", tmp_path / "out.pdf")
    assert res_missing.success is False
    assert "nicht gefunden" in (res_missing.error or "")

    # Keine PDF-Datei
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("Hello", encoding="utf-8")
    res_txt = wm.apply_to_pdf(txt_file, tmp_path / "out.pdf")
    assert res_txt.success is False
    assert "keine PDF-Datei" in (res_txt.error or "")


def test_add_watermark_to_document_helper():
    """Testet den add_watermark_to_document Funktions-Wrapper auf geöffnetem fitz-Dokument."""
    doc = fitz.open()
    doc.new_page()
    doc.new_page()

    count = add_watermark_to_document(doc, text="DIRECT_DOC", pages="all")
    assert count == 2
    assert "DIRECT_DOC" in doc[0].get_text()
    assert "DIRECT_DOC" in doc[1].get_text()
    doc.close()
