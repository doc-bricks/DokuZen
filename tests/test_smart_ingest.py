#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Test Suite: Smart Ingest Core
======================================
Tests für FormatDetector, FolderScanner und SmartIngestService.
"""

import os
import tempfile
import unittest
from pathlib import Path

from core.ingest.models import (
    FileType,
    IngestAction,
    IngestCandidate,
    IngestResult,
    IngestSummary,
)
from core.ingest.detector import FormatDetector
from core.ingest.scanner import FolderScanner
from core.ingest.service import SmartIngestService
from core.library.manager import LibraryManager


class TestFormatDetector(unittest.TestCase):
    """Tests für die Formaterkennung und Magic-Byte-Prüfung."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.detector = FormatDetector()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detect_pdf_by_extension_and_magic(self):
        pdf_file = self.root / "sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%test\n")
        
        file_type = self.detector.detect_file_type(pdf_file)
        self.assertEqual(file_type, FileType.PDF)
        # PDF ist bereits ein PDF, muss nicht konvertiert werden
        self.assertFalse(self.detector.is_convertible_to_pdf(pdf_file))

    def test_detect_pdf_renamed_extension_magic_fallback(self):
        # Datei heißt .dat, hat aber PDF-Magic-Bytes
        pdf_dat = self.root / "sample.dat"
        pdf_dat.write_bytes(b"%PDF-1.7\nsomething")
        
        file_type = self.detector.detect_file_type(pdf_dat)
        self.assertEqual(file_type, FileType.PDF)

    def test_detect_image_png_jpg(self):
        png_file = self.root / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
        self.assertEqual(self.detector.detect_file_type(png_file), FileType.IMAGE)
        self.assertTrue(self.detector.is_convertible_to_pdf(png_file))

        jpg_file = self.root / "photo.jpg"
        jpg_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")
        self.assertEqual(self.detector.detect_file_type(jpg_file), FileType.IMAGE)
        self.assertTrue(self.detector.is_convertible_to_pdf(jpg_file))

    def test_detect_office_docx_xlsx(self):
        docx_file = self.root / "doc.docx"
        docx_file.write_bytes(b"PK\x03\x04test_docx")
        self.assertEqual(self.detector.detect_file_type(docx_file), FileType.OFFICE)
        self.assertTrue(self.detector.is_convertible_to_pdf(docx_file))

        xlsx_file = self.root / "sheet.xlsx"
        xlsx_file.write_bytes(b"PK\x03\x04test_xlsx")
        self.assertEqual(self.detector.detect_file_type(xlsx_file), FileType.SPREADSHEET)

    def test_detect_text_markdown_html_code(self):
        txt_file = self.root / "note.txt"
        txt_file.write_text("Hello DokuZen", encoding="utf-8")
        self.assertEqual(self.detector.detect_file_type(txt_file), FileType.TEXT_MARKDOWN)
        self.assertTrue(self.detector.is_convertible_to_pdf(txt_file))

        md_file = self.root / "README.md"
        md_file.write_text("# Title\nBody", encoding="utf-8")
        self.assertEqual(self.detector.detect_file_type(md_file), FileType.TEXT_MARKDOWN)
        self.assertTrue(self.detector.is_convertible_to_pdf(md_file))

        html_file = self.root / "page.html"
        html_file.write_text("<!DOCTYPE html><html><body>Test</body></html>", encoding="utf-8")
        self.assertEqual(self.detector.detect_file_type(html_file), FileType.WEB_HTML)
        self.assertTrue(self.detector.is_convertible_to_pdf(html_file))

        py_file = self.root / "script.py"
        py_file.write_text("print('hello')", encoding="utf-8")
        self.assertEqual(self.detector.detect_file_type(py_file), FileType.CODE)

    def test_detect_unsupported_file(self):
        bin_file = self.root / "archive.iso"
        bin_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
        self.assertEqual(self.detector.detect_file_type(bin_file), FileType.UNSUPPORTED)
        self.assertFalse(self.detector.is_convertible_to_pdf(bin_file))

    def test_duplicate_detection(self):
        f1 = self.root / "file1.pdf"
        f1.write_bytes(b"%PDF-1.4 duplicate content")
        f2 = self.root / "file2.pdf"
        f2.write_bytes(b"%PDF-1.4 duplicate content")

        detector = FormatDetector()
        h1 = detector.compute_hash(f1)
        detector.register_existing_hash(h1)

        is_dup, existing = detector.is_duplicate(f2)
        self.assertTrue(is_dup)
        self.assertIsNotNone(existing)


