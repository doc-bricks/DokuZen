# -*- coding: utf-8 -*-
"""Regressionstests — DokuZen Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 33, PARTIAL Block 4b = gui/dialogs Operations-Set).

Worker-Klassen + gui.dialogs-Import sind ohne laufende QApplication testbar -> echte Tests.
Rest statisch (red-on-revert via B4B_SRC -> PRE-Backup-block4b/gui/dialogs).

  BUG-33 pyinstaller: Popen encoding+creationflags, cancel(), closeEvent, shlex.split.
  BUG-33 ocr/image_converter/pyinstaller: closeEvent stoppt+wartet Worker (kein QThread-Crash).
  BUG-33 image_converter: Worker cancel() + mkdir + Mehrfachstart-Guard.
  BUG-33 ocr/code_analysis: Datei-Schreiben in try/except.
  BUG-33 core/ocr/engine.py: from __future__ import annotations -> Modul ohne pytesseract importierbar.
"""
import os
import sys
from pathlib import Path

import pytest

_PROJ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(_PROJ))

_SRC = Path(os.environ.get("B4B_SRC", _PROJ))


def read(rel):
    # B4B_SRC (PRE) enthaelt gui/dialogs/ flach gespiegelt; Default = Projektbaum.
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echte Tests ---
def test_bug33_workers_have_cancel():
    from gui.dialogs.image_converter_dialog import ConversionWorker
    from gui.dialogs.pyinstaller_dialog import CompileWorker
    w = ConversionWorker([], "/tmp/x", "png")
    assert w._cancelled is False
    w.cancel()
    assert w._cancelled is True
    c = CompileWorker(["x"], "/tmp")
    assert c._cancelled is False
    c.cancel()
    assert c._cancelled is True


def test_bug33_gui_dialogs_importable_without_pytesseract():
    """core/ocr/engine.py (und damit ocr_dialog/gui.dialogs) muss ohne pytesseract importierbar sein."""
    import importlib
    # vor Fix: NameError 'Image' beim Import (Annotation Image.Image bei def-Zeit, pytesseract fehlt)
    mod = importlib.import_module("gui.dialogs.ocr_dialog")
    assert hasattr(mod, "OCRDialog")


# --- statische Assertions (red-on-revert via B4B_SRC -> PRE) ---
def test_bug33_static_pyinstaller():
    src = read("gui/dialogs/pyinstaller_dialog.py")
    assert 'encoding="utf-8"' in src and 'errors="replace"' in src, "BUG-33 Popen encoding fehlt"
    assert "CREATE_NO_WINDOW" in src, "BUG-33 creationflags fehlt"
    assert "def cancel(self):" in src, "BUG-33 CompileWorker.cancel fehlt"
    assert "def closeEvent(self, event):" in src, "BUG-33 pyinstaller closeEvent fehlt"
    assert "shlex.split(extra" in src, "BUG-33 shlex.split fehlt"


def test_bug33_static_ocr():
    src = read("gui/dialogs/ocr_dialog.py")
    assert "def closeEvent(self, event):" in src, "BUG-33 ocr closeEvent fehlt"
    assert "except OSError as e:" in src, "BUG-33 ocr _on_save try/except fehlt"


def test_bug33_static_code_analysis():
    src = read("gui/dialogs/code_analysis_dialog.py")
    assert "Zerlegung fehlgeschlagen" in src, "BUG-33 _on_split try/except fehlt"


def test_bug33_static_image_converter():
    src = read("gui/dialogs/image_converter_dialog.py")
    assert "def cancel(self):" in src, "BUG-33 ConversionWorker.cancel fehlt"
    assert "mkdir(parents=True, exist_ok=True)" in src, "BUG-33 Worker mkdir fehlt"
    assert "self._worker.isRunning():" in src, "BUG-33 Mehrfachstart-Guard fehlt"
    assert "def closeEvent(self, event):" in src, "BUG-33 image_converter closeEvent fehlt"


def test_bug33_static_convert_review():
    src = read("gui/dialogs/convert_dialog.py")
    assert "BUGSWEEP-33 REVIEW-NOTIZ" in src, "convert_dialog Freeze/Overwrite Review-Notiz fehlt"


def test_bug33_static_engine_future_annotations():
    # core/ocr/engine.py: aktuell (nicht in B4B_SRC) -> Projektbaum lesen
    src = (_PROJ / "core/ocr/engine.py").read_text(encoding="utf-8")
    assert "from __future__ import annotations" in src, "BUG-33 engine.py __future__-Annotations fehlt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
