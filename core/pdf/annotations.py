#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Annotations
==================================
Marker, Kommentare, Notizen und Stempel für PDFs.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class AnnotationType(Enum):
    """Typen von Annotationen."""
    HIGHLIGHT = "highlight"       # Text-Marker (gelb)
    UNDERLINE = "underline"       # Unterstreichung
    STRIKEOUT = "strikeout"       # Durchgestrichen
    SQUIGGLY = "squiggly"         # Wellenunterstreichung
    TEXT_NOTE = "text_note"       # Sticky Note
    FREETEXT = "freetext"         # Textbox-Overlay
    STAMP = "stamp"               # Stempel
    RECT = "rect"                 # Rechteck
    CIRCLE = "circle"             # Kreis/Ellipse
    LINE = "line"                 # Linie
    INK = "ink"                   # Freihand-Zeichnung


class StampType(Enum):
    """Vordefinierte Stempel-Typen."""
    APPROVED = "Approved"
    EXPERIMENTAL = "Experimental"
    NOT_APPROVED = "NotApproved"
    AS_IS = "AsIs"
    EXPIRED = "Expired"
    NOT_FOR_PUBLIC = "NotForPublicRelease"
    CONFIDENTIAL = "Confidential"
    FINAL = "Final"
    SOLD = "Sold"
    DRAFT = "Draft"
    FOR_COMMENT = "ForComment"
    TOP_SECRET = "TopSecret"


@dataclass
class AnnotationColor:
    """RGB-Farbe für Annotationen."""
    r: float  # 0.0 - 1.0
    g: float
    b: float
    
    @classmethod
    def yellow(cls) -> 'AnnotationColor':
        return cls(1.0, 1.0, 0.0)
    
    @classmethod
    def red(cls) -> 'AnnotationColor':
        return cls(1.0, 0.0, 0.0)
    
    @classmethod
    def green(cls) -> 'AnnotationColor':
        return cls(0.0, 1.0, 0.0)
    
    @classmethod
    def blue(cls) -> 'AnnotationColor':
        return cls(0.0, 0.0, 1.0)
    
    @classmethod
    def orange(cls) -> 'AnnotationColor':
        return cls(1.0, 0.65, 0.0)
    
    @classmethod
    def purple(cls) -> 'AnnotationColor':
        return cls(0.5, 0.0, 0.5)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.r, self.g, self.b)


