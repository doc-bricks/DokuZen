#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Keyboard Shortcuts Manager
=============================================
Zentrale Verwaltung aller Tastaturkürzel.
"""

import copy
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QKeySequence, QShortcut

from utils.logger import LoggerMixin


class ShortcutCategory(Enum):
    """Kategorien für Shortcuts."""
    FILE = "Datei"
    EDIT = "Bearbeiten"
    VIEW = "Ansicht"
    TOOLS = "Werkzeuge"
    NAVIGATION = "Navigation"
    CUSTOM = "Benutzerdefiniert"


@dataclass
class ShortcutDefinition:
    """Definition eines Tastaturkürzels."""
    action_id: str
    key_sequence: str
    description: str
    category: ShortcutCategory = ShortcutCategory.CUSTOM
    enabled: bool = True


class ShortcutManager(LoggerMixin):
    """
    Verwaltet Tastaturkürzel zentral.
    
    Features:
    - Registrierung von Shortcuts
    - Konflikt-Erkennung
    - Benutzerdefinierte Anpassung
    - Export/Import
    """
    
    # Standard-Shortcuts für DokuZen
    DEFAULT_SHORTCUTS = {
        # Datei
        "file.new": ShortcutDefinition("file.new", "Ctrl+N", "Neues Dokument", ShortcutCategory.FILE),
        "file.open": ShortcutDefinition("file.open", "Ctrl+O", "Datei öffnen", ShortcutCategory.FILE),
        "file.save": ShortcutDefinition("file.save", "Ctrl+S", "Speichern", ShortcutCategory.FILE),
        "file.import": ShortcutDefinition("file.import", "Ctrl+I", "Importieren", ShortcutCategory.FILE),
        "file.export": ShortcutDefinition("file.export", "Ctrl+E", "Exportieren", ShortcutCategory.FILE),
        "file.quit": ShortcutDefinition("file.quit", "Ctrl+Q", "Beenden", ShortcutCategory.FILE),
        
        # Bearbeiten
        "edit.undo": ShortcutDefinition("edit.undo", "Ctrl+Z", "Rückgängig", ShortcutCategory.EDIT),
        "edit.redo": ShortcutDefinition("edit.redo", "Ctrl+Y", "Wiederholen", ShortcutCategory.EDIT),
        "edit.find": ShortcutDefinition("edit.find", "Ctrl+F", "Suchen", ShortcutCategory.EDIT),
        "edit.select_all": ShortcutDefinition("edit.select_all", "Ctrl+A", "Alles auswählen", ShortcutCategory.EDIT),
        
        # Ansicht
        "view.zoom_in": ShortcutDefinition("view.zoom_in", "Ctrl++", "Vergrößern", ShortcutCategory.VIEW),
        "view.zoom_out": ShortcutDefinition("view.zoom_out", "Ctrl+-", "Verkleinern", ShortcutCategory.VIEW),
        "view.zoom_reset": ShortcutDefinition("view.zoom_reset", "Ctrl+0", "Zoom zurücksetzen", ShortcutCategory.VIEW),
        "view.fullscreen": ShortcutDefinition("view.fullscreen", "F11", "Vollbild", ShortcutCategory.VIEW),
        
        # Werkzeuge
        "tools.pdf_workshop": ShortcutDefinition("tools.pdf_workshop", "Ctrl+Shift+P", "PDF-Werkstatt", ShortcutCategory.TOOLS),
        "tools.ocr": ShortcutDefinition("tools.ocr", "Ctrl+Shift+O", "OCR", ShortcutCategory.TOOLS),
        "tools.redact": ShortcutDefinition("tools.redact", "Ctrl+Shift+R", "Schwärzen", ShortcutCategory.TOOLS),
        "tools.convert": ShortcutDefinition("tools.convert", "Ctrl+Shift+C", "Konvertieren", ShortcutCategory.TOOLS),
        "tools.merge": ShortcutDefinition("tools.merge", "Ctrl+Shift+M", "Zusammenführen", ShortcutCategory.TOOLS),
        "tools.form_builder": ShortcutDefinition("tools.form_builder", "Ctrl+Shift+F", "Formular-Builder", ShortcutCategory.TOOLS),
        "tools.marker": ShortcutDefinition("tools.marker", "Ctrl+Shift+K", "PDF-Marker", ShortcutCategory.TOOLS),
        "tools.settings": ShortcutDefinition("tools.settings", "Ctrl+,", "Einstellungen", ShortcutCategory.TOOLS),
        
        # Navigation
        "nav.next_page": ShortcutDefinition("nav.next_page", "PgDown", "Nächste Seite", ShortcutCategory.NAVIGATION),
        "nav.prev_page": ShortcutDefinition("nav.prev_page", "PgUp", "Vorherige Seite", ShortcutCategory.NAVIGATION),
        "nav.goto_page": ShortcutDefinition("nav.goto_page", "Ctrl+G", "Gehe zu Seite", ShortcutCategory.NAVIGATION),
    }
    
    def __init__(self, parent: QWidget = None):
        self._parent = parent
        # BUGSWEEP-32 (HIGH): deepcopy — dict() ist nur Shallow-Copy; ShortcutDefinition ist ein
        # NICHT-frozen dataclass. set_shortcut/enable_shortcut/import_config mutieren sonst die
        # GETEILTEN DEFAULT_SHORTCUTS-Objekte -> Cross-Instance-Pollution + reset_to_defaults wirkungslos.
        self._shortcuts: Dict[str, ShortcutDefinition] = copy.deepcopy(self.DEFAULT_SHORTCUTS)
        self._handlers: Dict[str, Callable] = {}
        self._qt_shortcuts: Dict[str, QShortcut] = {}
    
    def register_handler(self, action_id: str, handler: Callable):
        """Registriert einen Handler für eine Aktion."""
        self._handlers[action_id] = handler
        if self._parent and action_id in self._shortcuts:
            self._create_qt_shortcut(action_id)
    
    def _create_qt_shortcut(self, action_id: str):
        """Erstellt einen QShortcut."""
        if action_id in self._qt_shortcuts:
            self._qt_shortcuts[action_id].deleteLater()
        
        definition = self._shortcuts[action_id]
        if not definition.enabled:
            return
        
        shortcut = QShortcut(QKeySequence(definition.key_sequence), self._parent)
        if action_id in self._handlers:
            shortcut.activated.connect(self._handlers[action_id])
        self._qt_shortcuts[action_id] = shortcut
    
    def set_shortcut(self, action_id: str, key_sequence: str) -> bool:
        """Ändert ein Tastaturkürzel."""
        conflict = self.find_conflict(key_sequence, exclude=action_id)
        if conflict:
            self.logger.warning(f"Konflikt: {key_sequence} bereits für {conflict}")
            return False
        
        if action_id in self._shortcuts:
            self._shortcuts[action_id].key_sequence = key_sequence
            if action_id in self._qt_shortcuts:
                self._create_qt_shortcut(action_id)
            return True
        return False
    
    def get_shortcut(self, action_id: str) -> Optional[str]:
        """Gibt das Tastaturkürzel für eine Aktion zurück."""
        if action_id in self._shortcuts:
            return self._shortcuts[action_id].key_sequence
        return None
    
    def find_conflict(self, key_sequence: str, exclude: str = None) -> Optional[str]:
        """Findet Konflikte mit anderen Shortcuts."""
        for action_id, definition in self._shortcuts.items():
            if action_id != exclude and definition.key_sequence == key_sequence:
                return action_id
        return None
    
    def enable_shortcut(self, action_id: str, enabled: bool = True):
        """Aktiviert/Deaktiviert einen Shortcut."""
        if action_id in self._shortcuts:
            self._shortcuts[action_id].enabled = enabled
            if action_id in self._qt_shortcuts:
                self._qt_shortcuts[action_id].setEnabled(enabled)
    
    def get_by_category(self, category: ShortcutCategory) -> List[ShortcutDefinition]:
        """Gibt alle Shortcuts einer Kategorie zurück."""
        return [s for s in self._shortcuts.values() if s.category == category]
    
    def get_all(self) -> Dict[str, ShortcutDefinition]:
        """Gibt alle Shortcuts zurück."""
        return dict(self._shortcuts)
    
    def reset_to_defaults(self):
        """Setzt alle Shortcuts auf Standard zurück."""
        # BUGSWEEP-32 (HIGH): deepcopy — sonst zeigt _shortcuts wieder auf die (evtl. bereits
        # mutierten) Default-Objekte und "Auf Standard zurücksetzen" stellt nichts wieder her.
        self._shortcuts = copy.deepcopy(self.DEFAULT_SHORTCUTS)
        for action_id in self._qt_shortcuts:
            if action_id in self._handlers:
                self._create_qt_shortcut(action_id)
    
    def export_config(self) -> Dict:
        """Exportiert die Konfiguration."""
        return {
            action_id: {"key_sequence": s.key_sequence, "enabled": s.enabled}
            for action_id, s in self._shortcuts.items()
        }
    
    def import_config(self, config: Dict):
        """Importiert eine Konfiguration."""
        for action_id, data in config.items():
            if action_id in self._shortcuts:
                self._shortcuts[action_id].key_sequence = data.get("key_sequence", 
                    self._shortcuts[action_id].key_sequence)
                self._shortcuts[action_id].enabled = data.get("enabled", True)
                if action_id in self._qt_shortcuts:
                    self._create_qt_shortcut(action_id)


# Globale Instanz
_shortcut_manager: Optional[ShortcutManager] = None

def get_shortcut_manager() -> ShortcutManager:
    """Gibt die globale Shortcut-Manager-Instanz zurück."""
    global _shortcut_manager
    if _shortcut_manager is None:
        _shortcut_manager = ShortcutManager()
    return _shortcut_manager

def init_shortcut_manager(parent: QWidget) -> ShortcutManager:
    """Initialisiert den Shortcut-Manager mit Parent-Widget."""
    global _shortcut_manager
    _shortcut_manager = ShortcutManager(parent)
    return _shortcut_manager
