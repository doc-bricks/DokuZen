#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Smart Ingest Data Models
==================================
Datenstrukturen für Erkennung, Klassifikation und Ingest von Dokumenten.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List


class FileType(Enum):
    """Klassifizierte Dateitypen für Ingest und Routing."""
    PDF = "pdf"
    OFFICE = "office"
    TEXT_MARKDOWN = "text_markdown"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    WEB_HTML = "web_html"
    CODE = "code"
    FOLDER = "folder"
    UNSUPPORTED = "unsupported"


class IngestAction(Enum):
    """Mögliche Ingest-Aktionen."""
    ADD_DIRECT = "add_direct"
    CONVERT_TO_PDF = "convert_to_pdf"
    SKIP_DUPLICATE = "skip_duplicate"
    UNSUPPORTED = "unsupported"


@dataclass
class IngestCandidate:
    """Repräsentiert eine für den Ingest vorgeschlagene Datei oder Quelle."""
    path: str
    file_type: FileType
    recommended_action: IngestAction
    selected_action: IngestAction
    size_bytes: int = 0
    mime_hint: str = ""
    is_duplicate: bool = False
    exists: bool = True

    @property
    def name(self) -> str:
        """Dateiname ohne Pfad."""
        return Path(self.path).name

    @property
    def extension(self) -> str:
        """Dateierweiterung (lowercase mit Punkt)."""
        return Path(self.path).suffix.lower()

    @property
    def size_human(self) -> str:
        """Menschenlesbare Dateigröße."""
        size = float(self.size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


@dataclass
class IngestResult:
    """Ergebnis der Ingest-Aktion für eine Datei."""
    candidate: IngestCandidate
    success: bool
    output_path: Optional[str] = None
    action_performed: IngestAction = IngestAction.ADD_DIRECT
    error: Optional[str] = None


@dataclass
class IngestSummary:
    """Zusammenfassung eines vollständigen Ingest-Durchlaufs."""
    total_candidates: int = 0
    added_count: int = 0
    converted_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    results: List[IngestResult] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Alias für total_candidates."""
        return self.total_candidates

    @property
    def success_rate(self) -> float:
        """Erfolgsquote in Prozent (0.0 bis 100.0)."""
        if self.total_candidates == 0:
            return 100.0
        successful = self.added_count + self.converted_count + self.skipped_count
        return (successful / self.total_candidates) * 100.0