@dataclass
class Annotation:
    """Repräsentiert eine Annotation."""
    type: AnnotationType
    page_index: int
    rect: Tuple[float, float, float, float]  # x0, y0, x1, y1
    content: str = ""
    author: str = ""
    color: Optional[AnnotationColor] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary."""
        return {
            'type': self.type.value,
            'page_index': self.page_index,
            'rect': self.rect,
            'content': self.content,
            'author': self.author,
            'color': self.color.to_tuple() if self.color else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PDFAnnotator(LoggerMixin):
    """
    Fügt Annotationen zu PDF-Dateien hinzu.
    
    Features:
    - Text-Marker (Highlight, Underline, Strikeout)
    - Sticky Notes / Text-Kommentare
    - Freitext-Overlays
    - Stempel
    - Formen (Rechteck, Kreis, Linie)
    - Freihand-Zeichnung
    - Annotationen auslesen
    - Annotationen entfernen
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht verfügbar")

    def _resolve_stamp(self, stamp: Union[StampType, int, str]) -> Union[int, str]:
        """Löst StampType, Integer-ID oder Name zu einem PyMuPDF-kompatiblen Stempel-Wert auf."""
        stamp_map = {
            StampType.APPROVED: getattr(fitz, "STAMP_Approved", 0) if PYMUPDF_AVAILABLE else 0,
            StampType.EXPERIMENTAL: getattr(fitz, "STAMP_Experimental", 4) if PYMUPDF_AVAILABLE else 4,
            StampType.NOT_APPROVED: getattr(fitz, "STAMP_NotApproved", 9) if PYMUPDF_AVAILABLE else 9,
            StampType.AS_IS: getattr(fitz, "STAMP_AsIs", 1) if PYMUPDF_AVAILABLE else 1,
            StampType.EXPIRED: getattr(fitz, "STAMP_Expired", 5) if PYMUPDF_AVAILABLE else 5,
            StampType.NOT_FOR_PUBLIC: getattr(fitz, "STAMP_NotForPublicRelease", 10) if PYMUPDF_AVAILABLE else 10,
            StampType.CONFIDENTIAL: getattr(fitz, "STAMP_Confidential", 2) if PYMUPDF_AVAILABLE else 2,
            StampType.FINAL: getattr(fitz, "STAMP_Final", 6) if PYMUPDF_AVAILABLE else 6,
            StampType.SOLD: getattr(fitz, "STAMP_Sold", 11) if PYMUPDF_AVAILABLE else 11,
            StampType.DRAFT: getattr(fitz, "STAMP_Draft", 13) if PYMUPDF_AVAILABLE else 13,
            StampType.FOR_COMMENT: getattr(fitz, "STAMP_ForComment", 7) if PYMUPDF_AVAILABLE else 7,
            StampType.TOP_SECRET: getattr(fitz, "STAMP_TopSecret", 12) if PYMUPDF_AVAILABLE else 12,
        }
        if isinstance(stamp, StampType):
            return stamp_map.get(stamp, getattr(fitz, "STAMP_Approved", 0) if PYMUPDF_AVAILABLE else 0)
        if isinstance(stamp, int):
            return stamp
        if isinstance(stamp, str):
            try:
                enum_val = StampType[stamp.upper()]
                return stamp_map.get(enum_val, 0)
            except KeyError:
                pass
            attr_name = f"STAMP_{stamp}"
            if PYMUPDF_AVAILABLE and hasattr(fitz, attr_name):
                return getattr(fitz, attr_name)
            if Path(stamp).is_file():
                return stamp
            return getattr(fitz, "STAMP_Approved", 0) if PYMUPDF_AVAILABLE else 0
        return getattr(fitz, "STAMP_Approved", 0) if PYMUPDF_AVAILABLE else 0

    def _save_pdf(self, doc, pdf_path: str, output_path: str) -> Optional[Path]:
        """
        Speichert das fitz-Dokument.
        Bei In-Place-Überschreiben wird in eine temporäre Datei im Zielordner gespeichert,
        die nach Schließen des Dokuments im finally-Block atomar ersetzt wird.
        """
        src = Path(pdf_path).resolve()
        dst = Path(output_path).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src == dst:
            with tempfile.NamedTemporaryFile(dir=dst.parent, prefix="dokuzen_annot_", suffix=".tmp", delete=False) as tmp:
                temp_file = Path(tmp.name)
            doc.save(str(temp_file))
            return temp_file
        else:
            doc.save(output_path)
            return None

    def add_highlight(self, pdf_path: str, output_path: str,
                      page_index: int, rect: Tuple[float, float, float, float],
                      color: AnnotationColor = None,
                      content: str = "") -> bool:
        """
        Fügt einen Text-Marker hinzu.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Seitenindex (0-basiert)
            rect: Rechteck (x0, y0, x1, y1)
            color: Markerfarbe (Standard: Gelb)
            content: Optionaler Kommentar
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.yellow()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_highlight_annot(fitz.Rect(rect))
            annot.set_colors(stroke=color.to_tuple())
            if content:
                annot.set_info(content=content)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            self.logger.info(f"Highlight hinzugefügt: Seite {page_index + 1}")
            return True
        except Exception as e:
            self.logger.error(f"Highlight-Fehler: {e}")
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

    def add_underline(self, pdf_path: str, output_path: str,
                      page_index: int, rect: Tuple[float, float, float, float],
                      color: AnnotationColor = None) -> bool:
        """Fügt eine Unterstreichung hinzu."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.red()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_underline_annot(fitz.Rect(rect))
            annot.set_colors(stroke=color.to_tuple())
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Underline-Fehler: {e}")
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

    def add_strikeout(self, pdf_path: str, output_path: str,
                      page_index: int, rect: Tuple[float, float, float, float],
                      color: AnnotationColor = None) -> bool:
        """Fügt eine Durchstreichung hinzu."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.red()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_strikeout_annot(fitz.Rect(rect))
            annot.set_colors(stroke=color.to_tuple())
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Strikeout-Fehler: {e}")
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

    def add_text_note(self, pdf_path: str, output_path: str,
                      page_index: int, point: Tuple[float, float],
                      text: str, author: str = "") -> bool:
        """
        Fügt eine Sticky Note (Text-Kommentar) hinzu.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Seitenindex
            point: Position (x, y)
            text: Kommentartext
            author: Autor-Name
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_text_annot(fitz.Point(point), text)
            if author:
                annot.set_info(title=author)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            self.logger.info(f"Text-Note hinzugefügt: Seite {page_index + 1}")
            return True
        except Exception as e:
            self.logger.error(f"Text-Note-Fehler: {e}")
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

    def add_freetext(self, pdf_path: str, output_path: str,
                     page_index: int, rect: Tuple[float, float, float, float],
                     text: str, fontsize: int = 12,
                     color: AnnotationColor = None,
                     bg_color: AnnotationColor = None) -> bool:
        """
        Fügt einen Freitext-Overlay hinzu.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Seitenindex
            rect: Textbox-Rechteck
            text: Text
            fontsize: Schriftgröße
            color: Textfarbe
            bg_color: Hintergrundfarbe
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            text_color = color.to_tuple() if color else (0, 0, 0)
            fill_color = bg_color.to_tuple() if bg_color else (1, 1, 0.8)
            annot = page.add_freetext_annot(
                fitz.Rect(rect),
                text,
                fontsize=fontsize,
                text_color=text_color,
                fill_color=fill_color,
            )
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            self.logger.info(f"Freitext hinzugefügt: Seite {page_index + 1}")
            return True
        except Exception as e:
            self.logger.error(f"Freitext-Fehler: {e}")
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

    def add_stamp(self, pdf_path: str, output_path: str,
                  page_index: int, rect: Tuple[float, float, float, float],
                  stamp_type: Union[StampType, int, str] = StampType.APPROVED) -> bool:
        """
        Fügt einen Stempel hinzu.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Seitenindex
            rect: Stempel-Rechteck
            stamp_type: Stempel-Typ (StampType Enum, Integer-ID oder Name/Pfad)
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            stamp_val = self._resolve_stamp(stamp_type)
            annot = page.add_stamp_annot(fitz.Rect(rect), stamp=stamp_val)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            stamp_name = stamp_type.name if isinstance(stamp_type, StampType) else str(stamp_type)
            self.logger.info(f"Stempel '{stamp_name}' hinzugefügt: Seite {page_index + 1}")
            return True
        except Exception as e:
            self.logger.error(f"Stempel-Fehler: {e}")
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

    def add_rect(self, pdf_path: str, output_path: str,
                 page_index: int, rect: Tuple[float, float, float, float],
                 color: AnnotationColor = None,
                 fill_color: AnnotationColor = None,
                 width: float = 1.0) -> bool:
        """Fügt ein Rechteck hinzu."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.red()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_rect_annot(fitz.Rect(rect))
            annot.set_colors(stroke=color.to_tuple())
            if fill_color:
                annot.set_colors(fill=fill_color.to_tuple())
            annot.set_border(width=width)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Rechteck-Fehler: {e}")
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

    def add_circle(self, pdf_path: str, output_path: str,
                   page_index: int, rect: Tuple[float, float, float, float],
                   color: AnnotationColor = None,
                   fill_color: AnnotationColor = None,
                   width: float = 1.0) -> bool:
        """Fügt einen Kreis/Ellipse hinzu."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.blue()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_circle_annot(fitz.Rect(rect))
            annot.set_colors(stroke=color.to_tuple())
            if fill_color:
                annot.set_colors(fill=fill_color.to_tuple())
            annot.set_border(width=width)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Kreis-Fehler: {e}")
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

    def add_line(self, pdf_path: str, output_path: str,
                 page_index: int, 
                 start: Tuple[float, float],
                 end: Tuple[float, float],
                 color: AnnotationColor = None,
                 width: float = 1.0) -> bool:
        """Fügt eine Linie hinzu."""
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.red()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annot = page.add_line_annot(fitz.Point(start), fitz.Point(end))
            annot.set_colors(stroke=color.to_tuple())
            annot.set_border(width=width)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Linien-Fehler: {e}")
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

    def add_ink(self, pdf_path: str, output_path: str,
                page_index: int,
                points: List[List[Tuple[float, float]]],
                color: AnnotationColor = None,
                width: float = 1.0) -> bool:
        """
        Fügt eine Freihand-Zeichnung hinzu.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Seitenindex
            points: Liste von Pfaden, jeder Pfad ist Liste von (x, y) Punkten
            color: Stiftfarbe
            width: Stiftbreite
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        if color is None:
            color = AnnotationColor.blue()
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            ink_list = [[fitz.Point(p) for p in path] for path in points]
            annot = page.add_ink_annot(ink_list)
            annot.set_colors(stroke=color.to_tuple())
            annot.set_border(width=width)
            annot.update()
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Ink-Fehler: {e}")
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

    def get_annotations(self, pdf_path: str) -> List[Annotation]:
        """
        Liest alle Annotationen aus einem PDF.
        
        Args:
            pdf_path: PDF-Datei
            
        Returns:
            Liste von Annotation-Objekten
        """
        if not PYMUPDF_AVAILABLE:
            return []
        
        annotations = []
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            for page_idx, page in enumerate(doc):
                for annot in page.annots():
                    annot_type = self._map_annot_type(annot.type[0])
                    if annot_type:
                        annotations.append(Annotation(
                            type=annot_type,
                            page_index=page_idx,
                            rect=tuple(annot.rect),
                            content=annot.info.get('content', ''),
                            author=annot.info.get('title', ''),
                            created_at=None,
                        ))
        except Exception as e:
            self.logger.error(f"Annotations-Lese-Fehler: {e}")
        finally:
            if doc is not None:
                doc.close()

        return annotations
    
    def _map_annot_type(self, fitz_type: int) -> Optional[AnnotationType]:
        """Mappt PyMuPDF Annotation-Typ zu unserem Enum."""
        type_map = {
            fitz.PDF_ANNOT_HIGHLIGHT: AnnotationType.HIGHLIGHT,
            fitz.PDF_ANNOT_UNDERLINE: AnnotationType.UNDERLINE,
            fitz.PDF_ANNOT_STRIKE_OUT: AnnotationType.STRIKEOUT,
            fitz.PDF_ANNOT_SQUIGGLY: AnnotationType.SQUIGGLY,
            fitz.PDF_ANNOT_TEXT: AnnotationType.TEXT_NOTE,
            fitz.PDF_ANNOT_FREE_TEXT: AnnotationType.FREETEXT,
            fitz.PDF_ANNOT_STAMP: AnnotationType.STAMP,
            fitz.PDF_ANNOT_SQUARE: AnnotationType.RECT,
            fitz.PDF_ANNOT_CIRCLE: AnnotationType.CIRCLE,
            fitz.PDF_ANNOT_LINE: AnnotationType.LINE,
            fitz.PDF_ANNOT_INK: AnnotationType.INK,
        }
        return type_map.get(fitz_type)
    
    def remove_annotation(self, pdf_path: str, output_path: str,
                          page_index: int, annot_index: int) -> bool:
        """
        Entfernt eine spezifische Annotation.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Seitenindex
            annot_index: Index der Annotation auf der Seite
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_index]
            annots = list(page.annots())
            if annot_index < len(annots):
                page.delete_annot(annots[annot_index])
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            return True
        except Exception as e:
            self.logger.error(f"Annotation-Entfernen-Fehler: {e}")
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
    
    def remove_all_annotations(self, pdf_path: str, output_path: str,
                               page_index: int = None) -> bool:
        """
        Entfernt alle Annotationen.
        
        Args:
            pdf_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            page_index: Optional: Nur von dieser Seite (None = alle)
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(pdf_path)
            pages = [doc[page_index]] if page_index is not None else doc
            for page in pages:
                annots = list(page.annots())
                for annot in annots:
                    page.delete_annot(annot)
            temp_file = self._save_pdf(doc, pdf_path, output_path)
            self.logger.info(f"Annotationen entfernt: {pdf_path}")
            return True
        except Exception as e:
            self.logger.error(f"Annotationen-Entfernen-Fehler: {e}")
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
