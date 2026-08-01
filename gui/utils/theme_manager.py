#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Advanced Theme System
========================================
Erweitertes Theme-System mit Farbanpassung.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

from utils.logger import LoggerMixin


@dataclass
class ThemeColors:
    """Farbdefinitionen für ein Theme."""
    # Hauptfarben
    primary: str = "#1a73e8"
    primary_light: str = "#4285f4"
    primary_dark: str = "#1557b0"
    
    # Hintergrund
    background: str = "#ffffff"
    background_alt: str = "#f8f9fa"
    surface: str = "#ffffff"
    
    # Text
    text_primary: str = "#202124"
    text_secondary: str = "#5f6368"
    text_disabled: str = "#9aa0a6"
    text_on_primary: str = "#ffffff"
    
    # Rahmen
    border: str = "#dadce0"
    border_focus: str = "#1a73e8"
    
    # Status
    success: str = "#34a853"
    warning: str = "#fbbc04"
    error: str = "#ea4335"
    info: str = "#4285f4"
    
    # Spezial
    selection: str = "#e8f0fe"
    hover: str = "#f1f3f4"
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dictionary."""
        return {
            "primary": self.primary,
            "primary_light": self.primary_light,
            "primary_dark": self.primary_dark,
            "background": self.background,
            "background_alt": self.background_alt,
            "surface": self.surface,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "text_disabled": self.text_disabled,
            "text_on_primary": self.text_on_primary,
            "border": self.border,
            "border_focus": self.border_focus,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "info": self.info,
            "selection": self.selection,
            "hover": self.hover,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ThemeColors':
        """Erstellt aus Dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class Theme:
    """Vollständige Theme-Definition."""
    name: str
    display_name: str
    colors: ThemeColors = field(default_factory=ThemeColors)
    is_dark: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "colors": self.colors.to_dict(),
            "is_dark": self.is_dark
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Theme':
        # BUGSWEEP-32: .get statt data["..."] — fehlende Pflichtfelder in einer Custom-Theme-JSON
        # warfen sonst KeyError (vom Loader-except verschluckt -> Theme still uebersprungen).
        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", data.get("name", "")),
            colors=ThemeColors.from_dict(data.get("colors", {})),
            is_dark=data.get("is_dark", False)
        )


# === Vordefinierte Themes ===

THEME_LIGHT = Theme(
    name="light",
    display_name="Hell",
    colors=ThemeColors(),
    is_dark=False
)

THEME_DARK = Theme(
    name="dark",
    display_name="Dunkel",
    colors=ThemeColors(
        primary="#8ab4f8",
        primary_light="#aecbfa",
        primary_dark="#669df6",
        background="#202124",
        background_alt="#292a2d",
        surface="#303134",
        text_primary="#e8eaed",
        text_secondary="#9aa0a6",
        text_disabled="#5f6368",
        text_on_primary="#202124",
        border="#5f6368",
        border_focus="#8ab4f8",
        success="#81c995",
        warning="#fdd663",
        error="#f28b82",
        info="#8ab4f8",
        selection="#394457",
        hover="#3c4043"
    ),
    is_dark=True
)

THEME_SEPIA = Theme(
    name="sepia",
    display_name="Sepia",
    colors=ThemeColors(
        primary="#8b5a2b",
        primary_light="#a0522d",
        primary_dark="#704214",
        background="#f4ecd8",
        background_alt="#ebe3d0",
        surface="#f9f5eb",
        text_primary="#5b4636",
        text_secondary="#7a6a5a",
        text_disabled="#a09080",
        text_on_primary="#f4ecd8",
        border="#d4c8b0",
        border_focus="#8b5a2b",
        success="#6b8e23",
        warning="#daa520",
        error="#cd5c5c",
        info="#4682b4",
        selection="#e8dcc8",
        hover="#efe7d8"
    ),
    is_dark=False
)

THEME_NORD = Theme(
    name="nord",
    display_name="Nord",
    colors=ThemeColors(
        primary="#88c0d0",
        primary_light="#8fbcbb",
        primary_dark="#81a1c1",
        background="#2e3440",
        background_alt="#3b4252",
        surface="#434c5e",
        text_primary="#eceff4",
        text_secondary="#d8dee9",
        text_disabled="#4c566a",
        text_on_primary="#2e3440",
        border="#4c566a",
        border_focus="#88c0d0",
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
        info="#5e81ac",
        selection="#434c5e",
        hover="#3b4252"
    ),
    is_dark=True
)

