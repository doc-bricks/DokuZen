# -*- coding: utf-8 -*-
"""Unit-Tests für DokuZen Clipboard Spawner und Format-Exporte."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.clipboard.naming import slugify_filename, unique_path
from core.clipboard.structure import analyze_structure
from core.clipboard.manager import ClipboardManager, FORMATS
from plugins.spawner.clipboard_monitor import ClipboardSaver, ClipboardContent, ClipboardContentType


class TestClipboardNaming(unittest.TestCase):
    """Tests für Slug-Generierung und eindeutige Pfade."""

    def test_slugify_heading_with_umlauts(self):
        text = "Überschrift für ein tolles Dokument\nZweite Zeile."
        slug = slugify_filename(text, words=3)
        self.assertEqual(slug, "Ueberschrift_fuer_ein")

    def test_slugify_markdown_heading(self):
        text = "## Wichtiger Projektbericht: DokuZen\nDetails hier."
        slug = slugify_filename(text, words=2)
        self.assertEqual(slug, "Wichtiger_Projektbericht")

    def test_slugify_maxlen(self):
        text = "SehrLangerTitelDerSehrWeitUeberDieGrenzeHinausgehtUndDeshalbGekuerztWerdenMuss"
        slug = slugify_filename(text, words=1, maxlen=20)
        self.assertLessEqual(len(slug), 20)

    def test_slugify_fallback_on_empty(self):
        slug = slugify_filename("")
        self.assertTrue(slug.startswith("clipboard_"))

    def test_slugify_fallback_on_generic_word(self):
        slug = slugify_filename("Dokument")
        self.assertTrue(slug.startswith("clipboard_"))

    def test_unique_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "test_file"
            p1 = unique_path(base, "txt")
            self.assertEqual(p1.name, "test_file.txt")
            p1.touch()

            p2 = unique_path(base, "txt")
            self.assertEqual(p2.name, "test_file_1.txt")
            p2.touch()

            p3 = unique_path(base, "txt")
            self.assertEqual(p3.name, "test_file_2.txt")


class TestClipboardStructure(unittest.TestCase):
    """Tests für Überschriften- und Strukturanalyse."""

    def test_structure_detection(self):
        raw_text = """TITELZEILE IN GROSSBUCHSTABEN

Erster regulärer Absatz mit mehreren Wörtern.
Und zweiter Satz im selben Absatz.

Zweites Thema:
Hier kommt der Inhalt zum zweiten Thema."""
        struct = analyze_structure(raw_text)
        self.assertGreaterEqual(len(struct), 4)
        self.assertEqual(struct[0]["type"], "heading")
        self.assertEqual(struct[0]["text"], "TITELZEILE IN GROSSBUCHSTABEN")
        self.assertEqual(struct[1]["type"], "paragraph")
        self.assertIn("Erster regulärer Absatz", struct[1]["text"])
        self.assertEqual(struct[2]["type"], "heading")
        self.assertEqual(struct[2]["text"], "Zweites Thema")
        self.assertEqual(struct[3]["type"], "paragraph")

    def test_markdown_heading_levels(self):
        raw = "### Dritter Abschnitt\nText des Abschnitts."
        struct = analyze_structure(raw)
        self.assertEqual(len(struct), 2)
        self.assertEqual(struct[0]["type"], "heading")
        self.assertEqual(struct[0]["level"], 3)
        self.assertEqual(struct[0]["text"], "Dritter Abschnitt")


class TestClipboardManagerExports(unittest.TestCase):
    """Tests für Dateiexporte in allen 5 Formaten."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mgr = ClipboardManager(default_dir=self.tmpdir)
        self.sample_text = """PROJEKTBERICHT: DokuZen Spawner
Dies ist ein erster Testabsatz mit Umlauten ä, ö, ü und ß.

ABSCHNITT ZWEI:
Ein weiterer Absatz mit Sonderzeichen: € @ 100% & Co."""

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_txt(self):
        path = self.mgr.save_from_clipboard(fmt="TXT", custom_text=self.sample_text)
        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# PROJEKTBERICHT", content)
        self.assertIn("Testabsatz mit Umlauten", content)
        # Keine temporären Dateien verbleiben
        self.assertFalse(os.path.exists(path + ".tmp"))

    def test_save_md(self):
        path = self.mgr.save_from_clipboard(fmt="MD", custom_text=self.sample_text)
        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(content.startswith("# "))
        self.assertIn("---", content)
        self.assertIn("## ABSCHNITT ZWEI", content)

    def test_save_pdf(self):
        path = self.mgr.save_from_clipboard(fmt="PDF", custom_text=self.sample_text)
        self.assertTrue(os.path.exists(path))
        with open(path, "rb") as f:
            header = f.read(5)
        self.assertEqual(header, b"%PDF-")

    def test_save_docx(self):
        path = self.mgr.save_from_clipboard(fmt="DOCX", custom_text=self.sample_text)
        self.assertTrue(os.path.exists(path))
        from docx import Document
        doc = Document(path)
        self.assertGreater(len(doc.paragraphs), 0)

    def test_save_rtf_and_unicode_escapes(self):
        text_with_emoji = "Überschrift mit Rakete 🚀\nEurozeichen € und Umlaute: ÄÖÜäöü."
        path = self.mgr.save_from_clipboard(fmt="RTF", custom_text=text_with_emoji)
        self.assertTrue(os.path.exists(path))
        with open(path, "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"{\\rtf1\\ansi\\deff0"))
        # Unicode Escapes vorhanden
        self.assertIn(b"\\u8364?", raw)  # Eurozeichen
        self.assertIn(b"\\u-10179?", raw)  # Raketen-Surrogat

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.save_from_clipboard(fmt="XYZ", custom_text=self.sample_text)

    def test_empty_text_raises(self):
        with self.assertRaises(RuntimeError):
            self.mgr.save_from_clipboard(fmt="TXT", custom_text="   ")


class TestClipboardSaverIntegration(unittest.TestCase):
    """Tests für die erweiterte ClipboardSaver-Klasse in plugins.spawner."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.saver = ClipboardSaver(default_folder=self.tmpdir)
        self.content = ClipboardContent(
            content_type=ClipboardContentType.TEXT,
            text="BESPRECHUNGSNOTIZ: Neues Release\nWir planen das nächste Update.",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_content_all_formats(self):
        for fmt in ["txt", "md", "pdf", "docx", "rtf"]:
            out = self.saver.save_content(self.content, format=fmt)
            self.assertIsNotNone(out)
            self.assertTrue(os.path.exists(out))
            self.assertIn("BESPRECHUNGSNOTIZ_Neues_Release", os.path.basename(out))

    def test_save_as_text_with_explicit_filename(self):
        out = self.saver.save_as_text(self.content, filename="custom_note.txt")
        self.assertIsNotNone(out)
        self.assertTrue(os.path.exists(out))
        self.assertEqual(os.path.basename(out), "custom_note.txt")


if __name__ == "__main__":
    unittest.main()
