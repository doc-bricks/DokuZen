"""Metadata, documentation integrity, and ecosystem manifest tests for DokuZen."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_metadata():
    """Verify pyproject.toml configuration and metadata."""
    pyproject_path = ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    assert project.get("name") == "DokuZen"
    assert project.get("version") == "1.0.0"
    assert "AGPL-3.0" in project.get("license", {}).get("text", "")
    assert "PySide6>=6.5.0" in project.get("dependencies", [])

    urls = project.get("urls", {})
    assert urls.get("Homepage") == "https://github.com/doc-bricks/DokuZen"
    assert urls.get("Repository") == "https://github.com/doc-bricks/DokuZen.git"

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
    assert "PySide6" in content
    assert "PyMuPDF" in content
    assert "AGPL-3.0" in content


def test_readme_badges_and_links():
    """Validate badges and links across English and German README files."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for content in (readme_en, readme_de):
        assert "doc-bricks" in content
        assert "open-bricks" in content
        assert "AGPL-3.0" in content
        assert "llms.txt" in content
        assert "assets/banner.png" in content

    # Language switcher presence
    assert "[Deutsch](README_de.md)" in readme_en
    assert "[English](README.md)" in readme_de


def test_changelog_parity():
    """Ensure CHANGELOG.md documents version 1.0.0 and unreleased entries."""
    changelog_path = ROOT / "CHANGELOG.md"
    assert changelog_path.exists(), "CHANGELOG.md must exist"
    content = changelog_path.read_text(encoding="utf-8")

    assert "1.0.0" in content
    assert "## [Unreleased]" in content or "## [1.0.0]" in content
