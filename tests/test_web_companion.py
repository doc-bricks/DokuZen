#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für die Integrität und Validität des Web Companion (PWA).
"""

import json
from pathlib import Path
from core.workspace_export import validate_workspace_snapshot


def test_web_companion_assets_exist():
    base = Path(__file__).resolve().parent.parent / "web_companion"
    assert (base / "index.html").exists()
    assert (base / "style.css").exists()
    assert (base / "app.js").exists()
    assert (base / "library.js").exists()
    assert (base / "manifest.webmanifest").exists()
    assert (base / "sw.js").exists()
    assert (base / "sample_workspace.json").exists()


def test_web_companion_manifest_validity():
    base = Path(__file__).resolve().parent.parent / "web_companion"
    manifest_file = base / "manifest.webmanifest"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    
    assert data.get("name") == "DokuZen Companion"
    assert data.get("short_name") == "DokuZen"
    assert data.get("display") == "standalone"
    assert "icons" in data and len(data["icons"]) >= 2
    
    for icon in data["icons"]:
        icon_path = base / icon["src"]
        assert icon_path.exists(), f"Icon-Datei {icon_path} existiert nicht"


def test_web_companion_sample_snapshot():
    base = Path(__file__).resolve().parent.parent / "web_companion"
    sample_file = base / "sample_workspace.json"
    data = json.loads(sample_file.read_text(encoding="utf-8"))
    
    assert validate_workspace_snapshot(data) is True
    assert data["export_app"] == "DokuZen"
    assert data["redaction"]["absolute_paths_included"] is False
    assert data["redaction"]["secrets_included"] is False
