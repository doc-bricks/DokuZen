#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Smart Ingest Service
==============================
Koordiniert Formaterkennung, Konvertierung und Aufnahme in die Dokumentenbibliothek.
"""

import os
from pathlib import Path
from typing import List, Set, Optional, Callable

from utils.logger import LoggerMixin
from core.converter.formats import FormatConverter, OutputFormat
from core.library.manager import LibraryManager
from .models import FileType, IngestAction, IngestCandidate, IngestResult, IngestSummary
from .detector import FormatDetector
from .scanner import FolderScanner


class SmartIngestService(LoggerMixin):
    """
    Zentraler Service für Smart Ingest und Format-Routing.
    """

    def __init__(
        self,
        library_manager: LibraryManager,
        converter: Optional[FormatConverter] = None,
        detector: Optional[FormatDetector] = None,
        scanner: Optional[FolderScanner] = None,
    ):
        self.library = library_manager
        self.converter = converter or FormatConverter()
        self.detector = detector or FormatDetector()
        self.scanner = scanner or FolderScanner(self.detector)
        self.logger.debug("SmartIngestService initialisiert")

    def get_existing_paths(self, theme: Optional[str] = None) -> Set[str]:
        """Ermittelt alle bereits in der Bibliothek vorhandenen Dateipfade (normalisiert)."""
        existing: Set[str] = set()
        try:
            docs = self.library.get_documents(theme=theme)
            for d in docs:
                p = getattr(d, "path", None)
                if p:
                    existing.add(str(Path(p).resolve()))
                    existing.add(os.path.abspath(p))
                    existing.add(os.path.normcase(os.path.abspath(p)))
        except Exception as e:
            self.logger.warning(f"Konnte bestehende Dokumente nicht laden: {e}")
        return existing

    def prepare_candidates(
        self,
        paths: List[str],
        recursive: bool = True,
        auto_convert: bool = True,
        theme: Optional[str] = None,
        max_depth: int = 10,
    ) -> List[IngestCandidate]:
        """
        Scannt Pfade und erstellt analysierte IngestCandidate-Einträge.
        """
        scanned_files = self.scanner.scan_multiple(
            paths,
            recursive=recursive,
            max_depth=max_depth,
            only_supported=True
        )

        existing_paths = self.get_existing_paths(theme=theme)
        candidates: List[IngestCandidate] = []

        for fpath in scanned_files:
            candidate = self.detector.create_candidate(
                fpath,
                existing_paths=existing_paths,
                auto_convert_non_pdf=auto_convert
            )
            candidates.append(candidate)

        return candidates

    def _determine_pdf_output_path(self, input_path: str, output_dir: Optional[str] = None) -> str:
        """Bestimmt einen kollisionsfreien Ziel-PDF-Pfad."""
        src_path = Path(input_path)
        dest_dir = Path(output_dir) if output_dir else src_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        base_stem = src_path.stem
        target = dest_dir / f"{base_stem}.pdf"

        # Falls die Zieldatei bereits existiert und nicht identisch ist: Nummerierung
        counter = 1
        while target.exists():
            try:
                if target.samefile(src_path):
                    break
            except (OSError, ValueError):
                pass
            target = dest_dir / f"{base_stem}_{counter}.pdf"
            counter += 1

        return str(target.resolve())

    def ingest_single(
        self,
        candidate: IngestCandidate,
        theme: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> IngestResult:
        """
        Führt den Ingest für einen einzelnen Kandidaten aus.
        """
        action = candidate.selected_action

        # Fall 1: Duplikat überspringen
        if action == IngestAction.SKIP_DUPLICATE:
            return IngestResult(
                candidate=candidate,
                success=True,
                output_path=candidate.path,
                action_performed=IngestAction.SKIP_DUPLICATE,
                error=None
            )

        # Fall 2: Nicht unterstützt
        if action == IngestAction.UNSUPPORTED or candidate.file_type == FileType.UNSUPPORTED:
            return IngestResult(
                candidate=candidate,
                success=False,
                output_path=None,
                action_performed=IngestAction.UNSUPPORTED,
                error="Format wird für Ingest nicht unterstützt"
            )

        # Fall 3: Direkt zur Bibliothek hinzufügen
        if action == IngestAction.ADD_DIRECT:
            success = self.library.add_document(candidate.path, theme=theme)
            if success:
                return IngestResult(
                    candidate=candidate,
                    success=True,
                    output_path=candidate.path,
                    action_performed=IngestAction.ADD_DIRECT,
                    error=None
                )
            else:
                return IngestResult(
                    candidate=candidate,
                    success=False,
                    output_path=None,
                    action_performed=IngestAction.ADD_DIRECT,
                    error="Bibliothek wies das Dokument ab"
                )

        # Fall 4: Vor Ingest nach PDF konvertieren
        if action == IngestAction.CONVERT_TO_PDF:
            if candidate.file_type == FileType.PDF:
                # Bereits PDF, direkt hinzufügen
                success = self.library.add_document(candidate.path, theme=theme)
                return IngestResult(
                    candidate=candidate,
                    success=success,
                    output_path=candidate.path,
                    action_performed=IngestAction.ADD_DIRECT,
                    error=None if success else "Bibliothek wies das PDF ab"
                )

            target_pdf = self._determine_pdf_output_path(candidate.path, output_dir=output_dir)
            conv_res = self.converter.convert(
                candidate.path,
                target_pdf,
                output_format=OutputFormat.PDF
            )

            if not conv_res.success:
                return IngestResult(
                    candidate=candidate,
                    success=False,
                    output_path=None,
                    action_performed=IngestAction.CONVERT_TO_PDF,
                    error=conv_res.error or "Konvertierung fehlgeschlagen"
                )

            # Erfolgreich konvertiert -> ins Archiv/Bibliothek übernehmen
            lib_success = self.library.add_document(target_pdf, theme=theme)
            if lib_success:
                return IngestResult(
                    candidate=candidate,
                    success=True,
                    output_path=target_pdf,
                    action_performed=IngestAction.CONVERT_TO_PDF,
                    error=None
                )
            else:
                return IngestResult(
                    candidate=candidate,
                    success=False,
                    output_path=target_pdf,
                    action_performed=IngestAction.CONVERT_TO_PDF,
                    error="PDF erstellt, aber Bibliotheksaufnahme fehlgeschlagen"
                )

        return IngestResult(
            candidate=candidate,
            success=False,
            output_path=None,
            action_performed=action,
            error=f"Unbekannte Aktion: {action}"
        )

    def ingest_batch(
        self,
        candidates: List[IngestCandidate],
        theme: Optional[str] = None,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, IngestCandidate, IngestResult], None]] = None,
    ) -> IngestSummary:
        """
        Führt einen Batch-Ingest für eine Liste von Kandidaten aus.
        """
        summary = IngestSummary(total_candidates=len(candidates))

        for idx, candidate in enumerate(candidates):
            res = self.ingest_single(candidate, theme=theme, output_dir=output_dir)
            summary.results.append(res)

            if res.success:
                if res.action_performed == IngestAction.SKIP_DUPLICATE:
                    summary.skipped_count += 1
                elif res.action_performed == IngestAction.CONVERT_TO_PDF:
                    summary.converted_count += 1
                else:
                    summary.added_count += 1
            else:
                summary.failed_count += 1

            if progress_callback:
                progress_callback(idx + 1, len(candidates), candidate, res)

        return summary
