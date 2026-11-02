#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für Headless Batch CLI Security-Funktionen (DokuZen TW-DZ-17).
===================================================================
Validiert:
1. batch_security_info auf ungeschützten und geschützten PDFs.
2. batch_encrypt (Headless-Verschlüsselung, In-Place und neue Datei).
3. batch_unlock (Headless-Entsperrung mit Passwort).
4. execute_headless_cli für --security-info, --security/--encrypt, --unlock/--decrypt.
5. Exit-Codes und JSON-Ausgabe (--json).
"""

import argparse
import io
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz

from core.batch_cli import (
    batch_security_info,
    batch_encrypt,
    batch_unlock,
    execute_headless_cli,
    BatchResult,
)


class TestBatchCLISecurity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_pdf(self, filename: str = "batch_sample.pdf") -> Path:
        pdf_path = self.work_dir / filename
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "DokuZen Batch CLI Security Test")
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_batch_security_info_plain(self):
        src = self._create_sample_pdf("plain.pdf")
        res = batch_security_info(src)
        self.assertTrue(res.success)
        self.assertEqual(res.action, "security_info")
        self.assertFalse(res.details.get("is_encrypted"))
        self.assertFalse(res.details.get("needs_password"))

    def test_batch_security_info_missing_file(self):
        missing = self.work_dir / "not_there.pdf"
        res = batch_security_info(missing)
        self.assertFalse(res.success)
        self.assertIn("nicht gefunden", res.error)

    def test_batch_encrypt_and_unlock_roundtrip(self):
        src = self._create_sample_pdf("roundtrip.pdf")
        dst = self.work_dir / "roundtrip_enc.pdf"
        unlocked = self.work_dir / "roundtrip_unlocked.pdf"

        # Encrypt
        enc_res = batch_encrypt(
            input_file=src,
            output_file=dst,
            user_password="cliPassword",
            owner_password="cliOwner",
            method="AES-256",
            permissions=["print", "copy"],
        )
        self.assertTrue(enc_res.success)
        self.assertEqual(enc_res.action, "encrypt")
        self.assertTrue(dst.exists())

        # Inspect encrypted
        info_res = batch_security_info(dst)
        self.assertTrue(info_res.success)
        self.assertTrue(info_res.details.get("is_encrypted"))
        self.assertTrue(info_res.details.get("needs_password"))

        # Unlock
        unlock_res = batch_unlock(
            input_file=dst,
            output_file=unlocked,
            password="cliPassword",
        )
        self.assertTrue(unlock_res.success)
        self.assertEqual(unlock_res.action, "unlock")
        self.assertTrue(unlocked.exists())

        # Inspect unlocked
        info_unlocked = batch_security_info(unlocked)
        self.assertTrue(info_unlocked.success)
        self.assertFalse(info_unlocked.details.get("is_encrypted"))

    def test_batch_encrypt_inplace(self):
        src = self._create_sample_pdf("inplace.pdf")
        res = batch_encrypt(
            input_file=src,
            output_file=None,  # in-place
            user_password="userSecret",
        )
        self.assertTrue(res.success)
        self.assertTrue(res.details.get("in_place"))

        info = batch_security_info(src)
        self.assertTrue(info.details.get("is_encrypted"))

    def test_execute_headless_cli_security_info_json(self):
        src = self._create_sample_pdf("cli_info.pdf")
        args = argparse.Namespace(
            security_info_path=str(src),
            password="",
            user_password="",
            json_output=True,
        )

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            code = execute_headless_cli(args)

        self.assertEqual(code, 0)
        data = json.loads(captured.getvalue())
        self.assertTrue(data["success"])
        self.assertEqual(data["action"], "security_info")
        self.assertFalse(data["details"]["is_encrypted"])

    def test_execute_headless_cli_encrypt_and_unlock(self):
        src = self._create_sample_pdf("cli_action.pdf")
        enc = self.work_dir / "cli_enc.pdf"

        # 1. Encrypt via execute_headless_cli
        args_enc = argparse.Namespace(
            security_path=str(src),
            encrypt_path=None,
            output_path=str(enc),
            user_password="encPassword",
            owner_password="",
            password="",
            encryption_method="AES-256",
            permissions=["print"],
            json_output=True,
        )

        captured_enc = io.StringIO()
        with patch("sys.stdout", captured_enc):
            code_enc = execute_headless_cli(args_enc)

        self.assertEqual(code_enc, 0)
        data_enc = json.loads(captured_enc.getvalue())
        self.assertTrue(data_enc["success"])
        self.assertTrue(enc.exists())

        # 2. Unlock via execute_headless_cli
        unlocked = self.work_dir / "cli_unlocked.pdf"
        args_unlock = argparse.Namespace(
            unlock_path=str(enc),
            decrypt_path=None,
            output_path=str(unlocked),
            password="encPassword",
            user_password="",
            owner_password="",
            json_output=True,
        )

        captured_unlock = io.StringIO()
        with patch("sys.stdout", captured_unlock):
            code_unlock = execute_headless_cli(args_unlock)

        self.assertEqual(code_unlock, 0)
        data_unlock = json.loads(captured_unlock.getvalue())
        self.assertTrue(data_unlock["success"])
        self.assertTrue(unlocked.exists())


if __name__ == "__main__":
    unittest.main()
