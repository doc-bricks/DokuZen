#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Processor
===============================
Wrapper-Modul für PDF-Verarbeitung.
Kombiniert Reader, Merger und Security-Funktionalitaet.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

from utils.logger import LoggerMixin

# Re-export PDFInfo aus reader.py
from .reader import (
    PDFReader,
    PDFInfo,
    PDFPage,
    PDFMetadata,
    get_pdf_info,
    extract_text,
    is_pdf_encrypted,
    PYMUPDF_AVAILABLE,
)


class PDFProcessor(LoggerMixin):
    """
    Universelle PDF-Verarbeitungsklasse.

    Kombiniert Lese-, Schreib- und Bearbeitungsfunktionen
    für PDF-Dateien.

    Features:
    - PDF-Informationen abrufen
    - Text extrahieren
    - Seiten rendern
    - Seiten manipulieren (drehen, loeschen, extrahieren)
    - Metadaten ändern
    """

    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht installiert! pip install PyMuPDF")
        self._reader = PDFReader()
        self._path: Optional[str] = None

    def open(self, path: str, password: str = "") -> bool:
        """
        Oeffnet eine PDF-Datei.

        Args:
            path: Pfad zur PDF-Datei
            password: Passwort falls verschluesselt

        Returns:
            True bei Erfolg
        """
        self._path = path
        return self._reader.open(path, password)

    def close(self):
        """Schliesst die aktuelle PDF."""
        self._reader.close()
        self._path = None

    @property
    def is_open(self) -> bool:
        """Prüft ob eine PDF geöffnet ist."""
        return self._reader.is_open

    @property
    def page_count(self) -> int:
        """Anzahl der Seiten."""
        return self._reader.page_count

    @property
    def is_encrypted(self) -> bool:
        """Prüft ob PDF verschluesselt ist."""
        return self._reader.is_encrypted

    @property
    def needs_password(self) -> bool:
        """Prüft ob Passwort benoetigt wird."""
        return self._reader.needs_password

    def get_info(self) -> Optional[PDFInfo]:
        """
        Gibt vollstaendige PDF-Informationen zurück.

        Returns:
            PDFInfo-Objekt oder None
        """
        return self._reader.get_info()

    def get_page(self, page_num: int) -> Optional[PDFPage]:
        """
        Gibt Informationen zu einer Seite zurück.

        Args:
            page_num: Seitennummer (1-basiert)

        Returns:
            PDFPage-Objekt oder None
        """
        return self._reader.get_page(page_num)

    def get_text(self, page_num: Optional[int] = None) -> str:
        """
        Extrahiert Text aus der PDF.

        Args:
            page_num: Seitennummer (1-basiert) oder None für alle Seiten

        Returns:
            Extrahierter Text
        """
        return self._reader.get_text(page_num)

    def render_page(self, page_num: int, dpi: int = 150) -> Optional[bytes]:
        """
        Rendert eine Seite als PNG-Bild.

        Args:
            page_num: Seitennummer (1-basiert)
            dpi: Aufloesung

        Returns:
            PNG-Bytes oder None
        """
        return self._reader.render_page(page_num, dpi)

    def search_text(self, query: str, case_sensitive: bool = False) -> List:
        """
        Sucht Text in der PDF.

        Args:
            query: Suchbegriff
            case_sensitive: Gross-/Kleinschreibung beachten

        Returns:
            Liste von (Seitennummer, [Rechtecke])
        """
        return self._reader.search_text(query, case_sensitive)

    def extract_pages(self, page_numbers: List[int], output_path: str) -> bool:
        """
        Extrahiert bestimmte Seiten in eine neue PDF.

        Args:
            page_numbers: Liste der Seitennummern (1-basiert)
            output_path: Ausgabepfad

        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.error("PyMuPDF nicht verfuegbar")
            return False

        if self._reader._doc is None:
            self.logger.error("Keine PDF geöffnet")
            return False

        try:
            import fitz
            output_doc = fitz.open()
            try:
                for page_num in page_numbers:
                    if 1 <= page_num <= self._reader.page_count:
                        output_doc.insert_pdf(
                            self._reader._doc,
                            from_page=page_num - 1,
                            to_page=page_num - 1
                        )

                if output_doc.page_count > 0:
                    output_doc.save(output_path)
                    self.logger.info(f"Seiten extrahiert nach: {output_path}")
                    return True
                else:
                    self.logger.warning("Keine gültigen Seiten zum Extrahieren")
                    return False
            finally:
                output_doc.close()

        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren: {e}")
            return False

    def rotate_pages(self, page_numbers: List[int], angle: int, output_path: str) -> bool:
        """
        Rotiert bestimmte Seiten.

        Args:
            page_numbers: Liste der Seitennummern (1-basiert)
            angle: Rotationswinkel (90, 180, 270)
            output_path: Ausgabepfad

        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False

        if self._reader._doc is None:
            return False

        if angle not in [90, 180, 270]:
            self.logger.error(f"Ungueltiger Rotationswinkel: {angle}")
            return False

        try:
            import fitz
            # Kopie erstellen
            output_doc = fitz.open()
            try:
                output_doc.insert_pdf(self._reader._doc)

                for page_num in page_numbers:
                    if 1 <= page_num <= output_doc.page_count:
                        page = output_doc[page_num - 1]
                        page.set_rotation(page.rotation + angle)

                output_doc.save(output_path)
                self.logger.info(f"Seiten rotiert, gespeichert nach: {output_path}")
                return True
            finally:
                output_doc.close()

        except Exception as e:
            self.logger.error(f"Fehler beim Rotieren: {e}")
            return False

    def delete_pages(self, page_numbers: List[int], output_path: str) -> bool:
        """
        Loescht bestimmte Seiten und speichert die verbleibenden.

        Args:
            page_numbers: Liste der zu loeschenden Seitennummern (1-basiert)
            output_path: Ausgabepfad

        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False

        if self._reader._doc is None:
            return False

        try:
            import fitz
            # Kopie erstellen
            output_doc = fitz.open()
            try:
                output_doc.insert_pdf(self._reader._doc)

                # Seiten rückwaerts loeschen (um Indexverschiebung zu vermeiden)
                pages_to_delete = sorted([p - 1 for p in page_numbers
                                          if 1 <= p <= output_doc.page_count], reverse=True)

                for page_idx in pages_to_delete:
                    output_doc.delete_page(page_idx)

                if output_doc.page_count > 0:
                    output_doc.save(output_path)
                    self.logger.info(f"Seiten geloescht, gespeichert nach: {output_path}")
                    return True
                else:
                    self.logger.warning("Alle Seiten wurden geloescht")
                    return False
            finally:
                output_doc.close()

        except Exception as e:
            self.logger.error(f"Fehler beim Loeschen: {e}")
            return False

    def set_metadata(self, metadata: Dict[str, str], output_path: str) -> bool:
        """
        Setzt PDF-Metadaten.

        Args:
            metadata: Dict mit Metadaten (title, author, subject, keywords)
            output_path: Ausgabepfad

        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            return False

        if self._reader._doc is None:
            return False

        try:
            import fitz
            # Kopie erstellen
            output_doc = fitz.open()
            try:
                output_doc.insert_pdf(self._reader._doc)

                # Metadaten setzen
                output_doc.set_metadata(metadata)

                output_doc.save(output_path)
                self.logger.info(f"Metadaten gesetzt, gespeichert nach: {output_path}")
                return True
            finally:
                output_doc.close()

        except Exception as e:
            self.logger.error(f"Fehler beim Setzen der Metadaten: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# === Hilfsfunktionen ===

def process_pdf(path: str, password: str = "") -> Optional[PDFProcessor]:
    """
    Erstellt einen PDFProcessor und oeffnet die Datei.

    Args:
        path: Pfad zur PDF
        password: Optionales Passwort

    Returns:
        PDFProcessor oder None bei Fehler
    """
    processor = PDFProcessor()
    if processor.open(path, password):
        return processor
    return None


__all__ = [
    "PDFProcessor",
    "PDFInfo",
    "PDFPage",
    "PDFMetadata",
    "process_pdf",
    "get_pdf_info",
    "extract_text",
    "is_pdf_encrypted",
]
