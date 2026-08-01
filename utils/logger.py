#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Logger-Modul
==============================
Zentrale Logging-Konfiguration mit Rotating File Handler.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# Globale Logger-Instanz
_logger_initialized = False
_root_logger: Optional[logging.Logger] = None

# Konstanten
DEFAULT_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)-25s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
DEFAULT_BACKUP_COUNT = 4


def get_project_root() -> Path:
    """Ermittelt das Projekt-Root-Verzeichnis."""
    return Path(__file__).parent.parent


def setup_logger(
    log_file: Optional[str] = None,
    level: int = DEFAULT_LOG_LEVEL,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    console: bool = True
) -> logging.Logger:
    """
    Initialisiert das globale Logging-System.
    
    Args:
        log_file: Pfad zur Log-Datei (relativ zum Projekt-Root)
        level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximale Größe der Log-Datei in Bytes
        backup_count: Anzahl der Backup-Dateien
        console: Ob auch auf die Konsole geloggt werden soll
    
    Returns:
        Der konfigurierte Root-Logger
    """
    global _logger_initialized, _root_logger
    
    if _logger_initialized:
        return _root_logger
    
    # Root-Logger konfigurieren
    root_logger = logging.getLogger("DokuZen")
    root_logger.setLevel(level)
    
    # Formatter erstellen
    formatter = logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
    
    # File Handler (Rotating)
    if log_file is None:
        log_file = "logs/dokuzen.log"
    
    log_path = get_project_root() / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console Handler (optional)
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    _logger_initialized = True
    _root_logger = root_logger
    
    root_logger.info("Logger initialisiert")
    root_logger.debug(f"Log-Datei: {log_path}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Gibt einen Logger für ein spezifisches Modul zurück.
    
    Args:
        name: Name des Moduls (typischerweise __name__)
    
    Returns:
        Logger-Instanz für das Modul
    """
    # Kürze den Namen für bessere Lesbarkeit
    if name.startswith("DokuZen."):
        short_name = name[12:]  # Entferne "DokuZen."
    elif "." in name:
        parts = name.split(".")
        short_name = ".".join(parts[-2:]) if len(parts) > 1 else parts[-1]
    else:
        short_name = name
    
    return logging.getLogger(f"DokuZen.{short_name}")


def set_log_level(level: int):
    """Ändert das Log-Level zur Laufzeit."""
    if _root_logger:
        _root_logger.setLevel(level)
        for handler in _root_logger.handlers:
            handler.setLevel(level)


class LoggerMixin:
    """
    Mixin-Klasse für einfaches Logging in anderen Klassen.
    
    Verwendung:
        class MyClass(LoggerMixin):
            def my_method(self):
                self.logger.info("Nachricht")
    """
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
