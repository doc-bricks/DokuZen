#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Page Numbers
==============================
Fügt exportierten PDFs optionale Seitenzahlen hinzu.
"""

import shutil
import tempfile
from pathlib import Path

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PDFPageNumberer(LoggerMixin):
    """Fügt Seitenzahlen in PDFs ein."""

    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht verfügbar")

    def add_to_document(
        self,
        doc,
        pattern: str = "Seite {page} / {total}",
        font_size: float = 10.0,
        margin_bottom: float = 18.0,
        text_height: float = 18.0,
        color=(0.25, 0.25, 0.25),
    ) -> bool:
        """Fügt Seitenzahlen direkt in ein geöffnetes fitz-Dokument ein."""
        if not PYMUPDF_AVAILABLE:
            return False

        try:
            total_pages = len(doc)
            for page_index, page in enumerate(doc):
                label = pattern.format(page=page_index + 1, total=total_pages)
                rect = fitz.Rect(
                    36.0,
                    page.rect.height - margin_bottom - text_height,
                    page.rect.width - 36.0,
                    page.rect.height - margin_bottom,
                )
                page.insert_textbox(
                    rect,
                    label,
                    fontsize=font_size,
                    color=color,
                    align=fitz.TEXT_ALIGN_CENTER,
                )
            return True
        except Exception as exc:
            self.logger.error(f"Seitenzahlen-Fehler: {exc}")
            return False

    def add_to_pdf(
        self,
        pdf_path: str,
        output_path: str,
        pattern: str = "Seite {page} / {total}",
        font_size: float = 10.0,
        margin_bottom: float = 18.0,
    ) -> bool:
        """Fügt Seitenzahlen zu einer PDF hinzu und speichert sie neu."""
        if not PYMUPDF_AVAILABLE:
            return False

        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            ok = self.add_to_document(
                doc,
                pattern=pattern,
                font_size=font_size,
                margin_bottom=margin_bottom,
            )
            if not ok:
                return False

            src = Path(pdf_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src == dst:
                with tempfile.NamedTemporaryFile(dir=dst.parent, prefix="dokuzen_num_", suffix=".tmp", delete=False) as tmp:
                    temp_file = Path(tmp.name)
                doc.save(str(temp_file))
            else:
                doc.save(str(dst))
            return True
        except Exception as exc:
            self.logger.error(f"PDF-Seitenzahlen-Fehler: {exc}")
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return False
        finally:
            if doc is not None:
                doc.close()
            if temp_file and temp_file.exists():
                try:
                    shutil.move(str(temp_file), str(Path(output_path).resolve()))
                except Exception:
                    pass


def add_page_numbers_to_document(doc, **kwargs) -> bool:
    """Bequemer Funktions-Wrapper für geöffnete Dokumente."""
    return PDFPageNumberer().add_to_document(doc, **kwargs)


def add_page_numbers(pdf_path: str, output_path: str, **kwargs) -> bool:
    """Bequemer Funktions-Wrapper für Dateipfade."""
    return PDFPageNumberer().add_to_pdf(pdf_path, output_path, **kwargs)


__all__ = [
    "PDFPageNumberer",
    "add_page_numbers",
    "add_page_numbers_to_document",
]
