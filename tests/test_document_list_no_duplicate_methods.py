#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für DocumentListPanel — doppelte Methoden-Definitionen entfernt.

Bugfix: select_all und get_selected_paths waren zweimal definiert.
        Python nutzt immer die letzte Definition; die ersten waren toter Code.
"""

import sys
import inspect
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestDocumentListNoDuplicateMethods(unittest.TestCase):

    def _get_class_methods(self):
        """Lädt DocumentListPanel ohne PySide6-Import."""
        import ast
        src = (PROJECT_ROOT / "gui" / "panels" / "document_list.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "DocumentListPanel":
                return [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
        return []

    def test_get_selected_paths_defined_exactly_once(self):
        """get_selected_paths darf nur einmal im AST der Klasse vorkommen."""
        methods = self._get_class_methods()
        count = methods.count("get_selected_paths")
        self.assertEqual(count, 1,
            f"get_selected_paths ist {count}× definiert — sollte genau 1× sein")

    def test_select_all_defined_exactly_once(self):
        """select_all darf nur einmal im AST der Klasse vorkommen."""
        methods = self._get_class_methods()
        count = methods.count("select_all")
        self.assertEqual(count, 1,
            f"select_all ist {count}× definiert — sollte genau 1× sein")


if __name__ == "__main__":
    unittest.main()
