#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Windows Registry Integration
===============================================
Registriert Kontextmenü-Einträge im Windows Explorer.
"""

import sys

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    winreg = None  # type: ignore[assignment]
    _WINREG_AVAILABLE = False

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

from utils.logger import LoggerMixin


class ContextMenuTarget(Enum):
    """Ziel für Kontextmenü-Einträge."""

    FILE = "file"
    DIRECTORY = "directory"
    BACKGROUND = "background"
    DRIVE = "drive"


@dataclass
class ContextMenuItem:
    """Definition eines Kontextmenü-Eintrags."""

    name: str
    label: str
    command: str
    icon: Optional[str] = None
    extensions: Optional[List[str]] = None
    target: ContextMenuTarget = ContextMenuTarget.FILE
    position: str = "bottom"


class RegistryManager(LoggerMixin):
    """
    Verwaltet Windows-Registry-Einträge für Kontextmenüs.

    Features:
    - Kontextmenü für Dateitypen
    - Kontextmenü für Ordner
    - Untermenüs (Cascading)
    - Icon-Unterstützung
    """

    HKCR = winreg.HKEY_CLASSES_ROOT if _WINREG_AVAILABLE else None
    HKCU = winreg.HKEY_CURRENT_USER if _WINREG_AVAILABLE else None

    PATHS = {
        ContextMenuTarget.FILE: r"*\shell",
        ContextMenuTarget.DIRECTORY: r"Directory\shell",
        ContextMenuTarget.BACKGROUND: r"Directory\Background\shell",
        ContextMenuTarget.DRIVE: r"Drive\shell",
    }

    def __init__(self, app_name: str = "DokuZen"):
        self.app_name = app_name
        self._app_path = sys.executable if getattr(sys, "frozen", False) else None

    def _normalize_extensions(self, extensions: Optional[List[str]]) -> List[str]:
        """Normalisiert optionale Dateiendungen für Registry-Pfade."""
        if not extensions:
            return []
        normalized = []
        for ext in extensions:
            normalized.append(ext if ext.startswith(".") else f".{ext}")
        return normalized

    def _resolve_base_paths(
        self,
        target: ContextMenuTarget,
        use_hkcu: bool = True,
        extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """Ermittelt Basis-Registry-Pfade für Zieltyp oder Dateiendungen."""
        normalized_extensions = self._normalize_extensions(extensions)
        if normalized_extensions:
            prefix = (
                r"Software\Classes\SystemFileAssociations"
                if use_hkcu
                else r"SystemFileAssociations"
            )
            return [rf"{prefix}\{ext}\shell" for ext in normalized_extensions]

        base_path = self.PATHS.get(target, self.PATHS[ContextMenuTarget.FILE])
        if use_hkcu:
            base_path = rf"Software\Classes\{base_path}"
        return [base_path]

    def set_app_path(self, path: str):
        """Setzt den Pfad zur Anwendung."""
        self._app_path = path

    def register_menu_item(
        self, item: ContextMenuItem, use_hkcu: bool = True
    ) -> bool:
        """
        Registriert einen Kontextmenü-Eintrag.

        Args:
            item: Menü-Definition
            use_hkcu: HKEY_CURRENT_USER verwenden (kein Admin nötig)

        Returns:
            True bei Erfolg
        """
        try:
            root = self.HKCU if use_hkcu else self.HKCR
            for base_path in self._resolve_base_paths(
                item.target,
                use_hkcu=use_hkcu,
                extensions=item.extensions,
            ):
                self._create_menu_entry(root, base_path, item)

            self.logger.info(f"Kontextmenü registriert: {item.label}")
            return True

        except PermissionError:
            self.logger.error("Keine Berechtigung - als Admin ausführen")
            return False
        except Exception as e:
            self.logger.error(f"Registry-Fehler: {e}")
            return False

    def _create_menu_entry(self, root, base_path: str, item: ContextMenuItem):
        """Erstellt den Registry-Eintrag."""
        key_path = rf"{base_path}\{item.name}"

        with winreg.CreateKeyEx(root, key_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, item.label)
            if item.icon:
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, item.icon)
            if item.position == "top":
                winreg.SetValueEx(key, "Position", 0, winreg.REG_SZ, "Top")

        cmd_path = rf"{key_path}\command"
        with winreg.CreateKeyEx(root, cmd_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, item.command)

    def unregister_menu_item(
        self,
        name: str,
        target: ContextMenuTarget = ContextMenuTarget.FILE,
        extensions: Optional[List[str]] = None,
        use_hkcu: bool = True,
    ) -> bool:
        """
        Entfernt einen Kontextmenü-Eintrag.

        Args:
            name: Interner Name des Eintrags
            target: Zieltyp
            extensions: Dateierweiterungen (falls spezifisch)
            use_hkcu: HKEY_CURRENT_USER verwenden

        Returns:
            True bei Erfolg
        """
        try:
            root = self.HKCU if use_hkcu else self.HKCR
            for base_path in self._resolve_base_paths(
                target,
                use_hkcu=use_hkcu,
                extensions=extensions,
            ):
                self._delete_key_recursive(root, rf"{base_path}\{name}")

            self.logger.info(f"Kontextmenü entfernt: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Fehler beim Entfernen: {e}")
            return False

    def _delete_key_recursive(self, root, path: str):
        """Löscht einen Registry-Schlüssel rekursiv."""
        try:
            with winreg.OpenKeyEx(root, path, 0, winreg.KEY_READ) as key:
                while True:
                    try:
                        subkey = winreg.EnumKey(key, 0)
                        self._delete_key_recursive(root, rf"{path}\{subkey}")
                    except OSError:
                        break
            winreg.DeleteKey(root, path)
        except FileNotFoundError:
            pass

    def register_cascading_menu(
        self,
        menu_name: str,
        label: str,
        items: List[ContextMenuItem],
        target: ContextMenuTarget = ContextMenuTarget.FILE,
        extensions: Optional[List[str]] = None,
        icon: Optional[str] = None,
        use_hkcu: bool = True,
    ) -> bool:
        """
        Registriert ein Untermenü (Cascading Menu).

        Args:
            menu_name: Interner Name
            label: Angezeigter Text
            items: Untermenü-Einträge
            target: Zieltyp
            extensions: Dateierweiterungen für dateitypgebundene Menüs
            icon: Icon-Pfad
            use_hkcu: HKEY_CURRENT_USER verwenden
        """
        try:
            root = self.HKCU if use_hkcu else self.HKCR
            for base_path in self._resolve_base_paths(
                target,
                use_hkcu=use_hkcu,
                extensions=extensions,
            ):
                self._create_cascading_menu_entry(
                    root, base_path, menu_name, label, items, icon
                )

            self.logger.info(f"Untermenü registriert: {label}")
            return True

        except Exception as e:
            self.logger.error(f"Fehler: {e}")
            return False

    def _create_cascading_menu_entry(
        self,
        root,
        base_path: str,
        menu_name: str,
        label: str,
        items: List[ContextMenuItem],
        icon: Optional[str],
    ):
        """Erstellt einen Cascading-Menu-Eintrag unter einem Basis-Pfad."""
        key_path = rf"{base_path}\{menu_name}"

        with winreg.CreateKeyEx(root, key_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
            if icon:
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)

        shell_path = rf"{key_path}\shell"
        for item in items:
            item_path = rf"{shell_path}\{item.name}"
            with winreg.CreateKeyEx(root, item_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, item.label)
                if item.icon:
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, item.icon)

            cmd_path = rf"{item_path}\command"
            with winreg.CreateKeyEx(root, cmd_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, item.command)

    def is_registered(
        self,
        name: str,
        target: ContextMenuTarget = ContextMenuTarget.FILE,
        extensions: Optional[List[str]] = None,
        use_hkcu: bool = True,
    ) -> bool:
        """Prüft ob ein Eintrag existiert."""
        root = self.HKCU if use_hkcu else self.HKCR
        for base_path in self._resolve_base_paths(
            target,
            use_hkcu=use_hkcu,
            extensions=extensions,
        ):
            try:
                with winreg.OpenKeyEx(root, rf"{base_path}\{name}"):
                    return True
            except FileNotFoundError:
                continue
        return False


class DokuZenRegistry(LoggerMixin):
    """Spezifische Registry-Integration für DokuZen Pro."""

    def __init__(self, app_path: str = None):
        self._manager = RegistryManager("DokuZen")

        if app_path:
            self._app_path = app_path
        elif getattr(sys, "frozen", False):
            self._app_path = sys.executable
        else:
            self._app_path = str(Path(__file__).parent.parent.parent / "main.py")

        self._python_path = sys.executable

    def _build_command(self, action: str, use_quoted_path: bool = True) -> str:
        """Erstellt den Befehl für eine Aktion."""
        if getattr(sys, "frozen", False):
            cmd = f'"{self._app_path}"'
        else:
            cmd = f'"{self._python_path}" "{self._app_path}"'

        if use_quoted_path:
            return f'{cmd} --{action} "%1"'
        return f"{cmd} --{action}"

    def register_all(self) -> Dict[str, bool]:
        """Registriert alle DokuZen-Kontextmenüs."""
        results = {}

        pdf_items = [
            ContextMenuItem(
                "dz_pdf_open",
                "Mit DokuZen öffnen",
                self._build_command("open"),
                extensions=[".pdf"],
            ),
            ContextMenuItem(
                "dz_pdf_ocr",
                "OCR-Texterkennung",
                self._build_command("ocr"),
                extensions=[".pdf"],
            ),
            ContextMenuItem(
                "dz_pdf_unlock",
                "PDF entsperren",
                self._build_command("unlock"),
                extensions=[".pdf"],
            ),
            ContextMenuItem(
                "dz_pdf_redact",
                "Sensible Daten schwärzen",
                self._build_command("redact"),
                extensions=[".pdf"],
            ),
        ]

        results["pdf_menu"] = (
            self._manager.register_cascading_menu(
                "DokuZen_PDF",
                "DokuZen",
                pdf_items,
                extensions=[".pdf"],
            )
            if hasattr(self._manager, "register_cascading_menu")
            else False
        )

        results["spawn_text"] = self._manager.register_menu_item(
            ContextMenuItem(
                "dz_spawn_text",
                "Als Text spawnen (DokuZen)",
                self._build_command("spawn-text"),
                target=ContextMenuTarget.FILE,
            )
        )

        py_items = [
            ContextMenuItem(
                "dz_py_analyze",
                "Code analysieren",
                self._build_command("analyze-code"),
                extensions=[".py"],
            ),
            ContextMenuItem(
                "dz_py_encoding",
                "Encoding prüfen/reparieren",
                self._build_command("fix-encoding"),
                extensions=[".py"],
            ),
        ]

        for item in py_items:
            results[item.name] = self._manager.register_menu_item(item)

        results["folder_open"] = self._manager.register_menu_item(
            ContextMenuItem(
                "dz_open_folder",
                "In DokuZen öffnen",
                self._build_command("open-folder", False),
                target=ContextMenuTarget.BACKGROUND,
            )
        )

        return results

    def unregister_all(self) -> Dict[str, bool]:
        """Entfernt alle DokuZen-Kontextmenüs."""
        results = {}
        names = [
            "DokuZen_PDF",
            "dz_spawn_text",
            "dz_py_analyze",
            "dz_py_encoding",
            "dz_open_folder",
        ]

        for name in names:
            kwargs = {"extensions": [".pdf"]} if name == "DokuZen_PDF" else {}
            results[name] = self._manager.unregister_menu_item(name, **kwargs)

        return results

    def get_status(self) -> Dict[str, bool]:
        """Gibt den Registrierungsstatus zurück."""
        return {
            "pdf_menu": self._manager.is_registered(
                "DokuZen_PDF", extensions=[".pdf"]
            ),
            "spawn_text": self._manager.is_registered("dz_spawn_text"),
            # BUGSWEEP-31: dz_py_analyze wird mit extensions=[".py"] registriert (Pfad
            # SystemFileAssociations\.py\...) -> ohne extensions abgefragt fand is_registered den
            # Eintrag NIE und meldete dauerhaft "nicht registriert".
            "py_analyze": self._manager.is_registered("dz_py_analyze", extensions=[".py"]),
            "folder_open": self._manager.is_registered(
                "dz_open_folder", ContextMenuTarget.BACKGROUND
            ),
        }


def register_context_menus():
    """Registriert alle Kontextmenüs (für Setup)."""
    registry = DokuZenRegistry()
    results = registry.register_all()

    success = sum(1 for v in results.values() if v)
    print(f"Kontextmenüs registriert: {success}/{len(results)}")

    for name, ok in results.items():
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")


def unregister_context_menus():
    """Entfernt alle Kontextmenüs."""
    registry = DokuZenRegistry()
    registry.unregister_all()
    print("Kontextmenüs entfernt.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--unregister", action="store_true")
    parser.add_argument("--status", action="store_true")

    args = parser.parse_args()

    if args.register:
        register_context_menus()
    elif args.unregister:
        unregister_context_menus()
    elif args.status:
        registry = DokuZenRegistry()
        status = registry.get_status()
        for name, registered in status.items():
            print(f"{name}: {'Registriert' if registered else 'Nicht registriert'}")
    else:
        parser.print_help()
