#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für GlobalSearchBar — os.startfile nur im Windows-Branch.

Bugfix (#34): _on_item_double_clicked() verwendete nur os.startfile(),
              was auf macOS und Linux zu AttributeError führt.
              Korrekt: sys.platform-Branch wie in main_window.py.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE = PROJECT_ROOT / "gui" / "widgets" / "global_search_bar.py"


class TestSearchBarPlatformOpen(unittest.TestCase):
    """Bug #34: os.startfile darf nur im win32-Branch stehen."""

    def _source(self):
        return SOURCE.read_text(encoding="utf-8")

    def test_no_bare_startfile(self):
        """os.startfile darf nicht ohne sys.platform-Guard aufgerufen werden."""
        lines = self._source().splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "os.startfile" in stripped:
                # Prüfe ob in einem win32-Block — suche rückwärts nach dem Guard
                context = lines[max(0, i - 5):i + 1]
                has_win32_guard = any("win32" in l for l in context)
                self.assertTrue(has_win32_guard,
                    f"os.startfile in Zeile {i+1} ohne win32-Guard:\n"
                    + "\n".join(f"  {l}" for l in context))

    def test_darwin_branch_present(self):
        """Ein macOS-Branch (darwin + subprocess.run open) muss vorhanden sein."""
        source = self._source()
        self.assertIn("darwin", source,
            "Kein macOS-Branch in global_search_bar.py")
        self.assertIn('"open"', source,
            "Kein `subprocess.run([\"open\", ...])` in global_search_bar.py")

    def test_linux_branch_present(self):
        """Ein Linux-Branch (xdg-open) muss vorhanden sein."""
        source = self._source()
        self.assertIn("xdg-open", source,
            "Kein Linux-Branch (xdg-open) in global_search_bar.py")

    def test_win32_branch_present(self):
        """Ein Windows-Branch (win32) muss vorhanden sein."""
        source = self._source()
        self.assertIn("win32", source,
            "Kein Windows-Branch in global_search_bar.py")


if __name__ == "__main__":
    unittest.main()
