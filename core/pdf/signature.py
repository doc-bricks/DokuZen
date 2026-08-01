#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Signatur-Overlay
=====================================
Bild (Signatur-PNG/JPG) in eine PDF-Seite einbetten.
Unterstützt: PNG mit Transparenz, JPG, wählbare Seite, Position und Größe.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

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


DEFAULT_SIGNATURE_TERMS = (
    "unterschrift",
    "unterschrieben",
    "signatur",
    "signiert",
    "unterzeichnet",
    "signature",
    "signed",
)


@dataclass(frozen=True)
class SignatureDetectionResult:
    """Ergebnis der Vorabprüfung auf bereits vorhandene Signaturhinweise."""

    found: bool
    page_index: Optional[int] = None
    source: str = ""
    matched_term: Optional[str] = None
    text_excerpt: str = ""


@dataclass(frozen=True)
class SignatureEmbedResult:
    """Auswertbares Ergebnis eines geprüften Signatur-Overlays."""

    success: bool
    output_path: Optional[str] = None
    embedded: bool = False
    skipped_existing: bool = False
    detection: Optional[SignatureDetectionResult] = None
    error: Optional[str] = None


def _normalized_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _find_signature_term(
    text: str,
    terms: Sequence[str] = DEFAULT_SIGNATURE_TERMS,
) -> Optional[str]:
    haystack = _normalized_text(text)
    for term in terms:
        needle = _normalized_text(term)
        if needle and needle in haystack:
            return term
    return None


def _excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


