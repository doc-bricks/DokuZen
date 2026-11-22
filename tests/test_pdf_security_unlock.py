#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFSecurity._unlock_pymupdf — Owner-Passwort-Fix.

Bugfix: Im else-Zweig (needs_pass=False) wurde doc.authenticate("") aufgerufen
        statt doc.authenticate(password) — das Owner-Passwort wurde ignoriert.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import core.pdf.security as _sec_mod
from core.pdf.security import PDFSecurity


def _make_security():
    sec = PDFSecurity.__new__(PDFSecurity)
    sec._logger = MagicMock()
    return sec


class TestUnlockOwnerPassword(unittest.TestCase):

    def setUp(self):
        self._sec_fitz = MagicMock()
        self._sec_fitz.PDF_ENCRYPT_NONE = 0
        self._patcher = patch.object(_sec_mod, "fitz", self._sec_fitz)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def _mock_doc(self, is_encrypted=True, needs_pass=False, authenticate_returns=True):
        doc = MagicMock()
        doc.is_encrypted = is_encrypted
        doc.needs_pass = needs_pass
        doc.authenticate.return_value = authenticate_returns
        doc.save.return_value = None
        doc.close.return_value = None
        return doc

    def test_owner_password_passed_to_authenticate_when_no_user_password(self):
        """Kerntest des Bugfixes: password wird an authenticate() übergeben, nicht ''."""
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=False)
        self._sec_fitz.open.return_value = mock_doc

        with patch("builtins.open", MagicMock()):
            with patch.object(Path, "exists", return_value=True):
                result = sec._unlock_pymupdf("input.pdf", "output.pdf", "ownerpass")

        mock_doc.authenticate.assert_called_once_with("ownerpass")

    def test_empty_string_used_when_no_password_given(self):
        """Wenn kein Passwort übergeben: authenticate("") ist korrekt."""
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=False)
        self._sec_fitz.open.return_value = mock_doc

        result = sec._unlock_pymupdf("input.pdf", "output.pdf", "")

        mock_doc.authenticate.assert_called_once_with("")

    def test_user_password_used_when_needs_pass_true(self):
        """Wenn needs_pass=True: authenticate() wird mit übergebenem Passwort aufgerufen."""
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=True, authenticate_returns=True)
        self._sec_fitz.open.return_value = mock_doc

        result = sec._unlock_pymupdf("input.pdf", "output.pdf", "userpass")

        mock_doc.authenticate.assert_called_once_with("userpass")

    def test_wrong_password_returns_failure(self):
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=True, authenticate_returns=False)
        self._sec_fitz.open.return_value = mock_doc

        result = sec._unlock_pymupdf("input.pdf", "output.pdf", "wrongpass")

        self.assertFalse(result.success)
        self.assertIn("Passwort", result.error)


if __name__ == "__main__":
    unittest.main()
