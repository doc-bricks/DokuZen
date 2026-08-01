#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Tray Plugin
=============================
System-Tray-Integration für schnellen Zugriff.
"""

import sys
import threading
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass

from utils.logger import LoggerMixin

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


@dataclass
class TrayAction:
    """Definiert eine Tray-Menü-Aktion."""
    label: str
    callback: Callable
    enabled: bool = True
    checked: bool = False
    is_separator: bool = False


class TrayPlugin(LoggerMixin):
    """
    System-Tray-Plugin für DokuZen Pro.
    
    Features:
    - System-Tray-Icon
    - Kontextmenü mit Schnellaktionen
    - Hotkey-Integration
    - Clipboard → Datei Schnellzugriff
    """
    
    APP_NAME = "DokuZen Pro"
    
    def __init__(self, on_show_main: Callable = None,
                 on_spawn_text: Callable = None,
                 on_spawn_pdf: Callable = None):
        """
        Initialisiert das Tray-Plugin.
        
        Args:
            on_show_main: Callback zum Anzeigen des Hauptfensters
            on_spawn_text: Callback für Text-Spawning
            on_spawn_pdf: Callback für PDF-Spawning
        """
        if not PYSTRAY_AVAILABLE:
            self.logger.warning("pystray nicht installiert!")
        
        self._icon: Optional[Icon] = None
        self._running = False
        # BUGSWEEP-31: threadsicheres Quit-Signal. _on_quit laeuft im pystray-Worker-Thread;
        # ein dortiges sys.exit() beendet NUR diesen Thread, nicht den Main-Thread -> Geisterprozess.
        # Stattdessen setzt _on_quit dieses Event, das die Main-Schleife (main()) verlaesst.
        self.quit_event = threading.Event()

        # Callbacks
        self._on_show_main = on_show_main
        self._on_spawn_text = on_spawn_text
        self._on_spawn_pdf = on_spawn_pdf
        
        # Hotkeys
        self._hotkeys_registered = False
        self._hotkey_spawn_text = "ctrl+alt+t"
        self._hotkey_spawn_pdf = "ctrl+alt+p"
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def start(self):
        """Startet das Tray-Plugin."""
        if not PYSTRAY_AVAILABLE:
            self.logger.error("Kann nicht starten: pystray fehlt")
            return False
        
        if self._running:
            return True
        
        try:
            # Icon erstellen
            icon_image = self._create_icon_image()
            menu = self._create_menu()
            
            self._icon = Icon(
                self.APP_NAME,
                icon_image,
                self.APP_NAME,
                menu
            )
            
            # In separatem Thread starten
            self._running = True
            thread = threading.Thread(target=self._icon.run, daemon=True)
            thread.start()
            
            # Hotkeys registrieren
            self._register_hotkeys()
            
            self.logger.info("Tray-Plugin gestartet")
            return True
            
        except Exception as e:
            self.logger.error(f"Tray-Start fehlgeschlagen: {e}")
            self._running = False
            return False
    
    def stop(self):
        """Stoppt das Tray-Plugin."""
        self._unregister_hotkeys()
        
        if self._icon:
            self._icon.stop()
            self._icon = None
        
        self._running = False
        self.logger.info("Tray-Plugin gestoppt")
    
    def update_menu(self):
        """Aktualisiert das Tray-Menü."""
        if self._icon:
            self._icon.menu = self._create_menu()
    
    def show_notification(self, title: str, message: str):
        """Zeigt eine Benachrichtigung."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception as e:
                self.logger.debug(f"Notification fehlgeschlagen: {e}")
    
    def _create_icon_image(self) -> Image.Image:
        """Erstellt das Tray-Icon."""
        # Einfaches Icon erstellen (Buchstabe D in Kreis)
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Kreis
        draw.ellipse([2, 2, size-2, size-2], fill='#2196F3', outline='#1976D2', width=2)
        
        # Text "D"
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", 36)
        except (OSError, IOError):
            font = ImageFont.load_default()
        
        # Text zentrieren
        text = "D"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 4
        
        draw.text((x, y), text, fill='white', font=font)
        
        return image
    
    def _create_menu(self) -> Menu:
        """Erstellt das Kontextmenü."""
        items = [
            MenuItem("DokuZen öffnen", self._on_show_main_clicked, default=True),
            Menu.SEPARATOR,
            MenuItem("Text spawnen (Ctrl+Alt+T)", self._on_spawn_text_clicked),
            MenuItem("PDF spawnen (Ctrl+Alt+P)", self._on_spawn_pdf_clicked),
            Menu.SEPARATOR,
            MenuItem("Clipboard-History", Menu(
                MenuItem("Letzte 5 anzeigen", self._on_show_history),
                MenuItem("History leeren", self._on_clear_history),
            )),
            Menu.SEPARATOR,
            MenuItem("Beenden", self._on_quit),
        ]
        
        return Menu(*items)
    
    def _on_show_main_clicked(self, icon, item):
        """Zeigt das Hauptfenster."""
        if self._on_show_main:
            self._on_show_main()
    
    def _on_spawn_text_clicked(self, icon=None, item=None):
        """Spawnt Text aus Clipboard."""
        if self._on_spawn_text:
            result = self._on_spawn_text()
            if result:
                self.show_notification("Text gespeichert", f"Datei: {Path(result).name}")
    
    def _on_spawn_pdf_clicked(self, icon=None, item=None):
        """Spawnt PDF aus Clipboard."""
        if self._on_spawn_pdf:
            result = self._on_spawn_pdf()
            if result:
                self.show_notification("PDF gespeichert", f"Datei: {Path(result).name}")
    
    def _on_show_history(self, icon, item):
        """Zeigt Clipboard-History."""
        # Wird später implementiert
        self.logger.debug("History anzeigen")
    
    def _on_clear_history(self, icon, item):
        """Leert Clipboard-History."""
        self.logger.debug("History geleert")
    
    def _on_quit(self, icon, item):
        """Beendet die Anwendung."""
        # BUGSWEEP-31: KEIN sys.exit hier (laeuft im pystray-Worker-Thread -> wuerde nur diesen
        # Thread beenden, Main-Thread bliebe haengen). Quit-Event signalisiert die Main-Schleife.
        self.stop()
        self.quit_event.set()
    
    # === Hotkey-Management ===
    
    def _register_hotkeys(self):
        """Registriert globale Hotkeys."""
        if not KEYBOARD_AVAILABLE:
            self.logger.warning("keyboard nicht verfügbar - keine Hotkeys")
            return
        
        try:
            keyboard.add_hotkey(self._hotkey_spawn_text, self._on_spawn_text_clicked)
            keyboard.add_hotkey(self._hotkey_spawn_pdf, self._on_spawn_pdf_clicked)
            
            self._hotkeys_registered = True
            self.logger.info(f"Hotkeys registriert: {self._hotkey_spawn_text}, {self._hotkey_spawn_pdf}")
            
        except Exception as e:
            self.logger.warning(f"Hotkey-Registrierung fehlgeschlagen: {e}")
    
    def _unregister_hotkeys(self):
        """Entfernt globale Hotkeys."""
        if not KEYBOARD_AVAILABLE or not self._hotkeys_registered:
            return
        
        try:
            keyboard.remove_hotkey(self._hotkey_spawn_text)
            keyboard.remove_hotkey(self._hotkey_spawn_pdf)
            self._hotkeys_registered = False
            
        except Exception as e:
            self.logger.debug(f"Hotkey-Entfernung fehlgeschlagen: {e}")
    
    def set_hotkey(self, action: str, hotkey: str):
        """
        Setzt einen Hotkey.
        
        Args:
            action: 'spawn_text' oder 'spawn_pdf'
            hotkey: Hotkey-String (z.B. 'ctrl+alt+t')
        """
        if action == 'spawn_text':
            self._hotkey_spawn_text = hotkey
        elif action == 'spawn_pdf':
            self._hotkey_spawn_pdf = hotkey
        
        # Neu registrieren wenn aktiv
        if self._hotkeys_registered:
            self._unregister_hotkeys()
            self._register_hotkeys()


