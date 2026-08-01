#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Merger
============================
Führt mehrere PDFs zusammen oder teilt sie auf.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@dataclass
class MergeItem:
    """Ein Element zum Zusammenführen."""
    path: str
    pages: Optional[List[int]] = None  # None = alle Seiten, sonst 1-basiert
    password: str = ""


@dataclass
class MergeResult:
    """Ergebnis einer Merge-Operation."""
    success: bool
    output_path: str
    page_count: int
    error: Optional[str] = None


class PDFMerger(LoggerMixin):
    """
    Führt PDF-Dateien zusammen oder teilt sie auf.
    
    Features:
    - Mehrere PDFs zusammenführen
    - Seitenauswahl pro Dokument
    - PDF aufteilen (Split)
    - Seiten extrahieren
    - Seiten neu anordnen
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht installiert!")
    
    def merge(self, items: List[MergeItem], output_path: str) -> MergeResult:
        """
        Führt mehrere PDFs zusammen.
        
        Args:
            items: Liste von MergeItem-Objekten
            output_path: Pfad für die Ausgabe-PDF
            
        Returns:
            MergeResult mit Status
        """
        if not PYMUPDF_AVAILABLE:
            return MergeResult(False, output_path, 0, "PyMuPDF nicht verfügbar")
        
        if not items:
            return MergeResult(False, output_path, 0, "Keine Dateien angegeben")
        
        output_doc = None
        try:
            output_doc = fitz.open()
            total_pages = 0

            for item in items:
                if not Path(item.path).exists():
                    self.logger.warning(f"Datei nicht gefunden: {item.path}")
                    continue

                src_doc = None
                try:
                    src_doc = fitz.open(item.path)

                    if src_doc.is_encrypted:
                        if not src_doc.authenticate(item.password):
                            self.logger.warning(f"Passwort falsch: {item.path}")
                            continue

                    if item.pages is None:
                        page_indices = list(range(src_doc.page_count))
                    else:
                        page_indices = [p - 1 for p in item.pages if 0 < p <= src_doc.page_count]

                    for idx in page_indices:
                        output_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                        total_pages += 1

                    self.logger.debug(f"Hinzugefügt: {item.path} ({len(page_indices)} Seiten)")
                finally:
                    if src_doc is not None:
                        src_doc.close()

            if total_pages == 0:
                return MergeResult(False, output_path, 0, "Keine Seiten zum Zusammenführen")

            output_doc.save(output_path)
            self.logger.info(f"PDF erstellt: {output_path} ({total_pages} Seiten)")
            return MergeResult(True, output_path, total_pages)

        except Exception as e:
            self.logger.error(f"Merge-Fehler: {e}")
            return MergeResult(False, output_path, 0, str(e))
        finally:
            if output_doc is not None:
                output_doc.close()
    
    def merge_files(self, paths: List[str], output_path: str) -> MergeResult:
        """
        Einfache Variante: Mehrere PDFs komplett zusammenführen.
        
        Args:
            paths: Liste von PDF-Pfaden
            output_path: Ausgabepfad
            
        Returns:
            MergeResult
        """
        items = [MergeItem(path=p) for p in paths]
        return self.merge(items, output_path)
    
    def split(self, input_path: str, output_dir: str, 
              pages_per_file: int = 1) -> List[MergeResult]:
        """
        Teilt eine PDF in mehrere Dateien auf.
        
        Args:
            input_path: Eingabe-PDF
            output_dir: Ausgabeverzeichnis
            pages_per_file: Seiten pro Ausgabedatei
            
        Returns:
            Liste von MergeResults
        """
        if not PYMUPDF_AVAILABLE:
            return [MergeResult(False, "", 0, "PyMuPDF nicht verfügbar")]
        
        results = []
        
        src_doc = None
        try:
            src_doc = fitz.open(input_path)
            output_path_obj = Path(output_dir)
            output_path_obj.mkdir(parents=True, exist_ok=True)

            base_name = Path(input_path).stem
            total_pages = src_doc.page_count
            file_num = 1

            for start_page in range(0, total_pages, pages_per_file):
                end_page = min(start_page + pages_per_file - 1, total_pages - 1)

                new_doc = None
                try:
                    new_doc = fitz.open()
                    new_doc.insert_pdf(src_doc, from_page=start_page, to_page=end_page)

                    out_file = output_path_obj / f"{base_name}_Teil_{file_num:03d}.pdf"
                    new_doc.save(str(out_file))

                    page_count = end_page - start_page + 1
                    results.append(MergeResult(True, str(out_file), page_count))
                    file_num += 1
                finally:
                    if new_doc is not None:
                        new_doc.close()

            self.logger.info(f"PDF aufgeteilt: {len(results)} Dateien erstellt")

        except Exception as e:
            self.logger.error(f"Split-Fehler: {e}")
            results.append(MergeResult(False, "", 0, str(e)))
        finally:
            if src_doc is not None:
                src_doc.close()
        
        return results
    
    def extract_pages(self, input_path: str, output_path: str,
                      pages: List[int], password: str = "") -> MergeResult:
        """
        Extrahiert bestimmte Seiten aus einer PDF.
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            pages: Seitennummern (1-basiert)
            password: Passwort falls verschlüsselt
            
        Returns:
            MergeResult
        """
        item = MergeItem(path=input_path, pages=pages, password=password)
        return self.merge([item], output_path)
    
    def reorder_pages(self, input_path: str, output_path: str,
                      new_order: List[int], password: str = "") -> MergeResult:
        """
        Ordnet Seiten neu an.
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            new_order: Neue Reihenfolge (1-basierte Seitennummern)
            password: Passwort falls verschlüsselt
            
        Returns:
            MergeResult
        """
        item = MergeItem(path=input_path, pages=new_order, password=password)
        return self.merge([item], output_path)
    
    def delete_pages(self, input_path: str, output_path: str,
                     pages_to_delete: List[int], password: str = "") -> MergeResult:
        """
        Löscht bestimmte Seiten aus einer PDF.
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            pages_to_delete: Zu löschende Seiten (1-basiert)
            password: Passwort falls verschlüsselt
            
        Returns:
            MergeResult
        """
        if not PYMUPDF_AVAILABLE:
            return MergeResult(False, output_path, 0, "PyMuPDF nicht verfügbar")
        
        pages_to_keep = []
        src_doc = None
        try:
            src_doc = fitz.open(input_path)

            if src_doc.is_encrypted:
                if not src_doc.authenticate(password):
                    return MergeResult(False, output_path, 0, "Falsches Passwort")

            total = src_doc.page_count
            pages_to_keep = [i for i in range(1, total + 1) if i not in pages_to_delete]

        except Exception as e:
            return MergeResult(False, output_path, 0, str(e))
        finally:
            if src_doc is not None:
                src_doc.close()

        return self.extract_pages(input_path, output_path, pages_to_keep, password)
    
    def rotate_pages(self, input_path: str, output_path: str,
                     rotation: int, pages: Optional[List[int]] = None,
                     password: str = "") -> MergeResult:
        """
        Rotiert Seiten.
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            rotation: Grad (90, 180, 270)
            pages: Zu rotierende Seiten (None = alle)
            password: Passwort
            
        Returns:
            MergeResult
        """
        if not PYMUPDF_AVAILABLE:
            return MergeResult(False, output_path, 0, "PyMuPDF nicht verfügbar")
        
        if rotation not in [90, 180, 270]:
            return MergeResult(False, output_path, 0, "Ungültige Rotation")
        
        doc = None
        try:
            doc = fitz.open(input_path)

            if doc.is_encrypted:
                if not doc.authenticate(password):
                    return MergeResult(False, output_path, 0, "Falsches Passwort")

            if pages is None:
                page_indices = range(doc.page_count)
            else:
                page_indices = [p - 1 for p in pages if 0 < p <= doc.page_count]

            for idx in page_indices:
                page = doc[idx]
                page.set_rotation(page.rotation + rotation)

            page_count = doc.page_count
            doc.save(output_path)
            return MergeResult(True, output_path, page_count)

        except Exception as e:
            return MergeResult(False, output_path, 0, str(e))
        finally:
            if doc is not None:
                doc.close()


# === Hilfsfunktionen ===

def merge_pdfs(paths: List[str], output_path: str) -> bool:
    """Schnelle Funktion zum Zusammenführen."""
    merger = PDFMerger()
    result = merger.merge_files(paths, output_path)
    return result.success


def split_pdf(input_path: str, output_dir: str, pages_per_file: int = 1) -> List[str]:
    """Schnelle Funktion zum Aufteilen."""
    merger = PDFMerger()
    results = merger.split(input_path, output_dir, pages_per_file)
    return [r.output_path for r in results if r.success]
