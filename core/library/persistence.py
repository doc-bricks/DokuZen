#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Persistence Manager
==============================
Verwaltet die persistente Speicherung des Bibliothekszustands in JSON.
"""

import json
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from utils.logger import get_logger, LoggerMixin

# Modul-Konstanten: nicht durch Klassen-Patching in Tests beeinflussbar
_REAL_DEFAULT_STATE_PATH = Path.home() / ".dokuzen_state.json"
_LEGACY_STATE_PATH = Path.home() / ".dokuzentrum_state.json"


class PersistenceManager(LoggerMixin):
    """
    Verwaltet das Laden und Speichern des Bibliothekszustands.

    Struktur der State-Datei:
    {
        "version": "1.0",
        "last_saved": "2025-01-02T12:00:00",
        "themes": {
            "Arbeit": {
                "created": "2025-01-01T10:00:00",
                "documents": [
                    {
                        "path": "/path/to/doc.pdf",
                        "added": "2025-01-01T10:30:00",
                        "is_read": false,
                        "read_date": null,
                        "tags": [],
                        "notes": ""
                    }
                ]
            }
        },
        "settings": {
            "last_theme": "Arbeit",
            "sort_by": "name",
            "filter": "all"
        }
    }
    """

    VERSION = "1.0"
    DEFAULT_STATE_FILE = Path.home() / ".dokuzen_state.json"
    # Pfad der alten State-Datei (DokuZentrum → DokuZen Migration)
    _LEGACY_STATE_FILE = Path.home() / ".dokuzentrum_state.json"
    
    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialisiert den Persistence Manager.
        
        Args:
            state_file: Pfad zur State-Datei (optional)
        """
        self.state_file = Path(state_file) if state_file else self.DEFAULT_STATE_FILE
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = self._create_empty_state()
        self._dirty = False
        
        self.logger.info(f"PersistenceManager initialisiert: {self.state_file}")
    
    def _create_empty_state(self) -> Dict[str, Any]:
        """Erstellt einen leeren Zustand."""
        return {
            "version": self.VERSION,
            "last_saved": None,
            "themes": {
                "Allgemein": {
                    "created": datetime.now().isoformat(),
                    "documents": []
                }
            },
            "settings": {
                "last_theme": "Allgemein",
                "sort_by": "name",
                "filter": "all"
            }
        }
    
    def load(self) -> bool:
        """
        Lädt den Zustand aus der Datei.
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        with self._lock:
            if not self.state_file.exists():
                # Backward-Compat: Alte DokuZentrum-State-Datei automatisch migrieren.
                # Vergleich gegen Modul-Konstante (nicht die patchbare Klassen-Variable),
                # damit Tests, die DEFAULT_STATE_FILE überschreiben, die Migration nicht auslösen.
                if self.state_file == _REAL_DEFAULT_STATE_PATH and _LEGACY_STATE_PATH.exists():
                    try:
                        shutil.copy2(_LEGACY_STATE_PATH, self.state_file)
                        self.logger.info(
                            f"Legacy-State migriert: {_LEGACY_STATE_PATH.name} "
                            f"→ {self.state_file.name}"
                        )
                    except Exception as e:
                        self.logger.warning(f"Legacy-State-Migration fehlgeschlagen: {e}")
            if not self.state_file.exists():
                self.logger.info("Keine State-Datei gefunden, verwende leeren Zustand")
                self._state = self._create_empty_state()
                return True
            
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Version prüfen und ggf. migrieren
                if data.get("version") != self.VERSION:
                    data = self._migrate_state(data)
                
                self._state = data
                self._dirty = False
                self.logger.info(f"Zustand geladen: {len(self._state.get('themes', {}))} Themen")
                return True
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON-Fehler beim Laden: {e}")
                # Backup erstellen und neu starten
                self._backup_corrupted_file()
                self._state = self._create_empty_state()
                return False
            except Exception as e:
                self.logger.error(f"Fehler beim Laden: {e}", exc_info=True)
                return False
    
    def save(self, force: bool = False) -> bool:
        """
        Speichert den Zustand in die Datei.
        
        Args:
            force: Speichern auch wenn nicht dirty
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        with self._lock:
            if not force and not self._dirty:
                return True
            
            try:
                # State-Datei Verzeichnis erstellen
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Zeitstempel aktualisieren
                self._state["last_saved"] = datetime.now().isoformat()
                
                # Temporär speichern, dann umbenennen (atomic)
                temp_file = self.state_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self._state, f, ensure_ascii=False, indent=2)
                
                temp_file.replace(self.state_file)
                self._dirty = False
                self.logger.debug("Zustand gespeichert")
                return True
                
            except Exception as e:
                self.logger.error(f"Fehler beim Speichern: {e}", exc_info=True)
                return False
    
    def _migrate_state(self, old_state: Dict) -> Dict:
        """Migriert alte State-Versionen."""
        self.logger.info(f"Migriere State von Version {old_state.get('version')} zu {self.VERSION}")
        # Hier können Migrationslogiken hinzugefügt werden
        old_state["version"] = self.VERSION
        return old_state
    
    def _backup_corrupted_file(self):
        """Erstellt Backup einer korrupten State-Datei."""
        if self.state_file.exists():
            backup = self.state_file.with_suffix(f".backup_{datetime.now():%Y%m%d_%H%M%S}")
            # BUGSWEEP-30: rename kann bei OneDrive-Lock/PermissionError werfen — der Fehler
            # flog sonst ungefangen aus load()'s JSONDecodeError-Handler und crashte load() ganz.
            try:
                self.state_file.rename(backup)
                self.logger.warning(f"Korrupte Datei gesichert: {backup}")
            except OSError as e:
                self.logger.error(f"Korrupte Datei konnte nicht gesichert werden: {e}")
    
    # === Theme-Operationen ===
    
    def get_themes(self) -> List[str]:
        """Gibt alle Themennamen zurück."""
        return list(self._state.get("themes", {}).keys())
    
    def add_theme(self, name: str) -> bool:
        """Fügt ein neues Thema hinzu."""
        with self._lock:
            if name in self._state["themes"]:
                return False
            self._state["themes"][name] = {
                "created": datetime.now().isoformat(),
                "documents": []
            }
            self._dirty = True
            self.logger.info(f"Thema hinzugefügt: {name}")
            return True
    
    def rename_theme(self, old_name: str, new_name: str) -> bool:
        """Benennt ein Thema um."""
        with self._lock:
            if old_name not in self._state["themes"] or new_name in self._state["themes"]:
                return False
            self._state["themes"][new_name] = self._state["themes"].pop(old_name)
            self._dirty = True
            self.logger.info(f"Thema umbenannt: {old_name} -> {new_name}")
            return True
    
    def delete_theme(self, name: str) -> bool:
        """Löscht ein Thema."""
        with self._lock:
            if name not in self._state["themes"] or len(self._state["themes"]) <= 1:
                return False
            del self._state["themes"][name]
            # Falls das gelöschte Thema das aktive war, auf erstes verbleibendes setzen
            if self._state.get("settings", {}).get("last_theme") == name:
                remaining = list(self._state["themes"].keys())
                if remaining:
                    self._state["settings"]["last_theme"] = remaining[0]
            self._dirty = True
            self.logger.info(f"Thema gelöscht: {name}")
            return True
    
    # === Dokument-Operationen ===
    
    def get_documents(self, theme: str) -> List[Dict]:
        """Gibt alle Dokumente eines Themas zurück."""
        return self._state.get("themes", {}).get(theme, {}).get("documents", [])
    
    def add_document(self, theme: str, path: str) -> bool:
        """Fügt ein Dokument zu einem Thema hinzu."""
        with self._lock:
            if theme not in self._state["themes"]:
                return False
            
            # Duplikat-Check
            docs = self._state["themes"][theme]["documents"]
            if any(d["path"] == path for d in docs):
                self.logger.debug(f"Dokument bereits vorhanden: {path}")
                return False
            
            docs.append({
                "path": path,
                "added": datetime.now().isoformat(),
                "is_read": False,
                "read_date": None,
                "tags": [],
                "notes": ""
            })
            self._dirty = True
            self.logger.debug(f"Dokument hinzugefügt: {path}")
            return True
    
    def remove_document(self, theme: str, path: str) -> bool:
        """Entfernt ein Dokument aus einem Thema."""
        with self._lock:
            if theme not in self._state["themes"]:
                return False
            
            docs = self._state["themes"][theme]["documents"]
            for i, doc in enumerate(docs):
                if doc["path"] == path:
                    docs.pop(i)
                    self._dirty = True
                    self.logger.debug(f"Dokument entfernt: {path}")
                    return True
            return False
    
    def set_document_read(self, theme: str, path: str, is_read: bool) -> bool:
        """Setzt den Gelesen-Status eines Dokuments."""
        with self._lock:
            if theme not in self._state["themes"]:
                return False
            
            for doc in self._state["themes"][theme]["documents"]:
                if doc["path"] == path:
                    doc["is_read"] = is_read
                    doc["read_date"] = datetime.now().isoformat() if is_read else None
                    self._dirty = True
                    return True
            return False
    
    # === Settings ===
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Gibt eine Einstellung zurück."""
        return self._state.get("settings", {}).get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Setzt eine Einstellung."""
        with self._lock:
            if "settings" not in self._state:
                self._state["settings"] = {}
            self._state["settings"][key] = value
            self._dirty = True
    
    @property
    def is_dirty(self) -> bool:
        """Gibt zurück, ob ungespeicherte Änderungen vorliegen."""
        return self._dirty