class SignatureOverlay(LoggerMixin):
    """
    Bettet Signatur-Bilder (PNG/JPG) als Overlay in PDF-Seiten ein.

    Features:
    - PNG mit Alpha-Kanal (Transparenz) wird korrekt übertragen
    - JPG-Signaturen werden direkt eingebettet
    - Wählbare Zielseite (0-basiert)
    - Position und Größe frei einstellbar (PDF-Punkte; 1 Punkt = 1/72 Zoll)
    - Optionale Beibehaltung des Seitenverhältnisses via Pillow
    - Fehlgeschlagene Lade-/Schreibvorgänge werden sauber zurückgemeldet
    """

    def embed_signature(
        self,
        pdf_path: str,
        signature_path: str,
        output_path: str,
        page_index: int = 0,
        x: float = 50.0,
        y: Optional[float] = None,
        width: float = 200.0,
        height: float = 80.0,
        keep_aspect: bool = True,
    ) -> bool:
        """
        Bettet ein Signaturbild in eine PDF-Seite ein.

        Args:
            pdf_path:        Pfad zur Eingabe-PDF
            signature_path:  Pfad zum Signaturbild (PNG oder JPG)
            output_path:     Pfad zur Ausgabe-PDF (darf gleich pdf_path sein)
            page_index:      Zielseite, 0-basiert (Standard: 0 = erste Seite)
            x:               Abstand von links in PDF-Punkten
            y:               Abstand von oben in PDF-Punkten;
                             None → 50 Punkte vom unteren Seitenrand
            width:           Breite des Overlay-Rechtecks in PDF-Punkten
            height:          Höhe des Overlay-Rechtecks (ggf. korrigiert bei keep_aspect)
            keep_aspect:     True → Seitenverhältnis des Bildes beibehalten

        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.error("PyMuPDF (fitz) nicht verfügbar – pip install PyMuPDF")
            return False

        sig_path = Path(signature_path)
        if not sig_path.is_file():
            self.logger.error(f"Signaturbild nicht gefunden: {signature_path}")
            return False

        if not Path(pdf_path).is_file():
            self.logger.error(f"PDF nicht gefunden: {pdf_path}")
            return False

        doc = None
        try:
            doc = fitz.open(pdf_path)

            if page_index < 0 or page_index >= doc.page_count:
                self.logger.error(
                    f"Seitenindex {page_index} ungültig "
                    f"(PDF hat {doc.page_count} Seite(n))"
                )
                return False

            page = doc[page_index]
            page_rect = page.rect  # fitz.Rect(0, 0, page_width, page_height)

            # Y-Autoposition: 50 Punkte vom unteren Seitenrand
            actual_y = y if y is not None else page_rect.height - height - 50.0

            # Größe unter Wahrung des Seitenverhältnisses berechnen
            actual_width, actual_height = (
                self._adjusted_size(str(sig_path), width, height)
                if keep_aspect
                else (width, height)
            )

            # Overlay-Rechteck aufspannen (x0, y0, x1, y1)
            rect = fitz.Rect(
                x,
                actual_y,
                x + actual_width,
                actual_y + actual_height,
            )

            # Bild als Overlay einfügen (über dem PDF-Inhalt)
            page.insert_image(rect, filename=str(sig_path), overlay=True)

            doc.save(output_path)
            self.logger.info(
                f"Signatur eingebettet: Seite {page_index + 1}, "
                f"Rect={rect}, Ausgabe: {output_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Fehler beim Einbetten der Signatur: {e}")
            return False
        finally:
            if doc is not None:
                doc.close()

    def detect_existing_signature(
        self,
        pdf_path: str,
        page_index: int = 0,
        terms: Sequence[str] = DEFAULT_SIGNATURE_TERMS,
        use_ocr: bool = True,
        ocr_language: str = "deu+eng",
    ) -> SignatureDetectionResult:
        """
        Prüft, ob die Zielseite bereits Signaturhinweise enthält.

        Zuerst wird vorhandener PDF-Text per PyMuPDF gelesen. Nur wenn dabei
        kein Treffer entsteht und `use_ocr=True` ist, wird der bestehende
        OCR-Pfad für genau diese Seite versucht.
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht verfügbar; Signaturprüfung übersprungen")
            return SignatureDetectionResult(False)

        if not Path(pdf_path).is_file():
            self.logger.error(f"PDF nicht gefunden: {pdf_path}")
            return SignatureDetectionResult(False)

        doc = None
        try:
            doc = fitz.open(pdf_path)
            if page_index < 0 or page_index >= doc.page_count:
                self.logger.error(
                    f"Seitenindex {page_index} ungültig "
                    f"(PDF hat {doc.page_count} Seite(n))"
                )
                return SignatureDetectionResult(False)

            page_text = doc[page_index].get_text() or ""
            matched = _find_signature_term(page_text, terms)
            if matched:
                return SignatureDetectionResult(
                    True,
                    page_index=page_index,
                    source="pdf-text",
                    matched_term=matched,
                    text_excerpt=_excerpt(page_text),
                )

        except Exception as e:
            self.logger.warning(f"Signaturprüfung per PDF-Text fehlgeschlagen: {e}")
        finally:
            if doc is not None:
                doc.close()

        if not use_ocr:
            return SignatureDetectionResult(False)

        ocr_text = self._ocr_page_text(pdf_path, page_index, ocr_language)
        matched = _find_signature_term(ocr_text, terms)
        if matched:
            return SignatureDetectionResult(
                True,
                page_index=page_index,
                source="ocr",
                matched_term=matched,
                text_excerpt=_excerpt(ocr_text),
            )

        return SignatureDetectionResult(False)

    def embed_signature_checked(
        self,
        pdf_path: str,
        signature_path: str,
        output_path: str,
        page_index: int = 0,
        x: float = 50.0,
        y: Optional[float] = None,
        width: float = 200.0,
        height: float = 80.0,
        keep_aspect: bool = True,
        skip_if_present: bool = True,
        terms: Sequence[str] = DEFAULT_SIGNATURE_TERMS,
        use_ocr: bool = True,
        ocr_language: str = "deu+eng",
    ) -> SignatureEmbedResult:
        """
        Bettet eine Signatur ein, prüft aber optional vorher auf vorhandene
        Signaturhinweise.

        Bei Treffer wird das Original unverändert an `output_path` kopiert
        und als erfolgreicher Skip zurückgemeldet.
        """
        detection = None
        if skip_if_present:
            detection = self.detect_existing_signature(
                pdf_path,
                page_index=page_index,
                terms=terms,
                use_ocr=use_ocr,
                ocr_language=ocr_language,
            )
            if detection.found:
                try:
                    src = Path(pdf_path).resolve()
                    dst = Path(output_path).resolve()
                    if src != dst:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, dst)
                    return SignatureEmbedResult(
                        True,
                        output_path=str(output_path),
                        embedded=False,
                        skipped_existing=True,
                        detection=detection,
                    )
                except Exception as e:
                    self.logger.error(f"PDF konnte nach Signaturtreffer nicht kopiert werden: {e}")
                    return SignatureEmbedResult(
                        False,
                        embedded=False,
                        skipped_existing=True,
                        detection=detection,
                        error=str(e),
                    )

        success = self.embed_signature(
            pdf_path=pdf_path,
            signature_path=signature_path,
            output_path=output_path,
            page_index=page_index,
            x=x,
            y=y,
            width=width,
            height=height,
            keep_aspect=keep_aspect,
        )
        return SignatureEmbedResult(
            success,
            output_path=str(output_path) if success else None,
            embedded=success,
            skipped_existing=False,
            detection=detection,
            error=None if success else "Signatur konnte nicht eingebettet werden.",
        )

    def _ocr_page_text(self, pdf_path: str, page_index: int, language: str) -> str:
        """Liest OCR-Text für genau eine PDF-Seite, wenn Tesseract verfügbar ist."""
        try:
            from core.ocr.engine import OCREngine  # lokaler Import: OCR ist optional

            engine = OCREngine()
            if not engine.is_available:
                return ""
            results = engine.recognize_pdf(
                pdf_path,
                language=language,
                pages=[page_index + 1],
            )
            return "\n".join(result.text for result in results)
        except Exception as e:
            self.logger.warning(f"OCR-Signaturprüfung fehlgeschlagen: {e}")
            return ""

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    def _adjusted_size(
        self,
        image_path: str,
        max_width: float,
        max_height: float,
    ) -> Tuple[float, float]:
        """
        Berechnet Zielgröße unter Wahrung des Original-Seitenverhältnisses.

        Nutzt Pillow, falls verfügbar; andernfalls werden max_width/max_height
        unverändert zurückgegeben.
        """
        try:
            from PIL import Image  # noqa: PLC0415  (lokaler Import absichtlich)
            with Image.open(image_path) as img:
                img_w, img_h = img.size
            if img_w <= 0 or img_h <= 0:
                return max_width, max_height
            img_aspect = img_w / img_h
            rect_aspect = max_width / max_height
            if rect_aspect > img_aspect:
                # Höhe ist limitierend → Breite anpassen
                return max_height * img_aspect, max_height
            else:
                # Breite ist limitierend → Höhe anpassen
                return max_width, max_width / img_aspect
        except Exception as e:
            self.logger.warning(
                f"Seitenverhältnis konnte nicht berechnet werden "
                f"({e}); verwende Wunschgröße"
            )
            return max_width, max_height


