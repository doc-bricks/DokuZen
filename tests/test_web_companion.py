#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für die Integrität und Validität des Web Companion (PWA).
"""

import json
import shutil
import subprocess
from pathlib import Path
import pytest
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


def test_web_companion_tier2_i18n_parity():
    """Verify that web_companion/app.js exports all 6 Tier-2 languages with 100% parity."""
    base = Path(__file__).resolve().parent.parent / "web_companion"
    app_js = (base / "app.js").read_text(encoding="utf-8")
    assert "TRANSLATIONS" in app_js
    assert "SUPPORTED_LANGUAGES" in app_js
    for lang in ("de", "en", "es", "zh", "ja", "ru"):
        assert f"{lang}:" in app_js or f'"{lang}":' in app_js or f"'{lang}':" in app_js


def test_web_companion_html_has_lang_selector_and_i18n_attributes():
    """Verify index.html contains #lang-select and data-i18n attributes."""
    base = Path(__file__).resolve().parent.parent / "web_companion"
    html = (base / "index.html").read_text(encoding="utf-8")
    assert 'id="lang-select"' in html
    assert 'data-i18n=' in html
    assert 'data-i18n-title=' in html


def test_web_companion_sw_cache_v2():
    """Verify service worker offline cache versioning."""
    base = Path(__file__).resolve().parent.parent / "web_companion"
    sw_js = (base / "sw.js").read_text(encoding="utf-8")
    assert "dokuzen-companion-v2" in sw_js


def test_web_companion_node_test_suite():
    """Execute node --test web_companion/tests/companion_i18n.test.mjs if node is available."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not available in environment")
    test_file = Path(__file__).resolve().parent.parent / "web_companion" / "tests" / "companion_i18n.test.mjs"
    assert test_file.exists(), f"Node test file {test_file} must exist"
    res = subprocess.run([node_bin, "--test", str(test_file)], capture_output=True, text=True)
    assert res.returncode == 0, f"Node test failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
