#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Watermark Engine
==================================
Fügt Text- und Bild-Wasserzeichen in PDF-Dokumente ein.
Unterstützt:
- Text-Wasserzeichen mit konfigurierbarer Rotation, Schriftgröße, Farbe und Deckkraft
- Vordefinierte Stempel (ENTWURF, VERTRAULICH, KOPIE, DRAFT, GEHEIM)
- Bild-Wasserzeichen (PNG mit Alpha/Transparenz, JPG)
- Flexible Positionierung (Zentriert, Ecken, Gekachelt/Wiederholend)
- Vordergrund- (über dem Text) und Hintergrund-Ebenen (unter dem Text)
- Selektive Seitenbereiche (alle, erste, gerade, ungerade, Bereichsausdrücke)
- Atomares Speichern und In-Place-Überschreiben
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from utils.logger import LoggerMixin

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz  # PyMuPDF legacy import name
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False


class WatermarkType(str, Enum):
    """Typ des Wasserzeichens."""
    TEXT = "text"
    IMAGE = "image"


class WatermarkPosition(str, Enum):
    """Position des Wasserzeichens auf der Seite."""
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"
    TILED = "tiled"


class WatermarkLayer(str, Enum):
    """Ebene des Wasserzeichens."""
    FOREGROUND = "foreground"
    BACKGROUND = "background"


# Standardfarb-Definitionen (RGB im Bereich 0.0 - 1.0)
NAMED_COLORS: Dict[str, Tuple[float, float, float]] = {
    "gray": (0.6, 0.6, 0.6),
    "lightgray": (0.75, 0.75, 0.75),
    "darkgray": (0.35, 0.35, 0.35),
    "red": (0.85, 0.15, 0.15),
    "blue": (0.15, 0.35, 0.85),
    "green": (0.15, 0.65, 0.25),
    "black": (0.0, 0.0, 0.0),
    "orange": (0.9, 0.5, 0.1),
}


def parse_color(color_val: Any) -> Tuple[float, float, float]:
    """Parst Farbdefinitionen (Name, Hex-String oder Tuple) in ein RGB-Float-Tuple (0.0..1.0)."""
    if isinstance(color_val, (tuple, list)) and len(color_val) >= 3:
        r, g, b = color_val[0], color_val[1], color_val[2]
        # Wenn Werte im Bereich 0..255 liegen, normalisieren
        if any(c > 1.0 for c in (r, g, b)):
            return (float(r) / 255.0, float(g) / 255.0, float(b) / 255.0)
        return (float(r), float(g), float(b))

    if isinstance(color_val, str):
        cleaned = color_val.strip().lower()
        if cleaned in NAMED_COLORS:
            return NAMED_COLORS[cleaned]
        if cleaned.startswith("#"):
            hex_str = cleaned.lstrip("#")
            if len(hex_str) == 6:
                try:
                    r = int(hex_str[0:2], 16) / 255.0
                    g = int(hex_str[2:4], 16) / 255.0
                    b = int(hex_str[4:6], 16) / 255.0
                    return (r, g, b)
                except ValueError:
                    pass

    return NAMED_COLORS["gray"]


@dataclass
class WatermarkOptions:
    """Konfiguration für das Anbringen von Wasserzeichen."""
    watermark_type: WatermarkType = WatermarkType.TEXT
    text: str = "ENTWURF"
    image_path: Optional[str] = None
    font_size: Optional[float] = 48.0  # None oder <= 0 für automatische Anpassung
    font_name: str = "helv"
    color: Tuple[float, float, float] = (0.7, 0.7, 0.7)
    opacity: float = 0.25  # 0.05 bis 1.0
    angle: float = 45.0  # Rotation in Grad (z. B. 45.0 für Diagonale)
    position: WatermarkPosition = WatermarkPosition.CENTER
    layer: WatermarkLayer = WatermarkLayer.FOREGROUND
    pages: str = "all"  # 'all', 'first', 'even', 'odd', oder Notation wie '1-3, 5'
    scale: float = 0.5  # Skalierung für Bild-Wasserzeichen (Anteil an Seitenbreite)
    tiled_step_x: float = 200.0
    tiled_step_y: float = 200.0


