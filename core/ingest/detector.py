#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Format Detector
=========================
Automatische Formaterkennung via Dateierweiterung und Magic-Byte-Sniffing.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, Set, Tuple

from utils.logger import LoggerMixin
from .models import FileType, IngestAction, IngestCandidate


class FormatDetector(LoggerMixin):
    """
    Erkennt Dateiformate und leitet empfohlene Ingest-Aktionen ab.
    """

    EXT_MAP = {
        # PDF
        ".pdf": FileType.PDF,
        # Office
        ".docx": FileType.OFFICE,
        ".doc": FileType.OFFICE,
        ".odt": FileType.OFFICE,
        ".rtf": FileType.OFFICE,
        # Text & Markdown
        ".txt": FileType.TEXT_MARKDOWN,
        ".md": FileType.TEXT_MARKDOWN,
        ".markdown": FileType.TEXT_MARKDOWN,
        ".rst": FileType.TEXT_MARKDOWN,
        # Bilder
        ".jpg": FileType.IMAGE,
        ".jpeg": FileType.IMAGE,
        ".png": FileType.IMAGE,
        ".gif": FileType.IMAGE,
        ".bmp": FileType.IMAGE,
        ".tiff": FileType.IMAGE,
        ".tif": FileType.IMAGE,
        ".webp": FileType.IMAGE,
        # Tabellen
        ".xlsx": FileType.SPREADSHEET,
        ".xls": FileType.SPREADSHEET,
        ".csv": FileType.SPREADSHEET,
        # Web
        ".html": FileType.WEB_HTML,
        ".htm": FileType.WEB_HTML,
        # Code & Konfiguration
        ".py": FileType.CODE,
        ".json": FileType.CODE,
        ".xml": FileType.CODE,
        ".yaml": FileType.CODE,
        ".yml": FileType.CODE,
        ".sql": FileType.CODE,
        ".log": FileType.CODE,
        ".sh": FileType.CODE,
        ".bat": FileType.CODE,
        # SQLite
        ".db": FileType.CODE,
        ".sqlite": FileType.CODE,
        ".sqlite3": FileType.CODE,
    }

    # Formate, die direkt von der Bibliothek unterstützt werden
    LIBRARY_SUPPORTED_EXTS = {
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
        ".xlsx", ".xls", ".csv",
        ".py", ".log", ".json", ".xml", ".html", ".htm", ".md", ".markdown",
        ".db", ".sqlite", ".sqlite3"
    }

    # Formate, die nach PDF gewandelt werden können
    CONVERTIBLE_TO_PDF_EXTS = {
        ".docx", ".txt", ".md", ".markdown", ".html", ".htm",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"
    }

    def __init__(self):
        self._known_hashes: Set[str] = set()
        self.logger.debug("FormatDetector initialisiert")

    def compute_hash(self, path: str) -> str:
        """Berechnet den SHA-256 Hash einer Datei."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def register_existing_hash(self, file_hash: str):
        """Registriert einen bekannten Hash zur Duplikatserkennung."""
        self._known_hashes.add(file_hash)

    def is_duplicate(self, path: str) -> Tuple[bool, Optional[str]]:
        """Prüft, ob eine Datei anhand ihres Hashes bereits existiert."""
        try:
            h = self.compute_hash(path)
            if h in self._known_hashes:
                return True, h
            return False, h
        except (OSError, PermissionError):
            return False, None

    @staticmethod
    def _is_path_in_existing(path: str, existing_paths: Optional[Set[str]]) -> bool:
        """Prüft robust (inkl. Windows Case-Insensitivität und Slash-Varianten), ob ein Pfad bereits existiert."""
        if not existing_paths:
            return False
        abs_p = os.path.abspath(path)
        if path in existing_paths or abs_p in existing_paths:
            return True
        norm_p = os.path.normcase(abs_p)
        for ep in existing_paths:
            if os.path.normcase(os.path.abspath(ep)) == norm_p:
                return True
        return False

    def detect_file_type(self, path: str) -> FileType:
        """
        Ermittelt den Dateityp anhand der Erweiterung oder des Dateiinhalts (Magic Bytes).
        """
        p = Path(path)
        if p.is_dir():
            return FileType.FOLDER

        ext = p.suffix.lower()
        if ext in self.EXT_MAP:
            return self.EXT_MAP[ext]

        # Fallback: Sniffing von Magic Bytes
        if p.is_file():
            sniffed = self.sniff_magic_bytes(path)
            if sniffed != FileType.UNSUPPORTED:
                return sniffed

        return FileType.UNSUPPORTED

    def sniff_magic_bytes(self, path: str) -> FileType:
        """
        Liest die ersten Bytes der Datei, um unbekannte/erweiterungslose Dateien zu klassifizieren.
        """
        try:
            with open(path, "rb") as f:
                header = f.read(512)
        except (OSError, PermissionError):
            return FileType.UNSUPPORTED

        if not header:
            return FileType.UNSUPPORTED

        # PDF Magic Bytes
        if header.startswith(b"%PDF-"):
            return FileType.PDF

        # PNG
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return FileType.IMAGE

        # JPEG
        if header.startswith(b"\xff\xd8\xff"):
            return FileType.IMAGE

        # GIF
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return FileType.IMAGE

        # BMP
        if header.startswith(b"BM"):
            return FileType.IMAGE

        # TIFF
        if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
            return FileType.IMAGE

        # WebP (RIFF .... WEBP)
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            return FileType.IMAGE

        # HTML
        stripped = header.lstrip().lower()
        if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
            return FileType.WEB_HTML

        # Zip-basiertes Office (DOCX / XLSX)
        if header.startswith(b"PK\x03\x04"):
            # Prüfen ob Zip Word/Excel-Inhalte enthält
            if b"word/" in header or b"[Content_Types].xml" in header:
                return FileType.OFFICE
            if b"xl/" in header:
                return FileType.SPREADSHEET

        # Einfacher UTF-8 / ASCII Text (darf keine Null-Bytes enthalten)
        if b"\x00" not in header:
            try:
                header.decode("utf-8")
                return FileType.TEXT_MARKDOWN
            except UnicodeDecodeError:
                pass

        return FileType.UNSUPPORTED

    def is_convertible_to_pdf(self, path: str) -> bool:
        """Prüft, ob die Datei in ein PDF umgewandelt werden kann."""
        ext = Path(path).suffix.lower()
        if ext:
            return ext in self.CONVERTIBLE_TO_PDF_EXTS
        ft = self.detect_file_type(path)
        return ft in (FileType.IMAGE, FileType.TEXT_MARKDOWN, FileType.WEB_HTML)

    def determine_action(
        self,
        file_type: FileType,
        path: str,
        existing_paths: Optional[Set[str]] = None,
        auto_convert_non_pdf: bool = True
    ) -> IngestAction:
        """
        Bestimmt die empfohlene Ingest-Aktion.
        """
        if self._is_path_in_existing(path, existing_paths):
            return IngestAction.SKIP_DUPLICATE

        if file_type == FileType.PDF:
            return IngestAction.ADD_DIRECT

        if file_type in (FileType.OFFICE, FileType.IMAGE, FileType.TEXT_MARKDOWN, FileType.WEB_HTML):
            if auto_convert_non_pdf and self.is_convertible_to_pdf(path):
                return IngestAction.CONVERT_TO_PDF
            ext = Path(path).suffix.lower()
            if ext in self.LIBRARY_SUPPORTED_EXTS:
                return IngestAction.ADD_DIRECT
            return IngestAction.UNSUPPORTED

        if file_type in (FileType.SPREADSHEET, FileType.CODE):
            ext = Path(path).suffix.lower()
            if ext in self.LIBRARY_SUPPORTED_EXTS:
                return IngestAction.ADD_DIRECT
            return IngestAction.UNSUPPORTED

        return IngestAction.UNSUPPORTED

    def create_candidate(
        self,
        path: str,
        existing_paths: Optional[Set[str]] = None,
        auto_convert_non_pdf: bool = True
    ) -> IngestCandidate:
        """
        Erstellt ein IngestCandidate-Objekt mit allen Metadaten.
        """
        p = Path(path)
        exists = p.exists()
        size_bytes = 0
        if exists and p.is_file():
            try:
                size_bytes = p.stat().st_size
            except (OSError, PermissionError):
                size_bytes = 0

        file_type = self.detect_file_type(path)
        is_duplicate = self._is_path_in_existing(path, existing_paths)

        rec_action = self.determine_action(
            file_type,
            path,
            existing_paths=existing_paths,
            auto_convert_non_pdf=auto_convert_non_pdf
        )

        return IngestCandidate(
            path=str(p.resolve()) if exists else str(p),
            file_type=file_type,
            recommended_action=rec_action,
            selected_action=rec_action,
            size_bytes=size_bytes,
            mime_hint=f"type/{file_type.value}",
            is_duplicate=is_duplicate,
            exists=exists
        )
