#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Erweiterte Tests für core/knowledge/watcher.py und plugins/special_text/encoding_fixer.py."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.knowledge.file_index import FileIndex
from core.knowledge.watcher import (
    DebouncedQueue,
    FileChangeEvent,
    FileWatchHandler,
    FileWatcher,
    KnowledgeWatcher,
    WatchEvent,
)
from plugins.special_text.encoding_fixer import (
    EncodingFixer,
    convert_to_utf8,
    detect_file_encoding,
)


def test_debounced_queue_coalesces_modified_and_flushes_deleted_immediately():
    q = DebouncedQueue(debounce_seconds=5.0)
    ev1 = FileChangeEvent(WatchEvent.CREATED, "a.txt", False)
    ev2 = FileChangeEvent(WatchEvent.MODIFIED, "a.txt", False)
    q.put(ev1)
    q.put(ev2)

    # Noch innerhalb des 5s-Debounce-Fensters: nichts bereit
    assert q.get_ready() == []

    # DELETED löscht das pending Event und geht sofort in die Direkt-Queue
    ev_del = FileChangeEvent(WatchEvent.DELETED, "a.txt", False)
    q.put(ev_del)
    ready = q.get_ready()
    assert ready == [ev_del]


def test_debounced_queue_returns_events_after_debounce_elapsed():
    q = DebouncedQueue(debounce_seconds=0.02)
    ev = FileChangeEvent(WatchEvent.MODIFIED, "b.md", False)
    q.put(ev)
    time.sleep(0.05)
    assert q.get_ready() == [ev]
    assert q.get_ready() == []


def test_file_watch_handler_filters_ignored_patterns_dirs_and_extensions():
    received = []
    handler = FileWatchHandler(received.append, extensions={".txt", ".pdf"})

    assert handler._should_ignore("/tmp/foo.tmp") is True
    assert handler._should_ignore("/tmp/~$draft.docx") is True
    assert handler._should_ignore("/tmp/.hidden") is True
    assert handler._should_ignore("/repo/__pycache__/x.pyc") is True
    assert handler._should_ignore("/repo/notes.md") is True
    assert handler._should_ignore("/repo/readme.txt") is False

    # Directory-Events werden verworfen
    handler.on_created(SimpleNamespace(is_directory=True, src_path="/repo/sub"))
    handler.on_modified(SimpleNamespace(is_directory=True, src_path="/repo/sub"))
    handler.on_deleted(SimpleNamespace(is_directory=True, src_path="/repo/sub"))
    handler.on_moved(
        SimpleNamespace(is_directory=True, src_path="/repo/a", dest_path="/repo/b")
    )
    assert received == []

    # Atomares Speichern: .tmp -> .txt wird durchgelassen
    handler.on_moved(
        SimpleNamespace(
            is_directory=False,
            src_path="/repo/doc.tmp",
            dest_path="/repo/doc.txt",
        )
    )
    assert len(received) == 1
    assert received[0].event_type == WatchEvent.MOVED
    assert received[0].dest_path == "/repo/doc.txt"


def test_file_watcher_configuration_and_knowledge_watcher_created_modified(tmp_path: Path):
    fw = FileWatcher(debounce_seconds=0.1)
    fw.set_extensions(["PDF", ".md"])
    assert fw._extensions == {".pdf", ".md"}

    cb = MagicMock()
    fw.add_handler(cb)
    assert cb in fw._handlers
    fw.remove_handler(cb)
    assert cb not in fw._handlers

    missing = tmp_path / "does_not_exist"
    fw.add_watch_path(str(missing))
    assert fw.watch_paths == []

    db_path = tmp_path / "idx.db"
    fi = FileIndex(str(db_path))
    try:
        kw = KnowledgeWatcher(fi, debounce_seconds=0.1)
        doc_file = tmp_path / "note.txt"
        doc_file.write_text("Erster Inhalt", encoding="utf-8")

        kw._handle_event(FileChangeEvent(WatchEvent.CREATED, str(doc_file), False))
        assert fi.get_file(str(doc_file)) is not None

        doc_file.write_text("Aktualisierter Inhalt", encoding="utf-8")
        kw._handle_event(FileChangeEvent(WatchEvent.MODIFIED, str(doc_file), False))
        meta = fi.get_file(str(doc_file))
        assert meta is not None
        assert meta.size_bytes == doc_file.stat().st_size
    finally:
        fi.close()


def test_encoding_fixer_bom_and_heuristic_detection(monkeypatch, tmp_path: Path):
    fx = EncodingFixer()

    assert fx.detect_encoding_bytes(b"\xef\xbb\xbfHallo").detected_encoding == "utf-8-sig"
    assert fx.detect_encoding_bytes(b"\xff\xfeH\x00").detected_encoding == "utf-16-le"
    assert fx.detect_encoding_bytes(b"\xfe\xff\x00H").detected_encoding == "utf-16-be"

    # Heuristik ohne chardet prüfen
    monkeypatch.setattr("plugins.special_text.encoding_fixer.CHARDET_AVAILABLE", False)
    utf8_res = fx.detect_encoding_bytes("Prüfung UTF-8".encode("utf-8"))
    assert utf8_res.detected_encoding == "utf-8"
    assert utf8_res.is_confident is True

    latin_res = fx.detect_encoding_bytes("Größe".encode("latin-1"))
    assert latin_res.detected_encoding == "latin-1"

    assert fx.detect_encoding(str(tmp_path / "missing.txt")) is None
    assert detect_file_encoding(str(tmp_path / "missing.txt")) is None


def test_encoding_fixer_analyze_convert_and_batch(tmp_path: Path):
    fx = EncodingFixer()

    missing_info = fx.analyze_file(str(tmp_path / "absent.txt"))
    assert missing_info["error"] == "Datei nicht gefunden"

    utf8_file = tmp_path / "plain.txt"
    utf8_file.write_text("Reiner UTF-8 Text mit ÄÖÜ", encoding="utf-8")
    info = fx.analyze_file(str(utf8_file))
    assert info["has_bom"] is False
    assert info["non_ascii_chars"] == 3
    assert info["problem_chars"] == 0
    assert any("BOM" in s for s in info["suggestions"])

    # Ziel-Encoding ASCII schlägt bei Umlaut sauber fehl ohne Quelldatei zu beschädigen
    fail_res = fx.convert_file(
        str(utf8_file),
        target_encoding="ascii",
        output_path=str(tmp_path / "ascii_out.txt"),
        source_encoding="utf-8",
    )
    assert fail_res.success is False
    assert "Enkodierungsfehler" in (fail_res.error or "")
    assert not (tmp_path / "ascii_out.txt").exists()

    # Batch-Konvertierung nach separatem Zielordner inkl. fehlender Datei
    latin_file = tmp_path / "latin.txt"
    latin_file.write_bytes("Büro".encode("latin-1"))
    out_dir = tmp_path / "converted"
    results = fx.batch_convert(
        [str(latin_file), str(tmp_path / "missing.txt")],
        target_encoding="utf-8",
        output_dir=str(out_dir),
    )
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False
    assert (out_dir / "latin.txt").read_text(encoding="utf-8") == "Büro"

    # Hilfsfunktion convert_to_utf8
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "cp.txt"
        dst = Path(td) / "utf.txt"
        src.write_bytes("Märchen".encode("latin-1"))
        assert convert_to_utf8(str(src), str(dst)) is True
        assert dst.read_text(encoding="utf-8") == "Märchen"
