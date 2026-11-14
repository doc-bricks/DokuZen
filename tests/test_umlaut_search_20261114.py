#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Umlaut-Suche (2026-11-14, Querbefund aus ProSync).

SQLite-lower()/LIKE falten nur ASCII. Die Suche nach „Übersicht“ oder „übersicht“ fand
„Übersicht_2026.pdf“ nicht, ein Tag-Filter „ärzte“ nicht den Tag „Ärzte“ — im Deutschen
stehen Ä/Ö/Ü oft am Wortanfang.
"""
import os
import tempfile
from pathlib import Path

import pytest

from core.knowledge.file_index import FileIndex
from core.knowledge.search_engine import SearchEngine


@pytest.fixture
def env():
    with tempfile.TemporaryDirectory() as td:
        index = FileIndex(os.path.join(td, "idx.db"))
        engine = SearchEngine(index)
        yield td, index, engine
        index.close()


def _names(results):
    return sorted(Path(r.metadata.path).name for r in results)


def test_text_search_finds_capital_umlauts(env):
    td, index, engine = env
    for name in ("Übersicht_2026.txt", "Ölrechnung.txt", "Notiz.txt"):
        path = os.path.join(td, name)
        Path(path).write_text("Inhalt", encoding="utf-8")
        index.index_file(path)

    assert _names(engine.search("Übersicht")) == ["Übersicht_2026.txt"]
    assert _names(engine.search("übersicht")) == ["Übersicht_2026.txt"]
    assert _names(engine.search("öl")) == ["Ölrechnung.txt"]
    assert "Übersicht_2026.txt" in engine.suggest("über")


def test_tag_filter_and_tag_text_ignore_umlaut_case(env):
    td, index, engine = env
    path = os.path.join(td, "befund.txt")
    Path(path).write_text("Inhalt", encoding="utf-8")
    index.index_file(path)
    index.add_tag(path, "Ärzte")

    assert _names(engine.search("", tags=["ärzte"])) == ["befund.txt"]
    assert _names(engine.search("ärzte")) == ["befund.txt"]
