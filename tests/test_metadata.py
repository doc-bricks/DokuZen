"""Metadata, documentation integrity, and ecosystem manifest tests for DokuZen."""

from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
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
    assert urls.get("Third-Party Licenses") == "https://github.com/doc-bricks/DokuZen/blob/main/THIRD_PARTY_LICENSES.txt"
    assert urls.get("Marketing Log") == "https://github.com/doc-bricks/DokuZen/blob/main/MARKETING-LOG.txt"
    assert urls.get("LLM Ready") == "https://github.com/doc-bricks/DokuZen/blob/main/llms.txt"

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
        "NOTICE",
        "CHANGELOG.md",
        "llms.txt",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "PRIVACY_POLICY.md",
        "SUPPORT.md",
        "STORE_LISTING.md",
        "THIRD_PARTY_LICENSES.txt",
        "THIRD_PARTY_LICENSES.md",
        "MARKETING-LOG.txt",
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
    assert any(d in content for d in ["2026-08-23", "2026-08-24", "2026-09-07", "2026-09-19", "2026-09-24"])
    assert "NOTICE" in content
    assert "PySide6" in content
    assert "PyMuPDF" in content
    assert "AGPL-3.0" in content
    assert "SECURITY.md" in content


def test_readme_badges_and_bilingual_parity():
    """Validate badges and links across English and German README files."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    with open(ROOT / "pyproject.toml", "rb") as f:
        project_version = tomllib.load(f).get("project", {}).get("version")

    for content in (readme_en, readme_de):
        assert "doc-bricks" in content
        assert "open-bricks" in content
        assert "AGPL-3.0" in content
        assert "llms.txt" in content
        assert "assets/banner.png" in content
        assert "SECURITY.md" in content
        assert "source-platform-smoke.yml" in content
        assert f"version-{project_version}-blue.svg" in content
        assert "pytest-424" in content
        assert "NOTICE" in content

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

    assert "Unterstützte Versionen" in content
    assert "Supported Versions" in content
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

    import core
    assert getattr(core, "__version__", None) == version, (
        f"core.__version__ ({getattr(core, '__version__', None)}) stimmt nicht mit pyproject.toml ({version}) ueberein"
    )

    settings_file = ROOT / "config" / "settings.json"
    if settings_file.exists():
        settings_data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert settings_data.get("version") == version, (
            f"config/settings.json ({settings_data.get('version')}) stimmt nicht mit pyproject.toml ({version}) ueberein"
        )

    linux_build = ROOT / "tools" / "build_linux_bundle.py"
    if linux_build.exists():
        content = linux_build.read_text(encoding="utf-8")
        assert f'APP_VERSION = "{version}"' in content, (
            f"tools/build_linux_bundle.py fuehrt nicht APP_VERSION = \"{version}\""
        )

    metainfo_file = ROOT / "packaging" / "linux" / "io.github.doc_bricks.DokuZen.metainfo.xml"
    if metainfo_file.exists():
        root = ET.fromstring(metainfo_file.read_text(encoding="utf-8"))
        release_versions = [rel.attrib.get("version") for rel in root.findall(".//release")]
        assert version in release_versions, (
            f"packaging/linux/io.github.doc_bricks.DokuZen.metainfo.xml enthaelt keinen release-Eintrag fuer {version}"
        )


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
    assert "concurrency:" in content
    assert "cancel-in-progress: true" in content
    assert "ruff check" in content
    assert "test_security_license_contract.py" in content


def test_changelog_parity():
    """Ensure CHANGELOG.md documents version 1.0.0 and unreleased entries."""
    changelog_path = ROOT / "CHANGELOG.md"
    assert changelog_path.exists(), "CHANGELOG.md must exist"
    content = changelog_path.read_text(encoding="utf-8")

    assert "1.0.1" in content
    assert "1.0.0" in content
    assert "## [Unreleased]" in content or "## [1.0.0]" in content


def test_quick_navigation_18_points_and_reciprocal_anchors():
    """Validate that README.md and README_de.md maintain exactly 18 navigation points and reciprocal anchors."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    expected_anchors = [
        "visual-showcase",
        "architecture",
        "lifecycle",
        "core-features",
        "target-personas",
        "comparative-matrix",
        "installation",
        "cli-entry-points",
        "ecosystem",
        "privacy-security",
        "verification-testing",
        "keyboard-shortcuts",
        "windows-store",
        "linux-bundle",
        "workspace-export",
        "audit-transparency",
        "statutory-notice",
        "license-third-party",
    ]
    assert len(expected_anchors) == 18

    for anchor in expected_anchors:
        # Check anchor target in both READMEs
        assert f'<a id="{anchor}"></a>' in readme_en, f"Missing anchor <a id=\"{anchor}\"></a> in README.md"
        assert f'<a id="{anchor}"></a>' in readme_de, f"Missing anchor <a id=\"{anchor}\"></a> in README_de.md"

        # Check navigation link in both READMEs
        assert f"(#{anchor})" in readme_en, f"Missing navigation link (#{anchor}) in README.md"
        assert f"(#{anchor})" in readme_de, f"Missing navigation link (#{anchor}) in README_de.md"


