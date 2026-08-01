# -*- coding: utf-8 -*-
"""Regressionstests — DokuZen Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 28, PARTIAL Block 1).

core/knowledge + core/redaction importierbar -> echte Tests; Regex/SELECT zusaetzlich statisch.
Red-on-revert: DZ_SRC -> PRE-Backup-Verzeichnis (Block-1-Module).

  BUG-01 file_index: SELECT um size_bytes ergaenzt -> Re-Index einer bekannten Datei wirft nicht mehr
        (IndexError war vom bare-except verschluckt -> Änderungen nie indiziert).
  BUG-4 detector PHONE: +49-Nummern werden jetzt erkannt (fuehrendes \b matchte vor '+' nie).
  BUG-5 detector EMAIL: literales '|' aus TLD-Klasse entfernt.
"""
import os
import sys
import tempfile
from pathlib import Path

_PROJ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(_PROJ))

_SRC = Path(os.environ.get("DZ_SRC", _PROJ))


def read(rel):
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echte Tests ---
def test_bug01_reindex_known_file_no_swallowed_error():
    from core.knowledge.file_index import FileIndex
    d = tempfile.mkdtemp()
    f = os.path.join(d, "a.txt")
    open(f, "w", encoding="utf-8").write("v1")
    idx = FileIndex(db_path=os.path.join(d, "idx.db"))
    assert idx.index_file(f) is not None
    open(f, "w", encoding="utf-8").write("v2 laenger geaendert")
    # vor Fix: SELECT ohne size_bytes -> existing['size_bytes'] IndexError -> bare-except -> None
    assert idx.index_file(f, force_reindex=True) is not None


def test_bug4_phone_plus49_detected():
    from core.redaction.detector import RedactionDetector
    det = RedactionDetector()
    found_49 = [m.text for m in det.detect(" Kontakt: +49 170 1234567 bitte")]
    assert any("+49" in t for t in found_49), "+49-Nummer nicht erkannt (BUG-4)"
    # 0170-Variante darf weiterhin erkannt werden (keine Regression)
    found_0 = [m.text for m in det.detect(" Tel 0170 1234567 ")]
    assert any("0170" in t for t in found_0), "0170-Nummer nicht mehr erkannt (Regression!)"


def test_bug5_email_still_detected():
    from core.redaction.detector import RedactionDetector
    det = RedactionDetector()
    assert any("a@b.de" in m.text for m in det.detect(" mail a@b.de hier")), "E-Mail nicht erkannt"


# --- statische Assertions (red-on-revert) ---
def test_bug01_select_has_size_bytes():
    src = read("core/knowledge/file_index.py")
    assert "SELECT id, hash_sha256, modified_at, size_bytes FROM files" in src, "BUG-01 SELECT-Fix fehlt"


def test_bug4_phone_lookbehind():
    src = read("core/redaction/detector.py")
    assert r"(?<!\d)(?:\+49|0049|0)" in src, "BUG-4 (?<!\\d)-Anker fehlt"
    assert r"\b(?:\+49|0049|0)" not in src, "BUG-4 altes \\b vor +49 noch da"


def test_bug5_email_no_literal_pipe():
    src = read("core/redaction/detector.py")
    assert "[A-Z|a-z]" not in src, "BUG-5 literales | noch in TLD-Klasse"


def test_dedup_review_notiz_present():
    src = read("core/redaction/detector.py")
    assert "BUGSWEEP-28 KRITISCH USER-REVIEW" in src, "Redaction-Reliability-Review-Notiz fehlt"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
