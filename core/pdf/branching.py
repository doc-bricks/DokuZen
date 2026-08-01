#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Branching Manager
====================================
Implementiert Branch-/Auszug-Erzeugung (Split, Merge, Marker-Persistenz).
Das Originaldokument bleibt stets unverändert.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.logger import get_logger

_logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def generate_branch_path(original_path: str, suffix: str, output_dir: Optional[str] = None) -> str:
    """
    Erzeugt einen eindeutigen Pfad für ein neues Branch-Dokument.
    
    Args:
        original_path: Pfad der Originaldatei
        suffix: Suffix für den Branch-Namen (z.B. 'branch_part1', 'branch_auszug')
        output_dir: Optionales Zielverzeichnis (Standard: Ordner der Originaldatei)
        
    Returns:
        Absoluter Pfad der Ausgabedatei
    """
    orig_p = Path(original_path)
    target_dir = Path(output_dir) if output_dir else orig_p.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    
    stem = orig_p.stem
    filename = f"{stem}_{suffix}.pdf"
    output_path = target_dir / filename
    
    # Falls Datei bereits existiert, laufende Nummer anhängen
    counter = 1
    while output_path.exists():
        filename = f"{stem}_{suffix}_{counter}.pdf"
        output_path = target_dir / filename
        counter += 1
        
    return str(output_path)


def split_at_page(pdf_path: str, split_page: int, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """
    Teilt ein PDF nach einer angegebenen Seitennummer (1-basiert) in zwei Branch-Dokumente.
    
    Teil 1 enthält die Seiten 1 bis split_page.
    Teil 2 enthält die Seiten split_page + 1 bis Ende.
    
    Args:
        pdf_path: Pfad zur PDF-Datei
        split_page: Seitennummer (1-basiert), nach der geteilt wird
        output_dir: Ausgabeverzeichnis
        
    Returns:
        Tupel (Pfad_Teil_1, Pfad_Teil_2)
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF ist nicht verfügbar")
        
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {pdf_path}")
        
    doc = None
    doc1 = None
    doc2 = None
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        if split_page < 1 or split_page >= total_pages:
            raise ValueError(f"Ungültige Trennseite {split_page} für PDF mit {total_pages} Seiten")
            
        path1 = generate_branch_path(pdf_path, f"branch_teil1_p1-{split_page}", output_dir)
        path2 = generate_branch_path(pdf_path, f"branch_teil2_p{split_page + 1}-{total_pages}", output_dir)
        
        doc1 = fitz.open()
        doc1.insert_pdf(doc, from_page=0, to_page=split_page - 1)
        doc1.save(path1)
        
        doc2 = fitz.open()
        doc2.insert_pdf(doc, from_page=split_page, to_page=total_pages - 1)
        doc2.save(path2)
        
        _logger.info(f"Split erfolgreich: '{pdf_path}' -> '{path1}' ({split_page} S.) & '{path2}' ({total_pages - split_page} S.)")
        return path1, path2
        
    finally:
        if doc1 is not None:
            doc1.close()
        if doc2 is not None:
            doc2.close()
        if doc is not None:
            doc.close()


def merge_branches(items: List[Tuple[str, Optional[List[int]]]], output_path: str) -> bool:
    """
    Führt Seitenauszüge aus mehreren PDF-Quellen zu einem neuen Branch-Dokument zusammen.
    
    Args:
        items: Liste von Tupeln (pdf_path, page_list_1based). None = alle Seiten.
        output_path: Ziel-Pfad der zusammengestellten Branch-PDF.
        
    Returns:
        True bei Erfolg
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF ist nicht verfügbar")
        
    out_doc = None
    try:
        out_doc = fitz.open()
        total_inserted = 0
        
        for pdf_path, pages in items:
            if not Path(pdf_path).exists():
                _logger.warning(f"Branch-Merge Überspringe nicht existierende Datei: {pdf_path}")
                continue
                
            src_doc = None
            try:
                src_doc = fitz.open(pdf_path)
                page_count = len(src_doc)
                
                if pages is None:
                    target_indices = list(range(page_count))
                else:
                    target_indices = [p - 1 for p in pages if 0 < p <= page_count]
                    
                for idx in target_indices:
                    out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                    total_inserted += 1
            finally:
                if src_doc is not None:
                    src_doc.close()
                    
        if total_inserted == 0:
            _logger.warning("Branch-Merge: Keine Seiten zum Einfügen vorhanden")
            return False
            
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        out_doc.save(output_path)
        _logger.info(f"Branch-Merge erfolgreich: {total_inserted} Seiten in '{output_path}'")
        return True
        
    finally:
        if out_doc is not None:
            out_doc.close()


def save_marker_file(pdf_path: str, markers: Dict[int, str], marker_path: Optional[str] = None) -> str:
    """
    Speichert Markierungen (Seitennummer 0-basiert -> Marker 'm'/'d'/'k') in einer .dokuzen_marker Datei.
    
    Args:
        pdf_path: Pfad des Original-PDFs
        markers: Dictionary {page_index: marker_code}
        marker_path: Optionaler Dateipfad (Standard: Original-Name + '.dokuzen_marker')
        
    Returns:
        Pfad der erzeugten Marker-Datei
    """
    p = Path(pdf_path)
    if not marker_path:
        out_p = p.parent / f"{p.name}.dokuzen_marker"
    else:
        out_p = Path(marker_path)
        
    data = {
        "format": "dokuzen_marker_v1",
        "source_file": p.name,
        "markers": {str(k): v for k, v in markers.items() if v != 'none'}
    }
    
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    _logger.info(f"Markerdatei gespeichert: {out_p}")
    return str(out_p)


def load_marker_file(marker_path: str) -> Dict[int, str]:
    """
    Lädt Markierungen aus einer .dokuzen_marker Datei.
    
    Args:
        marker_path: Pfad der Marker-Datei
        
    Returns:
        Dictionary {page_index (int): marker_code (str)}
    """
    p = Path(marker_path)
    if not p.exists():
        raise FileNotFoundError(f"Markerdatei nicht gefunden: {marker_path}")
        
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    raw_markers = data.get("markers", {})
    return {int(k): str(v) for k, v in raw_markers.items()}
