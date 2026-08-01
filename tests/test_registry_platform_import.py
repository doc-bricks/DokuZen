#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellt sicher, dass registry.py auf Nicht-Windows-Plattformen importierbar ist,
ohne dass winreg installiert ist.
"""

import sys
import importlib.util as _ilu
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_REGISTRY_PATH = PROJECT_ROOT / "plugins" / "spawner" / "registry.py"
_PROBE_MODULE_NAME = "plugins.spawner.registry_noreg_probe"


class TestRegistryPlatformImport(unittest.TestCase):

    def setUp(self):
        self._saved_winreg = sys.modules.get("winreg", "MISSING")

    def tearDown(self):
        if self._saved_winreg == "MISSING":
            sys.modules.pop("winreg", None)
        else:
            sys.modules["winreg"] = self._saved_winreg
        sys.modules.pop(_PROBE_MODULE_NAME, None)

    def _load_registry_without_winreg(self):
        """Lädt registry.py mit winreg=None, simuliert Nicht-Windows-Umgebung."""
        sys.modules["winreg"] = None  # erzwingt ImportError-Pfad
        spec = _ilu.spec_from_file_location(_PROBE_MODULE_NAME, _REGISTRY_PATH)
        mod = _ilu.module_from_spec(spec)
        sys.modules[_PROBE_MODULE_NAME] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_importable_without_winreg(self):
        """registry.py darf keinen ImportError werfen, wenn winreg fehlt."""
        try:
            self._load_registry_without_winreg()
        except ImportError as e:
            self.fail(f"registry.py ist ohne winreg nicht importierbar: {e}")

    def test_winreg_available_flag_is_false(self):
        """_WINREG_AVAILABLE muss False sein, wenn winreg nicht verfügbar ist."""
        mod = self._load_registry_without_winreg()
        self.assertFalse(
            mod._WINREG_AVAILABLE,
            "_WINREG_AVAILABLE sollte False sein, wenn winreg fehlt",
        )

    def test_registry_manager_hkcr_is_none_without_winreg(self):
        """RegistryManager.HKCR muss None sein, wenn winreg nicht verfügbar ist."""
        mod = self._load_registry_without_winreg()
        self.assertIsNone(
            mod.RegistryManager.HKCR,
            "RegistryManager.HKCR sollte None sein, wenn winreg fehlt",
        )

    def test_registry_manager_hkcu_is_none_without_winreg(self):
        """RegistryManager.HKCU muss None sein, wenn winreg nicht verfügbar ist."""
        mod = self._load_registry_without_winreg()
        self.assertIsNone(
            mod.RegistryManager.HKCU,
            "RegistryManager.HKCU sollte None sein, wenn winreg fehlt",
        )


if __name__ == "__main__":
    unittest.main()
