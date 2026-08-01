#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Dokumenten- und Dateiverwaltungssuite
========================================================
Vereint 22 Text-, PDF- und Datei-Tools in einer Anwendung.

Autor: User
Version: 1.0.0
Lizenz: AGPL-3.0-or-later
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

# Projekt-Root zum Path hinzufügen
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def resource_path(*parts: str) -> Path:
    """Return paths from source checkout or PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    return base.joinpath(*parts)

# PySide6 Import mit Fallback-Hinweis
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon
except ImportError as e:
    # BUGSWEEP-34: nach stderr (stdout ist unter pythonw/PyInstaller-windowed wirkungslos) + Ursache (e)
    # ausgeben (fehlende DLL vs. fehlendes Paket unterscheidbar).
    print("=" * 60, file=sys.stderr)
    print("FEHLER: PySide6 nicht verfügbar!", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    print("Bitte installieren mit: pip install PySide6", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.exit(1)

from utils.logger import setup_logger, get_logger
from gui.main_window import MainWindow


@dataclass(frozen=True)
class StartupCommand:
    """Beschreibt eine optionale Startaktion für die GUI."""

    action: str
    paths: tuple[str, ...]


def parse_cli_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parst die kleinen GUI-Startoptionen von DokuZen."""

    parser = argparse.ArgumentParser(
        description=(
            "Startet DokuZen Pro optional direkt mit Import-, Öffnen-, OCR-, "
            "Schwärzungs- oder Merge-Aktion."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--open", dest="open_path", metavar="DATEI", help="Datei direkt öffnen und in der Vorschau anzeigen.")
    group.add_argument("--ocr", dest="ocr_path", metavar="DATEI", help="OCR-Dialog direkt mit der angegebenen Datei starten.")
    group.add_argument("--redact", dest="redact_path", metavar="DATEI", help="Schwärzungs-Dialog direkt mit der angegebenen PDF starten.")
    group.add_argument(
        "--merge",
        dest="merge_paths",
        nargs="+",
        metavar="PDF",
        help="PDF-Werkstatt direkt im Merge-Tab mit den angegebenen PDFs öffnen.",
    )
    group.add_argument(
        "--import",
        dest="import_paths",
        nargs="+",
        metavar="DATEI",
        help="Dateien beim Start in das aktuelle Thema importieren.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="DATEI",
        help="Kurzform für `--import DATEI ...`.",
    )

    args = parser.parse_args(argv)
    has_option_action = any(
        (
            args.open_path,
            args.ocr_path,
            args.redact_path,
            args.merge_paths,
            args.import_paths,
        )
    )
    if args.paths and has_option_action:
        parser.error("Positionspfade können nicht mit --open/--ocr/--redact/--merge/--import kombiniert werden.")

    return args


def build_startup_command(args: argparse.Namespace) -> Optional[StartupCommand]:
    """Leitet aus den CLI-Argumenten genau eine Startaktion ab."""

    if args.open_path:
        return StartupCommand("open", (args.open_path,))
    if args.ocr_path:
        return StartupCommand("ocr", (args.ocr_path,))
    if args.redact_path:
        return StartupCommand("redact", (args.redact_path,))
    if args.merge_paths:
        return StartupCommand("merge", tuple(args.merge_paths))
    if args.import_paths:
        return StartupCommand("import", tuple(args.import_paths))
    if args.paths:
        return StartupCommand("import", tuple(args.paths))
    return None


def apply_startup_command(window: MainWindow, command: StartupCommand) -> None:
    """Wendet eine CLI-Startaktion auf das Hauptfenster an."""

    if command.action == "import":
        window.startup_import_paths(command.paths)
        return
    if command.action == "open":
        window.startup_open_path(command.paths[0])
        return
    if command.action == "ocr":
        window.startup_ocr_path(command.paths[0])
        return
    if command.action == "redact":
        window.startup_redaction_path(command.paths[0])
        return
    if command.action == "merge":
        window.startup_merge_paths(command.paths)
        return
    raise ValueError(f"Unbekannte Startaktion: {command.action}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Initialize logging, create the QApplication, and launch DokuZen Pro."""

    args = parse_cli_args(argv)
    startup_command = build_startup_command(args)

    # Logger initialisieren
    setup_logger()
    logger = get_logger(__name__)
    logger.info("=" * 50)
    logger.info("DokuZen Pro startet...")
    logger.info("=" * 50)

    # BUGSWEEP-34: Top-Level-Exception-Handler — sonst werden Exceptions in Slots/Callbacks der
    # laufenden Qt-Event-Loop (z.B. via QTimer.singleShot unten) je nach PySide6-Version still
    # verschluckt und landen in keinem Log. sys.__excepthook__ danach für das Standardverhalten.
    def _log_excepthook(exc_type, exc_value, exc_tb):
        logger.critical("Unbehandelte Ausnahme", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _log_excepthook

    # High-DPI Skalierung aktivieren (vor QApplication!)
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    # Qt-Attribute setzen
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Anwendung erstellen
    # BUGSWEEP-34: nur den Programmnamen an Qt geben — die App-eigenen CLI-Argumente (--open etc.)
    # werden separat geparst; an Qt durchgereicht wuerde Qt sie als unbekannte Optionen behandeln.
    app = QApplication([sys.argv[0]])
    app.setApplicationName("DokuZen Pro")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DokuZen")
    
    # Icon setzen (falls vorhanden)
    for icon_path in (
        resource_path("assets", "dokuzen.ico"),
        resource_path("DokuZen.ico"),
    ):
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break
    
    # Hauptfenster erstellen und anzeigen
    try:
        window = MainWindow()
        window.show()
        logger.info("Hauptfenster geöffnet")
        if startup_command is not None:
            QTimer.singleShot(0, lambda: apply_startup_command(window, startup_command))
    except Exception as e:
        logger.critical(f"Fehler beim Erstellen des Hauptfensters: {e}", exc_info=True)
        return 1
    
    # Event-Loop starten
    exit_code = app.exec()
    
    logger.info("DokuZen Pro beendet")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
