#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für das Internationalisierungs- (I18N) und Übersetzungssystem in DokuZen.
"""

import json
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from translator import TranslationSystem, get_translator, tr


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_translations_file_structure():
    """Prüft, ob translations.json existiert, valide ist und alle 6 Sprachen abdeckt."""
    trans_file = Path(__file__).resolve().parent.parent / "locales" / "translations.json"
    assert trans_file.exists(), "locales/translations.json existiert nicht"

    with open(trans_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert len(data) >= 100, f"Zu wenige Übersetzungs-Einträge: {len(data)}"

    required_langs = ["de", "en", "es", "zh", "ja", "ru"]
    for key, lang_map in data.items():
        assert isinstance(lang_map, dict), f"Eintrag für '{key}' ist kein Dict"
        for lang in required_langs:
            assert lang in lang_map, f"Sprache '{lang}' fehlt für Key '{key}'"
            assert lang_map[lang], f"Leere Übersetzung für Sprache '{lang}' bei Key '{key}'"


def test_translation_system_methods():
    """Testet die Kernmethoden des TranslationSystem."""
    ts = TranslationSystem(default_lang="de")
    assert ts.get_language() == "de"
    assert ts.get_language_name() == "Deutsch"

    # Umschaltung auf Englisch
    ts.set_language("en")
    assert ts.get_language() == "en"
    assert ts.get_language_name() == "English"
    assert ts.t("Öffnen") == "Open"
    assert ts.t("Neues Thema") == "New Topic"

    # Umschaltung auf Spanisch
    ts.set_language("es")
    assert ts.get_language() == "es"
    assert ts.get_language_name() == "Español"
    assert ts.t("Öffnen") == "Abrir"
    assert ts.t("Neues Thema") == "Nuevo tema"

    # Umschaltung auf Chinesisch
    ts.set_language("zh")
    assert ts.get_language() == "zh"
    assert ts.get_language_name() == "中文"
    assert ts.t("Öffnen") == "打开"

    # Umschaltung auf Japanisch
    ts.set_language("ja")
    assert ts.get_language() == "ja"
    assert ts.get_language_name() == "日本語"
    assert ts.t("Öffnen") == "開く"

    # Umschaltung auf Russisch
    ts.set_language("ru")
    assert ts.get_language() == "ru"
    assert ts.get_language_name() == "Русский"
    assert ts.t("Öffnen") == "Открыть"

    # Zurück zu Deutsch
    ts.set_language("de")
    assert ts.get_language() == "de"
    assert ts.t("Öffnen") == "Öffnen"


def test_normalize_language_code():
    """Testet die Normalisierung verschiedener Sprach-Eingaben."""
    assert TranslationSystem.normalize_language_code("Deutsch") == "de"
    assert TranslationSystem.normalize_language_code("English") == "en"
    assert TranslationSystem.normalize_language_code("Español") == "es"
    assert TranslationSystem.normalize_language_code("中文") == "zh"
    assert TranslationSystem.normalize_language_code("日本語") == "ja"
    assert TranslationSystem.normalize_language_code("Русский") == "ru"

    assert TranslationSystem.normalize_language_code("de_DE") == "de"
    assert TranslationSystem.normalize_language_code("en-US") == "en"
    assert TranslationSystem.normalize_language_code("es_ES") == "es"
    assert TranslationSystem.normalize_language_code("zh_CN") == "zh"
    assert TranslationSystem.normalize_language_code("ja_JP") == "ja"
    assert TranslationSystem.normalize_language_code("ru_RU") == "ru"

    # Fallback bei unbekannten Codes
    assert TranslationSystem.normalize_language_code("unknown") == "de"
    assert TranslationSystem.normalize_language_code("") == "de"


def test_gui_retranslate_smoke(qapp):
    """Prüft, ob retranslate_ui auf MainWindow und Panels fehlerfrei durchläuft."""
    from gui.main_window import MainWindow

    win = MainWindow()
    t = get_translator()

    # Initial Deutsch
    t.set_language("de")
    win.retranslate_ui()
    assert win.windowTitle() == "DokuZen"

    # Umschalten auf Englisch
    t.set_language("en")
    win.retranslate_ui()
    assert t.get_language() == "en"

    # Umschalten auf Spanisch
    t.set_language("es")
    win.retranslate_ui()
    assert t.get_language() == "es"

    # Zurück auf Deutsch
    t.set_language("de")
    win.retranslate_ui()
    assert win.windowTitle() == "DokuZen"

    win.close()
