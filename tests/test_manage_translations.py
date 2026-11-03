#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_manage_translations.py - Vertragstests für manage_translations.py
=============================================================================
Hermetische Unit- und Vertragstests für das Translation Management CLI,
die Paritätsprüfung (Policy P-006 Tier-2), Statistikausgabe und atomare Persistenz.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manage_translations import (
    SUPPORTED_LANGUAGES,
    find_german_strings,
    get_catalog_stats,
    is_german_hint,
    load_translations,
    main,
    print_catalog_stats,
    resolve_translation_file,
    save_translations,
    scan_and_update,
    validate_catalog,
)
from translator import TranslationSystem


class TestManageTranslations(unittest.TestCase):
    """Testsuite für manage_translations.py und atomare Übersetzungspersistenz."""

    def setUp(self):
        self.trans_file = resolve_translation_file(PROJECT_ROOT)
        self._tmp = TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_tier2_supported_languages(self):
        """Prüft, ob exakt die 6 Tier-2 Sprachen deklariert sind."""
        self.assertEqual(SUPPORTED_LANGUAGES, ["de", "en", "es", "zh", "ja", "ru"])

    def test_real_catalog_exists_and_valid(self):
        """Validiert den echten DokuZen-Katalog auf 100% 6-Sprachen-Parität."""
        self.assertTrue(self.trans_file.exists(), f"translations.json nicht gefunden: {self.trans_file}")
        is_valid, findings = validate_catalog(self.trans_file)
        self.assertTrue(is_valid, f"Paritätsprüfung für echten Katalog fehlgeschlagen: {findings}")
        self.assertEqual(len(findings), 0)

    def test_real_catalog_stats(self):
        """Prüft Statistiken für den echten Katalog."""
        stats = get_catalog_stats(self.trans_file)
        self.assertNotIn("error", stats)
        self.assertGreaterEqual(stats["total_keys"], 540)
        self.assertTrue(stats["perfect_parity"])
        for lang in SUPPORTED_LANGUAGES:
            self.assertIn(lang, stats["languages"])
            self.assertEqual(stats["languages"][lang]["missing"], 0)
            self.assertEqual(stats["languages"][lang]["coverage_percent"], 100.0)

    def test_validate_catalog_detects_missing_language_slot(self):
        """Erkennt unvollständige Sprach-Slots in Übersetzungseinträgen."""
        bad_file = self.tmp_path / "bad_translations.json"
        bad_data = {
            "Speichern": {
                "de": "Speichern",
                "en": "Save",
                "es": "Guardar",
                "zh": "保存",
                "ja": "保存",
                # "ru" fehlt absichtlich
            }
        }
        bad_file.write_text(json.dumps(bad_data, ensure_ascii=False), encoding="utf-8")

        is_valid, findings = validate_catalog(bad_file)
        self.assertFalse(is_valid)
        self.assertTrue(any("Fehlender Sprach-Slot 'ru'" in f for f in findings))

    def test_validate_catalog_detects_empty_translation(self):
        """Erkennt leere Übersetzungs-Strings."""
        bad_file = self.tmp_path / "empty_translations.json"
        bad_data = {
            "Laden": {
                "de": "Laden",
                "en": "Load",
                "es": "Cargar",
                "zh": "加载",
                "ja": "読み込み",
                "ru": "   ",  # Leerstring
            }
        }
        bad_file.write_text(json.dumps(bad_data, ensure_ascii=False), encoding="utf-8")

        is_valid, findings = validate_catalog(bad_file)
        self.assertFalse(is_valid)
        self.assertTrue(any("Leere Übersetzung für Sprache 'ru'" in f for f in findings))

    def test_validate_catalog_invalid_structure(self):
        """Prüft Nicht-Existenz und ungültige JSON-Struktur."""
        non_existent = self.tmp_path / "not_there.json"
        is_valid, findings = validate_catalog(non_existent)
        self.assertFalse(is_valid)
        self.assertTrue(any("existiert nicht" in f for f in findings))

        corrupt_file = self.tmp_path / "corrupt.json"
        corrupt_file.write_text("{ broken json", encoding="utf-8")
        is_valid, findings = validate_catalog(corrupt_file)
        self.assertFalse(is_valid)
        self.assertTrue(any("JSON-Parsing-Fehler" in f for f in findings))

        array_file = self.tmp_path / "array.json"
        array_file.write_text("[]", encoding="utf-8")
        is_valid, findings = validate_catalog(array_file)
        self.assertFalse(is_valid)
        self.assertTrue(any("kein Dictionary" in f for f in findings))

    def test_atomic_save_and_load(self):
        """Prüft atomares Speichern und anschließendes Laden ohne .tmp-Dateirückstände."""
        target_file = self.tmp_path / "sub" / "locales" / "translations.json"
        sample_data = {
            "TestKey": {
                "de": "TestDE",
                "en": "TestEN",
                "es": "TestES",
                "zh": "TestZH",
                "ja": "TestJA",
                "ru": "TestRU",
            }
        }

        save_translations(target_file, sample_data)
        self.assertTrue(target_file.exists())

        loaded = load_translations(target_file)
        self.assertEqual(loaded, sample_data)

        # Keine temporären .tmp-Dateien im Verzeichnis
        tmp_files = list(target_file.parent.glob("*.tmp.*"))
        self.assertEqual(len(tmp_files), 0)

    def test_print_catalog_stats_output(self):
        """Prüft formatierte Konsolenausgabe."""
        stats = get_catalog_stats(self.trans_file)
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_catalog_stats(stats)
        out = buf.getvalue()
        self.assertIn("DokuZen - Tier-2 Übersetzungskatalog-Statistiken", out)
        self.assertIn("100% perfekte Parität", out)

    def test_german_hint_heuristics(self):
        """Prüft Heuristik für deutsche Begriffe und Umlaute."""
        self.assertTrue(is_german_hint("Öffnen"))
        self.assertTrue(is_german_hint("Schließen"))
        self.assertTrue(is_german_hint("Einstellungen"))
        self.assertTrue(is_german_hint("Wasserzeichen hinzufügen"))
        self.assertTrue(is_german_hint("PDF-Sicherheit"))
        self.assertFalse(is_german_hint("Cancel and close"))
        self.assertFalse(is_german_hint("random_token_123"))

    def test_scan_and_update(self):
        """Prüft Quellcode-Scanner und Katalog-Aktualisierung."""
        src_dir = self.tmp_path / "src"
        src_dir.mkdir(parents=True)
        py_file = src_dir / "sample_view.py"
        py_file.write_text(
            'label.setText("Dokument speichern")\nbtn.setToolTip("Abbrechen")\n',
            encoding="utf-8",
        )

        catalog_file = self.tmp_path / "translations.json"
        catalog_file.write_text("{}", encoding="utf-8")

        res = scan_and_update(src_dir, catalog_file)
        self.assertIn("Dokument speichern", res["added"])
        self.assertIn("Abbrechen", res["added"])

        data = load_translations(catalog_file)
        self.assertIn("Dokument speichern", data)
        self.assertEqual(data["Dokument speichern"]["de"], "Dokument speichern")
        self.assertEqual(data["Dokument speichern"]["en"], "")

    def test_find_german_strings_skips_internal_dirs(self):
        """Stellt sicher, dass __pycache__, .git und venv übersprungen werden."""
        skip_dir = self.tmp_path / "__pycache__"
        skip_dir.mkdir(parents=True)
        (skip_dir / "cached.py").write_text('tr("Fehler")', encoding="utf-8")

        found = find_german_strings(self.tmp_path)
        self.assertEqual(len(found), 0)

    def test_translator_system_atomic_persistence(self):
        """Verifiziert, dass TranslationSystem atomare Speicherung nutzt."""
        mock_locales = self.tmp_path / "locales"
        mock_locales.mkdir(parents=True)
        mock_trans = mock_locales / "translations.json"
        mock_trans.write_text(
            json.dumps({"Hallo": {"de": "Hallo", "en": "Hello", "es": "", "zh": "", "ja": "", "ru": ""}}),
            encoding="utf-8",
        )

        ts = TranslationSystem(app_dir=self.tmp_path)
        self.assertEqual(ts.t("Hallo"), "Hallo")

        ts.add_translation("Welt", de="Welt", en="World", es="Mundo", zh="世界", ja="世界", ru="Мир")
        self.assertEqual(ts.t("Welt"), "Welt")

        # Prüfe, dass keine .tmp-Dateien existieren
        tmp_files = list(mock_locales.glob("*.tmp.*"))
        self.assertEqual(len(tmp_files), 0)

        # Prüfe, dass Datei aktualisiert wurde
        with open(mock_trans, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertIn("Welt", saved)
        self.assertEqual(saved["Welt"]["en"], "World")

    def test_cli_main_check(self):
        """Prüft CLI main mit --check (Erfolg)."""
        ret = main(["--check", "--dir", str(PROJECT_ROOT)])
        self.assertEqual(ret, 0)

    def test_cli_main_check_failure(self):
        """Prüft CLI main mit --check bei fehlerhafter Datei (Exit 1)."""
        bad_dir = self.tmp_path / "empty_dir"
        bad_dir.mkdir()
        (bad_dir / "translations.json").write_text("{}", encoding="utf-8")
        ret = main(["--check", "--dir", str(bad_dir)])
        self.assertEqual(ret, 1)

    def test_cli_main_stats(self):
        """Prüft CLI main mit --stats."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["--stats", "--dir", str(PROJECT_ROOT)])
        self.assertEqual(ret, 0)
        self.assertIn("DokuZen - Tier-2 Übersetzungskatalog-Statistiken", buf.getvalue())

    def test_cli_main_stats_json(self):
        """Prüft CLI main mit --stats --json."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["--stats", "--json", "--dir", str(PROJECT_ROOT)])
        self.assertEqual(ret, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["perfect_parity"])
        self.assertGreaterEqual(parsed["total_keys"], 540)


if __name__ == "__main__":
    unittest.main()
