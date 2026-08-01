#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Theme Manager
===============================
Verwaltet Themen/Kategorien für die Dokumentenbibliothek.
"""

from typing import List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import LoggerMixin


@dataclass
class Theme:
    """Repräsentiert ein Thema in der Bibliothek."""
    name: str
    created: datetime = field(default_factory=datetime.now)
    document_count: int = 0
    read_count: int = 0
    unread_count: int = 0
    
    @property
    def display_name(self) -> str:
        """Name mit Dokumentenanzahl für Anzeige."""
        return f"{self.name} ({self.document_count})"
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        return {
            "name": self.name,
            "created": self.created.isoformat(),
            "document_count": self.document_count,
            "read_count": self.read_count,
            "unread_count": self.unread_count
        }


class ThemeManager(LoggerMixin):
    """
    Verwaltet Themen für die Dokumentenbibliothek.
    
    Arbeitet mit dem PersistenceManager zusammen.
    """
    
    # Reservierte Themen (können nicht gelöscht werden)
    RESERVED_THEMES = {"Allgemein"}
    
    def __init__(self, persistence_manager):
        """
        Initialisiert den ThemeManager.
        
        Args:
            persistence_manager: PersistenceManager-Instanz
        """
        self._persistence = persistence_manager
        self._current_theme: Optional[str] = None
        self._callbacks: List[Callable] = []
        
        self.logger.info("ThemeManager initialisiert")
    
    def get_all_themes(self) -> List[Theme]:
        """
        Gibt alle Themen als Theme-Objekte zurück.
        
        Returns:
            Liste von Theme-Objekten
        """
        themes = []
        for name in self._persistence.get_themes():
            docs = self._persistence.get_documents(name)
            read_count = sum(1 for d in docs if d.get("is_read", False))
            
            themes.append(Theme(
                name=name,
                document_count=len(docs),
                read_count=read_count,
                unread_count=len(docs) - read_count
            ))
        
        return sorted(themes, key=lambda t: t.name.lower())
    
    def get_theme_names(self) -> List[str]:
        """Gibt alle Themennamen zurück."""
        return sorted(self._persistence.get_themes(), key=str.lower)
    
    def create_theme(self, name: str) -> bool:
        """
        Erstellt ein neues Thema.
        
        Args:
            name: Name des Themas
            
        Returns:
            True bei Erfolg
        """
        name = name.strip()
        if not name:
            self.logger.warning("Leerer Themenname")
            return False
        
        if len(name) > 100:
            self.logger.warning("Themenname zu lang")
            return False
        
        success = self._persistence.add_theme(name)
        if success:
            self._notify_change("theme_created", name)
        return success
    
    def rename_theme(self, old_name: str, new_name: str) -> bool:
        """
        Benennt ein Thema um.
        
        Args:
            old_name: Aktueller Name
            new_name: Neuer Name
            
        Returns:
            True bei Erfolg
        """
        new_name = new_name.strip()
        if not new_name:
            return False
        
        if old_name in self.RESERVED_THEMES:
            self.logger.warning(f"Reserviertes Thema kann nicht umbenannt werden: {old_name}")
            return False
        
        success = self._persistence.rename_theme(old_name, new_name)
        if success:
            if self._current_theme == old_name:
                self._current_theme = new_name
                self._persistence.set_setting("last_theme", new_name)
            self._notify_change("theme_renamed", old_name, new_name)
        return success
    
    def delete_theme(self, name: str) -> bool:
        """
        Löscht ein Thema.
        
        Args:
            name: Name des zu löschenden Themas
            
        Returns:
            True bei Erfolg
        """
        if name in self.RESERVED_THEMES:
            self.logger.warning(f"Reserviertes Thema kann nicht gelöscht werden: {name}")
            return False
        
        if len(self._persistence.get_themes()) <= 1:
            self.logger.warning("Letztes Thema kann nicht gelöscht werden")
            return False
        
        success = self._persistence.delete_theme(name)
        if success:
            if self._current_theme == name:
                fallback_theme = self.get_theme_names()[0]
                self._current_theme = fallback_theme
                self._persistence.set_setting("last_theme", fallback_theme)
            self._notify_change("theme_deleted", name)
        return success
    
    def get_current_theme(self) -> Optional[str]:
        """Gibt das aktuell ausgewählte Thema zurück."""
        if self._current_theme is None:
            saved_theme = self._persistence.get_setting("last_theme", "Allgemein")
            available_themes = self._persistence.get_themes()

            if saved_theme in available_themes:
                self._current_theme = saved_theme
            elif available_themes:
                fallback_theme = sorted(available_themes, key=str.lower)[0]
                self._current_theme = fallback_theme
                self._persistence.set_setting("last_theme", fallback_theme)
            else:
                self._current_theme = None
        return self._current_theme
    
    def set_current_theme(self, name: str) -> bool:
        """
        Setzt das aktuelle Thema.
        
        Args:
            name: Name des Themas
            
        Returns:
            True bei Erfolg
        """
        if name not in self._persistence.get_themes():
            return False
        
        self._current_theme = name
        self._persistence.set_setting("last_theme", name)
        self._notify_change("theme_selected", name)
        return True
    
    def theme_exists(self, name: str) -> bool:
        """Prüft, ob ein Thema existiert."""
        return name in self._persistence.get_themes()
    
    # === Callback-System ===
    
    def add_change_callback(self, callback: Callable):
        """Registriert einen Callback für Änderungen."""
        self._callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable):
        """Entfernt einen Callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_change(self, event: str, *args):
        """Benachrichtigt alle registrierten Callbacks."""
        for callback in self._callbacks:
            try:
                callback(event, *args)
            except Exception as e:
                self.logger.error(f"Callback-Fehler: {e}")
