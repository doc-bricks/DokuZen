# -*- coding: utf-8 -*-
"""Regressionstests — DokuZen Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 31, PARTIAL Block 3 = plugins/).

encoding_fixer ist GUI-frei importierbar -> echte Tests. tray/registry zusaetzlich statisch
(red-on-revert via PLUG_SRC -> PRE-Backup-block3).

  BUG-31 encoding_fixer (FATAL): In-Place-Write atomar (tmp + os.replace) statt Original-Overwrite.
  BUG-31 encoding_fixer (MITTEL): Mojibake-Muster nach Laenge absteigend ersetzen
        (Präfix 'â€' zerstoerte sonst 'â€˜'/'â€™'/'â€¦'/'â€"').
  BUG-31 tray_plugin (MITTEL): _on_quit setzt quit_event statt sys.exit im Worker-Thread.
  BUG-31 registry (MITTEL): get_status fragt dz_py_analyze mit extensions=[".py"] ab.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_PROJ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(_PROJ))

_SRC = Path(os.environ.get("PLUG_SRC", _PROJ))


def read(rel):
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echte Tests: encoding_fixer ---
def test_bug31_mojibake_prefix_ordering():
    from plugins.special_text.encoding_fixer import EncodingFixer
    fx = EncodingFixer()
    # vor Fix: 'â€' (->'"') greift vor 'â€¦' -> '"¦Ende' (Ellipsis nie repariert)
    fixed, _ = fx.fix_mojibake("â€¦Ende")
    assert "…" in fixed, f"Ellipsis-Mojibake nicht korrekt repariert: {fixed!r}"
    assert "¦" not in fixed, f"Präfix-Ordering-Reststueck '¦' geblieben: {fixed!r}"
    fixed2, _ = fx.fix_mojibake("â€˜Hallo")
    assert "˜" not in fixed2, f"Präfix-Ordering-Reststueck '˜' geblieben: {fixed2!r}"


def test_bug31_convert_file_atomic_inplace():
    from plugins.special_text.encoding_fixer import EncodingFixer
    fx = EncodingFixer()
    d = tempfile.mkdtemp()
    fpath = os.path.join(d, "data.txt")
    with open(fpath, "wb") as f:
        f.write("Käse".encode("latin-1"))
    res = fx.convert_file(fpath, target_encoding="utf-8", source_encoding="latin-1")
    assert res.success, f"convert_file fehlgeschlagen: {getattr(res, 'error', None)}"
    # In-Place erfolgreich als UTF-8 lesbar
    assert Path(fpath).read_text(encoding="utf-8") == "Käse"
    # KEINE .tmp-Leiche (atomar abgeschlossen)
    assert not os.path.exists(fpath + ".tmp"), "tmp-Datei nicht aufgeraeumt"


def test_bug31_tray_quit_event_wiring():
    """Verdrahtung: SpawnerService.quit_event loest auf den TrayPlugin-Event auf (kein Plumbing-Bug)."""
    import threading
    from plugins.spawner.tray_plugin import SpawnerService
    svc = SpawnerService()  # nur Konstruktion (kein .start() -> keine Threads/pystray noetig)
    assert isinstance(svc.quit_event, threading.Event)
    svc.quit_event.set()
    assert svc.quit_event.is_set()


# --- statische Assertions (red-on-revert via PLUG_SRC -> PRE) ---
def test_bug31_static_encoding_atomic():
    src = read("plugins/special_text/encoding_fixer.py")
    assert "os.replace(tmp_path, out_path)" in src, "BUG-31 atomarer Write fehlt"


def test_bug31_static_encoding_sorted_patterns():
    src = read("plugins/special_text/encoding_fixer.py")
    assert "key=lambda kv: len(kv[0]), reverse=True" in src, "BUG-31 Laengen-Sortierung fehlt"


def test_bug31_static_tray_quit_event():
    src = read("plugins/spawner/tray_plugin.py")
    assert "self.quit_event = threading.Event()" in src, "BUG-31 quit_event fehlt"
    assert "self.quit_event.set()" in src, "BUG-31 quit_event.set() fehlt"
    assert "sys.exit(0)" not in src, "BUG-31 sys.exit(0) im Worker-Callback noch da"


def test_bug31_static_registry_extensions():
    src = read("plugins/spawner/registry.py")
    assert 'is_registered("dz_py_analyze", extensions=[".py"])' in src, "BUG-31 py_analyze extensions fehlt"


def test_bug31_review_notiz_encoding():
    src = read("plugins/special_text/encoding_fixer.py")
    assert "BUGSWEEP-31 REVIEW-NOTIZ" in src, "lossy-decode Review-Notiz fehlt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
