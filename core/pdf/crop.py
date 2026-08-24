#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kleine Utilitys zum Beschneiden von PDF-Seitenrändern."""

import shutil
import tempfile
from pathlib import Path

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


POINTS_PER_MM = 72.0 / 25.4


class PDFMarginCropper(LoggerMixin):
    """Beschneidet PDF-Seiten um einen festen Rand."""

    def crop_document_margins(self, doc, margin_mm: float = 5.0) -> bool:
        """Beschneidet alle Seiten eines offenen Dokuments per CropBox."""
        if not PYMUPDF_AVAILABLE or doc is None:
            return False

        margin_points = float(margin_mm) * POINTS_PER_MM
        if margin_points < 0:
            return False
        if margin_points == 0:
            return True

        target_rects = []
        for page in doc:
            rect = page.rect
            cropped = fitz.Rect(
                rect.x0 + margin_points,
                rect.y0 + margin_points,
                rect.x1 - margin_points,
                rect.y1 - margin_points,
            )
            if cropped.width <= 1 or cropped.height <= 1:
                self.logger.warning("Beschnitt zu groß für mindestens eine PDF-Seite")
                return False
            target_rects.append(cropped)

        for page, cropped in zip(doc, target_rects):
            page.set_cropbox(cropped)
        return True

    def crop_pdf_margins(self, pdf_path: str, output_path: str, margin_mm: float = 5.0) -> bool:
        """Beschneidet ein PDF auf Dateiebene."""
        if not PYMUPDF_AVAILABLE:
            return False

        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            if not self.crop_document_margins(doc, margin_mm=margin_mm):
                return False

            src = Path(pdf_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src == dst:
                with tempfile.NamedTemporaryFile(dir=dst.parent, prefix="dokuzen_crop_", suffix=".tmp", delete=False) as tmp:
                    temp_file = Path(tmp.name)
                doc.save(str(temp_file))
            else:
                doc.save(output_path)
            return True
        except Exception as exc:
            self.logger.error(f"PDF-Beschnitt fehlgeschlagen: {exc}")
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


def crop_document_margins(doc, margin_mm: float = 5.0) -> bool:
    """Beschneidet die Seitenränder eines offenen Dokuments."""
    return PDFMarginCropper().crop_document_margins(doc, margin_mm=margin_mm)


def crop_pdf_margins(pdf_path: str, output_path: str, margin_mm: float = 5.0) -> bool:
    """Beschneidet die Seitenränder eines PDFs."""
    return PDFMarginCropper().crop_pdf_margins(pdf_path, output_path, margin_mm=margin_mm)


__all__ = [
    "PDFMarginCropper",
    "POINTS_PER_MM",
    "crop_document_margins",
    "crop_pdf_margins",
]
