# -*- coding: utf-8 -*-
"""Regressionstests — DokuZen Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 30, PARTIAL Block 2 = core/).

Schwerpunkt: sqlite-Threading-KRIT (file_index + search_engine). Echter Cross-Thread-Test
prüft den EFFEKT (Persistenz), nicht "keine Exception" — der bare-except in index_file
verschluckt den ProgrammingError sonst tautologisch.
Statische red-on-revert-Assertions via DZ_SRC -> PRE-Backup (core/-Block-2-Module).

  BUG-30 file_index (KRIT): check_same_thread=False + RLock -> Watcher-Thread-Index persistiert.
  BUG-30 file_index (MITTEL): leerer Hash wird nicht indiziert (keine Duplikat-Vergiftung).
  BUG-30 file_index (MITTEL): rollback im except.
  BUG-30 search_engine (MITTEL): min_size/max_size is not None (Wert 0 nicht mehr verschluckt).
  BUG-30 builder/image_tools/persistence/ocr: atomar / append_images / rename-guard / timeout.
"""
import os
import sys
import threading
import tempfile
from pathlib import Path

import pytest

_PROJ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(_PROJ))

_SRC = Path(os.environ.get("DZ_SRC", _PROJ))


def read(rel):
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echter Cross-Thread-Test (staerkster Regressionstest) ---
def test_bug30_crossthread_index_file_persists():
    from core.knowledge.file_index import FileIndex
    d = tempfile.mkdtemp()
    fpath = os.path.join(d, "doc.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("Inhalt für den Index")
    idx = FileIndex(db_path=os.path.join(d, "idx.db"))
    try:
        results = []
        t = threading.Thread(target=lambda: results.append(idx.index_file(fpath)))
        t.start()
        t.join(timeout=10)
        # vor Fix (check_same_thread default): sqlite3.ProgrammingError im Worker-Thread
        # -> bare-except in index_file -> return None; KEIN INSERT.
        assert results and results[0] is not None, "Cross-Thread-Index lieferte None (sqlite-Threading-Bug)"
        # Effekt im Main-Thread sichtbar (gemeinsame Connection + Lock):
        assert idx.get_file(fpath) is not None, "Index aus Worker-Thread nicht persistiert"
    finally:
        idx.close()


def test_bug30_empty_hash_not_indexed():
    """Leerer Hash (calculate_hash-Fehler) darf nicht in den Index — sonst Duplikat-Vergiftung."""
    from core.knowledge.file_index import FileIndex
    d = tempfile.mkdtemp()
    fpath = os.path.join(d, "x.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("y")
    idx = FileIndex(db_path=os.path.join(d, "idx.db"))
    try:
        idx.calculate_hash = lambda *a, **k: ""  # simuliere IO-Fehler-Rückgabe
        assert idx.index_file(fpath) is None, "Datei mit leerem Hash wurde indiziert"
        assert idx.get_file(fpath) is None
    finally:
        idx.close()


# --- statische Assertions (red-on-revert via DZ_SRC -> PRE) ---
def test_bug30_static_check_same_thread():
    src = read("core/knowledge/file_index.py")
    assert "check_same_thread=False" in src, "BUG-30 check_same_thread=False fehlt"
    assert "self._lock = threading.RLock()" in src, "BUG-30 RLock fehlt"


def test_bug30_static_rollback_and_hashguard():
    src = read("core/knowledge/file_index.py")
    assert "self._conn.rollback()" in src, "BUG-30 rollback im except fehlt"
    assert "if not file_hash:" in src, "BUG-30 Leerhash-Guard fehlt"


def test_bug30_static_search_lock_and_size():
    src = read("core/knowledge/search_engine.py")
    assert "with self._index._lock:" in src, "BUG-30 SearchEngine-Lock fehlt"
    assert "if query.min_size is not None:" in src, "BUG-30 min_size is-not-None fehlt"
    assert "if query.max_size is not None:" in src, "BUG-30 max_size is-not-None fehlt"


def test_bug30_static_builder_atomic():
    src = read("core/forms/builder.py")
    assert "tmp.replace(target)" in src, "BUG-30 builder atomarer Save fehlt"
    # Modul muss ohne reportlab importierbar bleiben (lazy Annotationen)
    assert "from __future__ import annotations" in src, "BUG-30 builder __future__-Annotations fehlt"


def test_bug30_builder_importable_without_reportlab():
    """builder muss importierbar sein, auch wenn reportlab fehlt (Annotation darf nicht crashen)."""
    import importlib
    import core.forms.builder as b
    importlib.reload(b)
    assert hasattr(b, "FormTemplate")


def test_bug30_static_ico_append_images():
    src = read("core/converter/image_tools.py")
    assert "append_images=icons[1:]\n" in src, "BUG-30 append_images-Fix fehlt"
    assert "if len(icons) > 1 else None" not in src, "BUG-30 alter append_images=None-Zweig noch da"


def test_bug30_static_persistence_rename_guard():
    src = read("core/library/persistence.py")
    assert "except OSError as e:" in src, "BUG-30 rename-Guard fehlt"


def test_bug30_static_ocr_timeout():
    src = read("core/ocr/engine.py")
    assert "timeout=120" in src, "BUG-30 pytesseract timeout fehlt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