class TestFolderScanner(unittest.TestCase):
    """Tests für das rekursive Scannen und Filtern von Verzeichnissen."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.scanner = FolderScanner()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_folder_recursive_and_depth(self):
        sub1 = self.root / "sub1"
        sub2 = sub1 / "sub2"
        sub2.mkdir(parents=True)

        (self.root / "root.pdf").write_bytes(b"%PDF-root")
        (sub1 / "level1.docx").write_text("docx", encoding="utf-8")
        (sub2 / "level2.txt").write_text("txt", encoding="utf-8")

        # Recursive full scan
        found_all = self.scanner.scan(self.root, recursive=True)
        names = {Path(p).name for p in found_all}
        self.assertIn("root.pdf", names)
        self.assertIn("level1.docx", names)
        self.assertIn("level2.txt", names)

        # Non-recursive
        found_shallow = self.scanner.scan(self.root, recursive=False)
        self.assertEqual(len(found_shallow), 1)
        self.assertEqual(Path(found_shallow[0]).name, "root.pdf")

        # Depth limited (max_depth=1: root and immediate children)
        found_depth1 = self.scanner.scan(self.root, recursive=True, max_depth=1)
        names_d1 = {Path(p).name for p in found_depth1}
        self.assertIn("root.pdf", names_d1)
        self.assertIn("level1.docx", names_d1)
        self.assertNotIn("level2.txt", names_d1)

    def test_scan_filters_ignored_folders_and_temp_files(self):
        git_dir = self.root / ".git"
        git_dir.mkdir()
        (git_dir / "commit.pdf").write_bytes(b"%PDF-git")

        pycache_dir = self.root / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "cache.pdf").write_bytes(b"%PDF-cache")

        node_dir = self.root / "node_modules"
        node_dir.mkdir()
        (node_dir / "pkg.pdf").write_bytes(b"%PDF-node")

        (self.root / "~$temp_office.docx").write_bytes(b"temp")
        (self.root / "corrupt.tmp").write_bytes(b"tmp")
        (self.root / "Thumbs.db").write_bytes(b"thumb")
        (self.root / "valid.pdf").write_bytes(b"%PDF-valid")

        found = self.scanner.scan(self.root, recursive=True)
        names = {Path(p).name for p in found}

        self.assertIn("valid.pdf", names)
        self.assertNotIn("commit.pdf", names)
        self.assertNotIn("cache.pdf", names)
        self.assertNotIn("pkg.pdf", names)
        self.assertNotIn("~$temp_office.docx", names)
        self.assertNotIn("corrupt.tmp", names)
        self.assertNotIn("Thumbs.db", names)


class TestSmartIngestService(unittest.TestCase):
    """Tests für die Orchestrierung via SmartIngestService."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.state_file = self.root / "state.json"

        self.library = LibraryManager(state_file=str(self.state_file))
        self.service = SmartIngestService(self.library)

    def tearDown(self):
        self.library.shutdown()
        self.temp_dir.cleanup()

    def test_prepare_candidates_from_files_and_folders(self):
        sub = self.root / "incoming_folder"
        sub.mkdir()

        f1 = self.root / "doc1.pdf"
        f1.write_bytes(b"%PDF-1.5 test")
        f2 = sub / "doc2.txt"
        f2.write_text("Simple text file", encoding="utf-8")

        candidates = self.service.prepare_candidates([str(f1), str(sub)], recursive=True)
        names = {c.name for c in candidates}
        self.assertIn("doc1.pdf", names)
        self.assertIn("doc2.txt", names)

        # Action for pdf should be ADD_DIRECT
        cand_pdf = next(c for c in candidates if c.name == "doc1.pdf")
        self.assertEqual(cand_pdf.selected_action, IngestAction.ADD_DIRECT)

        # Action for txt should be CONVERT_TO_PDF when auto_convert is True
        cand_txt = next(c for c in candidates if c.name == "doc2.txt")
        self.assertEqual(cand_txt.selected_action, IngestAction.CONVERT_TO_PDF)

    def test_ingest_batch_add_and_convert(self):
        # 1. PDF
        pdf_file = self.root / "sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 minimal test")

        # 2. Text-Datei zur Konvertierung
        txt_file = self.root / "notes.txt"
        txt_file.write_text("Notes content for conversion to pdf", encoding="utf-8")

        candidates = self.service.prepare_candidates([str(pdf_file), str(txt_file)])
        
        progress_calls = []
        def on_progress(idx, total, cand, res):
            progress_calls.append((idx, total, cand.name, res.success))

        summary = self.service.ingest_batch(
            candidates,
            theme="Allgemein",
            progress_callback=on_progress
        )

        self.assertEqual(summary.total_count, 2)
        self.assertEqual(summary.added_count, 1)
        self.assertEqual(summary.converted_count, 1)
        self.assertEqual(summary.failed_count, 0)
        self.assertEqual(summary.success_rate, 100.0)
        self.assertEqual(len(progress_calls), 2)

        # Verify docs in library
        docs = self.library.get_documents()
        self.assertEqual(len(docs), 2)

    def test_ingest_batch_skip_duplicate(self):
        pdf_file = self.root / "doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 sample content")

        # Erstes Mal importieren
        c1 = self.service.prepare_candidates([str(pdf_file)])
        self.service.ingest_batch(c1)

        # Zweites Mal vorbereiten mit neuem Service (initialisiert mit vorhandener Library)
        service2 = SmartIngestService(self.library)
        c2 = service2.prepare_candidates([str(pdf_file)])
        self.assertTrue(c2[0].is_duplicate)
        self.assertEqual(c2[0].selected_action, IngestAction.SKIP_DUPLICATE)

        summary2 = service2.ingest_batch(c2)
        self.assertEqual(summary2.skipped_count, 1)
        self.assertEqual(summary2.added_count, 0)


if __name__ == "__main__":
    unittest.main()
