#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFProcessor — Guard-Check ist semantisch korrekt.

Bugfix: `if not self._reader._doc:` behandelt 0-Seiten-PDFs fälschlicherweise
        als "nicht geladen" (bool(fitz.Document mit 0 Seiten) == False).
        Korrekt: `if self._reader._doc is None:`
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE = PROJECT_ROOT / "core" / "pdf" / "processor.py"


class TestPDFProcessorDocGuard(unittest.TestCase):
    """Guard-Check verwendet `is None` statt Wahrheitswert-Prüfung."""

    def test_no_falsy_doc_guard(self):
        """processor.py darf nicht `if not self._reader._doc:` verwenden."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn(
            "if not self._reader._doc:",
            source,
            "Guard-Check darf nicht `if not self._reader._doc:` sein — "
            "0-Seiten-PDFs würden falsch als nicht geladen behandelt."
        )

    def test_correct_none_guard_present(self):
        """processor.py muss `if self._reader._doc is None:` verwenden."""
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "if self._reader._doc is None:",
            source,
            "Guard-Check muss `if self._reader._doc is None:` sein."
        )

    def test_guard_count(self):
        """Alle vier Methoden-Guards wurden korrigiert."""
        source = SOURCE.read_text(encoding="utf-8")
        count = source.count("if self._reader._doc is None:")
        self.assertGreaterEqual(count, 4,
            f"Erwartet mindestens 4 Guard-Checks, gefunden: {count}")


if __name__ == "__main__":
    unittest.main()
