"""Metadata, documentation integrity, and ecosystem manifest tests for DokuZen."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_metadata_and_pep621_classifiers():
    """Verify pyproject.toml configuration, PEP 621 metadata, URLs, and classifiers."""
    pyproject_path = ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    assert project.get("name") == "DokuZen"
    # Gegen die Paketkonfiguration pruefen statt gegen ein Literal: sonst schlaegt
    # der Test bei jeder Versionsanhebung fehl, ohne dass etwas kaputt ist - und
    # eine Abweichung zwischen pyproject und store_package.json bleibt unentdeckt.
    version = project.get("version")
    assert re.fullmatch(r"\d+\.\d+\.\d+", version or ""), version
    with open(Path(__file__).resolve().parents[1] / "store_package.json", encoding="utf-8") as sf:
        store_version = json.load(sf)["version"]
    assert store_version.startswith(version + "."), (
        "pyproject %s passt nicht zu store_package.json %s" % (version, store_version))
    assert "AGPL-3.0" in project.get("license", {}).get("text", "")
    assert "PySide6>=6.5.0" in project.get("dependencies", [])

    urls = project.get("urls", {})
    assert urls.get("Homepage") == "https://github.com/doc-bricks/DokuZen"
    assert urls.get("Repository") == "https://github.com/doc-bricks/DokuZen.git"
    assert urls.get("Documentation") == "https://github.com/doc-bricks/DokuZen#readme"
    assert urls.get("Changelog") == "https://github.com/doc-bricks/DokuZen/blob/main/CHANGELOG.md"
    assert urls.get("Security") == "https://github.com/doc-bricks/DokuZen/blob/main/SECURITY.md"
    assert urls.get("Umbrella") == "https://github.com/open-bricks"

    classifiers = project.get("classifiers", [])
    assert any("3.10" in c for c in classifiers)
    assert any("3.11" in c for c in classifiers)
    assert any("3.12" in c for c in classifiers)
    assert any("3.13" in c for c in classifiers)
    assert any("OS Independent" in c for c in classifiers)
    assert any("Windows" in c for c in classifiers)
    assert any("Linux" in c for c in classifiers)

    # Ruff configuration
    ruff_conf = data.get("tool", {}).get("ruff", {})
    assert ruff_conf.get("target-version") == "py310"
    assert ruff_conf.get("line-length") == 120


def test_required_documentation_files():
    """Ensure all required core documentation and policy files exist and are populated."""
    required_files = [
        "README.md",
        "README_de.md",
        "LICENSE",
        "CHANGELOG.md",
        "llms.txt",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "PRIVACY_POLICY.md",
        "SUPPORT.md",
        "STORE_LISTING.md",
        "THIRD_PARTY_LICENSES.txt",
        "WINDOWS_STORE_PREP.md",
    ]
    for rel_path in required_files:
        path = ROOT / rel_path
        assert path.exists(), f"Missing required file: {rel_path}"
        assert path.stat().st_size > 0, f"File is empty: {rel_path}"


def test_llms_txt_structure():
    """Validate llms.txt structure, required sections, and architectural context."""
    llms_path = ROOT / "llms.txt"
    assert llms_path.exists(), "llms.txt must exist"
    content = llms_path.read_text(encoding="utf-8")

    assert "DokuZen" in content
    assert "doc-bricks" in content
    assert "open-bricks" in content
    assert "Last-checked:" in content or "Last-checked:**" in content
    assert any(d in content for d in ["2026-08-23", "2026-08-24"])
    assert "PySide6" in content
    assert "PyMuPDF" in content
    assert "AGPL-3.0" in content
    assert "SECURITY.md" in content


def test_readme_badges_and_bilingual_parity():
    """Validate badges and links across English and German README files."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for content in (readme_en, readme_de):
        assert "doc-bricks" in content
        assert "open-bricks" in content
        assert "AGPL-3.0" in content
        assert "llms.txt" in content
        assert "assets/banner.png" in content
        assert "SECURITY.md" in content
        assert "source-platform-smoke.yml" in content

    # Language switcher presence
    assert "[Deutsch](README_de.md)" in readme_en
    assert "[English](README.md)" in readme_de

    # Quick navigation presence
    assert "Quick Navigation" in readme_en
    assert "Schnellnavigation" in readme_de


