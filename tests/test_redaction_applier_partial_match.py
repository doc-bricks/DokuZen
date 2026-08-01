#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für RedactionApplier.redact_pdf() — Statistik über nicht gefundene Treffer.

Bugfix (Review 2026-07-23, P0 Privacy):
    page.search_for(match.text) findet Treffer mit internen Leerzeichen oder
    Zeilenumbrüchen (z.B. IBAN "DE89 3704 ...") häufig NICHT. Bisher gab
    redact_pdf() in diesem Fall trotzdem `True` zurück, obwohl der Treffer im
    Ergebnis-PDF ungeschwärzt blieb -- ein stiller PII-Leak. Jetzt zählt
    RedactionApplier mit, wie viele Treffer tatsächlich lokalisiert wurden,
    und stellt das Ergebnis über `last_redaction_stats` sowie eine
    Logger-Warnung bereit.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_match(text, page=1):
    from core.redaction.detector import Match, SensitiveType
    return Match(text=text, start=0, end=len(text), type=SensitiveType.CUSTOM,
                 confidence=100.0, page=page)


class TestRedactionApplierPartialMatch(unittest.TestCase):

    def _make_applier_with_page(self, search_for_side_effect):
        """Baut einen RedactionApplier mit einem fitz-Stub, dessen einzige Seite
        `search_for` gemäss side_effect beantwortet."""
        import core.redaction.detector as det_mod

        page = MagicMock()
        page.search_for.side_effect = search_for_side_effect

        doc = MagicMock()
        doc.page_count = 1
        doc.__getitem__ = MagicMock(return_value=page)

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = doc

        with patch.dict('sys.modules', {'fitz': fitz_stub}):
            applier = det_mod.RedactionApplier()
        return applier, doc, page

    def test_missed_match_is_counted_and_logged(self):
        """Ein Treffer ohne Fundstelle wird als 'missed' gezählt und geloggt,
        das Gesamtergebnis bleibt aber True (Datei wurde geschrieben)."""
        import core.redaction.detector as det_mod

        # Erster Treffer: gefunden. Zweiter Treffer (IBAN mit Leerzeichen): nicht gefunden.
        applier, doc, page = self._make_applier_with_page(
            search_for_side_effect=[[MagicMock()], []]
        )

        matches = [_make_match("max@example.com"), _make_match("DE89 3704 0044 0532 0130 00")]

        mock_logger = MagicMock()
        applier._logger = mock_logger
        result = applier.redact_pdf("input.pdf", "output.pdf", matches)

        self.assertTrue(result)
        self.assertEqual(applier.last_redaction_stats["total"], 2)
        self.assertEqual(applier.last_redaction_stats["redacted"], 1)
        self.assertEqual(applier.last_redaction_stats["missed"], 1)
        mock_logger.warning.assert_called_once()
        doc.save.assert_called_once_with("output.pdf")

    def test_all_matches_found_reports_zero_missed(self):
        """Wenn alle Treffer lokalisiert werden, bleibt 'missed' bei 0 und es
        wird keine Warnung geloggt."""
        applier, doc, page = self._make_applier_with_page(
            search_for_side_effect=[[MagicMock()], [MagicMock()]]
        )

        matches = [_make_match("a@b.de"), _make_match("c@d.de")]

        mock_logger = MagicMock()
        applier._logger = mock_logger
        result = applier.redact_pdf("input.pdf", "output.pdf", matches)

        self.assertTrue(result)
        self.assertEqual(applier.last_redaction_stats, {"total": 2, "redacted": 2, "missed": 0})
        mock_logger.warning.assert_not_called()

    def test_stats_reset_on_each_call(self):
        """last_redaction_stats wird bei jedem Aufruf frisch berechnet, nicht
        über mehrere redact_pdf()-Aufrufe hinweg akkumuliert."""
        applier, doc, page = self._make_applier_with_page(
            search_for_side_effect=[[], [MagicMock()], [MagicMock()]]
        )

        applier._logger = MagicMock()
        applier.redact_pdf("input.pdf", "output.pdf", [_make_match("erster")])
        applier.redact_pdf("input.pdf", "output.pdf",
                            [_make_match("zweiter"), _make_match("dritter")])

        self.assertEqual(applier.last_redaction_stats, {"total": 2, "redacted": 2, "missed": 0})


if __name__ == "__main__":
    unittest.main()
