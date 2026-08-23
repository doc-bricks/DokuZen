#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TranslationSystem - Multi-Language Support für DokuZen
======================================================
Version: 1.1.0 (gehärtet & I18N-erweitert)
Quelle: DOCS/DEV_DokuZen/translator.py

Verwendung:
-----------
from translator import TranslationSystem, get_translator, tr

translator = get_translator()
label.setText(tr('Datei öffnen'))
translator.set_language('en')
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

_GLOBAL_TRANSLATOR: Optional['TranslationSystem'] = None


class TranslationSystem:
    """Multi-Language Support System v1.1.0 für DokuZen."""

    SUPPORTED_LANGUAGES = ['de', 'en', 'es', 'zh', 'ja', 'ru']
    LANGUAGE_NAMES = {
        'de': 'Deutsch',
        'en': 'English',
        'es': 'Español',
        'zh': '中文',
        'ja': '日本語',
        'ru': 'Русский',
    }
    CODE_FROM_NAME = {v: k for k, v in LANGUAGE_NAMES.items()}

    def __init__(self, default_lang: str = 'de', app_dir: Optional[Path] = None):
        """
        Initialisiert das Translation-System.

        Args:
            default_lang: Standard-Sprache ('de', 'en', 'es', 'zh', 'ja', 'ru')
            app_dir: Verzeichnis der Anwendung (default: Verzeichnis dieser Datei)
        """
        lang_code = self.normalize_language_code(default_lang)
        self.current_lang = lang_code if lang_code in self.SUPPORTED_LANGUAGES else 'de'

        if app_dir is None:
            app_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        self.app_dir = Path(app_dir)

        self.translations_file = self.app_dir / "locales" / "translations.json"

        self.string_patterns = [
            re.compile(r'setText\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setWindowTitle\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QLabel\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QPushButton\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'addAction\s*\([^,]*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'addTab\s*\([^,]+,\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'text\s*=\s*"([^"]+)"'),
        ]

        self.german_hints = [
            "datei", "bearbeiten", "ansicht", "hilfe", "öffnen", "speichern",
            "schließen", "einstellungen", "abbrechen", "ok", "ja", "nein",
            "start", "stop", "pause", "fortsetzen", "laden", "aktualisieren",
            "filter", "fehler", "export", "import", "optionen", "anzeigen",
            "bibliothek", "vorschau", "dokument", "schwärzen", "marker"
        ]

        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    @classmethod
    def normalize_language_code(cls, lang_input: str) -> str:
        """Normalisiert Sprachbezeichnungen ('Deutsch' -> 'de', 'English' -> 'en', 'de_DE' -> 'de')."""
        if not lang_input:
            return 'de'
        cleaned = str(lang_input).strip()
        if cleaned in cls.CODE_FROM_NAME:
            return cls.CODE_FROM_NAME[cleaned]
        code = cleaned.lower()
        if '_' in code:
            code = code.split('_')[0]
        if '-' in code:
            code = code.split('-')[0]
        if code in cls.SUPPORTED_LANGUAGES:
            return code
        return 'de'

    def _load_translations(self):
        """Lädt die Übersetzungstabelle aus translations.json."""
        if self.translations_file.exists():
            try:
                with open(self.translations_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            except Exception:
                self.translations = {}
        else:
            self.translations = {}

    def _save_translations(self):
        """Speichert die Übersetzungstabelle."""
        self.translations_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.translations_file, 'w', encoding='utf-8') as f:
            json.dump(self.translations, f, indent=2, ensure_ascii=False)

    def t(self, key: str) -> str:
        """
        Übersetzt einen Key in die aktuelle Sprache.
        Fallback-Kette: Aktuelle Sprache -> EN -> DE -> Original-Key.
        """
        if not key:
            return key

        if key in self.translations:
            lang_dict = self.translations[key]
            val = lang_dict.get(self.current_lang)
            if val:
                return val
            val_en = lang_dict.get('en')
            if val_en:
                return val_en
            val_de = lang_dict.get('de')
            if val_de:
                return val_de
            return key

        # Dynamische Registrierung unbekannter deutscher Strings
        if self._is_german(key):
            self.translations[key] = {
                "de": key, "en": "", "es": "", "zh": "", "ja": "", "ru": ""
            }
            try:
                self._save_translations()
            except Exception:
                pass

        return key

    def tr(self, key: str) -> str:
        """Alias für t()."""
        return self.t(key)

    def set_language(self, lang: str):
        """Setzt die aktive UI-Sprache."""
        norm = self.normalize_language_code(lang)
        if norm in self.SUPPORTED_LANGUAGES:
            self.current_lang = norm

    def get_language(self) -> str:
        """Gibt den aktuellen Sprachcode zurück ('de', 'en', ...)."""
        return self.current_lang

    def get_language_name(self) -> str:
        """Gibt den lesbaren Namen der aktuellen Sprache zurück ('Deutsch', 'English', ...)."""
        return self.LANGUAGE_NAMES.get(self.current_lang, 'Deutsch')

    def add_translation(
        self,
        key: str,
        de: str = "",
        en: str = "",
        es: str = "",
        zh: str = "",
        ja: str = "",
        ru: str = ""
    ):
        """Fügt eine Übersetzung manuell hinzu."""
        if key not in self.translations:
            self.translations[key] = {}
        self.translations[key].update({
            "de": de or key,
            "en": en or "",
            "es": es or "",
            "zh": zh or "",
            "ja": ja or "",
            "ru": ru or ""
        })
        self._save_translations()

    def _is_german(self, text: str) -> bool:
        """Prüft heuristisch, ob ein String deutsch ist."""
        if any(ch in text for ch in "äöüÄÖÜß"):
            return True
        text_lower = text.lower()
        return any(hint in text_lower for hint in self.german_hints)

    def get_missing_translations(self, target_lang: str = 'en') -> List[str]:
        """Liefert alle Keys, für die in target_lang keine Übersetzung vorhanden ist."""
        return [k for k, v in self.translations.items() if not v.get(target_lang)]


def get_translator(default_lang: str = 'de') -> TranslationSystem:
    """Gibt das globale Singleton des Translation-Systems zurück."""
    global _GLOBAL_TRANSLATOR
    if _GLOBAL_TRANSLATOR is None:
        _GLOBAL_TRANSLATOR = TranslationSystem(default_lang=default_lang)
    return _GLOBAL_TRANSLATOR


def tr(key: str) -> str:
    """Globale Hilfsfunktion zur Übersetzung."""
    return get_translator().t(key)


if __name__ == "__main__":
    translator = get_translator()
    print(f"DokuZen Translator initialized. Language: {translator.get_language()} ({translator.get_language_name()})")
    print(f"Total translation entries: {len(translator.translations)}")
