#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für Falsy-Doc-Guards in Dialog-Klassen.

Bugfix #36: pdf_marker_dialog.py hatte `if doc:` und `if new_doc:` in finally-Blöcken.
            0-Seiten-PDFs (bool==False) wurden nie geschlossen → Resource-Leak.
Bugfix #37: pdf_pages_dialog.py hatte `if self._doc:` / `if not self._doc:` statt
            `if self._doc is not None:` / `if self._doc is None:`.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MARKER_SOURCE = PROJECT_ROOT / "gui" / "dialogs" / "pdf_marker_dialog.py"
PAGES_SOURCE = PROJECT_ROOT / "gui" / "dialogs" / "pdf_pages_dialog.py"


class TestPDFMarkerDialogGuards(unittest.TestCase):
    """Bug #36: Falsy Guards in pdf_marker_dialog.py."""

    def _source(self):
        return MARKER_SOURCE.read_text(encoding="utf-8")

    def test_no_bare_if_doc_guard(self):
        """Kein `if doc:` oder `if new_doc:` darf mehr vorkommen."""
        source = self._source()
        for guard in ("if doc:", "if new_doc:"):
            self.assertNotIn(guard, source,
                f"Falsy Guard gefunden in pdf_marker_dialog.py: {guard!r}")

    def test_is_none_guards_present(self):
        """Mindestens 3 `is not None:`-Guards in pdf_marker_dialog.py."""
        source = self._source()
        count = source.count("is not None:")
        self.assertGreaterEqual(count, 3,
            f"Erwartet ≥3 `is not None:`-Guards, gefunden: {count}")


class TestPDFPagesDialogGuards(unittest.TestCase):
    """Bug #37: Falsy Guards in pdf_pages_dialog.py."""

    def _source(self):
        return PAGES_SOURCE.read_text(encoding="utf-8")

    def test_no_bare_if_self_doc(self):
        """Kein `if self._doc:` oder `if not self._doc:` darf vorkommen."""
        source = self._source()
        self.assertNotIn("if self._doc:", source,
            "Falsy Guard `if self._doc:` in pdf_pages_dialog.py gefunden")
        self.assertNotIn("if not self._doc:", source,
            "Falsy Guard `if not self._doc:` in pdf_pages_dialog.py gefunden")

    def test_is_none_pattern_used(self):
        """Korrekte Guards `if self._doc is not None:` und `if self._doc is None:` vorhanden."""
        source = self._source()
        self.assertIn("if self._doc is not None:", source,
            "`if self._doc is not None:` nicht in pdf_pages_dialog.py")
        self.assertIn("if self._doc is None:", source,
            "`if self._doc is None:` nicht in pdf_pages_dialog.py")

    def test_is_none_guard_count(self):
        """Mindestens 5 `_doc is`-Guards in pdf_pages_dialog.py (7 wurden gefixt)."""
        source = self._source()
        count_not_none = source.count("self._doc is not None")
        count_is_none = source.count("self._doc is None")
        total = count_not_none + count_is_none
        self.assertGreaterEqual(total, 5,
            f"Erwartet ≥5 `_doc is`-Guards, gefunden: {total}")


if __name__ == "__main__":
    unittest.main()
