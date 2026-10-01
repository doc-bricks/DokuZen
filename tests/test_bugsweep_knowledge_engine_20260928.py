#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regressionstests für den Bugsweep der Knowledge Engine (2026-09-28).
Geprüfter Bereich: Knowledge-Engine, Volltext-Indexierung, Such-Ranking und Tag-Filterung
(core/knowledge/file_index.py + core/knowledge/search_engine.py + core/knowledge/watcher.py)
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from core.knowledge.file_index import FileIndex, FileMetadata, FileCategory
from core.knowledge.search_engine import SearchEngine, SearchQuery, SearchField, SearchResult, SortOrder
from core.knowledge.watcher import KnowledgeWatcher, FileChangeEvent, WatchEvent


class TestKnowledgeEngineRegressions:

    @pytest.fixture
    def env(self):
        """Erstellt eine temporäre Umgebung mit FileIndex und SearchEngine."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_index.db")
            fi = FileIndex(db_path)
            se = SearchEngine(fi)
            yield td, fi, se
            fi.close()

    def test_search_by_tag_filters_out_untagged_files(self, env):
        """
        Defekt (1): Wenn nach einem Tag gefiltert wird (query.tags=['important']),
        darf die Suche NUR Dateien zurückgeben, die diesen Tag besitzen.
        Bisher lieferte die SQL-Query alle ungetaggten Dateien mit zurück.
        """
        td, fi, se = env
        f1 = os.path.join(td, "doc1.txt")
        f2 = os.path.join(td, "doc2.txt")
        f3 = os.path.join(td, "doc3.txt")
        for f in [f1, f2, f3]:
            Path(f).write_text("Hello world content", encoding="utf-8")
            fi.index_file(f)

        fi.add_tag(f1, "important")

        # Suche nach Tag "important"
        results = se.search("", tags=["important"])
        result_paths = [r.metadata.path for r in results]

        assert f1 in result_paths, "Getaggte Datei f1 muss gefunden werden"
        assert f2 not in result_paths, "Ungetaggte Datei f2 darf nicht zurückgegeben werden"
        assert f3 not in result_paths, "Ungetaggte Datei f3 darf nicht zurückgegeben werden"
        assert len(results) == 1, f"Erwartet genau 1 Treffer, aber {len(results)} erhalten"
        assert "tags" in results[0].match_fields

    def test_search_by_tag_and_text_intersection(self, env):
        """
        Defekt (2): Suche nach Text UND Tag muss die Schnittmenge bilden.
        """
        td, fi, se = env
        f_matching = os.path.join(td, "budget_q3.txt")
        f_wrong_tag = os.path.join(td, "budget_draft.txt")
        f_wrong_text = os.path.join(td, "meeting_notes.txt")

        for f in [f_matching, f_wrong_tag, f_wrong_text]:
            Path(f).write_text("Content", encoding="utf-8")
            fi.index_file(f)

        fi.add_tag(f_matching, "finance")
        fi.add_tag(f_wrong_text, "finance")
        fi.add_tag(f_wrong_tag, "draft")

        results = se.search("budget", tags=["finance"])
        result_paths = [r.metadata.path for r in results]

        assert f_matching in result_paths, "Datei mit 'budget' UND Tag 'finance' muss matchen"
        assert f_wrong_tag not in result_paths, "Datei ohne Tag 'finance' darf nicht matchen"
        assert f_wrong_text not in result_paths, "Datei ohne 'budget' darf nicht matchen"
        assert len(results) == 1

    def test_search_field_tags_only(self, env):
        """
        Defekt (3): SearchField.TAGS muss Freitext in Tags durchsuchen und
        Dateien ausschließen, bei denen nur der Dateiname matchet.
        """
        td, fi, se = env
        f_tagged = os.path.join(td, "regular_file.txt")
        f_named = os.path.join(td, "urgent_report.txt")

        for f in [f_tagged, f_named]:
            Path(f).write_text("Content", encoding="utf-8")
            fi.index_file(f)

        fi.add_tag(f_tagged, "urgent")

        query = SearchQuery(text="urgent", fields=[SearchField.TAGS])
        results = se.advanced_search(query)
        result_paths = [r.metadata.path for r in results]

        assert f_tagged in result_paths, "Datei mit Tag 'urgent' muss gefunden werden"
        assert f_named not in result_paths, "Datei nur mit 'urgent' im Namen darf bei fields=[TAGS] nicht matchen"
        assert len(results) == 1
        assert "tags" in results[0].match_fields

    def test_search_field_extension_and_weight(self, env):
        """
        Defekt (4): SearchField.EXTENSION muss Dateiendungen matchen und 'extension'
        in match_fields und Score einbeziehen.
        """
        td, fi, se = env
        f_pdf = os.path.join(td, "document.pdf")
        f_txt = os.path.join(td, "document.txt")

        for f in [f_pdf, f_txt]:
            Path(f).write_text("Content", encoding="utf-8")
            fi.index_file(f)

        query = SearchQuery(text="pdf", fields=[SearchField.EXTENSION])
        results = se.advanced_search(query)
        result_paths = [r.metadata.path for r in results]

        assert f_pdf in result_paths, ".pdf Datei muss gematcht werden"
        assert f_txt not in result_paths, ".txt Datei darf nicht gematcht werden"
        assert len(results) == 1
        assert "extension" in results[0].match_fields
        assert results[0].score >= se.FIELD_WEIGHTS["extension"]

    def test_to_dict_none_dates_resilience(self):
        """
        Defekt (5): FileMetadata.to_dict() und SearchResult.to_dict() dürfen bei
        None-Datumsangaben (z. B. aus fehlerhaften/alten DB-Zeilen) nicht mit
        AttributeError: 'NoneType' object has no attribute 'isoformat' abstürzen.
        """
        meta = FileMetadata(
            path="/dummy/path.pdf",
            name="path.pdf",
            extension=".pdf",
            size_bytes=100,
            hash_sha256="abc123hash",
            category=FileCategory.DOCUMENT,
            mime_type="application/pdf",
            created_at=None,
            modified_at=None,
            indexed_at=None,
        )

        d = meta.to_dict()
        assert d["created_at"] is None
        assert d["modified_at"] is None
        assert d["indexed_at"] is None

        res = SearchResult(metadata=meta, score=0.9)
        res_d = res.to_dict()
        assert res_d["modified_at"] is None

    def test_file_index_remove_file_and_cascade(self, env):
        """
        Defekt (6): FileIndex.remove_file() muss Dateien und deren Tags/Versionen
        sauber aus der Datenbank entfernen.
        """
        td, fi, se = env
        f = os.path.join(td, "obsolete.txt")
        Path(f).write_text("Old content", encoding="utf-8")
        fi.index_file(f)
        fi.add_tag(f, "temp")

        # Modifizieren um eine Version zu erzeugen
        Path(f).write_text("Modified content", encoding="utf-8")
        fi.index_file(f, force_reindex=True)

        assert fi.get_file(f) is not None

        # Datei entfernen
        removed = fi.remove_file(f)
        assert removed is True
        assert fi.get_file(f) is None

        # Sicherstellen dass Tag-Verknüpfung weg ist
        tag_count = fi._conn.execute(
            "SELECT COUNT(*) FROM file_tags WHERE file_id NOT IN (SELECT id FROM files)"
        ).fetchone()[0]
        assert tag_count == 0, "Verwaiste file_tags Einträge dürfen nicht existieren"

        # Nochmaliges Löschen liefert False
        assert fi.remove_file(f) is False

    def test_knowledge_watcher_handles_deleted_and_moved_files(self, env):
        """
        Defekt (7): KnowledgeWatcher muss bei DELETED die Datei aus dem Index entfernen
        und bei MOVED den alten Pfad bereinigen und den neuen indizieren.
        """
        td, fi, se = env
        f_old = os.path.join(td, "old_name.txt")
        f_new = os.path.join(td, "new_name.txt")
        Path(f_old).write_text("Track me", encoding="utf-8")
        fi.index_file(f_old)

        watcher = KnowledgeWatcher(fi)

        # Simuliere MOVE Event
        move_event = FileChangeEvent(
            event_type=WatchEvent.MOVED,
            path=f_old,
            dest_path=f_new,
            is_directory=False
        )
        Path(f_old).rename(f_new)
        watcher._handle_event(move_event)

        assert fi.get_file(f_old) is None, "Alter Pfad muss nach Move aus Index entfernt sein"
        assert fi.get_file(f_new) is not None, "Neuer Pfad muss nach Move im Index sein"

        # Simuliere DELETE Event
        delete_event = FileChangeEvent(
            event_type=WatchEvent.DELETED,
            path=f_new,
            is_directory=False
        )
        if Path(f_new).exists():
            os.unlink(f_new)
        watcher._handle_event(delete_event)

        assert fi.get_file(f_new) is None, "Gelöschte Datei muss nach Delete aus Index entfernt sein"