@dataclass
class WatermarkResult:
    """Ergebnis einer Wasserzeichen-Operation."""
    success: bool
    output_path: Optional[str] = None
    pages_watermarked: int = 0
    total_pages: int = 0
    error: Optional[str] = None


class PDFWatermarker(LoggerMixin):
    """
    Verwaltet das Anbringen von Wasserzeichen auf PDF-Dokumenten.
    """

    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF ist nicht verfügbar!")

    def resolve_target_pages(self, page_count: int, page_spec: str) -> List[int]:
        """
        Löst eine Seitenangabe in 0-basierte Seitenindizes auf.
        """
        if page_count <= 0:
            return []

        spec = (page_spec or "all").strip().lower()

        if spec in ("all", "alle"):
            return list(range(page_count))
        if spec in ("first", "erste", "1"):
            return [0]
        if spec in ("even", "gerade"):
            return [i for i in range(page_count) if (i + 1) % 2 == 0]
        if spec in ("odd", "ungerade"):
            return [i for i in range(page_count) if (i + 1) % 2 == 1]

        # Notation parsen (z. B. '1-3, 5')
        try:
            from core.pdf.page_ranges import parse_page_range_notation
            one_based = parse_page_range_notation(spec, page_count=page_count)
            return [p - 1 for p in one_based if 1 <= p <= page_count]
        except Exception as e:
            self.logger.warning("Fehler beim Parsen der Seiten-Notation '%s': %s", spec, e)
            return []

    def _apply_text_watermark_to_page(
        self,
        page: Any,
        options: WatermarkOptions,
    ) -> None:
        """Fügt ein Text-Wasserzeichen auf einer einzelnen fitz.Page ein."""
        text = options.text.strip()
        if not text:
            return

        rect = page.rect
        width = rect.width
        height = rect.height
        overlay = (options.layer == WatermarkLayer.FOREGROUND)
        fontname = options.font_name or "helv"
        color = options.color
        opacity = max(0.01, min(1.0, float(options.opacity)))

        # Schriftgröße bestimmen
        if options.font_size is not None and options.font_size > 0:
            fontsize = float(options.font_size)
        else:
            # Automatische Skalierung passend zur Seitenbreite
            approx_chars = max(len(text), 6)
            fontsize = max(18.0, min(120.0, (width * 1.2) / approx_chars))

        text_len = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)

        if options.position == WatermarkPosition.TILED:
            # Gekacheltes Wasserzeichen über die gesamte Seite
            step_x = max(80.0, float(options.tiled_step_x))
            step_y = max(80.0, float(options.tiled_step_y))
            tile_fontsize = max(10.0, min(36.0, fontsize * 0.4))
            tile_len = fitz.get_text_length(text, fontname=fontname, fontsize=tile_fontsize)

            y_pos = step_y * 0.5
            while y_pos < height:
                x_pos = step_x * 0.5
                while x_pos < width:
                    pt = fitz.Point(x_pos, y_pos)
                    orig = fitz.Point(pt.x - tile_len / 2, pt.y + tile_fontsize * 0.3)
                    morph = (pt, fitz.Matrix(options.angle))
                    page.insert_text(
                        orig,
                        text,
                        fontname=fontname,
                        fontsize=tile_fontsize,
                        morph=morph,
                        color=color,
                        fill_opacity=opacity,
                        overlay=overlay,
                    )
                    x_pos += step_x
                y_pos += step_y
            return

        # Feste Positionen berechnen
        pos = options.position
        if pos == WatermarkPosition.TOP_LEFT:
            center = fitz.Point(width * 0.25, height * 0.2)
        elif pos == WatermarkPosition.TOP_RIGHT:
            center = fitz.Point(width * 0.75, height * 0.2)
        elif pos == WatermarkPosition.BOTTOM_LEFT:
            center = fitz.Point(width * 0.25, height * 0.8)
        elif pos == WatermarkPosition.BOTTOM_RIGHT:
            center = fitz.Point(width * 0.75, height * 0.8)
        elif pos == WatermarkPosition.TOP_CENTER:
            center = fitz.Point(width * 0.5, height * 0.2)
        elif pos == WatermarkPosition.BOTTOM_CENTER:
            center = fitz.Point(width * 0.5, height * 0.8)
        else:  # CENTER
            center = fitz.Point(width * 0.5, height * 0.5)

        origin = fitz.Point(center.x - text_len / 2, center.y + fontsize * 0.3)
        morph = (center, fitz.Matrix(options.angle))

        page.insert_text(
            origin,
            text,
            fontname=fontname,
            fontsize=fontsize,
            morph=morph,
            color=color,
            fill_opacity=opacity,
            overlay=overlay,
        )

    def _apply_image_watermark_to_page(
        self,
        page: Any,
        options: WatermarkOptions,
    ) -> None:
        """Fügt ein Bild-Wasserzeichen auf einer einzelnen fitz.Page ein."""
        if not options.image_path or not os.path.exists(options.image_path):
            self.logger.warning("Bilddatei für Wasserzeichen nicht gefunden: %s", options.image_path)
            return

        rect = page.rect
        width = rect.width
        height = rect.height
        overlay = (options.layer == WatermarkLayer.FOREGROUND)
        scale = max(0.05, min(1.0, float(options.scale)))

        target_width = width * scale
        # Aspect-Ratio ermitteln
        img_w, img_h = 100.0, 100.0
        try:
            with fitz.open(options.image_path) as img_doc:
                if len(img_doc) > 0:
                    page_img = img_doc[0]
                    img_w, img_h = page_img.rect.width, page_img.rect.height
        except Exception:
            # Fallback über QImage oder PIL wenn fitz Bild nicht als Dokument öffnen kann
            try:
                from PIL import Image
                with Image.open(options.image_path) as im:
                    img_w, img_h = float(im.width), float(im.height)
            except Exception:
                img_w, img_h = 100.0, 100.0

        aspect = img_h / max(1.0, img_w)
        target_height = target_width * aspect

        # Höhe auf max 90% der Seitenhöhe begrenzen
        if target_height > height * 0.9:
            target_height = height * 0.9
            target_width = target_height / max(0.01, aspect)

        # Position berechnen
        pos = options.position
        if pos == WatermarkPosition.TOP_LEFT:
            x0 = width * 0.05
            y0 = height * 0.05
        elif pos == WatermarkPosition.TOP_RIGHT:
            x0 = width * 0.95 - target_width
            y0 = height * 0.05
        elif pos == WatermarkPosition.BOTTOM_LEFT:
            x0 = width * 0.05
            y0 = height * 0.95 - target_height
        elif pos == WatermarkPosition.BOTTOM_RIGHT:
            x0 = width * 0.95 - target_width
            y0 = height * 0.95 - target_height
        elif pos == WatermarkPosition.TOP_CENTER:
            x0 = (width - target_width) / 2
            y0 = height * 0.05
        elif pos == WatermarkPosition.BOTTOM_CENTER:
            x0 = (width - target_width) / 2
            y0 = height * 0.95 - target_height
        else:  # CENTER
            x0 = (width - target_width) / 2
            y0 = (height - target_height) / 2

        img_rect = fitz.Rect(x0, y0, x0 + target_width, y0 + target_height)
        page.insert_image(img_rect, filename=options.image_path, overlay=overlay)

    def apply_to_document(
        self,
        doc: Any,
        options: WatermarkOptions,
    ) -> int:
        """
        Wendet die Wasserzeichen-Optionen direkt auf ein geöffnetes fitz.Document an.
        Gibt die Anzahl der bearbeiteten Seiten zurück.
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.error("PyMuPDF ist nicht verfügbar.")
            return 0

        target_indices = self.resolve_target_pages(len(doc), options.pages)
        if not target_indices:
            self.logger.warning("Keine gültigen Zielseiten für Wasserzeichen gefunden.")
            return 0

        count = 0
        for idx in target_indices:
            page = doc[idx]
            if options.watermark_type == WatermarkType.IMAGE:
                self._apply_image_watermark_to_page(page, options)
            else:
                self._apply_text_watermark_to_page(page, options)
            count += 1

        return count

    def apply_to_pdf(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        options: Optional[WatermarkOptions] = None,
    ) -> WatermarkResult:
        """
        Bettet Wasserzeichen in eine PDF-Datei ein und speichert das Ergebnis atomar ab.
        """
        if not PYMUPDF_AVAILABLE:
            return WatermarkResult(
                success=False,
                error="PyMuPDF (fitz) ist nicht installiert.",
            )

        src = Path(input_path).resolve()
        dst = Path(output_path).resolve()

        if not src.exists():
            return WatermarkResult(
                success=False,
                output_path=str(dst),
                error=f"Eingabedatei nicht gefunden: {src}",
            )

        if not str(src).lower().endswith(".pdf"):
            return WatermarkResult(
                success=False,
                output_path=str(dst),
                error="Eingabedatei ist keine PDF-Datei.",
            )

        opts = options or WatermarkOptions()

        doc = None
        temp_file: Optional[Path] = None
        try:
            doc = fitz.open(str(src))
            total_pages = len(doc)
            if total_pages == 0:
                return WatermarkResult(
                    success=False,
                    output_path=str(dst),
                    error="Die PDF-Datei enthält keine Seiten.",
                )

            count = self.apply_to_document(doc, opts)
            if count == 0:
                return WatermarkResult(
                    success=False,
                    output_path=str(dst),
                    total_pages=total_pages,
                    error="Auf keiner Seite konnte ein Wasserzeichen angebracht werden (Seitenbereich ungültig).",
                )

            dst.parent.mkdir(parents=True, exist_ok=True)

            if src == dst:
                with tempfile.NamedTemporaryFile(
                    dir=dst.parent,
                    prefix="dokuzen_wm_",
                    suffix=".tmp",
                    delete=False,
                ) as tmp:
                    temp_file = Path(tmp.name)
                doc.save(str(temp_file))
            else:
                doc.save(str(dst))

            return WatermarkResult(
                success=True,
                output_path=str(dst),
                pages_watermarked=count,
                total_pages=total_pages,
            )

        except Exception as exc:
            self.logger.error("Fehler beim Anbringen des Wasserzeichens: %s", exc)
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return WatermarkResult(
                success=False,
                output_path=str(dst),
                error=f"Wasserzeichen-Verarbeitung fehlgeschlagen: {exc}",
            )
        finally:
            if doc is not None:
                doc.close()
            if temp_file and temp_file.exists():
                try:
                    shutil.move(str(temp_file), str(dst))
                except Exception:
                    pass


def add_watermark_to_document(doc: Any, **kwargs) -> int:
    """Funktions-Wrapper für geöffnete fitz-Dokumente."""
    options = WatermarkOptions(**kwargs) if kwargs else WatermarkOptions()
    return PDFWatermarker().apply_to_document(doc, options)


def add_watermark_to_pdf(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    **kwargs,
) -> WatermarkResult:
    """Funktions-Wrapper für PDF-Dateipfade."""
    options = WatermarkOptions(**kwargs) if kwargs else WatermarkOptions()
    return PDFWatermarker().apply_to_pdf(input_path, output_path, options)


__all__ = [
    "WatermarkType",
    "WatermarkPosition",
    "WatermarkLayer",
    "WatermarkOptions",
    "WatermarkResult",
    "PDFWatermarker",
    "add_watermark_to_document",
    "add_watermark_to_pdf",
    "parse_color",
    "NAMED_COLORS",
]
