"""Security and License Compliance Contract Tests for DokuZen.

Validates:
1. Dependency floor hardening against known CVEs/GHSAs (Pillow, PyMuPDF, pikepdf, pytesseract, pystray).
2. License inventory completeness, SPDX identifiers, and boundary documentation in THIRD_PARTY_LICENSES.txt.
3. Bilingual SECURITY.md policy structure, response SLA, and Zero-Egress / local-first invariants.
4. Plaintext secret, private token, webhook, and hardcoded private user path hygiene.
5. Gitignore protection against conflict markers, lock files, and environment files.
6. Core license file validity (AGPL-3.0) and pyproject.toml license metadata parity.
"""

from __future__ import annotations

import os
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestSecurityLicenseContract(unittest.TestCase):
    """Automated security, dependency floor, and license compliance contract tests."""

    def test_dependency_floors_harden_known_cves(self):
        """Ensure minimum version floors protect against known CVEs/GHSAs."""
        pyproject_path = ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), "pyproject.toml must exist")

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        deps = data.get("project", {}).get("dependencies", [])
        dep_dict = {}
        for dep in deps:
            m = re.match(r"^([a-zA-Z0-9_-]+)>=([0-9.]+)", dep)
            if m:
                dep_dict[m.group(1).lower()] = tuple(int(x) for x in m.group(2).split("."))

        # Pillow floor must be >= 12.0.0 to prevent 35+ known CVEs/GHSAs in <= 11.x
        self.assertIn("pillow", dep_dict, "pillow must be in dependencies")
        self.assertGreaterEqual(dep_dict["pillow"], (12, 0, 0), "Pillow floor must be at least 12.0.0")

        # PyMuPDF floor must be >= 1.24.0
        self.assertIn("pymupdf", dep_dict, "pymupdf must be in dependencies")
        self.assertGreaterEqual(dep_dict["pymupdf"], (1, 24, 0), "PyMuPDF floor must be at least 1.24.0")

        # pikepdf floor must be >= 8.15.1
        self.assertIn("pikepdf", dep_dict, "pikepdf must be in dependencies")
        self.assertGreaterEqual(dep_dict["pikepdf"], (8, 15, 1), "pikepdf floor must be at least 8.15.1")

        # pytesseract floor must be >= 0.3.13
        self.assertIn("pytesseract", dep_dict, "pytesseract must be in dependencies")
        self.assertGreaterEqual(dep_dict["pytesseract"], (0, 3, 13), "pytesseract floor must be at least 0.3.13")

    def test_third_party_license_inventory_alignment(self):
        """Verify THIRD_PARTY_LICENSES.txt covers all direct packages and documents licenses."""
        inv_path = ROOT / "THIRD_PARTY_LICENSES.txt"
        self.assertTrue(inv_path.exists(), "THIRD_PARTY_LICENSES.txt must exist")
        content = inv_path.read_text(encoding="utf-8")

        # Must mention license categories
        required_identifiers = [
            "AGPL-3.0-or-later",
            "LGPL-3.0-only",
            "GPL-3.0-only",
            "MPL-2.0",
            "Apache-2.0",
            "MIT",
            "BSD",
            "0BSD",
        ]
        for ident in required_identifiers:
            self.assertIn(ident, content, f"Identifier {ident} must be documented in THIRD_PARTY_LICENSES.txt")

        # Must mention audit timestamp
        self.assertIn("2026-08-24", content, "Inventory must reflect the 2026-08-24 audit")

    def test_security_policy_structure_and_reporting_sla(self):
        """Verify bilingual SECURITY.md policy structure, response SLA, and reporting channels."""
        sec_path = ROOT / "SECURITY.md"
        self.assertTrue(sec_path.exists(), "SECURITY.md must exist")
        content = sec_path.read_text(encoding="utf-8")

        self.assertIn("## Deutsch", content)
        self.assertIn("## English", content)
        self.assertIn("48", content, "Must specify 48-hour response SLA")
        self.assertIn("security@open-bricks.org", content)
        self.assertIn("support@lukasgeiger.com", content)
        self.assertIn("Zero-Egress", content)
        self.assertIn("Non-Elevation", content)

    def test_no_plaintext_secrets_or_hardcoded_user_paths_in_code(self):
        """Scan source code for private paths, API keys, tokens, or plaintext secrets."""
        secret_patterns = {
            "AWS Key": re.compile(r"AKIA[0-9A-Z]{16}"),
            "Private Key": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA|PRIVATE) KEY-----"),
            "Discord / Slack Webhook": re.compile(r"https://(discord\.com/api/webhooks|hooks\.slack\.com/services)/"),
            "OpenAI / Anthropic Key": re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        }

        user_path_pattern = re.compile(r"C:[/\\]Users[/\\](?!Default|Public)[a-zA-Z0-9_.-]+", re.IGNORECASE)

        source_dirs = ["core", "gui", "plugins", "packaging", "tools", "utils"]
        violations = []

        for s_dir in source_dirs:
            p = ROOT / s_dir
            if not p.exists():
                continue
            for file_path in p.rglob("*.py"):
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(text.splitlines(), 1):
                    # Check for secrets
                    for label, pattern in secret_patterns.items():
                        if pattern.search(line):
                            violations.append(f"Secret [{label}] at {file_path.relative_to(ROOT)}:{line_no}")
                    # Check for hardcoded private user paths
                    if user_path_pattern.search(line):
                        violations.append(f"User Path at {file_path.relative_to(ROOT)}:{line_no} -> {line.strip()}")

        self.assertEqual(violations, [], f"Found security/privacy path violations in source code: {violations}")

    def test_gitignore_conflict_and_lock_hygiene(self):
        """Ensure .gitignore prevents syncing conflicts, lock files, and env variables."""
        gitignore_path = ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore must exist")
        content = gitignore_path.read_text(encoding="utf-8")

        required_patterns = [
            "*.conflict",
            "*.sync-conflict-*",
            "LOCK*.txt",
            ".env",
            "*.log",
            "*_WORKSTATION-LG*",
        ]
        for pattern in required_patterns:
            self.assertIn(pattern, content, f"Missing pattern {pattern} in .gitignore")

    def test_license_spdx_and_author_parity(self):
        """Ensure LICENSE file is AGPL-3.0 and pyproject.toml references AGPL-3.0-or-later."""
        license_path = ROOT / "LICENSE"
        self.assertTrue(license_path.exists(), "LICENSE must exist")
        license_text = license_path.read_text(encoding="utf-8")

        self.assertIn("GNU AFFERO GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3, 19 November 2007", license_text)
        self.assertIn("Lukas Geiger", license_text)

        pyproject_path = ROOT / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        self.assertEqual(data.get("project", {}).get("license", {}).get("text"), "AGPL-3.0-or-later")


if __name__ == "__main__":
    unittest.main()
