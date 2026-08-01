#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - File Watcher (Knowledge Engine)
==================================================
Watchdog-basiertes Auto-Update für den Datei-Index.
"""

import threading
import time
from pathlib import Path
from typing import Optional, List, Callable, Set
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty

from utils.logger import LoggerMixin

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent,
        FileDeletedEvent, FileMovedEvent, DirCreatedEvent, DirDeletedEvent
    )
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object


class WatchEvent(Enum):
    """Typen von Dateisystem-Events."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChangeEvent:
    """Repräsentiert eine Dateiänderung."""
    event_type: WatchEvent
    path: str
    is_directory: bool
    dest_path: Optional[str] = None  # Nur bei MOVED


class DebouncedQueue:
    """
    Queue mit Debouncing für häufige Events.
    
    Verhindert mehrfache Verarbeitung wenn eine Datei
    schnell hintereinander geändert wird.
    """
    
    def __init__(self, debounce_seconds: float = 1.0):
        self._queue: Queue = Queue()
        self._pending: dict = {}  # path -> (event, timestamp)
        self._debounce = debounce_seconds
        self._lock = threading.Lock()
    
    def put(self, event: FileChangeEvent):
        """Fügt Event zur Queue hinzu mit Debouncing."""
        with self._lock:
            now = time.time()
            path = event.path
            
            # Bei DELETE sofort verarbeiten
            if event.event_type == WatchEvent.DELETED:
                self._queue.put(event)
                if path in self._pending:
                    del self._pending[path]
                return
            
            # Debounce: Nur neuestes Event behalten
            self._pending[path] = (event, now)
    
    def get_ready(self) -> List[FileChangeEvent]:
        """Holt alle Events die den Debounce-Zeitraum überschritten haben."""
        ready = []
        now = time.time()
        
        with self._lock:
            expired_paths = []
            
            for path, (event, timestamp) in self._pending.items():
                if now - timestamp >= self._debounce:
                    ready.append(event)
                    expired_paths.append(path)
            
            for path in expired_paths:
                del self._pending[path]
            
            # Direct queue items
            while not self._queue.empty():
                try:
                    ready.append(self._queue.get_nowait())
                except Empty:
                    break
        
        return ready


class FileWatchHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Watchdog Event Handler für Dateiänderungen."""
    
    def __init__(self, callback: Callable[[FileChangeEvent], None],
                 extensions: Set[str] = None,
                 ignore_patterns: List[str] = None):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        
        self._callback = callback
        self._extensions = extensions  # None = alle
        self._ignore_patterns = ignore_patterns or [
            '*.tmp', '*.temp', '~*', '.*', '*.swp', '*.bak',
            '__pycache__', '.git', '.svn', 'node_modules'
        ]
    
    def _should_ignore(self, path: str) -> bool:
        """Prüft ob Pfad ignoriert werden soll."""
        p = Path(path)
        
        # Ignore Patterns
        for pattern in self._ignore_patterns:
            if pattern.startswith('*.'):
                if p.suffix == pattern[1:]:
                    return True
            elif pattern.startswith('~'):
                if p.name.startswith('~'):
                    return True
            elif pattern.startswith('.'):
                if p.name.startswith('.'):
                    return True
            else:
                if pattern in str(p):
                    return True
        
        # Extension Filter
        if self._extensions and p.suffix.lower() not in self._extensions:
            return True
        
        return False
    
    def on_created(self, event):
        """Datei erstellt."""
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        
        self._callback(FileChangeEvent(
            event_type=WatchEvent.CREATED,
            path=event.src_path,
            is_directory=False
        ))
    
    def on_modified(self, event):
        """Datei geändert."""
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        
        self._callback(FileChangeEvent(
            event_type=WatchEvent.MODIFIED,
            path=event.src_path,
            is_directory=False
        ))
    
    def on_deleted(self, event):
        """Datei gelöscht."""
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        
        self._callback(FileChangeEvent(
            event_type=WatchEvent.DELETED,
            path=event.src_path,
            is_directory=False
        ))
    
    def on_moved(self, event):
        """Datei verschoben/umbenannt."""
        if event.is_directory:
            return
        if self._should_ignore(event.src_path) and self._should_ignore(event.dest_path):
            return
        
        self._callback(FileChangeEvent(
            event_type=WatchEvent.MOVED,
            path=event.src_path,
            is_directory=False,
            dest_path=event.dest_path
        ))


class FileWatcher(LoggerMixin):
    """
    Überwacht Ordner auf Dateiänderungen.
    
    Features:
    - Mehrere Watch-Pfade
    - Debouncing (verhindert Event-Spam)
    - Extension-Filter
    - Ignore-Patterns
    - Graceful Shutdown
    """
    
    def __init__(self, debounce_seconds: float = 1.0):
        """
        Initialisiert den FileWatcher.
        
        Args:
            debounce_seconds: Wartezeit vor Event-Verarbeitung
        """
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("Watchdog nicht verfügbar - pip install watchdog")
        
        self._observer: Optional[Observer] = None
        self._watch_paths: List[str] = []
        self._event_queue = DebouncedQueue(debounce_seconds)
        self._handlers: List[Callable[[FileChangeEvent], None]] = []
        self._running = False
        self._process_thread: Optional[threading.Thread] = None
        self._extensions: Optional[Set[str]] = None
        self._ignore_patterns: List[str] = []
    
    def set_extensions(self, extensions: List[str]):
        """Setzt den Extension-Filter."""
        self._extensions = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                               for ext in extensions)
    
    def set_ignore_patterns(self, patterns: List[str]):
        """Setzt Ignore-Patterns."""
        self._ignore_patterns = patterns
    
    def add_handler(self, handler: Callable[[FileChangeEvent], None]):
        """Registriert einen Event-Handler."""
        self._handlers.append(handler)
    
    def remove_handler(self, handler: Callable[[FileChangeEvent], None]):
        """Entfernt einen Event-Handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    def add_watch_path(self, path: str, recursive: bool = True):
        """
        Fügt einen Überwachungspfad hinzu.
        
        Args:
            path: Zu überwachender Ordner
            recursive: Unterordner einbeziehen
        """
        if not WATCHDOG_AVAILABLE:
            return
        
        if not Path(path).exists():
            self.logger.warning(f"Pfad existiert nicht: {path}")
            return
        
        if path in self._watch_paths:
            return
        
        self._watch_paths.append(path)
        
        # Falls bereits gestartet, sofort überwachen
        if self._observer and self._running:
            handler = FileWatchHandler(
                self._on_event,
                self._extensions,
                self._ignore_patterns
            )
            self._observer.schedule(handler, path, recursive=recursive)
            self.logger.info(f"Watch hinzugefügt: {path}")
    
    def remove_watch_path(self, path: str):
        """Entfernt einen Überwachungspfad."""
        if path in self._watch_paths:
            self._watch_paths.remove(path)
            # Observer muss neu gestartet werden um Watches zu entfernen
            if self._running:
                self.restart()
    
    def _on_event(self, event: FileChangeEvent):
        """Interner Event-Callback."""
        self._event_queue.put(event)
    
    def _process_events(self):
        """Verarbeitet Events aus der Queue (läuft in eigenem Thread)."""
        while self._running:
            events = self._event_queue.get_ready()
            
            for event in events:
                for handler in self._handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        self.logger.error(f"Handler-Fehler: {e}")
            
            time.sleep(0.5)  # Check interval
    
    def start(self):
        """Startet die Überwachung."""
        if not WATCHDOG_AVAILABLE:
            self.logger.error("Watchdog nicht verfügbar")
            return
        
        if self._running:
            return
        
        self._observer = Observer()
        
        handler = FileWatchHandler(
            self._on_event,
            self._extensions,
            self._ignore_patterns
        )
        
        for path in self._watch_paths:
            if Path(path).exists():
                self._observer.schedule(handler, path, recursive=True)
                self.logger.info(f"Überwache: {path}")
        
        self._running = True
        self._observer.start()
        
        # Event-Processor starten
        self._process_thread = threading.Thread(
            target=self._process_events,
            daemon=True,
            name="FileWatcher-Processor"
        )
        self._process_thread.start()
        
        self.logger.info("FileWatcher gestartet")
    
    def stop(self):
        """Stoppt die Überwachung (Graceful Shutdown)."""
        if not self._running:
            return
        
        self._running = False
        
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
        
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
            self._process_thread = None
        
        self.logger.info("FileWatcher gestoppt")
    
    def restart(self):
        """Neustart der Überwachung."""
        self.stop()
        self.start()
    
    @property
    def is_running(self) -> bool:
        """Gibt zurück ob der Watcher läuft."""
        return self._running
    
    @property
    def watch_paths(self) -> List[str]:
        """Gibt die überwachten Pfade zurück."""
        return self._watch_paths.copy()


