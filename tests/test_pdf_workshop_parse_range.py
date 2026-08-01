#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFWorkshopDialog._parse_page_range — ungültige Eingaben.

Bugfix: Ungültige Ausdrücke wie "5-", "-5", "a-b" warfen ungefangene ValueError
        aus dem Qt-Slot. Die Methode gibt jetzt [] zurück statt zu crashen.
"""

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from gui.dialogs.pdf_workshop import PDFWorkshopDialog


class TestParsePageRange(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])
        cls._dlg = PDFWorkshopDialog.__new__(PDFWorkshopDialog)

    def _parse(self, text):
        return self._dlg._parse_page_range(text)

    # --- Korrekte Eingaben ---

    def test_single_pages(self):
        self.assertEqual(self._parse("1,3,5"), [1, 3, 5])

    def test_range(self):
        self.assertEqual(self._parse("5-10"), [5, 6, 7, 8, 9, 10])

    def test_mixed(self):
        self.assertEqual(self._parse("1,3,5-7"), [1, 3, 5, 6, 7])

    def test_whitespace_tolerance(self):
        self.assertEqual(self._parse(" 1 , 3 , 5 - 7 "), [1, 3, 5, 6, 7])

    def test_deduplicates(self):
        self.assertEqual(self._parse("1,1,2,2"), [1, 2])

    # --- Ungültige Eingaben — dürfen NICHT werfen ---

    def test_empty_string_returns_empty(self):
        self.assertEqual(self._parse(""), [])

    def test_trailing_dash_returns_empty(self):
        self.assertEqual(self._parse("5-"), [])

    def test_leading_dash_returns_empty(self):
        self.assertEqual(self._parse("-5"), [])

    def test_alpha_returns_empty(self):
        self.assertEqual(self._parse("a-b"), [])

    def test_non_numeric_single_returns_empty(self):
        self.assertEqual(self._parse("abc"), [])

    def test_double_dash_returns_empty(self):
        self.assertEqual(self._parse("1--5"), [])


if __name__ == "__main__":
    unittest.main()