def test_mermaid_diagrams_syntax():
    """Verify presence of valid Mermaid architecture and lifecycle diagrams in both READMEs."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for content in (readme_en, readme_de):
        assert "```mermaid" in content
        assert "flowchart TD" in content or "graph TD" in content
        assert "sequenceDiagram" in content
        assert "autonumber" in content


def test_visual_showcase_screenshots_exist():
    """Verify that all screenshots referenced in the visual showcase gallery exist on disk."""
    expected_screenshots = [
        "screenshots/main.png",
        "screenshots/store/01_bibliothek.png",
        "screenshots/store/02_pdf_vorschau.png",
        "screenshots/store/03_ocr_dialog.png",
        "screenshots/store/04_schwaerzung.png",
        "screenshots/store/05_konvertierung.png",
        "screenshots/store/06_batch_verarbeitung.png",
    ]
    for rel_path in expected_screenshots:
        path = ROOT / rel_path
        assert path.exists(), f"Showcase screenshot missing: {rel_path}"
        with Image.open(path) as img:
            assert img.format == "PNG", f"{rel_path} must be PNG"
            w, h = img.size
            assert w > 0 and h > 0, f"Invalid dimensions for {rel_path}"


def test_sibling_ecosystem_and_urls():
    """Ensure sibling ecosystem repositories are documented and cross-linked."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    siblings = [
        "doc-bricks/CleanMarkdown",
        "doc-bricks/FormularErstellen",
        "doc-bricks/UniversalDocsGrabber",
        "doc-bricks/PDFtoPDFocr",
        "doc-bricks/DokuReader",
        "doc-bricks/MediaBrain",
        "doc-bricks/TextBrain",
        "file-bricks/WinStorePackager",
        "file-bricks/ProSync",
        "file-bricks/ExplorerPro",
        "dev-bricks/DevCenter",
        "open-bricks/.github",
    ]
    for sibling in siblings:
        assert sibling in readme_en, f"Missing sibling {sibling} in README.md"
        assert sibling in readme_de, f"Missing sibling {sibling} in README_de.md"


def test_security_policy_bilingual_and_invariants():
    """Validate bilingual structure and security invariants in SECURITY.md."""
    sec_path = ROOT / "SECURITY.md"
    assert sec_path.exists(), "SECURITY.md must exist"
    content = sec_path.read_text(encoding="utf-8")

    assert "## Deutsch" in content
    assert "## English" in content
    assert "Zero-Egress" in content
    assert "Non-Elevation" in content
    assert "security@open-bricks.org" in content
    assert "support@lukasgeiger.com" in content
    assert "Security Advisories" in content


def test_version_parity():
    """Ensure consistent version numbering across all project manifests."""
    pyproject_path = ROOT / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    version = data.get("project", {}).get("version")
    # Gegen die uebrigen Manifeste pruefen statt gegen ein Literal: ein fester Wert
    # macht den Test bei jeder Versionsanhebung rot, ohne echte Abweichung - und
    # verdeckt umgekehrt eine tatsaechliche Drift zwischen den Dateien.
    assert re.fullmatch(r"\d+\.\d+\.\d+", version or ""), version

    store_cfg = ROOT / "store_package.json"
    if store_cfg.exists():
        store_data = json.loads(store_cfg.read_text(encoding="utf-8"))
        store_version = store_data.get("version", "")
        # Store-Format ist vierstellig (X.Y.Z.Build)
        assert store_version.startswith(version + "."), (
            "pyproject %s passt nicht zu store_package.json %s" % (version, store_version))

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{version}]" in changelog, "CHANGELOG fuehrt keinen Eintrag fuer %s" % version


def test_offline_and_zero_egress_invariants():
    """Verify that all core, GUI, and plugin source modules adhere to Zero-Egress invariants."""
    source_dirs = ["core", "gui", "plugins"]
    forbidden_imports = ["requests", "urllib.request", "aiohttp", "httpx", "socketserver", "ftplib", "smtplib"]

    py_files = []
    for s_dir in source_dirs:
        py_files.extend((ROOT / s_dir).glob("**/*.py"))

    assert len(py_files) >= 50, f"Expected at least 50 Python source files, found {len(py_files)}"

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        for forbidden in forbidden_imports:
            assert f"import {forbidden}" not in content, f"Forbidden network import '{forbidden}' found in {py_file}"
            assert f"from {forbidden}" not in content, f"Forbidden network import '{forbidden}' found in {py_file}"


def test_ci_workflow_integrity():
    """Verify GitHub Actions CI workflows exist and cover multi-platform test matrices."""
    workflow_path = ROOT / ".github" / "workflows" / "source-platform-smoke.yml"
    assert workflow_path.exists(), "CI workflow source-platform-smoke.yml must exist"
    content = workflow_path.read_text(encoding="utf-8")

    assert "ubuntu-latest" in content
    assert "macos-latest" in content
    assert "windows-latest" in content
    assert "actions/checkout@v4" in content
    assert "actions/setup-python@v5" in content
    assert "pytest" in content


def test_changelog_parity():
    """Ensure CHANGELOG.md documents version 1.0.0 and unreleased entries."""
    changelog_path = ROOT / "CHANGELOG.md"
    assert changelog_path.exists(), "CHANGELOG.md must exist"
    content = changelog_path.read_text(encoding="utf-8")

    assert "1.0.0" in content
    assert "## [Unreleased]" in content or "## [1.0.0]" in content


