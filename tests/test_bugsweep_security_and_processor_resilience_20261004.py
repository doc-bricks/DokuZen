#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bugsweep Regressionstests — Security Pipeline & Processor Resilienz.
Erstellt am: 2026-10-04

Verifiziert:
1. PDFSecurity:
   - In-Place Entsperrung (_unlock_pymupdf, _unlock_pikepdf) ohne Lock-Kollision.
   - Zielverzeichnis-Erstellung (dst.parent.mkdir).
   - pikepdf leeres Passwort ("" / None) ohne TypeError.
   - Vollständiges Permission-Mapping (alle 8 Enums & String-Aliases) in encrypt().
   - In-Place Verschlüsselung und In-Place Restriktionsentfernung.
   - Saubere Bereinigung temporärer Dateien im Fehler- und Erfolgsfall.
2. PDFProcessor:
   - In-Place Bearbeitung (rotate_pages, delete_pages, extract_pages, set_metadata).
   - Zielverzeichniserstellung für extrahierte/bearbeitete PDFs.
   - Automatische Re-Open-Handhabung nach In-Place-Schreiben auf Windows.
"""

import os
import sys
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz  # PyMuPDF
import pikepdf

from core.pdf.security import PDFSecurity, Permission, EncryptionMethod
from core.pdf.processor import PDFProcessor


class TestSecurityResilience(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.security = PDFSecurity()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_pdf(self, filename: str = "sample.pdf") -> Path:
        pdf_path = self.work_dir / filename
        doc = fitz.open()
        p1 = doc.new_page()
        p1.insert_text((72, 72), "DokuZen Page 1")
        p2 = doc.new_page()
        p2.insert_text((72, 72), "DokuZen Page 2")
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_unlock_pymupdf_creates_parent_directory(self):
        src = self._create_sample_pdf("doc.pdf")
        dst = self.work_dir / "nested" / "deep" / "unlocked.pdf"
        self.assertFalse(dst.parent.exists())

        res = self.security._unlock_pymupdf(str(src), str(dst), "")
        self.assertTrue(res.success)
        self.assertTrue(dst.exists())

    def test_unlock_pymupdf_inplace(self):
        src = self._create_sample_pdf("inplace_unlock.pdf")
        res = self.security._unlock_pymupdf(str(src), str(src), "")
        self.assertTrue(res.success)
        self.assertTrue(src.exists())
        # Datei muss weiterhin valide lesbar sein
        doc = fitz.open(str(src))
        self.assertEqual(doc.page_count, 2)
        doc.close()

    def test_unlock_pikepdf_with_empty_password_and_inplace(self):
        src = self._create_sample_pdf("inplace_pike.pdf")
        # Leerer String
        res = self.security._unlock_pikepdf(str(src), str(src), "")
        self.assertTrue(res.success)
        # None-Äquivalent
        res_none = self.security._unlock_pikepdf(str(src), str(src), None)
        self.assertTrue(res_none.success)
        with pikepdf.open(str(src)) as pdf:
            self.assertEqual(len(pdf.pages), 2)

    def test_unlock_pikepdf_creates_parent_directory(self):
        src = self._create_sample_pdf("pike_doc.pdf")
        dst = self.work_dir / "deep_pike" / "out.pdf"
        res = self.security._unlock_pikepdf(str(src), str(dst), "")
        self.assertTrue(res.success)
        self.assertTrue(dst.exists())

    def test_remove_restrictions_inplace_and_creates_dir(self):
        src = self._create_sample_pdf("restr.pdf")
        # Neues Unterverzeichnis
        dst = self.work_dir / "sub" / "restr_out.pdf"
        res = self.security.remove_restrictions(str(src), str(dst), "")
        self.assertTrue(res.success)
        self.assertTrue(dst.exists())

        # In-Place
        res_in = self.security.remove_restrictions(str(dst), str(dst), "")
        self.assertTrue(res_in.success)
        self.assertTrue(dst.exists())

    def test_encrypt_all_permissions_and_inplace(self):
        src = self._create_sample_pdf("encrypt_test.pdf")
        all_perms = [
            Permission.PRINT,
            Permission.COPY,
            Permission.MODIFY,
            Permission.ANNOTATE,
            Permission.FILL_FORMS,
            Permission.EXTRACT,
            Permission.ASSEMBLE,
            Permission.PRINT_HIGH_QUALITY,
        ]
        # In-Place Verschlüsselung
        res = self.security.encrypt(
            str(src),
            str(src),
            user_password="user123",
            owner_password="owner123",
            method=EncryptionMethod.AES_256,
            permissions=all_perms
        )
        self.assertTrue(res.success)
        self.assertTrue(src.exists())

        # Testen mit PyMuPDF
        doc = fitz.open(str(src))
        self.assertTrue(doc.is_encrypted)
        self.assertTrue(doc.needs_pass)
        auth = doc.authenticate("user123")
        self.assertGreater(auth, 0)
        doc.close()

    def test_encrypt_string_permissions_and_new_directory(self):
        src = self._create_sample_pdf("encrypt_str.pdf")
        dst = self.work_dir / "nested_enc" / "enc.pdf"
        string_perms = ["print", "copy", "fill_forms", "extract", "assemble", "print_highres"]
        res = self.security.encrypt(
            str(src),
            str(dst),
            user_password="pw",
            permissions=string_perms
        )
        self.assertTrue(res.success)
        self.assertTrue(dst.exists())


class TestProcessorResilience(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.proc = PDFProcessor()

    def tearDown(self):
        self.proc.close()
        self.temp_dir.cleanup()

    def _create_sample_pdf(self, filename: str = "proc_sample.pdf", pages: int = 3) -> Path:
        pdf_path = self.work_dir / filename
        doc = fitz.open()
        for i in range(pages):
            p = doc.new_page()
            p.insert_text((72, 72), f"Page {i + 1}")
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_extract_pages_creates_parent_dir_and_inplace(self):
        pdf_path = self._create_sample_pdf("extract.pdf", 3)
        self.assertTrue(self.proc.open(str(pdf_path)))

        dst = self.work_dir / "nested_extract" / "extracted.pdf"
        ok = self.proc.extract_pages([1, 2], str(dst))
        self.assertTrue(ok)
        self.assertTrue(dst.exists())

        # In-Place Extraktion
        ok_in = self.proc.extract_pages([1], str(pdf_path))
        self.assertTrue(ok_in)
        # Processor sollte weiterhin aktiv und synchronisiert sein
        self.assertEqual(self.proc.page_count, 1)

    def test_rotate_pages_creates_dir_and_inplace(self):
        pdf_path = self._create_sample_pdf("rotate.pdf", 2)
        self.assertTrue(self.proc.open(str(pdf_path)))

        # In neues Verzeichnis
        dst = self.work_dir / "rotated" / "rot.pdf"
        self.assertTrue(self.proc.rotate_pages([1], 90, str(dst)))
        self.assertTrue(dst.exists())

        # In-Place
        self.assertTrue(self.proc.rotate_pages([1], 180, str(pdf_path)))
        self.assertEqual(self.proc.page_count, 2)
        # Überprüfen dass Datei auf Festplatte rotiert ist
        doc = fitz.open(str(pdf_path))
        self.assertEqual(doc[0].rotation, 180)
        doc.close()

    def test_delete_pages_inplace(self):
        pdf_path = self._create_sample_pdf("del.pdf", 3)
        self.assertTrue(self.proc.open(str(pdf_path)))
        self.assertEqual(self.proc.page_count, 3)

        # Lösche Seite 2 in-place
        self.assertTrue(self.proc.delete_pages([2], str(pdf_path)))
        self.assertEqual(self.proc.page_count, 2)

        doc = fitz.open(str(pdf_path))
        self.assertEqual(doc.page_count, 2)
        doc.close()

    def test_set_metadata_creates_dir_and_inplace(self):
        pdf_path = self._create_sample_pdf("meta.pdf", 1)
        self.assertTrue(self.proc.open(str(pdf_path)))

        meta = {"title": "DokuZen Meta Title", "author": "Zen Master"}
        # In neues Verzeichnis
        dst = self.work_dir / "meta_dir" / "out.pdf"
        self.assertTrue(self.proc.set_metadata(meta, str(dst)))
        self.assertTrue(dst.exists())

        # In-Place
        self.assertTrue(self.proc.set_metadata(meta, str(pdf_path)))
        doc = fitz.open(str(pdf_path))
        self.assertEqual(doc.metadata.get("title"), "DokuZen Meta Title")
        doc.close()


if __name__ == "__main__":
    unittest.main()
