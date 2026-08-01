#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PersistenceManager.delete_theme — last_theme-Fix.

Bugfix: Beim Löschen eines Themas wurde last_theme in settings nicht aktualisiert,
        wenn das gelöschte Thema das aktive war.
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Stubs ---
if "utils.logger" not in sys.modules:
    _logger_stub = types.ModuleType("utils.logger")

    class _LoggerMixin:
        @property
        def logger(self):
            if not hasattr(self, "_logger"):
                self._logger = MagicMock()
            return self._logger

    _logger_stub.LoggerMixin = _LoggerMixin
    _logger_stub.get_logger = lambda name: MagicMock()
    _logger_stub.setup_logger = lambda **kw: None
    sys.modules["utils.logger"] = _logger_stub

import importlib.util as _ilu

# Temporär ersetzen (wie test_pdf_security_unlock.py für fitz), damit andere
# Tests (z. B. test_source_platform_smoke.py) dieselbe Klasse patchen, die
# LibraryManager intern verwendet.
_orig_pm_mod = sys.modules.get("core.library.persistence")
_spec = _ilu.spec_from_file_location(
    "core.library.persistence",
    PROJECT_ROOT / "core" / "library" / "persistence.py"
)
_pm_mod = _ilu.module_from_spec(_spec)
sys.modules["core.library.persistence"] = _pm_mod
_spec.loader.exec_module(_pm_mod)

# sys.modules wiederherstellen — dieser Test arbeitet nur mit _pm_mod.PersistenceManager
if _orig_pm_mod is not None:
    sys.modules["core.library.persistence"] = _orig_pm_mod
else:
    del sys.modules["core.library.persistence"]

PersistenceManager = _pm_mod.PersistenceManager


def _make_pm_with_two_themes(active_theme="Arbeit"):
    pm = PersistenceManager.__new__(PersistenceManager)
    pm._logger = MagicMock()
    import threading
    pm._lock = threading.Lock()
    pm._dirty = False
    pm._state = {
        "version": "1.0",
        "themes": {
            "Arbeit": {"created": "2026-01-01T00:00:00", "documents": []},
            "Privat": {"created": "2026-01-01T00:00:00", "documents": []},
        },
        "settings": {
            "last_theme": active_theme,
            "sort_by": "name",
            "filter": "all",
        },
    }
    return pm


class TestDeleteThemeLastThemeUpdate(unittest.TestCase):

    def test_delete_active_theme_updates_last_theme(self):
        """Kerntest: Wenn das aktive Thema gelöscht wird, zeigt last_theme auf ein anderes Thema."""
        pm = _make_pm_with_two_themes(active_theme="Arbeit")
        result = pm.delete_theme("Arbeit")

        self.assertTrue(result)
        self.assertNotIn("Arbeit", pm._state["themes"])
        last = pm._state["settings"]["last_theme"]
        self.assertNotEqual(last, "Arbeit",
                            "last_theme darf nicht mehr auf 'Arbeit' zeigen")
        self.assertIn(last, pm._state["themes"],
                      "last_theme muss ein existierendes Thema sein")

    def test_delete_inactive_theme_keeps_last_theme(self):
        """Wenn ein inaktives Thema gelöscht wird, bleibt last_theme unverändert."""
        pm = _make_pm_with_two_themes(active_theme="Arbeit")
        pm.delete_theme("Privat")

        self.assertEqual(pm._state["settings"]["last_theme"], "Arbeit")

    def test_delete_only_theme_not_allowed(self):
        """Das letzte Thema darf nicht gelöscht werden."""
        pm = PersistenceManager.__new__(PersistenceManager)
        pm._logger = MagicMock()
        import threading
        pm._lock = threading.Lock()
        pm._dirty = False
        pm._state = {
            "version": "1.0",
            "themes": {
                "Einzig": {"created": "2026-01-01T00:00:00", "documents": []},
            },
            "settings": {"last_theme": "Einzig"},
        }
        result = pm.delete_theme("Einzig")
        self.assertFalse(result)
        self.assertIn("Einzig", pm._state["themes"])

    def test_delete_nonexistent_theme_returns_false(self):
        pm = _make_pm_with_two_themes()
        result = pm.delete_theme("Nicht vorhanden")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
