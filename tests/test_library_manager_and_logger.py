#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für core/library/manager.py, core/library/themes.py und utils/logger.py."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.library.manager import Document, FilterMode, LibraryManager, SortMode
from utils.logger import LoggerMixin, get_logger


def test_document_from_dict_corrupt_dates_and_missing_file(tmp_path: Path):
    doc = Document.from_dict(
        {
            "path": str(tmp_path / "not_there.pdf"),
            "added": "not-an-iso-date",
            "is_read": True,
            "read_date": 12345,
            "tags": ["vertrag"],
            "notes": "Notiz",
        }
    )
    assert doc.added == datetime.min
    assert doc.read_date is None
    assert doc.exists is False
    assert doc.size == 0
    assert doc.size_human == "0.0 B"
    assert doc.name == "not_there.pdf"
    assert doc.extension == ".pdf"


def test_library_manager_crud_filter_search_sort_and_stats(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = LibraryManager(state_file=state_file)
    assert mgr.initialize() is True

    f_alpha = tmp_path / "alpha.txt"
    f_beta = tmp_path / "beta.md"
    f_bad = tmp_path / "program.exe"
    f_alpha.write_text("a" * 200, encoding="utf-8")
    f_beta.write_text("b" * 10, encoding="utf-8")
    f_bad.write_text("bin", encoding="utf-8")

    events = []
    mgr.add_change_callback(lambda ev, *args: events.append(ev))
    # Fehlerhafter Callback darf Manager nicht abstürzen lassen
    mgr.add_change_callback(lambda ev, *args: (_ for _ in ()).throw(RuntimeError("boom")))

    ok, fail = mgr.add_documents([str(f_alpha), str(f_beta), str(f_bad)])
    assert (ok, fail) == (2, 1)
    assert "document_added" in events

    assert mgr.set_read_status(str(f_alpha.resolve()), True) is True
    assert mgr.toggle_read_status(str(f_beta.resolve())) is True
    assert mgr.toggle_read_status(str(f_beta.resolve())) is True  # wieder ungelesen

    mgr.set_filter(FilterMode.READ)
    assert [d.name for d in mgr.get_documents()] == ["alpha.txt"]

    mgr.set_filter(FilterMode.UNREAD)
    assert [d.name for d in mgr.get_documents()] == ["beta.md"]

    mgr.set_filter(FilterMode.ALL)
    mgr.set_search("alpha")
    assert [d.name for d in mgr.get_documents()] == ["alpha.txt"]
    mgr.set_search("")

    mgr.set_sort(SortMode.SIZE, reverse=True)
    assert [d.name for d in mgr.get_documents()] == ["alpha.txt", "beta.md"]

    stats = mgr.get_statistics()
    assert stats["document_count"] == 2
    assert stats["read_count"] == 1
    assert stats["unread_count"] == 1

    assert mgr.remove_document(str(f_alpha.resolve())) is True
    assert mgr.get_statistics()["document_count"] == 1
    mgr.shutdown()
    assert state_file.exists()


def test_theme_manager_validation_reserved_rename_and_delete(tmp_path: Path):
    mgr = LibraryManager(state_file=tmp_path / "state.json")
    mgr.initialize()
    tm = mgr.themes

    assert tm.create_theme("   ") is False
    assert tm.create_theme("X" * 101) is False
    assert tm.create_theme("Steuern") is True
    assert tm.theme_exists("Steuern") is True

    # Reserviertes Thema 'Allgemein' weder umbenennbar noch löschbar
    assert tm.rename_theme("Allgemein", "Sonstiges") is False
    assert tm.delete_theme("Allgemein") is False

    assert tm.set_current_theme("Steuern") is True
    assert tm.rename_theme("Steuern", "Finanzen") is True
    assert tm.get_current_theme() == "Finanzen"

    assert tm.delete_theme("Finanzen") is True
    assert tm.get_current_theme() == "Allgemein"


def test_get_logger_preserves_module_name_without_truncation():
    log_plain = get_logger("simple")
    assert log_plain.name == "DokuZen.simple"

    log_dotted = get_logger("core.pdf.reader")
    assert log_dotted.name == "DokuZen.pdf.reader"

    log_prefixed = get_logger("DokuZen.reader")
    assert log_prefixed.name == "DokuZen.reader"

    class Dummy(LoggerMixin):
        pass

    d = Dummy()
    assert d.logger is d.logger
    assert d.logger.name == "DokuZen.Dummy"
