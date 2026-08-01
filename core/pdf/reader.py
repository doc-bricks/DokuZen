#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Reader
============================
Liest und analysiert PDF-Dateien.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass
from datetime import datetime

from utils.logger import LoggerMixin

# PDF-Bibliothek importieren
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@dataclass
class PDFPage:
    """Repräsentiert eine PDF-Seite."""
    number: int  # 1-basiert
    width: float
    height: float
    rotation: int
    text: str = ""
    has_images: bool = False
    image_count: int = 0


@dataclass
class PDFMetadata:
    """PDF-Metadaten."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None


@dataclass
class PDFInfo:
    """Vollständige PDF-Informationen."""
    path: str
    page_count: int
    file_size: int
    is_encrypted: bool
    is_locked: bool
    metadata: PDFMetadata
    has_text: bool
    has_images: bool


class PDFReader(LoggerMixin):
    """
    Liest und analysiert PDF-Dateien.
    
    Verwendet PyMuPDF (fitz) als Backend.
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht installiert! pip install PyMuPDF")
        self._doc: Optional[fitz.Document] = None
        self._path: Optional[Path] = None
    
    def open(self, path: str, password: str = "") -> bool:
        """
        Öffnet eine PDF-Datei.
        
        Args:
            path: Pfad zur PDF-Datei
            password: Passwort falls verschlüsselt
            
        Returns:
            True bei Erfolg
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.error("PyMuPDF nicht verfügbar")
            return False
        
        self.close()
        
        try:
            self._path = Path(path)
            self._doc = fitz.open(str(self._path))
            
            # Falls verschlüsselt, Passwort versuchen
            if self._doc.is_encrypted:
                if not self._doc.authenticate(password):
                    self.logger.warning(f"PDF ist verschlüsselt: {path}")
                    # Trotzdem offen lassen für Info-Abfragen
            
            self.logger.debug(f"PDF geöffnet: {path} ({self._doc.page_count} Seiten)")
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Öffnen: {e}")
            if self._doc is not None:
                self._doc.close()
            self._doc = None
            self._path = None
            return False
    
    def close(self):
        """Schließt die aktuelle PDF."""
        if self._doc is not None:
            self._doc.close()
            self._doc = None
            self._path = None
    
    @property
    def is_open(self) -> bool:
        """Prüft ob eine PDF geöffnet ist."""
        return self._doc is not None
    
    @property
    def page_count(self) -> int:
        """Anzahl der Seiten."""
        return self._doc.page_count if self._doc is not None else 0
    
    @property
    def is_encrypted(self) -> bool:
        """Prüft ob PDF verschlüsselt ist."""
        return self._doc.is_encrypted if self._doc is not None else False
    
    @property
    def needs_password(self) -> bool:
        """Prüft ob Passwort benötigt wird."""
        if self._doc is None:
            return False
        return self._doc.is_encrypted and self._doc.needs_pass
    
    def get_info(self) -> Optional[PDFInfo]:
        """
        Gibt vollständige PDF-Informationen zurück.
        
        Returns:
            PDFInfo-Objekt oder None
        """
        if self._doc is None or not self._path:
            return None
        
        # Metadaten extrahieren
        meta = self._doc.metadata
        metadata = PDFMetadata(
            title=meta.get("title"),
            author=meta.get("author"),
            subject=meta.get("subject"),
            keywords=meta.get("keywords"),
            creator=meta.get("creator"),
            producer=meta.get("producer")
        )
        
        # Datums-Parsing
        if meta.get("creationDate"):
            metadata.creation_date = self._parse_pdf_date(meta["creationDate"])
        if meta.get("modDate"):
            metadata.modification_date = self._parse_pdf_date(meta["modDate"])
        
        # Text/Bilder prüfen (erste Seite als Stichprobe)
        has_text = False
        has_images = False
        if self._doc.page_count > 0 and not self.needs_password:
            page = self._doc[0]
            has_text = bool(page.get_text().strip())
            has_images = len(page.get_images()) > 0
        
        return PDFInfo(
            path=str(self._path),
            page_count=self._doc.page_count,
            file_size=self._path.stat().st_size,
            is_encrypted=self._doc.is_encrypted,
            is_locked=self.needs_password,
            metadata=metadata,
            has_text=has_text,
            has_images=has_images
        )
    
    def get_page(self, page_num: int) -> Optional[PDFPage]:
        """
        Gibt Informationen zu einer Seite zurück.
        
        Args:
            page_num: Seitennummer (1-basiert)
            
        Returns:
            PDFPage-Objekt oder None
        """
        if self._doc is None or self.needs_password:
            return None
        
        if page_num < 1 or page_num > self._doc.page_count:
            return None
        
        page = self._doc[page_num - 1]  # 0-basiert intern
        images = page.get_images()
        
        return PDFPage(
            number=page_num,
            width=page.rect.width,
            height=page.rect.height,
            rotation=page.rotation,
            text=page.get_text(),
            has_images=len(images) > 0,
            image_count=len(images)
        )
    
    def get_text(self, page_num: Optional[int] = None) -> str:
        """
        Extrahiert Text aus der PDF.
        
        Args:
            page_num: Seitennummer (1-basiert) oder None für alle Seiten
            
        Returns:
            Extrahierter Text
        """
        if self._doc is None or self.needs_password:
            return ""
        
        if page_num is not None:
            if page_num < 1 or page_num > self._doc.page_count:
                return ""
            return self._doc[page_num - 1].get_text()
        
        # Alle Seiten
        texts = []
        for page in self._doc:
            texts.append(page.get_text())
        return "\n\n".join(texts)
    
    def iter_pages(self) -> Generator[PDFPage, None, None]:
        """
        Iteriert über alle Seiten.
        
        Yields:
            PDFPage-Objekte
        """
        if self._doc is None or self.needs_password:
            return
        
        for i, page in enumerate(self._doc):
            images = page.get_images()
            yield PDFPage(
                number=i + 1,
                width=page.rect.width,
                height=page.rect.height,
                rotation=page.rotation,
                text=page.get_text(),
                has_images=len(images) > 0,
                image_count=len(images)
            )
    
    def render_page(self, page_num: int, dpi: int = 150) -> Optional[bytes]:
        """
        Rendert eine Seite als PNG-Bild.
        
        Args:
            page_num: Seitennummer (1-basiert)
            dpi: Auflösung
            
        Returns:
            PNG-Bytes oder None
        """
        if self._doc is None or self.needs_password:
            return None
        
        if page_num < 1 or page_num > self._doc.page_count:
            return None
        
        page = self._doc[page_num - 1]
        zoom = dpi / 72  # 72 ist Standard-DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        return pix.tobytes("png")
    
    def search_text(self, query: str, case_sensitive: bool = False) -> List[Tuple[int, List]]:
        """
        Sucht Text in der PDF.
        
        Args:
            query: Suchbegriff
            case_sensitive: Groß-/Kleinschreibung beachten
            
        Returns:
            Liste von (Seitennummer, [Rechtecke])
        """
        if self._doc is None or self.needs_password or not query:
            return []
        
        results = []
        for i, page in enumerate(self._doc):
            if case_sensitive:
                rects = page.search_for(query)
            else:
                # fitz.search_for is case-sensitive; collect all case variants
                # present in the page text and search for each
                page_text = page.get_text()
                rects = []
                seen: set = set()
                for m in re.finditer(re.escape(query), page_text, re.IGNORECASE):
                    variant = m.group()
                    if variant not in seen:
                        seen.add(variant)
                        rects.extend(page.search_for(variant))
            if rects:
                results.append((i + 1, rects))
        
        return results
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parst PDF-Datumsformat (D:YYYYMMDDHHmmSS)."""
        try:
            if date_str.startswith("D:"):
                date_str = date_str[2:]
            # Nur Jahr, Monat, Tag extrahieren
            return datetime.strptime(date_str[:8], "%Y%m%d")
        except (ValueError, IndexError, TypeError):
            return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# === Hilfsfunktionen ===

def get_pdf_info(path: str) -> Optional[PDFInfo]:
    """Schnelle Funktion um PDF-Info zu erhalten."""
    with PDFReader() as reader:
        if reader.open(path):
            return reader.get_info()
    return None


def extract_text(path: str, password: str = "") -> str:
    """Extrahiert Text aus einer PDF."""
    with PDFReader() as reader:
        if reader.open(path, password):
            return reader.get_text()
    return ""


def is_pdf_encrypted(path: str) -> bool:
    """Prüft ob eine PDF verschlüsselt ist."""
    with PDFReader() as reader:
        if reader.open(path):
            return reader.is_encrypted
    return False
