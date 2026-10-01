#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Folder Scanner
========================
Rekursives Durchsuchen von Ordnern mit Filterung von System- und temporären Dateien.
"""

import os
from pathlib import Path
from typing import List, Set, Optional

from utils.logger import LoggerMixin
from .models import FileType
from .detector import FormatDetector


class FolderScanner(LoggerMixin):
    """
    Durchsucht Verzeichnisse und filtert Ingest-Kandidaten.
    """

    IGNORE_DIRS = {
        ".git", ".svn", ".hg", ".idea", ".vscode", "__pycache__",
        "node_modules", ".pytest_cache", ".ruff_cache", "venv", ".venv",
        "env", ".env", "build", "dist", "_archive"
    }

    IGNORE_PREFIXES = (".", "~", "$")
    IGNORE_SUFFIXES = (".tmp", ".temp", ".bak", ".swp", ".lock")

    def __init__(self, detector: Optional[FormatDetector] = None):
        self.detector = detector or FormatDetector()
        self.logger.debug("FolderScanner initialisiert")

    def should_ignore_dir(self, dir_name: str) -> bool:
        """Prüft, ob ein Verzeichnis ignoriert werden soll."""
        if dir_name in self.IGNORE_DIRS:
            return True
        if dir_name.startswith(self.IGNORE_PREFIXES):
            return True
        return False

    def should_ignore_file(self, file_name: str) -> bool:
        """Prüft, ob eine Datei ignoriert werden soll."""
        if file_name.startswith(self.IGNORE_PREFIXES):
            return True
        lower = file_name.lower()
        if lower.endswith(self.IGNORE_SUFFIXES):
            return True
        if lower in ("thumbs.db", "desktop.ini", ".ds_store"):
            return True
        return False

    def scan_path(
        self,
        path: str,
        recursive: bool = True,
        max_depth: int = 10,
        only_supported: bool = True
    ) -> List[str]:
        """
        Scannt einen Pfad (Datei oder Verzeichnis) und gibt alle Ingest-Dateien zurück.
        """
        p = Path(path)
        if not p.exists():
            return []

        if p.is_file():
            if self.should_ignore_file(p.name):
                return []
            if only_supported:
                ft = self.detector.detect_file_type(str(p))
                if ft == FileType.UNSUPPORTED:
                    return []
            return [str(p.resolve())]

        if not p.is_dir():
            return []

        # Verzeichnis durchsuchen
        discovered: List[str] = []
        root_depth = len(p.resolve().parts)

        for root, dirs, files in os.walk(str(p.resolve())):
            # Tiefenbegrenzung prüfen
            current_depth = len(Path(root).parts) - root_depth
            if max_depth is not None and current_depth > max_depth:
                dirs.clear()
                continue

            # Zu ignorierende Verzeichnisse aus dirs entfernen (in-place für os.walk)
            dirs[:] = [d for d in dirs if not self.should_ignore_dir(d)]

            if not recursive:
                dirs.clear()
            elif max_depth is not None and current_depth >= max_depth:
                dirs.clear()

            for fname in files:
                if self.should_ignore_file(fname):
                    continue
                fpath = os.path.join(root, fname)
                if only_supported:
                    ft = self.detector.detect_file_type(fpath)
                    if ft == FileType.UNSUPPORTED:
                        continue
                discovered.append(str(Path(fpath).resolve()))

        return discovered

    def scan_multiple(
        self,
        paths: List[str],
        recursive: bool = True,
        max_depth: int = 10,
        only_supported: bool = True
    ) -> List[str]:
        """
        Scannt eine Liste von Dateien und/oder Verzeichnissen, dedupliziert die Resultate.
        """
        result: List[str] = []
        seen: Set[str] = set()

        for p in paths:
            found = self.scan_path(
                p,
                recursive=recursive,
                max_depth=max_depth,
                only_supported=only_supported
            )
            for item in found:
                if item not in seen:
                    seen.add(item)
                    result.append(item)

        return sorted(result)

    # Alias
    scan = scan_path
