#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Clipboard Monitor
====================================
Überwacht die Zwischenablage und ermöglicht schnelles Speichern.
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logger import LoggerMixin

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


class ClipboardContentType(Enum):
    """Typen von Clipboard-Inhalten."""
    TEXT = "text"
    IMAGE = "image"
    FILES = "files"
    UNKNOWN = "unknown"


@dataclass
class ClipboardContent:
    """Repräsentiert Clipboard-Inhalt."""
    content_type: ClipboardContentType
    text: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def preview(self) -> str:
        """Kurze Vorschau des Inhalts."""
        if self.text:
            preview = self.text[:50].replace('\n', ' ')
            if len(self.text) > 50:
                preview += "..."
            return preview
        return f"[{self.content_type.value}]"
    
    @property
    def char_count(self) -> int:
        """Zeichenanzahl."""
        return len(self.text) if self.text else 0
    
    @property
    def word_count(self) -> int:
        """Wortanzahl."""
        return len(self.text.split()) if self.text else 0
    
    @property
    def line_count(self) -> int:
        """Zeilenanzahl."""
        return self.text.count('\n') + 1 if self.text else 0


class ClipboardMonitor(LoggerMixin):
    """
    Überwacht die Zwischenablage auf Änderungen.
    
    Features:
    - Erkennt Text-Änderungen
    - Callback bei neuen Inhalten
    - History der letzten Einträge
    - Thread-basierte Überwachung
    """
    
    def __init__(self, check_interval: float = 0.5, history_size: int = 50):
        """
        Initialisiert den Monitor.
        
        Args:
            check_interval: Prüfintervall in Sekunden
            history_size: Maximale History-Größe
        """
        if not PYPERCLIP_AVAILABLE:
            self.logger.warning("pyperclip nicht installiert!")
        
        self._check_interval = check_interval
        self._history_size = history_size
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_content: str = ""
        
        self._history: List[ClipboardContent] = []
        self._callbacks: List[Callable[[ClipboardContent], None]] = []
        
        self._lock = threading.Lock()
    
    @property
    def is_running(self) -> bool:
        """Prüft ob Monitor läuft."""
        return self._running
    
    @property
    def history(self) -> List[ClipboardContent]:
        """Gibt die History zurück."""
        with self._lock:
            return list(self._history)
    
    def add_callback(self, callback: Callable[[ClipboardContent], None]):
        """Registriert einen Callback für neue Inhalte."""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ClipboardContent], None]):
        """Entfernt einen Callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def start(self):
        """Startet die Überwachung."""
        if self._running:
            return
        
        if not PYPERCLIP_AVAILABLE:
            self.logger.error("Kann nicht starten: pyperclip fehlt")
            return
        
        self._running = True
        self._last_content = self._get_clipboard_text()
        
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        self.logger.info("Clipboard-Monitor gestartet")
    
    def stop(self):
        """Stoppt die Überwachung."""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        self.logger.info("Clipboard-Monitor gestoppt")
    
    def _monitor_loop(self):
        """Haupt-Überwachungsschleife."""
        while self._running:
            try:
                current = self._get_clipboard_text()
                
                if current and current != self._last_content:
                    self._last_content = current
                    self._on_new_content(current)
                
            except Exception as e:
                self.logger.debug(f"Clipboard-Fehler: {e}")
            
            time.sleep(self._check_interval)
    
    def _get_clipboard_text(self) -> str:
        """Holt Text aus der Zwischenablage."""
        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""
    
    def _on_new_content(self, text: str):
        """Verarbeitet neuen Clipboard-Inhalt."""
        content = ClipboardContent(
            content_type=ClipboardContentType.TEXT,
            text=text
        )
        
        # Zur History hinzufügen
        with self._lock:
            self._history.insert(0, content)
            
            # History begrenzen
            while len(self._history) > self._history_size:
                self._history.pop()
        
        # Snapshot nehmen, damit Modifikationen aus anderen Threads keine
        # RuntimeError während der Iteration auslösen
        with self._lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            try:
                callback(content)
            except Exception as e:
                self.logger.error(f"Callback-Fehler: {e}")
        
        self.logger.debug(f"Neuer Clipboard-Inhalt: {content.preview}")
    
    def get_current(self) -> Optional[ClipboardContent]:
        """Gibt aktuellen Clipboard-Inhalt zurück."""
        text = self._get_clipboard_text()
        if text:
            return ClipboardContent(
                content_type=ClipboardContentType.TEXT,
                text=text
            )
        return None
    
    def clear_history(self):
        """Leert die History."""
        with self._lock:
            self._history.clear()


class ClipboardSaver(LoggerMixin):
    """
    Speichert Clipboard-Inhalte als Dateien.
    
    Features:
    - Verschiedene Formate (TXT, MD, PDF)
    - Automatische Dateinamen
    - Konfigurierbare Zielordner
    """
    
    def __init__(self, default_folder: str = None):
        """
        Initialisiert den Saver.
        
        Args:
            default_folder: Standard-Speicherordner
        """
        self._default_folder = Path(default_folder) if default_folder else Path.home() / "Documents" / "DokuZen" / "Spawned"
        self._default_folder.mkdir(parents=True, exist_ok=True)
    
    @property
    def default_folder(self) -> Path:
        return self._default_folder
    
    @default_folder.setter
    def default_folder(self, path: str):
        self._default_folder = Path(path)
        self._default_folder.mkdir(parents=True, exist_ok=True)
    
    def save_as_text(self, content: ClipboardContent, 
                     filename: str = None, folder: str = None) -> Optional[str]:
        """
        Speichert als Textdatei.
        
        Args:
            content: Zu speichernder Inhalt
            filename: Dateiname (optional, wird generiert)
            folder: Zielordner (optional, nutzt Standard)
            
        Returns:
            Pfad zur gespeicherten Datei oder None
        """
        if not content or not content.text:
            return None
        
        target_folder = Path(folder) if folder else self._default_folder
        target_folder.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            filename = self._generate_filename("txt")
        elif not filename.endswith('.txt'):
            filename += '.txt'
        
        filepath = target_folder / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content.text)
            
            self.logger.info(f"Gespeichert: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Speicherfehler: {e}")
            return None
    
    def save_as_markdown(self, content: ClipboardContent,
                         filename: str = None, folder: str = None,
                         title: str = None) -> Optional[str]:
        """Speichert als Markdown-Datei."""
        if not content or not content.text:
            return None
        
        target_folder = Path(folder) if folder else self._default_folder
        target_folder.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            filename = self._generate_filename("md")
        elif not filename.endswith('.md'):
            filename += '.md'
        
        filepath = target_folder / filename
        
        # Markdown mit Header
        md_content = f"# {title or 'Clipboard-Inhalt'}\n\n"
        md_content += f"> Erstellt: {content.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md_content += "---\n\n"
        md_content += content.text
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            self.logger.info(f"Gespeichert: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Speicherfehler: {e}")
            return None
    
    def save_as_pdf(self, content: ClipboardContent,
                    filename: str = None, folder: str = None) -> Optional[str]:
        """Speichert als PDF-Datei."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
        except ImportError:
            self.logger.error("reportlab nicht verfügbar")
            return None
        
        if not content or not content.text:
            return None
        
        target_folder = Path(folder) if folder else self._default_folder
        target_folder.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            filename = self._generate_filename("pdf")
        elif not filename.endswith('.pdf'):
            filename += '.pdf'
        
        filepath = target_folder / filename
        
        try:
            c = canvas.Canvas(str(filepath), pagesize=A4)
            width, height = A4
            
            # Text aufteilen und zeichnen
            y = height - 2*cm
            for line in content.text.split('\n'):
                if y < 2*cm:
                    c.showPage()
                    y = height - 2*cm
                
                # Zeile kürzen wenn zu lang
                c.drawString(2*cm, y, line[:90])
                y -= 0.4*cm
            
            c.save()
            
            self.logger.info(f"PDF gespeichert: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"PDF-Speicherfehler: {e}")
            return None
    
    def _generate_filename(self, extension: str) -> str:
        """Generiert einen Dateinamen mit Zeitstempel."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"clip_{timestamp}.{extension}"


# === Hilfsfunktionen ===

def save_clipboard_as_file(format: str = "txt", folder: str = None) -> Optional[str]:
    """Schnelle Funktion zum Speichern des Clipboard-Inhalts."""
    monitor = ClipboardMonitor()
    content = monitor.get_current()
    
    if not content:
        return None
    
    saver = ClipboardSaver(folder)
    
    if format == "txt":
        return saver.save_as_text(content)
    elif format == "md":
        return saver.save_as_markdown(content)
    elif format == "pdf":
        return saver.save_as_pdf(content)
    
    return None
