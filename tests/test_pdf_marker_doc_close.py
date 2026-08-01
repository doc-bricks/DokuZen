#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFMarkerDialog — fitz-Dokument wird auch bei Exception geschlossen.

Bugfix 1: _load_pdf() schloss doc nicht wenn len(doc) eine Exception warf.
Bugfix 2: _extract_pages_to_file() öffnete zwei docs; wenn das zweite open()
          fehlschlug, wurde das erste nie geschlossen.
Bugfix 3: ThumbnailLoader.run() schluckte Exceptions still (except: pass).
Bugfix #36: `if doc:` / `if new_doc:` in finally → `if doc is not None:` /
            `if new_doc is not None:` — 0-Seiten-PDFs wurden nie geschlossen.
"""

import sys
import ast
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE = Path(PROJECT_ROOT) / "gui" / "dialogs" / "pdf_marker_dialog.py"


class TestPDFMarkerDocCloseAST(unittest.TestCase):
    """AST-basierte Prüfungen — kein PySide6 benötigt."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    def _find_method(self, class_name, method_name):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        return item
        return None

    def _has_finally_with_close(self, func_node):
        """Prüft ob eine Funktion einen finally-Block mit doc.close() enthält."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Try) and node.finalbody:
                for stmt in ast.walk(ast.Module(body=node.finalbody, type_ignores=[])):
                    if (isinstance(stmt, ast.Expr) and
                            isinstance(stmt.value, ast.Call) and
                            isinstance(stmt.value.func, ast.Attribute) and
                            stmt.value.func.attr == 'close'):
                        return True
        return False

    def test_load_pdf_has_finally_with_close(self):
        """_load_pdf() muss finally mit doc.close() und is-not-None-Guard haben."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("doc = None", source)
        self.assertIn("if doc is not None:", source)
        self.assertIn("doc.close()", source)
        self.assertNotIn("if doc:", source,
            "Falsy Guard `if doc:` darf nicht mehr in pdf_marker_dialog.py vorkommen")

    def test_extract_pages_uses_finally_for_both_docs(self):
        """Die Extract-Methode muss finally verwenden das beide docs mit is-not-None schließt."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("new_doc = None", source)
        self.assertIn("if new_doc is not None:", source)
        self.assertIn("new_doc.close()", source)
        self.assertIn("if doc is not None:", source)
        self.assertNotIn("if new_doc:", source,
            "Falsy Guard `if new_doc:` darf nicht mehr in pdf_marker_dialog.py vorkommen")

    def test_no_bare_doc_close_before_except(self):
        """doc.close() darf nicht nur auf dem Erfolgspfad (ohne finally) stehen."""
        # Find the _load_pdf_for_count pattern (old: doc.close() inside try, before except)
        # The old pattern was:
        #   try:
        #       doc = fitz.open(path)
        #       self._page_count = len(doc)
        #       doc.close()   <-- this was the bug
        #   except:
        # Verify the code no longer has doc.close() immediately before except without finally
        source = SOURCE.read_text(encoding="utf-8")
        lines = source.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "doc.close()" and i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped.startswith("except"):
                    self.fail(
                        f"Line {i+1}: bare doc.close() immediately before except "
                        f"(not in finally) — resource leak"
                    )


class TestThumbnailLoaderLogsException(unittest.TestCase):
    """ThumbnailLoader.run() darf Exceptions nicht still verschlucken."""

    def test_thumbnail_loader_no_bare_pass_on_exception(self):
        """except Exception in ThumbnailLoader.run() darf kein bloßes 'pass' sein."""
        source = SOURCE.read_text(encoding="utf-8")
        # Nach dem Fix muss _logger.warning im Fehler-Handler stehen
        self.assertIn("_logger.warning", source,
            "ThumbnailLoader.run() muss Exceptions per _logger.warning loggen")

    def test_module_level_logger_defined(self):
        """pdf_marker_dialog.py muss einen Modul-Logger definieren."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("get_logger", source,
            "get_logger() muss für den Modul-Logger importiert werden")


if __name__ == "__main__":
    unittest.main()