# === Modul-Level-Hilfsfunktion ===

def embed_signature(
    pdf_path: str,
    signature_path: str,
    output_path: str,
    page_index: int = 0,
    x: float = 50.0,
    y: Optional[float] = None,
    width: float = 200.0,
    height: float = 80.0,
    keep_aspect: bool = True,
) -> bool:
    """
    Bettet ein Signaturbild in eine PDF-Seite ein (Hilfsfunktion).

    Erstellt intern ein SignatureOverlay-Objekt.
    Alle Parameter entsprechen SignatureOverlay.embed_signature().
    """
    return SignatureOverlay().embed_signature(
        pdf_path,
        signature_path,
        output_path,
        page_index=page_index,
        x=x,
        y=y,
        width=width,
        height=height,
        keep_aspect=keep_aspect,
    )


def detect_existing_signature(
    pdf_path: str,
    page_index: int = 0,
    terms: Sequence[str] = DEFAULT_SIGNATURE_TERMS,
    use_ocr: bool = True,
    ocr_language: str = "deu+eng",
) -> SignatureDetectionResult:
    """Prüft eine PDF-Seite auf vorhandene Signaturhinweise."""
    return SignatureOverlay().detect_existing_signature(
        pdf_path,
        page_index=page_index,
        terms=terms,
        use_ocr=use_ocr,
        ocr_language=ocr_language,
    )


def embed_signature_checked(
    pdf_path: str,
    signature_path: str,
    output_path: str,
    page_index: int = 0,
    x: float = 50.0,
    y: Optional[float] = None,
    width: float = 200.0,
    height: float = 80.0,
    keep_aspect: bool = True,
    skip_if_present: bool = True,
    terms: Sequence[str] = DEFAULT_SIGNATURE_TERMS,
    use_ocr: bool = True,
    ocr_language: str = "deu+eng",
) -> SignatureEmbedResult:
    """Bettet eine Signatur mit optionaler Vorabprüfung ein."""
    return SignatureOverlay().embed_signature_checked(
        pdf_path,
        signature_path,
        output_path,
        page_index=page_index,
        x=x,
        y=y,
        width=width,
        height=height,
        keep_aspect=keep_aspect,
        skip_if_present=skip_if_present,
        terms=terms,
        use_ocr=use_ocr,
        ocr_language=ocr_language,
    )


__all__ = [
    "DEFAULT_SIGNATURE_TERMS",
    "SignatureDetectionResult",
    "SignatureEmbedResult",
    "SignatureOverlay",
    "detect_existing_signature",
    "embed_signature",
    "embed_signature_checked",
    "PYMUPDF_AVAILABLE",
]
