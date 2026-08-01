#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für Seiten-Notation im DokuZen-PDF-Marker."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_parse_page_range_notation_accepts_ranges_and_single_pages():
    from core.pdf.page_ranges import parse_page_range_notation

    assert parse_page_range_notation("1-3, 5, 7-8") == [1, 2, 3, 5, 7, 8]


def test_parse_page_range_notation_rejects_out_of_bounds_pages():
    from core.pdf.page_ranges import parse_page_range_notation

    assert parse_page_range_notation("1-3, 6", page_count=5) == []
    assert parse_page_range_notation("0, 2", page_count=5) == []


def test_parse_page_range_notation_rejects_invalid_tokens():
    from core.pdf.page_ranges import parse_page_range_notation

    assert parse_page_range_notation("5-") == []
    assert parse_page_range_notation("7-3") == []
    assert parse_page_range_notation("abc") == []


def test_pdf_marker_dialog_offers_page_notation_controls():
    source = (
        PROJECT_ROOT / "gui" / "dialogs" / "pdf_marker_dialog.py"
    ).read_text(encoding="utf-8")

    assert "Seiten-Notation:" in source
    assert "Notation anwenden" in source
    assert "parse_page_range_notation(notation, page_count=self._page_count)" in source
