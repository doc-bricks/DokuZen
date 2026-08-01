# -*- coding: utf-8 -*-
"""Regressionstests — DokuZen Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 34, PARTIAL Block 4c = restliche gui/dialogs — Monolith-Abschluss).

GUI-Dialoge brauchen QApplication -> echter Test = Modul-Import-Smoke aller 8 Dialoge.
Fixes zusaetzlich statisch (red-on-revert via B4C_SRC -> PRE-Backup-block4c/gui/dialogs).

  BUG-34 pdf_pages (KRIT): In-Place-Save atomar (tmp+replace, offenes Doc schliessen).
  BUG-34 pdf_marker: QImage.copy() im Worker, QPixmap.fromImage erst im GUI-Slot.
  BUG-34 redaction: input==output-Guard (Original-Korruptionsschutz).
  BUG-34 text_pool: atomarer Save + cp1252-vor-latin-1 + dragEnter-ignore.
  BUG-34 form_builder: QPainter-Import + scoped RenderHint (Canvas-Crash-Risiko).
  BUG-34 settings: _load_settings stellt font_family/icon_size/pdf_quality/pdf_compress wieder her.
  BUG-34 sqlite: _count_rows try/except.
"""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_PROJ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(_PROJ))

_SRC = Path(os.environ.get("B4C_SRC", _PROJ))


def read(rel):
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echter Smoke-Test: alle 8 Block-4c-Dialogmodule importierbar (inkl. form_builder QPainter-Import) ---
def test_bug34_all_block4c_dialogs_import():
    import importlib
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    for mod in [
        "pdf_workshop", "pdf_marker_dialog", "pdf_pages_dialog", "settings_dialog",
        "sqlite_viewer_dialog", "form_builder_dialog", "redaction_dialog", "text_pool_dialog",
    ]:
        m = importlib.import_module(f"gui.dialogs.{mod}")
        assert m is not None


# --- statische Assertions (red-on-revert via B4C_SRC -> PRE) ---
def test_bug34_static_pdf_pages_atomic():
    src = read("gui/dialogs/pdf_pages_dialog.py")
    assert "tmp.replace(path)" in src, "BUG-34 pdf_pages atomarer In-Place-Save fehlt"
    assert "same and self._doc is not None" in src, "BUG-34 offenes Doc schliessen fehlt"


def test_bug34_static_pdf_marker_qimage():
    src = read("gui/dialogs/pdf_marker_dialog.py")
    assert "img.copy()" in src, "BUG-34 QImage.copy() im Worker fehlt"
    assert "QPixmap.fromImage(image)" in src, "BUG-34 fromImage im GUI-Slot fehlt"


def test_bug34_static_redaction_guard():
    src = read("gui/dialogs/redaction_dialog.py")
    assert "Originaldatei nicht überschreiben" in src, "BUG-34 redaction input==output-Guard fehlt"


def test_bug34_static_text_pool():
    src = read("gui/dialogs/text_pool_dialog.py")
    assert "tmp.replace(path)" in src, "BUG-34 text_pool atomarer Save fehlt"
    assert "'utf-8', 'utf-8-sig', 'cp1252', 'latin-1'" in src, "BUG-34 Encoding-Reihenfolge fehlt"
    assert "event.ignore()" in src, "BUG-34 dragEnter-ignore fehlt"


def test_bug34_static_form_builder_qpainter():
    src = read("gui/dialogs/form_builder_dialog.py")
    assert "QPainter.RenderHint.Antialiasing" in src, "BUG-34 scoped RenderHint fehlt"
    assert "QPainter" in src.split("from PySide6.QtGui import")[1].split("\n")[0], "BUG-34 QPainter-Import fehlt"


def test_bug34_static_settings_roundtrip():
    src = read("gui/dialogs/settings_dialog.py")
    assert '("font_family", self._font_family)' in src, "BUG-34 settings Round-Trip-Restore fehlt"


def test_bug34_static_sqlite_count_guard():
    src = read("gui/dialogs/sqlite_viewer_dialog.py")
    assert "Zeilen zählen fehlgeschlagen" in src, "BUG-34 _count_rows try/except fehlt"
    assert "BUGSWEEP-34 REVIEW-NOTIZ" in src, "BUG-34 QueryWorker-Review-Notiz fehlt"


_B5SRC = Path(os.environ.get("B5_SRC", _PROJ))


def test_bug34_block5_main_py():
    """Block 5 (Monolith-Abschluss): main.py Bootstrap-Fixes."""
    src = (_B5SRC / "main.py").read_text(encoding="utf-8")
    assert "sys.excepthook = _log_excepthook" in src, "BUG-34 sys.excepthook fehlt"
    assert "QApplication([sys.argv[0]])" in src, "BUG-34 QApplication-args-Fix fehlt"
    assert "file=sys.stderr" in src, "BUG-34 ImportError->stderr fehlt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