class KnowledgeWatcher(LoggerMixin):
    """
    Spezialisierter Watcher für die Knowledge Engine.
    
    Verbindet FileWatcher mit FileIndex für automatische Indizierung.
    """
    
    def __init__(self, file_index, debounce_seconds: float = 2.0):
        """
        Initialisiert den KnowledgeWatcher.
        
        Args:
            file_index: FileIndex-Instanz
            debounce_seconds: Wartezeit vor Indizierung
        """
        from .file_index import FileIndex
        
        self._index: FileIndex = file_index
        self._watcher = FileWatcher(debounce_seconds)
        self._watcher.add_handler(self._handle_event)
        
        # Standard-Extensions für Dokumente
        self._watcher.set_extensions([
            '.pdf', '.docx', '.doc', '.txt', '.md', '.rtf',
            '.py', '.js', '.html', '.css', '.json', '.xml',
            '.png', '.jpg', '.jpeg', '.gif',
            '.db', '.sqlite', '.sqlite3'
        ])
    
    def _handle_event(self, event: FileChangeEvent):
        """Verarbeitet Dateiänderungen."""
        if event.event_type == WatchEvent.CREATED:
            self.logger.debug(f"Neue Datei: {event.path}")
            self._index.index_file(event.path)
            
        elif event.event_type == WatchEvent.MODIFIED:
            self.logger.debug(f"Datei geändert: {event.path}")
            self._index.index_file(event.path, force_reindex=True)
            
        elif event.event_type == WatchEvent.DELETED:
            self.logger.debug(f"Datei gelöscht: {event.path}")
            # TODO: Aus Index entfernen oder als gelöscht markieren
            
        elif event.event_type == WatchEvent.MOVED:
            self.logger.debug(f"Datei verschoben: {event.path} -> {event.dest_path}")
            # TODO: Pfad im Index aktualisieren
            if event.dest_path:
                self._index.index_file(event.dest_path)
    
    def add_watch_path(self, path: str):
        """Fügt Überwachungspfad hinzu."""
        self._watcher.add_watch_path(path)
    
    def start(self):
        """Startet die Überwachung."""
        self._watcher.start()
    
    def stop(self):
        """Stoppt die Überwachung."""
        self._watcher.stop()
    
    @property
    def is_running(self) -> bool:
        """Gibt zurück ob der Watcher läuft."""
        return self._watcher.is_running
