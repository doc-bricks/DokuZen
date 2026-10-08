#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Headless Batch CLI
================================
Headless-Ausführung von PDF- und Dokumentenoperationen (Merge, OCR, Redaction, Info)
ohne GUI / Qt-Event-Loop für Automations-Skripte, CI/CD und Agenten-Workflows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass
class BatchResult:
    """Ergebnis einer Headless-Batch-Operation."""

    success: bool
    action: str
    input_files: List[str] = field(default_factory=list)
    output_file: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert das Ergebnis in ein serialisierbares Dictionary."""
        return asdict(self)


def batch_merge(
    input_files: Sequence[str | Path],
    output_file: str | Path,
) -> BatchResult:
    """Führt mehrere PDF-Dateien ohne GUI zusammen."""
    normalized_inputs = [str(Path(p).resolve()) for p in input_files]
    dst = str(Path(output_file).resolve())

    if not normalized_inputs:
        return BatchResult(
            success=False,
            action="merge",
            output_file=dst,
            error="Keine Eingabedateien angegeben.",
        )

    # Prüfen, ob alle Eingabedateien existieren
    missing = [p for p in normalized_inputs if not os.path.exists(p)]
    if missing:
        return BatchResult(
            success=False,
            action="merge",
            input_files=normalized_inputs,
            output_file=dst,
            error=f"Eingabedatei(en) nicht gefunden: {', '.join(missing)}",
        )

    try:
        from core.pdf.merger import PDFMerger, MergeItem, PYMUPDF_AVAILABLE
    except ImportError as e:
        return BatchResult(
            success=False,
            action="merge",
            input_files=normalized_inputs,
            output_file=dst,
            error=f"PDFMerger-Modul konnte nicht geladen werden: {e}",
        )

    if not PYMUPDF_AVAILABLE:
        return BatchResult(
            success=False,
            action="merge",
            input_files=normalized_inputs,
            output_file=dst,
            error="PyMuPDF (fitz) ist nicht installiert.",
        )

    # Zielverzeichnis anlegen
    Path(dst).parent.mkdir(parents=True, exist_ok=True)

    items = [MergeItem(path=p) for p in normalized_inputs]
    merger = PDFMerger()
    res = merger.merge(items, dst)

    if res.success:
        return BatchResult(
            success=True,
            action="merge",
            input_files=normalized_inputs,
            output_file=dst,
            details={"page_count": res.page_count},
        )
    return BatchResult(
        success=False,
        action="merge",
        input_files=normalized_inputs,
        output_file=dst,
        error=res.error or "Zusammenführen fehlgeschlagen.",
    )


def batch_ocr(
    input_file: str | Path,
    output_file: Optional[str | Path] = None,
    language: str = "deu+eng",
    ocr_format: str = "text",
) -> BatchResult:
    """Führt OCR auf einer PDF oder einem Bild headlessly durch."""
    src = str(Path(input_file).resolve())
    dst = str(Path(output_file).resolve()) if output_file else None

    if not os.path.exists(src):
        return BatchResult(
            success=False,
            action="ocr",
            input_files=[src],
            output_file=dst,
            error=f"Eingabedatei nicht gefunden: {src}",
        )

    try:
        from core.ocr.engine import OCREngine
    except ImportError as e:
        return BatchResult(
            success=False,
            action="ocr",
            input_files=[src],
            output_file=dst,
            error=f"OCREngine-Modul konnte nicht geladen werden: {e}",
        )

    engine = OCREngine()
    if not engine.is_available:
        return BatchResult(
            success=False,
            action="ocr",
            input_files=[src],
            output_file=dst,
            error="Tesseract OCR ist auf diesem System nicht verfügbar oder nicht im PATH konfiguriert.",
        )

    is_pdf = src.lower().endswith(".pdf")

    if ocr_format == "pdf":
        if not is_pdf:
            return BatchResult(
                success=False,
                action="ocr",
                input_files=[src],
                output_file=dst,
                error="Das Ausgabeformat 'pdf' (durchsuchbare PDF) erfordert eine PDF-Eingabedatei.",
            )
        if not dst:
            return BatchResult(
                success=False,
                action="ocr",
                input_files=[src],
                error="Für das Ausgabeformat 'pdf' muss eine Ausgabedatei (-o / --output) angegeben werden.",
            )
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        ok = engine.pdf_to_searchable_pdf(src, dst, language=language)
        if ok:
            return BatchResult(
                success=True,
                action="ocr",
                input_files=[src],
                output_file=dst,
                details={"format": "searchable_pdf", "language": language},
            )
        return BatchResult(
            success=False,
            action="ocr",
            input_files=[src],
            output_file=dst,
            error="Erstellung der durchsuchbaren PDF fehlgeschlagen.",
        )

    # Format 'text'
    if is_pdf:
        results = engine.recognize_pdf(src, language=language)
        if not results:
            return BatchResult(
                success=False,
                action="ocr",
                input_files=[src],
                output_file=dst,
                error="Keine OCR-Ergebnisse oder PDF konnte nicht gerendert werden.",
            )
        full_text = "\n\n".join(r.text for r in results)
        avg_conf = (
            sum(r.confidence for r in results) / len(results) if results else 0.0
        )
        total_words = sum(r.word_count for r in results)
        details = {
            "format": "text",
            "page_count": len(results),
            "total_words": total_words,
            "average_confidence": round(avg_conf, 2),
            "text": full_text,
        }
    else:
        res = engine.recognize_image(src, language=language)
        if not res.success:
            return BatchResult(
                success=False,
                action="ocr",
                input_files=[src],
                output_file=dst,
                error=res.error or "Bild-Texterkennung fehlgeschlagen.",
            )
        full_text = res.text
        details = {
            "format": "text",
            "page_count": 1,
            "total_words": len(full_text.split()),
            "average_confidence": round(res.confidence, 2),
            "text": full_text,
        }

    if dst:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(full_text)

    return BatchResult(
        success=True,
        action="ocr",
        input_files=[src],
        output_file=dst,
        details=details,
    )


def batch_redact(
    input_file: str | Path,
    output_file: str | Path,
    terms: Optional[Sequence[str]] = None,
    blacklist_file: Optional[str | Path] = None,
    sensitive_types: Optional[Sequence[str]] = None,
) -> BatchResult:
    """Führt Schwärzung sensibler Begriffe und Formate in einer PDF durch."""
    src = str(Path(input_file).resolve())
    dst = str(Path(output_file).resolve())

    if not os.path.exists(src):
        return BatchResult(
            success=False,
            action="redact",
            input_files=[src],
            output_file=dst,
            error=f"Eingabedatei nicht gefunden: {src}",
        )

    if not src.lower().endswith(".pdf"):
        return BatchResult(
            success=False,
            action="redact",
            input_files=[src],
            output_file=dst,
            error="Schwärzung unterstützt aktuell ausschließlich PDF-Dateien.",
        )

    try:
        from core.redaction.detector import (
            RedactionDetector,
            RedactionApplier,
            extract_page_text_and_char_rects,
            SensitiveType,
        )
        import fitz
    except ImportError as e:
        return BatchResult(
            success=False,
            action="redact",
            input_files=[src],
            output_file=dst,
            error=f"Redaction-Modul konnte nicht geladen werden: {e}",
        )

    detector = RedactionDetector()

    # Blacklist-Datei laden falls angegeben
    if blacklist_file:
        bf = str(Path(blacklist_file).resolve())
        if not os.path.exists(bf):
            return BatchResult(
                success=False,
                action="redact",
                input_files=[src],
                output_file=dst,
                error=f"Blacklist-Datei nicht gefunden: {bf}",
            )
        count = detector.load_blacklist(bf)
        _logger.info("Blacklist geladen: %d Wörter aus %s", count, bf)

    # Benutzerdefinierte Suchbegriffe hinzufügen
    if terms:
        for term in terms:
            if term.strip():
                detector.add_to_blacklist(term.strip())

    doc = None
    all_matches = []
    try:
        doc = fitz.open(src)
        for i, page in enumerate(doc):
            text, char_rects = extract_page_text_and_char_rects(page)
            matches = detector.detect(text, page=i + 1, char_rects=char_rects)
            # Falls Sensitiv-Typen eingeschränkt wurden
            if sensitive_types:
                types_lower = {t.lower() for t in sensitive_types}
                matches = [
                    m
                    for m in matches
                    if m.type.value.lower() in types_lower
                    or (m.type == SensitiveType.CUSTOM and "custom" in types_lower)
                ]
            all_matches.extend(matches)
    except Exception as e:
        return BatchResult(
            success=False,
            action="redact",
            input_files=[src],
            output_file=dst,
            error=f"Fehler bei der Erkennung sensibler Inhalte: {e}",
        )
    finally:
        if doc is not None:
            doc.close()

    applier = RedactionApplier()
    if all_matches:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        ok = applier.redact_pdf(src, dst, all_matches)
        stats = applier.last_redaction_stats
        if ok:
            return BatchResult(
                success=True,
                action="redact",
                input_files=[src],
                output_file=dst,
                details={
                    "total_matches": len(all_matches),
                    "redacted_count": stats.get("redacted", 0),
                    "missed_count": stats.get("missed", 0),
                },
            )
        return BatchResult(
            success=False,
            action="redact",
            input_files=[src],
            output_file=dst,
            error="Anwendung der Schwärzungen auf PDF fehlgeschlagen.",
        )

    # Keine Treffer -> unverändert kopieren
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    try:
        import shutil

        shutil.copyfile(src, dst)
        return BatchResult(
            success=True,
            action="redact",
            input_files=[src],
            output_file=dst,
            details={"total_matches": 0, "redacted_count": 0, "missed_count": 0},
        )
    except Exception as e:
        return BatchResult(
            success=False,
            action="redact",
            input_files=[src],
            output_file=dst,
            error=f"Kopieren der ungeschwärzten Datei fehlgeschlagen: {e}",
        )


def batch_info(input_file: str | Path) -> BatchResult:
    """Extrahiert Metadaten und Seitenanzahl einer PDF headlessly."""
    src = str(Path(input_file).resolve())
    if not os.path.exists(src):
        return BatchResult(
            success=False,
            action="info",
            input_files=[src],
            error=f"Datei nicht gefunden: {src}",
        )

    try:
        from core.pdf.reader import get_pdf_info, PYMUPDF_AVAILABLE
    except ImportError as e:
        return BatchResult(
            success=False,
            action="info",
            input_files=[src],
            error=f"PDFReader-Modul konnte nicht geladen werden: {e}",
        )

    if not PYMUPDF_AVAILABLE:
        return BatchResult(
            success=False,
            action="info",
            input_files=[src],
            error="PyMuPDF (fitz) ist nicht installiert.",
        )

    info = get_pdf_info(src)
    if info is None:
        return BatchResult(
            success=False,
            action="info",
            input_files=[src],
            error="PDF-Informationen konnten nicht gelesen werden.",
        )

    details = {
        "file_name": Path(info.path).name,
        "path": info.path,
        "page_count": info.page_count,
        "is_encrypted": info.is_encrypted,
        "is_locked": info.is_locked,
        "has_text": info.has_text,
        "has_images": info.has_images,
        "file_size": info.file_size,
        "metadata": {
            "title": info.metadata.title,
            "author": info.metadata.author,
            "subject": info.metadata.subject,
            "creator": info.metadata.creator,
            "producer": info.metadata.producer,
        },
    }
    return BatchResult(
        success=True,
        action="info",
        input_files=[src],
        details=details,
    )


def execute_headless_cli(args: argparse.Namespace) -> int:
    """Führt eine Headless-CLI-Aktion aus und steuert Exit-Codes."""
    result: Optional[BatchResult] = None

    # Merge
    if getattr(args, "merge_paths", None):
        if not getattr(args, "output_path", None):
            err_msg = "Für das Headless-Merge muss eine Ausgabedatei (-o / --output) angegeben werden."
            if getattr(args, "json_output", False):
                print(json.dumps({"success": False, "error": err_msg}, indent=2, ensure_ascii=False))
            else:
                print(f"FEHLER: {err_msg}", file=sys.stderr)
            return 2
        result = batch_merge(args.merge_paths, args.output_path)

    # OCR
    elif getattr(args, "ocr_path", None):
        result = batch_ocr(
            input_file=args.ocr_path,
            output_file=getattr(args, "output_path", None),
            language=getattr(args, "ocr_lang", "deu+eng"),
            ocr_format=getattr(args, "ocr_format", "text"),
        )

    # Redact
    elif getattr(args, "redact_path", None):
        if not getattr(args, "output_path", None):
            err_msg = "Für das Headless-Schwärzen muss eine Ausgabedatei (-o / --output) angegeben werden."
            if getattr(args, "json_output", False):
                print(json.dumps({"success": False, "error": err_msg}, indent=2, ensure_ascii=False))
            else:
                print(f"FEHLER: {err_msg}", file=sys.stderr)
            return 2
        result = batch_redact(
            input_file=args.redact_path,
            output_file=args.output_path,
            terms=getattr(args, "redact_terms", None),
            blacklist_file=getattr(args, "blacklist_file", None),
            sensitive_types=getattr(args, "sensitive_types", None),
        )

    # Info
    elif getattr(args, "info_path", None):
        result = batch_info(input_file=args.info_path)

    else:
        err_msg = "Keine gültige Headless-Aktion angegeben (--merge, --ocr, --redact oder --info erforderlich)."
        if getattr(args, "json_output", False):
            print(json.dumps({"success": False, "error": err_msg}, indent=2, ensure_ascii=False))
        else:
            print(f"FEHLER: {err_msg}", file=sys.stderr)
        return 2

    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        if result.success:
            print(f"[OK] DokuZen Headless {result.action.upper()}: Vorgang erfolgreich abgeschlossen.")
            if result.output_file:
                print(f"     Ausgabedatei: {result.output_file}")
            if result.details:
                for k, v in result.details.items():
                    if k != "text":
                        print(f"     {k}: {v}")
                    elif not result.output_file and k == "text":
                        print("\n--- Extrahierter Text ---")
                        print(v)
        else:
            print(f"[FEHLER] DokuZen Headless {result.action.upper()}: {result.error}", file=sys.stderr)

    return 0 if result.success else 1
