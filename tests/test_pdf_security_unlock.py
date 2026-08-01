#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFSecurity._unlock_pymupdf — Owner-Passwort-Fix.

Bugfix: Im else-Zweig (needs_pass=False) wurde doc.authenticate("") aufgerufen
        statt doc.authenticate(password) — das Owner-Passwort wurde ignoriert.
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Stubs für optionale Deps (nur wenn noch nicht vorhanden) ---
for _mod in ("pikepdf", "PIL", "PIL.Image", "docx", "openpyxl",
             "pytesseract", "cv2", "numpy", "pptx", "chardet",
             "cryptography", "cryptography.fernet"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

if "utils.logger" not in sys.modules:
    _logger_stub = types.ModuleType("utils.logger")

    class _LoggerMixin:
        @property
        def logger(self):
            if not hasattr(self, "_logger"):
                self._logger = MagicMock()
            return self._logger

    _logger_stub.LoggerMixin = _LoggerMixin
    _logger_stub.setup_logger = lambda **kw: None
    _logger_stub.get_logger = lambda name: MagicMock()
    sys.modules["utils.logger"] = _logger_stub

import importlib.util as _ilu

# Fitz temporär durch Mock ersetzen, damit security.py immer unsere
# Mock-Variante von fitz.open() erhält — unabhängig davon, ob das reale
# PyMuPDF bereits von einem anderen Test (z. B. test_dialog_smoke) geladen
# wurde. sys.modules["fitz"] wird nach dem Laden wiederhergestellt.
_orig_fitz = sys.modules.get("fitz")
_sec_fitz = MagicMock()
sys.modules["fitz"] = _sec_fitz

_spec = _ilu.spec_from_file_location(
    "core.pdf.security",
    PROJECT_ROOT / "core" / "pdf" / "security.py"
)
_sec_mod = _ilu.module_from_spec(_spec)
sys.modules["core.pdf.security"] = _sec_mod
_spec.loader.exec_module(_sec_mod)

# sys.modules["fitz"] wiederherstellen (damit z. B. test_source_platform_smoke
# weiterhin das reale fitz verwenden kann)
if _orig_fitz is not None:
    sys.modules["fitz"] = _orig_fitz
else:
    del sys.modules["fitz"]

# Sicherstellen, dass PYMUPDF_AVAILABLE = True (MagicMock-Import garantiert das)
_sec_mod.PYMUPDF_AVAILABLE = True

PDFSecurity = _sec_mod.PDFSecurity


def _make_security():
    sec = PDFSecurity.__new__(PDFSecurity)
    sec._logger = MagicMock()
    return sec


class TestUnlockOwnerPassword(unittest.TestCase):

    def setUp(self):
        # Vor jedem Test den fitz-Mock im Security-Modul zurücksetzen
        _sec_fitz.reset_mock()
        _sec_fitz.PDF_ENCRYPT_NONE = 0

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
        _sec_fitz.open.return_value = mock_doc

        with patch("builtins.open", MagicMock()):
            with patch.object(Path, "exists", return_value=True):
                result = sec._unlock_pymupdf("input.pdf", "output.pdf", "ownerpass")

        mock_doc.authenticate.assert_called_once_with("ownerpass")

    def test_empty_string_used_when_no_password_given(self):
        """Wenn kein Passwort übergeben: authenticate("") ist korrekt."""
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=False)
        _sec_fitz.open.return_value = mock_doc

        result = sec._unlock_pymupdf("input.pdf", "output.pdf", "")

        mock_doc.authenticate.assert_called_once_with("")

    def test_user_password_used_when_needs_pass_true(self):
        """Wenn needs_pass=True: authenticate() wird mit übergebenem Passwort aufgerufen."""
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=True, authenticate_returns=True)
        _sec_fitz.open.return_value = mock_doc

        result = sec._unlock_pymupdf("input.pdf", "output.pdf", "userpass")

        mock_doc.authenticate.assert_called_once_with("userpass")

    def test_wrong_password_returns_failure(self):
        sec = _make_security()
        mock_doc = self._mock_doc(is_encrypted=True, needs_pass=True, authenticate_returns=False)
        _sec_fitz.open.return_value = mock_doc

        result = sec._unlock_pymupdf("input.pdf", "output.pdf", "wrongpass")

        self.assertFalse(result.success)
        self.assertIn("Passwort", result.error)


if __name__ == "__main__":
    unittest.main()
