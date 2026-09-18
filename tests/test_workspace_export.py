#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für das Workspace-Export-Modul (dokuzen-workspace-v1.json).
"""

import json
from pathlib import Path
import pytest

from core.workspace_export import (
    SCHEMA_NAME,
    SCHEMA_VERSION,
    APP_NAME,
    SAFE_SETTINGS_KEYS,
    FORBIDDEN_SETTINGS_KEYS,
    sanitize_settings,
    sanitize_document,
    build_workspace_snapshot,
    validate_workspace_snapshot,
    export_workspace_to_file,
)
from core.library.manager import Document


def test_sanitize_settings_defaults():
    """Prüft, ob Standard-Einstellungen sicher gesetzt werden."""
    sanitized = sanitize_settings(None)
    assert sanitized["theme"] == "light"
    assert sanitized["language"] == "de"
    assert "last_directory" not in sanitized
    assert "master_password" not in sanitized


def test_sanitize_settings_filtering():
    """Prüft, ob sensible Daten und absolute Pfade herausgefiltert werden."""
    raw_settings = {
        "theme": "dark",
        "language": "en",
        "last_directory": r"C:\Users\lukas\SecretFolder",
        "window_state": {"geometry": [100, 100, 800, 600]},
        "master_password": "super_secret_password_123",
        "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        "pdf_dpi": 300,
        "duplicate_check": False,
        "random_path": "/var/secret/data.db",
    }
    sanitized = sanitize_settings(raw_settings)

    assert sanitized["theme"] == "dark"
    assert sanitized["language"] == "en"
    assert sanitized["pdf_dpi"] == 300
    assert sanitized["duplicate_check"] is False

    for forbidden in FORBIDDEN_SETTINGS_KEYS:
        assert forbidden not in sanitized

    for k, v in sanitized.items():
        if isinstance(v, str):
            assert "C:\\" not in v
            assert "/var" not in v


def test_sanitize_document_redaction():
    """Prüft, dass Dokument-Pfade strikt redigiert werden."""
    from datetime import datetime
    doc = Document(
        path=r"C:\Users\lukas\Documents\Kontoauszug_2026_09.pdf",
        added=datetime(2026, 9, 1, 10, 0, 0),
        is_read=True,
        tags=["Finanzen", "Bank"],
        notes="Monatsabschluss September",
    )
    sanitized = sanitize_document(doc)

    assert sanitized["filename"] == "Kontoauszug_2026_09.pdf"
    assert sanitized["extension"] == ".pdf"
    assert sanitized["is_read"] is True
    assert sanitized["tags"] == ["Finanzen", "Bank"]
    assert sanitized["notes"] == "Monatsabschluss September"
    assert "C:\\" not in str(sanitized)
    assert "Users" not in str(sanitized)


def test_build_workspace_snapshot_schema():
    """Prüft den Aufbau des Snapshots gemäß dokuzen-workspace-v1."""
    snapshot = build_workspace_snapshot()

    assert snapshot["schema"] == SCHEMA_NAME
    assert snapshot["schema_version"] == SCHEMA_VERSION
    assert snapshot["export_app"] == APP_NAME
    assert snapshot["redaction"]["absolute_paths_included"] is False
    assert snapshot["redaction"]["secrets_included"] is False
    assert isinstance(snapshot["themes"], list)
    assert isinstance(snapshot["documents"], list)
    assert isinstance(snapshot["totals"], dict)
    assert validate_workspace_snapshot(snapshot) is True


def test_build_workspace_snapshot_with_library_dict():
    """Prüft Snapshot-Erstellung aus einem Bibliotheks-Dictionary."""
    mock_library = {
        "themes": {
            "Forschung": {
                "documents": [
                    {
                        "path": r"C:\data\KI_Paper.pdf",
                        "name": "KI_Paper.pdf",
                        "tags": ["KI"],
                        "is_read": True,
                        "size": 500000,
                    }
                ]
            },
            "Privat": {
                "documents": [
                    {
                        "path": r"D:\docs\Rezept.txt",
                        "name": "Rezept.txt",
                        "tags": ["Kochen"],
                        "is_read": False,
                        "size": 1200,
                    }
                ]
            },
        }
    }

    snapshot = build_workspace_snapshot(library=mock_library)
    assert len(snapshot["themes"]) == 2
    assert len(snapshot["documents"]) == 2
    assert snapshot["totals"]["theme_count"] == 2
    assert snapshot["totals"]["document_count"] == 2
    assert snapshot["totals"]["read_document_count"] == 1

    for d in snapshot["documents"]:
        assert not d["filename"].startswith("C:")
        assert not d["filename"].startswith("D:")
        assert "\\" not in d["filename"]
        assert "/" not in d["filename"]


def test_export_workspace_to_file(tmp_path):
    """Prüft atomaren Datei-Export und UTF-8-Encoding."""
    target_file = tmp_path / "export" / "dokuzen-workspace-v1.json"
    mock_library = {
        "themes": {
            "Überblick & Verträge": {
                "documents": [
                    {
                        "path": "/opt/docs/München_Vertrag_äöüß.pdf",
                        "name": "München_Vertrag_äöüß.pdf",
                        "tags": ["München", "Verträge"],
                        "is_read": True,
                    }
                ]
            }
        }
    }

    exported = export_workspace_to_file(target_file, library=mock_library)
    assert exported.exists()
    assert exported.stat().st_size > 0

    content = json.loads(exported.read_text(encoding="utf-8"))
    assert content["schema"] == SCHEMA_NAME
    assert content["themes"][0]["name"] == "Überblick & Verträge"
    assert content["documents"][0]["filename"] == "München_Vertrag_äöüß.pdf"
    assert "äöüß" in exported.read_text(encoding="utf-8")


def test_validate_workspace_snapshot_rejects_leaks():
    """Prüft, dass ungültige oder datenleckende Snapshots abgewiesen werden."""
    bad_snapshot = {
        "schema": SCHEMA_NAME,
        "schema_version": 1,
        "redaction": {"absolute_paths_included": True},
        "documents": [],
    }
    assert validate_workspace_snapshot(bad_snapshot) is False

    leaking_doc_snapshot = {
        "schema": SCHEMA_NAME,
        "schema_version": 1,
        "redaction": {"absolute_paths_included": False},
        "documents": [{"filename": r"C:\Users\Secret\File.pdf"}],
        "settings": {},
    }
    assert validate_workspace_snapshot(leaking_doc_snapshot) is False
