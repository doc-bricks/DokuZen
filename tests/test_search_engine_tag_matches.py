#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für SearchEngine._add_tag_matches — Freitext-Tag-Suche-Fix.

Bugfix: _add_tag_matches wurde bei SearchField.ALL + query.text aufgerufen,
        aber der elif-Zweig für Freitext-Tag-Suche fehlte komplett.
        Damit wurden Tags bei normaler Freitext-Suche nie einbezogen.
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Stubs ---
for _mod in ("fitz", "pikepdf", "PIL", "PIL.Image", "docx", "openpyxl",
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

# file_index stub
if "core.knowledge.file_index" not in sys.modules:
    _fi_stub = types.ModuleType("core.knowledge.file_index")
    _fi_stub.FileIndex = object
    _fi_stub.FileMetadata = MagicMock
    from enum import Enum
    class _FileCategory(Enum):
        DOCUMENT = "document"
        IMAGE = "image"
        OTHER = "other"
    _fi_stub.FileCategory = _FileCategory
    sys.modules["core.knowledge.file_index"] = _fi_stub
    sys.modules["core.knowledge"] = types.ModuleType("core.knowledge")

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "core.knowledge.search_engine",
    PROJECT_ROOT / "core" / "knowledge" / "search_engine.py"
)
_se_mod = _ilu.module_from_spec(_spec)
sys.modules["core.knowledge.search_engine"] = _se_mod
_spec.loader.exec_module(_se_mod)

# Stub aus sys.modules entfernen — SearchEngine hat seine Referenzen bereits
# gebunden. Ohne Cleanup würde test_file_index_doc_close.py den Stub erhalten
# und FileIndex = object vorfinden, was dort einen AttributeError auslöst.
sys.modules.pop("core.knowledge.file_index", None)
sys.modules.pop("core.knowledge", None)

SearchEngine = _se_mod.SearchEngine
SearchQuery = _se_mod.SearchQuery
SearchResult = _se_mod.SearchResult
SearchField = _se_mod.SearchField


def _row_to_metadata(row):
    """Konvertiert einen Mock-Row in ein Mock-FileMetadata-Objekt."""
    m = MagicMock()
    m.path = row["path"]
    m.name = row.get("name", "file.pdf")
    m.tags = []
    m.pdf_title = None
    m.pdf_author = None
    return m


def _make_engine_with_mock_conn(tag_rows=None, file_rows=None):
    """Erstellt eine SearchEngine mit einem gemockten DB-Conn."""
    engine = SearchEngine.__new__(SearchEngine)
    engine._logger = MagicMock()

    mock_index = MagicMock()
    mock_index._row_to_metadata.side_effect = _row_to_metadata

    # Standard-Datei-Rows (für Haupt-Query leer)
    file_cursor = MagicMock()
    file_cursor.fetchall.return_value = file_rows or []

    # Tag-Rows
    tag_cursor = MagicMock()
    tag_cursor.fetchall.return_value = tag_rows or []

    call_count = [0]

    def fake_execute(sql, params=None):
        call_count[0] += 1
        if "tags" in sql.lower() and "join" in sql.lower():
            return tag_cursor
        return file_cursor

    mock_index._conn.execute.side_effect = fake_execute
    engine._index = mock_index
    return engine


class TestAddTagMatchesFreitext(unittest.TestCase):

    def _make_tag_row(self, path, name="file.pdf"):
        row = {"path": path, "name": name}
        return row

    def test_freitext_tag_match_returns_results_for_all_field(self):
        """Kerntest: Bei SearchField.ALL + query.text werden Tag-Treffer gefunden."""
        tag_rows = [self._make_tag_row("/docs/report.pdf")]
        engine = _make_engine_with_mock_conn(tag_rows=tag_rows)

        query = SearchQuery(text="report", fields=[SearchField.ALL])
        results = engine._add_tag_matches([], query)

        self.assertEqual(len(results), 1, "Tag-Treffer muss bei ALL+text gefunden werden")
        self.assertIn("tags", results[0].match_fields)

    def test_freitext_tag_match_not_triggered_without_all_field(self):
        """Ohne SearchField.ALL werden keine Tag-Freitext-Treffer geliefert."""
        tag_rows = [self._make_tag_row("/docs/report.pdf")]
        engine = _make_engine_with_mock_conn(tag_rows=tag_rows)

        query = SearchQuery(text="report", fields=[SearchField.NAME])
        results = engine._add_tag_matches([], query)

        self.assertEqual(len(results), 0,
                         "Ohne ALL-Feld darf kein Freitext-Tag-Treffer erscheinen")

    def test_specific_tag_filter_still_works(self):
        """query.tags=[...] funktioniert weiterhin korrekt."""
        tag_rows = [self._make_tag_row("/docs/classified.pdf")]
        engine = _make_engine_with_mock_conn(tag_rows=tag_rows)

        query = SearchQuery(text="", tags=["confidential"], fields=[SearchField.ALL])
        results = engine._add_tag_matches([], query)

        self.assertEqual(len(results), 1)

    def test_already_found_paths_not_duplicated(self):
        """Bereits gefundene Pfade werden nicht doppelt hinzugefügt."""
        existing_meta = MagicMock()
        existing_meta.path = "/docs/report.pdf"
        existing_result = SearchResult(metadata=existing_meta, score=0.8, match_fields=["name"])

        tag_rows = [self._make_tag_row("/docs/report.pdf")]
        engine = _make_engine_with_mock_conn(tag_rows=tag_rows)

        query = SearchQuery(text="report", fields=[SearchField.ALL])
        results = engine._add_tag_matches([existing_result], query)

        self.assertEqual(len(results), 1, "Bereits gefundener Pfad darf nicht dupliziert werden")

    def test_empty_text_no_tag_search(self):
        """Wenn text leer: kein Freitext-Tag-Matching."""
        tag_rows = [self._make_tag_row("/docs/report.pdf")]
        engine = _make_engine_with_mock_conn(tag_rows=tag_rows)

        query = SearchQuery(text="", fields=[SearchField.ALL])
        results = engine._add_tag_matches([], query)

        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