THEME_OCEAN = Theme(
    name="ocean",
    display_name="Ozean",
    colors=ThemeColors(
        primary="#0077b6",
        primary_light="#00b4d8",
        primary_dark="#023e8a",
        background="#caf0f8",
        background_alt="#ade8f4",
        surface="#ffffff",
        text_primary="#03045e",
        text_secondary="#0077b6",
        text_disabled="#90e0ef",
        text_on_primary="#ffffff",
        border="#90e0ef",
        border_focus="#0077b6",
        success="#2a9d8f",
        warning="#e9c46a",
        error="#e76f51",
        info="#0077b6",
        selection="#90e0ef",
        hover="#ade8f4"
    ),
    is_dark=False
)


# === Theme-Manager ===

class ThemeManager(LoggerMixin):
    """
    Verwaltet Themes und wendet sie an.
    
    Features:
    - Vordefinierte Themes
    - Benutzerdefinierte Themes
    - StyleSheet-Generierung
    - Theme speichern/laden
    """
    
    BUILTIN_THEMES = {
        "light": THEME_LIGHT,
        "dark": THEME_DARK,
        "sepia": THEME_SEPIA,
        "nord": THEME_NORD,
        "ocean": THEME_OCEAN,
    }
    
    def __init__(self):
        self._themes = dict(self.BUILTIN_THEMES)
        self._current_theme: Theme = THEME_LIGHT
        self._custom_themes_path: Optional[Path] = None
    
    def set_custom_themes_path(self, path: str):
        """Setzt Pfad für benutzerdefinierte Themes."""
        self._custom_themes_path = Path(path)
        self._load_custom_themes()
    
    def _load_custom_themes(self):
        """Lädt benutzerdefinierte Themes."""
        if not self._custom_themes_path or not self._custom_themes_path.exists():
            return
        
        for file in self._custom_themes_path.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                theme = Theme.from_dict(data)
                # BUGSWEEP-32: from_dict crasht nicht mehr bei fehlendem "name" (gibt name="");
                # solche unvollstaendigen Themes hier explizit ueberspringen, statt sie als
                # Phantom-Theme unter dem leeren Key zu registrieren (mehrere wuerden kollidieren).
                if not theme.name:
                    self.logger.warning(f"Theme ohne Namen übersprungen: {file}")
                    continue
                self._themes[theme.name] = theme
                self.logger.debug(f"Theme geladen: {theme.display_name}")
            except Exception as e:
                self.logger.warning(f"Theme-Fehler {file}: {e}")
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """Gibt ein Theme zurück."""
        return self._themes.get(name)
    
    def get_all_themes(self) -> Dict[str, Theme]:
        """Gibt alle verfügbaren Themes zurück."""
        return dict(self._themes)
    
    def get_current_theme(self) -> Theme:
        """Gibt das aktuelle Theme zurück."""
        return self._current_theme
    
    def apply_theme(self, theme_name: str, app: QApplication = None) -> bool:
        """Wendet ein Theme an."""
        theme = self._themes.get(theme_name)
        if not theme:
            self.logger.error(f"Theme nicht gefunden: {theme_name}")
            return False
        
        self._current_theme = theme
        
        if app is None:
            app = QApplication.instance()
        
        if app:
            stylesheet = self.generate_stylesheet(theme)
            app.setStyleSheet(stylesheet)
            self.logger.info(f"Theme angewendet: {theme.display_name}")
        
        return True
    
    def generate_stylesheet(self, theme: Theme) -> str:
        """Generiert das StyleSheet für ein Theme."""
        c = theme.colors
        
        return f"""
/* DokuZen Pro - Theme: {theme.display_name} */

/* === Allgemein === */
QWidget {{
    background-color: {c.background};
    color: {c.text_primary};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}}

QMainWindow {{
    background-color: {c.background};
}}

/* === Menüs === */
QMenuBar {{
    background-color: {c.surface};
    border-bottom: 1px solid {c.border};
    padding: 2px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    background: transparent;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {c.hover};
}}

QMenu {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {c.selection};
}}

QMenu::separator {{
    height: 1px;
    background: {c.border};
    margin: 4px 8px;
}}

/* === Toolbar === */
QToolBar {{
    background-color: {c.surface};
    border-bottom: 1px solid {c.border};
    padding: 4px;
    spacing: 4px;
}}

QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    color: {c.text_primary};
}}

QToolButton:hover {{
    background-color: {c.hover};
}}

QToolButton:pressed {{
    background-color: {c.selection};
}}

/* === Buttons === */
QPushButton {{
    background-color: {c.primary};
    color: {c.text_on_primary};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {c.primary_light};
}}

QPushButton:pressed {{
    background-color: {c.primary_dark};
}}

QPushButton:disabled {{
    background-color: {c.border};
    color: {c.text_disabled};
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    color: {c.primary};
}}

QPushButton[flat="true"]:hover {{
    background-color: {c.selection};
}}

/* === Eingabefelder === */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {c.selection};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c.border_focus};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {c.background_alt};
    color: {c.text_disabled};
}}

/* === ComboBox === */
QComboBox {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 6px;
    padding: 8px;
    min-width: 100px;
}}

QComboBox:focus {{
    border-color: {c.border_focus};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 6px;
    selection-background-color: {c.selection};
}}

/* === Listen === */
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 6px;
    outline: none;
}}

QListWidget::item, QTreeWidget::item {{
    padding: 6px;
    border-radius: 4px;
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {c.selection};
    color: {c.text_primary};
}}

QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {c.hover};
}}

QHeaderView::section {{
    background-color: {c.background_alt};
    border: none;
    border-bottom: 1px solid {c.border};
    padding: 8px;
    font-weight: 600;
}}

/* === Tabs === */
QTabWidget::pane {{
    border: 1px solid {c.border};
    border-radius: 6px;
    background-color: {c.surface};
}}

QTabBar::tab {{
    background-color: {c.background_alt};
    border: 1px solid {c.border};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background-color: {c.surface};
    border-bottom-color: {c.surface};
}}

QTabBar::tab:hover:!selected {{
    background-color: {c.hover};
}}

/* === Scrollbars === */
QScrollBar:vertical {{
    background: {c.background_alt};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background: {c.border};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c.text_disabled};
}}

QScrollBar:horizontal {{
    background: {c.background_alt};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background: {c.border};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}

/* === GroupBox === */
QGroupBox {{
    border: 1px solid {c.border};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {c.text_secondary};
}}

/* === Checkbox & Radio === */
QCheckBox, QRadioButton {{
    spacing: 8px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
}}

QCheckBox::indicator {{
    border-radius: 4px;
}}

QRadioButton::indicator {{
    border-radius: 9px;
}}

QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {{
    border: 2px solid {c.border};
    background: {c.surface};
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    border: 2px solid {c.primary};
    background: {c.primary};
}}

/* === Splitter === */
QSplitter::handle {{
    background-color: {c.border};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* === StatusBar === */
QStatusBar {{
    background-color: {c.surface};
    border-top: 1px solid {c.border};
}}

/* === ProgressBar === */
QProgressBar {{
    background-color: {c.background_alt};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {c.primary};
    border-radius: 4px;
}}

/* === ToolTip === */
QToolTip {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 4px;
    padding: 6px;
    color: {c.text_primary};
}}

/* === Dialoge === */
QDialog {{
    background-color: {c.background};
}}

/* === Spezielle Klassen === */
.success {{
    color: {c.success};
}}

.warning {{
    color: {c.warning};
}}

.error {{
    color: {c.error};
}}

.info {{
    color: {c.info};
}}
"""
    
    def save_theme(self, theme: Theme, filepath: str):
        """Speichert ein Theme."""
        # BUGSWEEP-32: atomar (tmp + os.replace) — sonst hinterlaesst ein Crash/OneDrive-Lock
        # mitten im json.dump eine halbe/korrupte Theme-JSON (geht beim nächsten Laden verloren).
        tmp_path = f"{filepath}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(theme.to_dict(), f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    
    def create_custom_theme(self, name: str, display_name: str,
                           base_theme: str = "light", **color_overrides) -> Theme:
        """Erstellt ein benutzerdefiniertes Theme."""
        base = self._themes.get(base_theme, THEME_LIGHT)
        
        colors_dict = base.colors.to_dict()
        colors_dict.update(color_overrides)
        
        theme = Theme(
            name=name,
            display_name=display_name,
            colors=ThemeColors.from_dict(colors_dict),
            is_dark=base.is_dark
        )
        
        self._themes[name] = theme
        return theme


# Globale Instanz
_theme_manager: Optional[ThemeManager] = None

def get_theme_manager() -> ThemeManager:
    """Gibt die globale Theme-Manager-Instanz zurück."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
