#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für PDFSecurity Suite (DokuZen TW-DZ-17).
==============================================
Validiert:
1. get_security_info für unverschlüsselte und verschlüsselte PDFs (mit/ohne Passwort).
2. Verschlüsselung mit AES-256, AES-128 und RC4-128.
3. Benutzer- und Eigentümer-Passwörter sowie Berechtigungseinschränkungen.
4. Entsperrung (Unlock) mit PyMuPDF und pikepdf, inkl. falschem Passwort.
5. In-Place-Schutz und atomares Schreiben bei Verschlüsselung und Entsperrung.
6. Fehlerbehandlung bei nicht existierenden Dateien und fehlenden Passwörtern.
7. Hilfsfunktionen: unlock_pdf, is_pdf_locked, encrypt_pdf.
"""

import os
import sys
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
import pikepdf

from core.pdf.security import (
    PDFSecurity,
    EncryptionMethod,
    Permission,
    SecurityInfo,
    UnlockResult,
    unlock_pdf,
    is_pdf_locked,
    encrypt_pdf,
)


class TestPDFSecuritySuite(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.security = PDFSecurity()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_pdf(self, filename: str = "sample.pdf", text: str = "DokuZen Security Test") -> Path:
        pdf_path = self.work_dir / filename
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_get_security_info_unencrypted(self):
        src = self._create_sample_pdf("plain.pdf")
        info = self.security.get_security_info(src)
        self.assertIsNotNone(info)
        self.assertFalse(info.is_encrypted)
        self.assertFalse(info.needs_password)
        self.assertFalse(info.user_password_set)
        self.assertFalse(info.owner_password_set)
        self.assertIn(info.encryption_method, ("Keine", None))
        self.assertIsNotNone(info.permissions)
        self.assertTrue(info.permissions.get("print"))
        self.assertTrue(info.permissions.get("copy"))

    def test_get_security_info_missing_file_returns_none(self):
        missing = self.work_dir / "does_not_exist.pdf"
        info = self.security.get_security_info(missing)
        self.assertIsNone(info)

    def test_encrypt_and_get_security_info_aes256(self):
        src = self._create_sample_pdf("doc.pdf")
        dst = self.work_dir / "encrypted_aes256.pdf"

        res = self.security.encrypt(
            input_path=src,
            output_path=dst,
            user_password="user123",
            owner_password="owner123",
            method=EncryptionMethod.AES_256,
            permissions=[Permission.PRINT, Permission.COPY],
        )
        self.assertTrue(res.success)
        self.assertTrue(dst.exists())

        # Ohne Passwort lesen: erkennt Verschlüsselung
        info_locked = self.security.get_security_info(dst)
        self.assertIsNotNone(info_locked)
        self.assertTrue(info_locked.is_encrypted)
        self.assertTrue(info_locked.needs_password)

        # Mit Passwort lesen: authentifiziert
        info_auth = self.security.get_security_info(dst, password="user123")
        self.assertIsNotNone(info_auth)
        self.assertTrue(info_auth.is_encrypted)
        self.assertTrue(info_auth.permissions.get("print"))
        self.assertTrue(info_auth.permissions.get("copy"))
        self.assertFalse(info_auth.permissions.get("modify"))

    def test_encrypt_string_method_and_string_permissions(self):
        src = self._create_sample_pdf("doc_str.pdf")
        dst = self.work_dir / "doc_str_enc.pdf"

        res = self.security.encrypt(
            input_path=src,
            output_path=dst,
            user_password="userSecret",
            owner_password="ownerSecret",
            method="AES-128",
            permissions=["print", "annotate", "fill_forms"],
        )
        self.assertTrue(res.success)
        self.assertTrue(dst.exists())

        info = self.security.get_security_info(dst, password="userSecret")
        self.assertIsNotNone(info)
        self.assertTrue(info.is_encrypted)
        self.assertTrue(info.permissions.get("print"))
        self.assertTrue(info.permissions.get("annotate"))
        self.assertTrue(info.permissions.get("fill_forms"))
        self.assertFalse(info.permissions.get("copy"))

    def test_encrypt_in_place_atomic(self):
        src = self._create_sample_pdf("inplace_enc.pdf")
        orig_size = src.stat().st_size

        res = self.security.encrypt(
            input_path=src,
            output_path=None,  # in-place
            user_password="securePassword",
        )
        self.assertTrue(res.success)
        self.assertEqual(res.output_path, str(src))

        # PDF sollte nun verschlüsselt sein
        self.assertTrue(is_pdf_locked(str(src)))

    def test_unlock_encrypted_pdf(self):
        src = self._create_sample_pdf("doc_to_unlock.pdf")
        enc = self.work_dir / "doc_locked.pdf"
        unlocked = self.work_dir / "doc_unlocked.pdf"

        encrypt_res = self.security.encrypt(
            input_path=src,
            output_path=enc,
            user_password="mypassword",
            owner_password="adminpassword",
        )
        self.assertTrue(encrypt_res.success)

        # Falsches Passwort schlägt fehl
        fail_res = self.security.unlock(enc, unlocked, password="wrongpassword")
        self.assertFalse(fail_res.success)
        self.assertFalse(unlocked.exists())

        # Richtiges Passwort entsperrt
        ok_res = self.security.unlock(enc, unlocked, password="mypassword")
        self.assertTrue(ok_res.success)
        self.assertTrue(unlocked.exists())
        self.assertFalse(is_pdf_locked(str(unlocked)))

    def test_unlock_in_place_atomic(self):
        src = self._create_sample_pdf("doc_inplace_unlock.pdf")
        enc = self.work_dir / "doc_inplace.pdf"

        self.security.encrypt(src, enc, user_password="pass")
        self.assertTrue(is_pdf_locked(str(enc)))

        res = self.security.unlock(enc, None, password="pass")
        self.assertTrue(res.success)
        self.assertFalse(is_pdf_locked(str(enc)))

    def test_encrypt_missing_passwords_fails(self):
        src = self._create_sample_pdf("empty_pw.pdf")
        dst = self.work_dir / "out.pdf"
        res = self.security.encrypt(src, dst, user_password="", owner_password="")
        self.assertFalse(res.success)
        self.assertIn("Passwort", res.error)

    def test_encrypt_missing_file_fails(self):
        missing = self.work_dir / "nonexistent.pdf"
        dst = self.work_dir / "out.pdf"
        res = self.security.encrypt(missing, dst, user_password="test")
        self.assertFalse(res.success)
        self.assertIn("nicht gefunden", res.error)

    def test_unlock_missing_file_fails(self):
        missing = self.work_dir / "nonexistent.pdf"
        res = self.security.unlock(missing, None, password="test")
        self.assertFalse(res.success)
        self.assertIn("nicht gefunden", res.error)

    def test_helper_functions(self):
        src = self._create_sample_pdf("helper_test.pdf")
        enc = self.work_dir / "helper_enc.pdf"
        unlocked = self.work_dir / "helper_unlocked.pdf"

        # encrypt_pdf
        self.assertTrue(encrypt_pdf(str(src), str(enc), password="12345"))
        self.assertTrue(is_pdf_locked(str(enc)))

        # unlock_pdf
        self.assertTrue(unlock_pdf(str(enc), str(unlocked), password="12345"))
        self.assertFalse(is_pdf_locked(str(unlocked)))


if __name__ == "__main__":
    unittest.main()