class SpawnerService(LoggerMixin):
    """
    Kombinierter Service für Clipboard-Monitoring und Tray.
    
    Vereint ClipboardMonitor und TrayPlugin.
    """
    
    def __init__(self, spawn_folder: str = None):
        """
        Initialisiert den Spawner-Service.
        
        Args:
            spawn_folder: Zielordner für gespawnte Dateien
        """
        from plugins.spawner.clipboard_monitor import ClipboardMonitor, ClipboardSaver
        
        self._spawn_folder = spawn_folder
        
        # Komponenten
        self._monitor = ClipboardMonitor()
        self._saver = ClipboardSaver(spawn_folder)
        self._tray = TrayPlugin(
            on_spawn_text=self._spawn_text,
            on_spawn_pdf=self._spawn_pdf
        )
        
        self._running = False
    
    def start(self):
        """Startet den Service."""
        self._monitor.start()
        self._tray.start()
        self._running = True
        self.logger.info("Spawner-Service gestartet")
    
    def stop(self):
        """Stoppt den Service."""
        self._monitor.stop()
        self._tray.stop()
        self._running = False
        self.logger.info("Spawner-Service gestoppt")
    
    def _spawn_text(self) -> Optional[str]:
        """Spawnt aktuellen Clipboard-Inhalt als Text."""
        content = self._monitor.get_current()
        if content:
            return self._saver.save_as_text(content)
        return None
    
    def _spawn_pdf(self) -> Optional[str]:
        """Spawnt aktuellen Clipboard-Inhalt als PDF."""
        content = self._monitor.get_current()
        if content:
            return self._saver.save_as_pdf(content)
        return None
    
    @property
    def history(self):
        """Gibt Clipboard-History zurück."""
        return self._monitor.history

    @property
    def quit_event(self):
        """Quit-Event des Tray-Plugins (BUGSWEEP-31: Main-Schleife wartet darauf)."""
        return self._tray.quit_event


# === Standalone-Start ===

def main():
    """Startet den Spawner-Service standalone."""
    import time
    
    service = SpawnerService()
    service.start()
    
    print("Spawner-Service läuft. Drücke Ctrl+C zum Beenden.")
    
    try:
        # BUGSWEEP-31: auf Quit-Event warten (vom Tray-"Beenden") statt endlosem while True,
        # sonst beendet das Tray-Menue den Prozess nie (Geisterprozess).
        while not service.quit_event.is_set():
            time.sleep(0.5)
        service.stop()
        print("Beendet.")
    except KeyboardInterrupt:
        service.stop()
        print("Beendet.")


if __name__ == "__main__":
    main()