def test_personas_and_comparative_matrix_parity():
    """Verify presence of 4 target personas and 10 comparative invariants across docs."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")
    marketing = (ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")
    licenses_md = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")

    expected_personas = ["[PERSONA-01]", "[PERSONA-02]", "[PERSONA-03]", "[PERSONA-04]"]
    for persona in expected_personas:
        assert persona in readme_en, f"Missing {persona} in README.md"
        assert persona in readme_de, f"Missing {persona} in README_de.md"
        assert persona in marketing, f"Missing {persona} in MARKETING-LOG.txt"

    expected_invariants = [
        "INV-LOCAL-01",
        "INV-COST-02",
        "INV-PRIV-03",
        "INV-TOOL-04",
        "INV-OCR-05",
        "INV-PERF-06",
        "INV-PLAT-07",
        "INV-FMT-08",
        "INV-SECR-09",
        "INV-ARCH-10",
    ]
    for inv in expected_invariants:
        assert inv in readme_en, f"Missing {inv} in README.md"
        assert inv in readme_de, f"Missing {inv} in README_de.md"
        assert inv in marketing, f"Missing {inv} in MARKETING-LOG.txt"
        assert inv in licenses_md, f"Missing {inv} in THIRD_PARTY_LICENSES.md"


def test_statutory_liability_notice():
    """Verify German statutory liability limitation under § 521 BGB in READMEs."""
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    assert "521 BGB" in readme_en
    assert "521 BGB" in readme_de
    assert "Haftungsbeschränkung bei unentgeltlicher Bereitstellung" in readme_de


def test_canonical_root_notice_attribution():
    """Verify presence, copyright holder, umbrella reference, and license in root NOTICE."""
    notice_path = ROOT / "NOTICE"
    assert notice_path.exists(), "NOTICE file must exist in repo root"
    content = notice_path.read_text(encoding="utf-8")

    assert "DokuZen" in content
    assert "Lukas Geiger" in content
    assert "doc-bricks" in content
    assert "open-bricks" in content
    assert "AGPL-3.0" in content
    assert "THIRD_PARTY_LICENSES.md" in content


def test_ci_lifecycle_and_hardening_workflows():
    """Verify that CI lifecycle workflows (welcome, stale, smoke, bundle) have timeouts, permissions, and concurrency."""
    workflows_dir = ROOT / ".github" / "workflows"

    # welcome.yml
    welcome_path = workflows_dir / "welcome.yml"
    assert welcome_path.exists(), "welcome.yml must exist"
    w_content = welcome_path.read_text(encoding="utf-8")
    assert "actions/first-interaction@v3" in w_content
    assert "timeout-minutes: 5" in w_content
    assert "cancel-in-progress: true" in w_content
    assert "issues: write" in w_content
    assert "pull-requests: write" in w_content

    # stale.yml
    stale_path = workflows_dir / "stale.yml"
    assert stale_path.exists(), "stale.yml must exist"
    s_content = stale_path.read_text(encoding="utf-8")
    assert "actions/stale@v9" in s_content
    assert 'cron: "30 1 * * *"' in s_content
    assert "timeout-minutes: 10" in s_content
    assert "cancel-in-progress: true" in s_content
    assert "issues: write" in s_content
    assert "pull-requests: write" in s_content
    assert "exempt-issue-labels:" in s_content

    # source-platform-smoke.yml
    smoke_path = workflows_dir / "source-platform-smoke.yml"
    assert smoke_path.exists(), "source-platform-smoke.yml must exist"
    sm_content = smoke_path.read_text(encoding="utf-8")
    assert "permissions:" in sm_content
    assert "contents: read" in sm_content
    assert "timeout-minutes: 15" in sm_content
    assert "cancel-in-progress: true" in sm_content

    # linux-bundle.yml
    bundle_path = workflows_dir / "linux-bundle.yml"
    assert bundle_path.exists(), "linux-bundle.yml must exist"
    b_content = bundle_path.read_text(encoding="utf-8")
    assert "permissions:" in b_content
    assert "contents: read" in b_content
    assert "timeout-minutes: 15" in b_content
    assert "cancel-in-progress: true" in b_content


def test_gitignore_multi_host_and_lock_guards():
    """Ensure .gitignore protects against multi-host conflict files, canonical locks, and test caches."""
    gitignore_path = ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist"
    content = gitignore_path.read_text(encoding="utf-8")

    # Multi-host sync patterns
    assert "*-WORKSTATION*" in content
    assert "*-ASUS*" in content
    assert "*-Mac Studio*" in content
    assert "*-MacBook*" in content
    assert "*conflicted copy*" in content

    # Canonical lock system
    assert "LOCK.user.*" in content
    assert "LOCK.until.*" in content
    assert "LOCK.condition.*" in content
    assert "LOCK.permissions.json" in content
    assert ".automation-lock" in content
    assert "!package-lock.json" in content

    # Test & coverage caches
    assert ".pytest_temp/" in content
    assert ".hypothesis/" in content
    assert ".turbo/" in content


def test_pyproject_pep621_notice_and_pytest_hardening():
    """Verify pyproject.toml PEP 621 license-files, Notice URL, 20 saturated keywords, and pytest options."""
    pyproject_path = ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    license_files = project.get("license-files", [])
    assert "NOTICE" in license_files
    assert "THIRD_PARTY_LICENSES.md" in license_files

    urls = project.get("urls", {})
    assert "Notice" in urls
    assert urls["Notice"].endswith("/NOTICE")

    keywords = project.get("keywords", [])
    assert len(keywords) == 20
    assert "desktop-app" in keywords
    assert "document-processing" in keywords
    assert "local-first" in keywords
    assert "zero-egress" in keywords

    pytest_conf = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_conf.get("minversion") == "7.0"
    assert "--basetemp=.pytest_temp" in pytest_conf.get("addopts", "")
    norecursedirs = pytest_conf.get("norecursedirs", [])
    assert ".pytest_temp" in norecursedirs
    assert ".git" in norecursedirs
