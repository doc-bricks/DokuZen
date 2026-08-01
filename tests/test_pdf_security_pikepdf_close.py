#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFSecurity — pikepdf-Dokument wird auch bei Ausnahme geschlossen.

Bugfix: pdf.close() wurde übersprungen wenn pdf.save() eine Exception warf.
        Betrifft _unlock_pikepdf() und remove_restrictions().
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_pikepdf_stub(save_raises=None):
    """Erstellt einen pikepdf-Stub mit optionalem Fehler beim save()."""
    pdf_doc = MagicMock()
    if save_raises:
        pdf_doc.save.side_effect = save_raises

    pikepdf_stub = MagicMock()
    pikepdf_stub.open.return_value = pdf_doc
    pikepdf_stub.PasswordError = Exception

    return pikepdf_stub, pdf_doc


class TestUnlockPikepdfClose(unittest.TestCase):

    def test_close_called_on_save_exception(self):
        """pdf.close() wird auch aufgerufen wenn save() eine Exception wirft."""
        import core.pdf.security as sec_mod

        pikepdf_stub, pdf_doc = _make_pikepdf_stub(save_raises=OSError("Disk voll"))

        with patch.object(sec_mod, 'pikepdf', pikepdf_stub, create=True), \
             patch.object(sec_mod, 'PIKEPDF_AVAILABLE', True):
            security = sec_mod.PDFSecurity.__new__(sec_mod.PDFSecurity)
            result = security._unlock_pikepdf("input.pdf", "output.pdf", "")

        pdf_doc.close.assert_called_once()
        self.assertFalse(result.success)

    def test_close_called_on_success(self):
        """pdf.close() wird auch bei Erfolg aufgerufen."""
        import core.pdf.security as sec_mod

        pikepdf_stub, pdf_doc = _make_pikepdf_stub()

        with patch.object(sec_mod, 'pikepdf', pikepdf_stub, create=True), \
             patch.object(sec_mod, 'PIKEPDF_AVAILABLE', True):
            security = sec_mod.PDFSecurity.__new__(sec_mod.PDFSecurity)
            result = security._unlock_pikepdf("input.pdf", "output.pdf", "")

        pdf_doc.close.assert_called_once()
        self.assertTrue(result.success)


class TestRemoveRestrictionsPikepdfClose(unittest.TestCase):

    def test_close_called_on_save_exception(self):
        """pdf.close() wird auch aufgerufen wenn save() in remove_restrictions() wirft."""
        import core.pdf.security as sec_mod

        pikepdf_stub, pdf_doc = _make_pikepdf_stub(save_raises=RuntimeError("save failed"))

        with patch.object(sec_mod, 'pikepdf', pikepdf_stub, create=True), \
             patch.object(sec_mod, 'PIKEPDF_AVAILABLE', True):
            security = sec_mod.PDFSecurity.__new__(sec_mod.PDFSecurity)
            result = security.remove_restrictions("input.pdf", "output.pdf", "")

        pdf_doc.close.assert_called_once()
        self.assertFalse(result.success)

    def test_close_called_on_success(self):
        """pdf.close() wird auch bei Erfolg von remove_restrictions() aufgerufen."""
        import core.pdf.security as sec_mod

        pikepdf_stub, pdf_doc = _make_pikepdf_stub()

        with patch.object(sec_mod, 'pikepdf', pikepdf_stub, create=True), \
             patch.object(sec_mod, 'PIKEPDF_AVAILABLE', True):
            security = sec_mod.PDFSecurity.__new__(sec_mod.PDFSecurity)
            result = security.remove_restrictions("input.pdf", "output.pdf", "")

        pdf_doc.close.assert_called_once()
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
