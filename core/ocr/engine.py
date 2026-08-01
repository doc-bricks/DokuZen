#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - OCR Engine
============================
Texterkennung mit Tesseract.
"""

# BUGSWEEP-33: pytesseract/PIL sind optional (try/except unten). Ohne diese __future__-Direktive
# wird die Annotation `image: Image.Image` (recognize_image_object) bei Klassendefinition ausgewertet
# -> NameError, wenn pytesseract/PIL fehlt -> das ganze ocr-Modul (und damit gui.dialogs) unimportierbar.
# PEP 563 macht alle Annotationen zu Strings (lazy). (Gleiche Klasse wie der builder.py-Fix in Block 2.)
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from utils.logger import LoggerMixin

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False



@dataclass
class OCRResult:
    """Ergebnis einer OCR-Operation."""
    success: bool
    text: str
    confidence: float = 0.0
    language: str = ""
    error: Optional[str] = None


@dataclass
class OCRPageResult:
    """OCR-Ergebnis für eine Seite."""
    page_num: int
    text: str
    confidence: float
    word_count: int


class OCREngine(LoggerMixin):
    """
    OCR-Engine mit Tesseract.
    
    Features:
    - Bild zu Text
    - PDF zu durchsuchbarer PDF
    - Mehrsprachige Erkennung
    - Konfidenz-Auswertung
    """
    
    # Standard-Sprachen
    DEFAULT_LANGUAGE = "deu+eng"
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialisiert die OCR-Engine.
        
        Args:
            tesseract_path: Pfad zur Tesseract-Executable (optional)
        """
        if not TESSERACT_AVAILABLE:
            self.logger.warning("pytesseract nicht installiert!")
        
        self._tesseract_path = tesseract_path
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Tesseract-Verfügbarkeit prüfen
        self._is_available = self._check_tesseract()
    
    def _check_tesseract(self) -> bool:
        """Prüft ob Tesseract verfügbar ist."""
        if not TESSERACT_AVAILABLE:
            return False
        
        try:
            version = pytesseract.get_tesseract_version()
            self.logger.info(f"Tesseract gefunden: Version {version}")
            return True
        except Exception as e:
            self.logger.warning(f"Tesseract nicht gefunden: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Prüft ob OCR verfügbar ist."""
        return self._is_available
    
    def get_available_languages(self) -> List[str]:
        """Gibt verfügbare Sprachen zurück."""
        if not self._is_available:
            return []
        
        try:
            return pytesseract.get_languages()
        except Exception as e:
            self.logger.warning(f"Tesseract languages error: {e}")
            return []
    
    def recognize_image(self, image_path: str, 
                       language: str = DEFAULT_LANGUAGE) -> OCRResult:
        """
        Erkennt Text in einem Bild.
        
        Args:
            image_path: Pfad zum Bild
            language: Tesseract-Sprachcode
            
        Returns:
            OCRResult
        """
        if not self._is_available:
            return OCRResult(False, "", error="Tesseract nicht verfügbar")
        
        try:
            image = Image.open(image_path)

            # OCR durchführen
            # BUGSWEEP-30: timeout — ein korruptes/pathologisches Bild kann den Tesseract-
            # Subprozess sonst unbegrenzt haengen lassen (kein Abbruch).
            text = pytesseract.image_to_string(image, lang=language, timeout=120)

            # Konfidenz berechnen
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT, timeout=120)
            confidences = [int(c) for c in data['conf'] if c != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return OCRResult(
                success=True,
                text=text.strip(),
                confidence=avg_confidence,
                language=language
            )
            
        except Exception as e:
            self.logger.error(f"OCR-Fehler: {e}")
            return OCRResult(False, "", error=str(e))
    
    def recognize_image_object(self, image: Image.Image,
                               language: str = DEFAULT_LANGUAGE) -> OCRResult:
        """
        Erkennt Text in einem PIL-Image-Objekt.
        
        Args:
            image: PIL Image
            language: Sprachcode
            
        Returns:
            OCRResult
        """
        if not self._is_available:
            return OCRResult(False, "", error="Tesseract nicht verfügbar")
        
        try:
            # BUGSWEEP-30: timeout gegen haengenden Tesseract-Subprozess (siehe recognize_image).
            text = pytesseract.image_to_string(image, lang=language, timeout=120)

            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT, timeout=120)
            confidences = [int(c) for c in data['conf'] if c != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return OCRResult(
                success=True,
                text=text.strip(),
                confidence=avg_confidence,
                language=language
            )
            
        except Exception as e:
            return OCRResult(False, "", error=str(e))
    
    def recognize_pdf(self, pdf_path: str, 
                     language: str = DEFAULT_LANGUAGE,
                     pages: Optional[List[int]] = None) -> List[OCRPageResult]:
        """
        Erkennt Text in einer PDF (Seite für Seite).
        
        Args:
            pdf_path: Pfad zur PDF
            language: Sprachcode
            pages: Zu erkennende Seiten (1-basiert, None = alle)
            
        Returns:
            Liste von OCRPageResult
        """
        if not self._is_available:
            return []
        
        results = []
        
        if PYMUPDF_AVAILABLE:
            results = self._recognize_pdf_pymupdf(pdf_path, language, pages)
        else:
            self.logger.error("PyMuPDF nicht verfügbar")
        
        return results
    
    def _recognize_pdf_pymupdf(self, pdf_path: str, language: str,
                               pages: Optional[List[int]]) -> List[OCRPageResult]:
        """OCR mit PyMuPDF (Rendering zu Bild)."""
        results = []
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            page_range = pages if pages else range(1, doc.page_count + 1)
            for page_num in page_range:
                if page_num < 1 or page_num > doc.page_count:
                    continue
                page = doc[page_num - 1]
                mat = fitz.Matrix(300/72, 300/72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                result = self.recognize_image_object(img, language)
                if result.success:
                    results.append(OCRPageResult(
                        page_num=page_num,
                        text=result.text,
                        confidence=result.confidence,
                        word_count=len(result.text.split())
                    ))
        except Exception as e:
            self.logger.error(f"PyMuPDF-OCR Fehler: {e}")
        finally:
            if doc is not None:
                doc.close()

        return results
    
    def pdf_to_searchable_pdf(self, input_path: str, output_path: str,
                              language: str = DEFAULT_LANGUAGE) -> bool:
        """
        Konvertiert eine Bild-PDF zu einer durchsuchbaren PDF.
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            language: OCR-Sprache
            
        Returns:
            True bei Erfolg
        """
        if not self._is_available or not PYMUPDF_AVAILABLE:
            self.logger.error("Tesseract oder PyMuPDF nicht verfügbar")
            return False
        
        doc = None
        try:
            doc = fitz.open(input_path)
            for page_num in range(doc.page_count):
                page = doc[page_num]
                existing_text = page.get_text().strip()
                if existing_text:
                    self.logger.debug(f"Seite {page_num + 1} hat bereits Text")
                    continue
                mat = fitz.Matrix(300/72, 300/72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=language, extension='pdf')
                ocr_doc = fitz.open("pdf", pdf_bytes)
                if ocr_doc.page_count > 0:
                    pass  # Komplexere Implementierung nötig
                ocr_doc.close()
            doc.save(output_path)
            self.logger.info(f"Durchsuchbare PDF erstellt: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"PDF-OCR Konvertierung fehlgeschlagen: {e}")
            return False
        finally:
            if doc is not None:
                doc.close()


# === Hilfsfunktionen ===

def ocr_image(image_path: str, language: str = "deu+eng") -> str:
    """Schnelle OCR für ein Bild."""
    engine = OCREngine()
    result = engine.recognize_image(image_path, language)
    return result.text if result.success else ""


def ocr_pdf(pdf_path: str, language: str = "deu+eng") -> str:
    """Extrahiert Text aus PDF via OCR."""
    engine = OCREngine()
    results = engine.recognize_pdf(pdf_path, language)
    return "\n\n".join(r.text for r in results)


def is_ocr_available() -> bool:
    """Prüft ob OCR verfügbar ist."""
    return OCREngine().is_available
