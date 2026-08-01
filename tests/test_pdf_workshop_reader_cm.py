#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für pdf_workshop — PDFReader wird als Context Manager genutzt.

Bugfix: reader.open()/.close() direkt aufgerufen; bei Exception in get_info()
        oder page_count-Zugriff wurde reader.close() nie aufgerufen.
"""

import sys
import ast
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE = Path(PROJECT_ROOT) / "gui" / "dialogs" / "pdf_workshop.py"


class TestPDFWorkshopReaderContextManager(unittest.TestCase):
    """AST-basierte Prüfungen — kein PySide6 benötigt."""

    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_no_bare_reader_close_call(self):
        """reader.close() darf nicht direkt aufgerufen werden — Context Manager stattdessen."""
        source = self.source
        # Search for pattern: reader.close() without being inside a finally block
        # Simplified: just check there's no 'reader.close()' in the source at all
        self.assertNotIn("reader.close()", source,
                         "reader.close() direkt aufgerufen statt Context Manager zu nutzen")

    def test_pdf_reader_used_as_context_manager(self):
        """PDFReader muss als Context Manager (with PDFReader() as reader:) genutzt werden."""
        self.assertIn("with PDFReader() as reader:", self.source,
                      "PDFReader nicht als Context Manager genutzt")

    def _count_with_pdfr(self):
        count = 0
        for node in ast.walk(self.tree):
            if isinstance(node, ast.With):
                for item in node.items:
                    if (isinstance(item.context_expr, ast.Call) and
                            isinstance(item.context_expr.func, ast.Name) and
                            item.context_expr.func.id == 'PDFReader'):
                        count += 1
        return count

    def test_both_reader_usages_use_context_manager(self):
        """Beide PDFReader-Verwendungen müssen als Context Manager vorliegen."""
        count = self._count_with_pdfr()
        self.assertGreaterEqual(count, 2,
                                f"Erwartet ≥2 'with PDFReader()' Blöcke, gefunden: {count}")


if __name__ == "__main__":
    unittest.main()
