import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.batch_cli import (
    BatchResult,
    batch_info,
    batch_merge,
    batch_ocr,
    batch_redact,
    execute_headless_cli,
)
from main import main, parse_cli_args


def _create_dummy_pdf(path: Path, text: str = "Testinhalt Seite 1") -> None:
    """Erstellt eine hermetische Test-PDF mit minimalem Text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    doc.save(str(path))
    doc.close()


class BatchCliTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_batch_merge_success(self):
        pdf1 = self.dir_path / "doc1.pdf"
        pdf2 = self.dir_path / "doc2.pdf"
        out_pdf = self.dir_path / "merged.pdf"

        _create_dummy_pdf(pdf1, "Erste PDF")
        _create_dummy_pdf(pdf2, "Zweite PDF")

        result = batch_merge([pdf1, pdf2], out_pdf)

        self.assertTrue(result.success)
        self.assertEqual(result.action, "merge")
        self.assertEqual(result.output_file, str(out_pdf.resolve()))
        self.assertEqual(result.details.get("page_count"), 2)
        self.assertTrue(out_pdf.exists())

        # Read back merged PDF
        doc = fitz.open(str(out_pdf))
        self.assertEqual(doc.page_count, 2)
        doc.close()

    def test_batch_merge_missing_inputs(self):
        result = batch_merge([self.dir_path / "nonexistent.pdf"], self.dir_path / "out.pdf")
        self.assertFalse(result.success)
        self.assertIn("nicht gefunden", result.error)

    def test_batch_merge_empty_inputs(self):
        result = batch_merge([], self.dir_path / "out.pdf")
        self.assertFalse(result.success)
        self.assertIn("Keine Eingabedateien", result.error)

    def test_batch_ocr_missing_file(self):
        result = batch_ocr(self.dir_path / "nonexistent.pdf")
        self.assertFalse(result.success)
        self.assertIn("nicht gefunden", result.error)

    def test_batch_ocr_mocked_success_text(self):
        pdf_path = self.dir_path / "scanned.pdf"
        out_txt = self.dir_path / "ocr_result.txt"
        _create_dummy_pdf(pdf_path, "Scan Inhalt")

        from core.ocr.engine import OCRPageResult

        mock_page_result = OCRPageResult(
            page_num=1,
            text="Erkannter Mustertext aus OCR",
            confidence=95.5,
            word_count=4,
        )

        with patch("core.ocr.engine.OCREngine._check_tesseract", return_value=True), \
             patch("core.ocr.engine.OCREngine.recognize_pdf", return_value=[mock_page_result]):
            result = batch_ocr(pdf_path, output_file=out_txt, language="deu")

            self.assertTrue(result.success)
            self.assertEqual(result.action, "ocr")
            self.assertEqual(result.details["page_count"], 1)
            self.assertEqual(result.details["total_words"], 4)
            self.assertIn("Erkannter Mustertext", result.details["text"])
            self.assertTrue(out_txt.exists())
            self.assertEqual(out_txt.read_text(encoding="utf-8").strip(), "Erkannter Mustertext aus OCR")

    def test_batch_ocr_pdf_format_requires_pdf(self):
        img_path = self.dir_path / "bild.png"
        img_path.write_bytes(b"dummy")

        with patch("core.ocr.engine.OCREngine._check_tesseract", return_value=True):
            result = batch_ocr(img_path, self.dir_path / "out.pdf", ocr_format="pdf")
            self.assertFalse(result.success)
            self.assertIn("erfordert eine PDF-Eingabedatei", result.error)

    def test_batch_redact_success(self):
        pdf_path = self.dir_path / "confidential.pdf"
        out_pdf = self.dir_path / "redacted.pdf"
        _create_dummy_pdf(pdf_path, "Vertraulicher Name: Hans Schmidt, Tel: 01701234567")

        result = batch_redact(
            input_file=pdf_path,
            output_file=out_pdf,
            terms=["Hans Schmidt"],
        )

        self.assertTrue(result.success)
        self.assertEqual(result.action, "redact")
        self.assertTrue(out_pdf.exists())
        self.assertGreaterEqual(result.details.get("total_matches", 0), 1)

    def test_batch_redact_missing_file(self):
        result = batch_redact(self.dir_path / "nonexistent.pdf", self.dir_path / "out.pdf")
        self.assertFalse(result.success)
        self.assertIn("nicht gefunden", result.error)

    def test_batch_redact_non_pdf(self):
        txt_path = self.dir_path / "datei.txt"
        txt_path.write_text("sensibel", encoding="utf-8")
        result = batch_redact(txt_path, self.dir_path / "out.pdf")
        self.assertFalse(result.success)
        self.assertIn("ausschließlich PDF-Dateien", result.error)

    def test_batch_info_success(self):
        pdf_path = self.dir_path / "sample.pdf"
        _create_dummy_pdf(pdf_path, "Metadaten-Test")

        result = batch_info(pdf_path)
        self.assertTrue(result.success)
        self.assertEqual(result.action, "info")
        self.assertEqual(result.details["page_count"], 1)
        self.assertFalse(result.details["is_encrypted"])
        self.assertEqual(result.details["file_name"], "sample.pdf")

    def test_batch_info_missing_file(self):
        result = batch_info(self.dir_path / "nonexistent.pdf")
        self.assertFalse(result.success)
        self.assertIn("nicht gefunden", result.error)

    def test_execute_headless_cli_merge_missing_output_returns_2(self):
        args = parse_cli_args(["--headless", "--merge", "a.pdf", "b.pdf"])
        buf_err = io.StringIO()
        with redirect_stderr(buf_err):
            code = execute_headless_cli(args)
        self.assertEqual(code, 2)
        self.assertIn("Ausgabedatei", buf_err.getvalue())

    def test_execute_headless_cli_json_output(self):
        pdf_path = self.dir_path / "sample.pdf"
        _create_dummy_pdf(pdf_path, "JSON Test")

        args = parse_cli_args(["--headless", "--info", str(pdf_path), "--json"])
        buf_out = io.StringIO()
        with redirect_stdout(buf_out):
            code = execute_headless_cli(args)

        self.assertEqual(code, 0)
        data = json.loads(buf_out.getvalue())
        self.assertTrue(data["success"])
        self.assertEqual(data["action"], "info")
        self.assertEqual(data["details"]["page_count"], 1)

    def test_execute_headless_cli_no_action_returns_2(self):
        args = parse_cli_args(["--headless"])
        buf_err = io.StringIO()
        with redirect_stderr(buf_err):
            code = execute_headless_cli(args)
        self.assertEqual(code, 2)
        self.assertIn("Keine gültige Headless-Aktion", buf_err.getvalue())

    def test_main_headless_integration(self):
        pdf_path = self.dir_path / "main_test.pdf"
        _create_dummy_pdf(pdf_path, "Main Integration Test")

        buf_out = io.StringIO()
        with redirect_stdout(buf_out):
            exit_code = main(["--headless", "--info", str(pdf_path), "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(buf_out.getvalue())
        self.assertTrue(payload["success"])
        self.assertEqual(payload["details"]["page_count"], 1)


if __name__ == "__main__":
    unittest.main()
