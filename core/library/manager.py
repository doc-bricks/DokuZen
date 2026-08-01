#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Library Manager
=================================
Zentrale Verwaltung der Dokumentenbibliothek.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from utils.logger import LoggerMixin
from .persistence import PersistenceManager
from .themes import ThemeManager


class FilterMode(Enum):
    """Filter-Modi für die Dokumentenliste."""
    ALL = "all"
    READ = "read"
    UNREAD = "unread"


class SortMode(Enum):
    """Sortier-Modi für die Dokumentenliste."""
    NAME = "name"
    DATE_ADDED = "date_added"
    DATE_READ = "date_read"
    SIZE = "size"
    TYPE = "type"


@dataclass
class Document:
    """Repräsentiert ein Dokument in der Bibliothek."""
    path: str
    added: datetime
    is_read: bool = False
    read_date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    @property
    def name(self) -> str:
        """Dateiname ohne Pfad."""
        return Path(self.path).name
    
    @property
    def extension(self) -> str:
        """Dateierweiterung (lowercase)."""
        return Path(self.path).suffix.lower()
    
    @property
    def exists(self) -> bool:
        """Prüft, ob die Datei existiert."""
        return Path(self.path).exists()
    
    @property
    def size(self) -> int:
        """Dateigröße in Bytes (0 wenn nicht vorhanden)."""
        try:
            return Path(self.path).stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    @property
    def size_human(self) -> str:
        """Menschenlesbare Dateigröße."""
        size = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dictionary."""
        return {
            "path": self.path,
            "added": self.added.isoformat(),
            "is_read": self.is_read,
            "read_date": self.read_date.isoformat() if self.read_date else None,
            "tags": self.tags,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Document":
        """Erstellt Document aus Dictionary."""
        def _safe_iso(val):
            """BUG-U5: korruptes/leeres Datum aus JSON → None statt ValueError."""
            if not val:
                return None
            try:
                return datetime.fromisoformat(val)
            except (ValueError, TypeError):
                return None

        return cls(
            path=data["path"],
            added=_safe_iso(data.get("added")) or datetime.min,
            is_read=data.get("is_read", False),
            read_date=_safe_iso(data.get("read_date")),
            tags=data.get("tags", []),
            notes=data.get("notes", "")
        )


class LibraryManager(LoggerMixin):
    """
    Zentrale Verwaltung der Dokumentenbibliothek.
    
    Koordiniert PersistenceManager und ThemeManager.
    """
    
    # Unterstützte Dateierweiterungen
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
        ".xlsx", ".xls", ".csv",
        ".py", ".log", ".json", ".xml", ".html", ".md",
        ".db", ".sqlite", ".sqlite3"
    }
    
    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialisiert den Library Manager.
        
        Args:
            state_file: Pfad zur State-Datei (optional)
        """
        self._persistence = PersistenceManager(state_file)
        self._themes = ThemeManager(self._persistence)
        
        self._filter_mode = FilterMode.ALL
        self._sort_mode = SortMode.NAME
        self._sort_reverse = False
        self._search_query = ""
        
        self._callbacks: List[Callable] = []
        
        self.logger.info("LibraryManager initialisiert")
    
    def initialize(self) -> bool:
        """
        Initialisiert die Bibliothek (lädt State).
        
        Returns:
            True bei Erfolg
        """
        success = self._persistence.load()
        if success:
            # Einstellungen laden
            self._filter_mode = FilterMode(
                self._persistence.get_setting("filter", "all")
            )
            self._sort_mode = SortMode(
                self._persistence.get_setting("sort_by", "name")
            )
            self.logger.info("Bibliothek initialisiert")
        return success
    
    def save(self) -> bool:
        """Speichert den aktuellen Zustand."""
        return self._persistence.save()
    
    def shutdown(self):
        """Beendet den Manager und speichert."""
        self.save()
        self.logger.info("LibraryManager beendet")
    
    # === Theme-Zugriff ===
    
    @property
    def themes(self) -> ThemeManager:
        """Zugriff auf den ThemeManager."""
        return self._themes
    
    # === Dokument-Operationen ===
    
    def get_documents(self, theme: Optional[str] = None) -> List[Document]:
        """
        Gibt Dokumente zurück (gefiltert und sortiert).
        
        Args:
            theme: Themenname (oder aktuelles Thema)
            
        Returns:
            Liste von Document-Objekten
        """
        if theme is None:
            theme = self._themes.get_current_theme()
        
        if not theme:
            return []
        
        raw_docs = self._persistence.get_documents(theme)
        documents = [Document.from_dict(d) for d in raw_docs]
        
        # Filter anwenden
        documents = self._apply_filter(documents)
        
        # Suche anwenden
        if self._search_query:
            documents = self._apply_search(documents)
        
        # Sortieren
        documents = self._apply_sort(documents)
        
        return documents
    
    def add_document(self, path: str, theme: Optional[str] = None) -> bool:
        """
        Fügt ein Dokument hinzu.
        
        Args:
            path: Dateipfad
            theme: Zielthema (oder aktuelles Thema)
            
        Returns:
            True bei Erfolg
        """
        path = str(Path(path).resolve())
        
        if theme is None:
            theme = self._themes.get_current_theme()
        
        if not theme:
            return False
        
        # Erweiterung prüfen
        ext = Path(path).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            self.logger.warning(f"Nicht unterstützte Erweiterung: {ext}")
            return False
        
        success = self._persistence.add_document(theme, path)
        if success:
            self._notify_change("document_added", path, theme)
        return success
    
    def add_documents(self, paths: List[str], theme: Optional[str] = None) -> Tuple[int, int]:
        """
        Fügt mehrere Dokumente hinzu.
        
        Returns:
            Tuple (erfolgreich, fehlgeschlagen)
        """
        success_count = 0
        fail_count = 0
        
        for path in paths:
            if self.add_document(path, theme):
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count
    
    def remove_document(self, path: str, theme: Optional[str] = None) -> bool:
        """Entfernt ein Dokument aus der Bibliothek."""
        if theme is None:
            theme = self._themes.get_current_theme()
        
        success = self._persistence.remove_document(theme, path)
        if success:
            self._notify_change("document_removed", path, theme)
        return success
    
    def set_read_status(self, path: str, is_read: bool, theme: Optional[str] = None) -> bool:
        """Setzt den Gelesen-Status."""
        if theme is None:
            theme = self._themes.get_current_theme()
        
        success = self._persistence.set_document_read(theme, path, is_read)
        if success:
            self._notify_change("document_status_changed", path, is_read)
        return success
    
    def toggle_read_status(self, path: str, theme: Optional[str] = None) -> bool:
        """Wechselt den Gelesen-Status."""
        docs = self.get_documents(theme)
        for doc in docs:
            if doc.path == path:
                return self.set_read_status(path, not doc.is_read, theme)
        return False
    
    # === Filter & Sortierung ===
    
    def set_filter(self, mode: FilterMode):
        """Setzt den Filter-Modus."""
        self._filter_mode = mode
        self._persistence.set_setting("filter", mode.value)
        self._notify_change("filter_changed", mode)
    
    def set_sort(self, mode: SortMode, reverse: bool = False):
        """Setzt die Sortierung."""
        self._sort_mode = mode
        self._sort_reverse = reverse
        self._persistence.set_setting("sort_by", mode.value)
        self._notify_change("sort_changed", mode)
    
    def set_search(self, query: str):
        """Setzt die Suchabfrage."""
        self._search_query = query.lower().strip()
        self._notify_change("search_changed", query)
    
    def _apply_filter(self, documents: List[Document]) -> List[Document]:
        """Wendet den Filter an."""
        if self._filter_mode == FilterMode.READ:
            return [d for d in documents if d.is_read]
        elif self._filter_mode == FilterMode.UNREAD:
            return [d for d in documents if not d.is_read]
        return documents
    
    def _apply_search(self, documents: List[Document]) -> List[Document]:
        """Wendet die Suche an."""
        if not self._search_query:
            return documents
        
        return [
            d for d in documents
            if self._search_query in d.name.lower()
            or self._search_query in d.path.lower()
            or any(self._search_query in tag.lower() for tag in d.tags)
        ]
    
    def _apply_sort(self, documents: List[Document]) -> List[Document]:
        """Wendet die Sortierung an."""
        key_funcs = {
            SortMode.NAME: lambda d: d.name.lower(),
            SortMode.DATE_ADDED: lambda d: d.added,
            SortMode.DATE_READ: lambda d: d.read_date or datetime.min,
            SortMode.SIZE: lambda d: d.size,
            SortMode.TYPE: lambda d: d.extension
        }
        
        key_func = key_funcs.get(self._sort_mode, key_funcs[SortMode.NAME])
        return sorted(documents, key=key_func, reverse=self._sort_reverse)
    
    # === Callback-System ===
    
    def add_change_callback(self, callback: Callable):
        """Registriert einen Callback."""
        self._callbacks.append(callback)
    
    def _notify_change(self, event: str, *args):
        """Benachrichtigt Callbacks."""
        for callback in self._callbacks:
            try:
                callback(event, *args)
            except Exception as e:
                self.logger.error(f"Callback-Fehler: {e}")
    
    # === Statistiken ===
    
    def get_statistics(self) -> Dict:
        """Gibt Bibliotheksstatistiken zurück."""
        total_docs = 0
        total_read = 0
        themes = self._themes.get_all_themes()
        
        for theme in themes:
            total_docs += theme.document_count
            total_read += theme.read_count
        
        return {
            "theme_count": len(themes),
            "document_count": total_docs,
            "read_count": total_read,
            "unread_count": total_docs - total_read
        }
