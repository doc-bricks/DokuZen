#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für redact_pdf() — stille Ausnahmen werden geloggt.

Bugfix: except Exception: return False ohne Logging.
        Fehler in redact_pdf() wurden spurlos verschluckt.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestRedactPdfLogsError(unittest.TestCase):

    def _make_fitz_stub(self, raises=None):
        fitz_stub = MagicMock()
        if raises:
            fitz_stub.open.side_effect = raises
        else:
            doc = MagicMock()
            doc.__iter__ = MagicMock(return_value=iter([]))
            fitz_stub.open.return_value = doc
        return fitz_stub

    def test_exception_is_logged_not_silent(self):
        """Fehler in redact_pdf() wird per logger.error geloggt, nicht still verschluckt."""
        import core.redaction.detector as det_mod

        fitz_stub = self._make_fitz_stub(raises=RuntimeError("fitz kaputt"))

        with patch.object(det_mod, '_logger') as mock_logger, \
             patch('builtins.__import__', side_effect=lambda name, *a, **kw:
                   fitz_stub if name == 'fitz' else __import__(name, *a, **kw)):
            # Patch fitz inside the function's local import
            with patch.dict('sys.modules', {'fitz': fitz_stub}):
                result = det_mod.redact_pdf("input.pdf", "output.pdf")

        self.assertFalse(result)
        mock_logger.error.assert_called_once()
        logged_msg = mock_logger.error.call_args[0][0]
        self.assertIn("fitz kaputt", logged_msg)

    def test_returns_false_on_exception(self):
        """redact_pdf() gibt False zurück wenn ein Fehler auftritt."""
        import core.redaction.detector as det_mod

        fitz_stub = self._make_fitz_stub(raises=OSError("Datei nicht gefunden"))

        with patch.dict('sys.modules', {'fitz': fitz_stub}), \
             patch.object(det_mod, '_logger'):
            result = det_mod.redact_pdf("nichtexistent.pdf", "out.pdf")

        self.assertFalse(result)

    def test_doc_closed_on_exception(self):
        """fitz.open()-Dokument wird auch bei Ausnahme geschlossen."""
        import core.redaction.detector as det_mod

        doc = MagicMock()
        pages = [MagicMock()]
        pages[0].get_text.side_effect = RuntimeError("get_text kaputt")
        doc.__iter__ = MagicMock(return_value=iter(pages))

        fitz_stub = MagicMock()
        fitz_stub.open.return_value = doc

        with patch.dict('sys.modules', {'fitz': fitz_stub}), \
             patch.object(det_mod, '_logger'):
            det_mod.redact_pdf("input.pdf", "output.pdf")

        doc.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
