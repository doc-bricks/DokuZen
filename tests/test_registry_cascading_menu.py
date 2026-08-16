#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für DokuZenRegistry.register_all und RegistryManager-Cascading-Menus.
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

if "winreg" not in sys.modules:
    sys.modules["winreg"] = MagicMock()

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "plugins.spawner.registry",
    PROJECT_ROOT / "plugins" / "spawner" / "registry.py",
)
_reg_mod = _ilu.module_from_spec(_spec)
sys.modules["plugins.spawner.registry"] = _reg_mod
_spec.loader.exec_module(_reg_mod)

DokuZenRegistry = _reg_mod.DokuZenRegistry
RegistryManager = _reg_mod.RegistryManager


def _make_registry():
    reg = DokuZenRegistry.__new__(DokuZenRegistry)
    reg._logger = MagicMock()
    reg._manager = MagicMock(spec=RegistryManager)
    reg._manager.register_cascading_menu.return_value = True
    reg._manager.register_menu_item.return_value = True
    reg._manager.unregister_menu_item.return_value = True
    reg._manager.is_registered.return_value = True
    reg._manager.__class__ = RegistryManager
    reg._python_path = "python"
    reg._app_path = "main.py"
    return reg


class TestRegisterAllPdfScope(unittest.TestCase):

    def test_register_all_passes_pdf_extensions_to_cascading_menu(self):
        """Das PDF-Untermenü muss auf .pdf begrenzt werden."""
        reg = _make_registry()
        reg.register_all()

        _, kwargs = reg._manager.register_cascading_menu.call_args
        self.assertEqual(kwargs.get("extensions"), [".pdf"])

    def test_register_all_calls_cascading_menu_for_pdf(self):
        """register_all muss register_cascading_menu für das PDF-Menü aufrufen."""
        reg = _make_registry()
        reg.register_all()

        self.assertTrue(
            reg._manager.register_cascading_menu.called,
            "register_cascading_menu sollte für das PDF-Menü aufgerufen werden",
        )

    def test_register_all_returns_dict(self):
        """register_all gibt ein dict mit Ergebnissen zurück."""
        reg = _make_registry()
        result = reg.register_all()
        self.assertIsInstance(result, dict)

    def test_register_all_no_type_error(self):
        """register_all darf keinen TypeError auslösen."""
        reg = _make_registry()
        try:
            reg.register_all()
        except TypeError as e:
            self.fail(f"register_all löste TypeError aus: {e}")

    def test_unregister_all_removes_pdf_menu_via_pdf_scope(self):
        """Das PDF-Menü muss beim Deregistrieren ebenfalls .pdf-gebunden sein."""
        reg = _make_registry()
        reg.unregister_all()

        first_call_args = reg._manager.unregister_menu_item.call_args_list[0]
        _, kwargs = first_call_args
        self.assertEqual(kwargs.get("extensions"), [".pdf"])

    def test_status_checks_pdf_menu_via_pdf_scope(self):
        """Die Statusprüfung darf nicht nur den globalen *\\shell-Pfad prüfen."""
        reg = _make_registry()
        reg.get_status()

        first_call_args = reg._manager.is_registered.call_args_list[0]
        _, kwargs = first_call_args
        self.assertEqual(kwargs.get("extensions"), [".pdf"])


class TestRegistryManagerCascadingExtensions(unittest.TestCase):

    def test_cascading_menu_uses_pdf_association_path(self):
        """PDF-Untermenüs dürfen nicht global unter *\\shell landen."""
        manager = RegistryManager()
        created_paths = []

        def _fake_create(_root, base_path, _menu_name, _label, _items, _icon):
            created_paths.append(base_path)

        manager._create_cascading_menu_entry = _fake_create

        ok = manager.register_cascading_menu(
            "DokuZen_PDF",
            "DokuZen",
            [],
            extensions=[".pdf"],
        )

        self.assertTrue(ok)
        self.assertEqual(
            created_paths,
            [r"Software\Classes\SystemFileAssociations\.pdf\shell"],
        )


if __name__ == "__main__":
    unittest.main()
