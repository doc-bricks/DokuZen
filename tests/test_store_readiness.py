"""Unit and regression tests for DokuZen Windows Store release packaging.

Verifies:
- store_package.json schema, publisher CN, version parity, https URLs, 6 Tier-2 languages
- AppxManifest.xml schema, capabilities (runFullTrust), executable parity, 6 Tier-2 Resource languages
- Store tile icons (44x44, 50x50, 150x150, 310x150, 310x310) dimensions and PNG headers
- Store screenshots (1920x1080 PNG) completeness and aspect ratio
- Store readiness check gate passes with 0 findings
"""

from __future__ import annotations

import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]

from tools.check_store_readiness import (
    ACTIVE_MANIFEST_RELATIVE,
    FORBIDDEN_TRADEMARK_KEYWORDS,
    REQUIRED_DOCUMENTS,
    REQUIRED_ICONS,
    REQUIRED_RELEASE_STAGING,
    REQUIRED_SCREENSHOTS,
    check_store_repository,
    parse_keywords_from_listing,
)


class TestWindowsStoreReadiness(unittest.TestCase):

    def test_store_package_json_validity_and_parity(self):
        cfg_file = PROJECT_ROOT / "store_package.json"
        self.assertTrue(cfg_file.exists(), "store_package.json is missing")

        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        self.assertEqual(data.get("identity_name"), "Geiger.DokuZen")
        self.assertEqual(data.get("publisher"), "CN=52596601-BAB4-4F3F-B182-E8F3F273B202")
        self.assertEqual(data.get("publisher_display"), "Geiger")
        self.assertEqual(data.get("executable"), "DokuZen-Pro-1.0.0-win64.exe")
        self.assertIn("runFullTrust", data.get("capabilities", []))
        self.assertTrue(data.get("privacy_url", "").startswith("https://"))
        self.assertTrue(data.get("support_url", "").startswith("https://"))

        # Tier-2 6-Sprachen-Parität
        languages = data.get("languages", [])
        for expected in ("de-DE", "en-US", "es-ES", "zh-CN", "ja-JP", "ru-RU"):
            self.assertIn(expected, languages)
        for lang in ("de", "en", "es", "zh", "ja", "ru"):
            desc_key = f"description_{lang}"
            kw_key = f"keywords_{lang}"
            self.assertIn(desc_key, data)
            self.assertLessEqual(len(data[desc_key]), 100)
            self.assertIn(kw_key, data)
            self.assertEqual(len(data[kw_key]), 7)

    def test_appx_manifest_xml_structure_and_identity(self):
        manifest_file = PROJECT_ROOT / ACTIVE_MANIFEST_RELATIVE
        self.assertTrue(manifest_file.exists(), f"AppxManifest.xml is missing under {ACTIVE_MANIFEST_RELATIVE}")

        root = ET.fromstring(manifest_file.read_text(encoding="utf-8"))
        ns = {
            "appx": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
            "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
            "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
        }

        identity = root.find("appx:Identity", ns)
        if identity is None:
            identity = root.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity")
        self.assertIsNotNone(identity, "Identity element missing in AppxManifest.xml")
        self.assertEqual(identity.attrib.get("Name"), "Geiger.DokuZen")
        self.assertEqual(identity.attrib.get("Publisher"), "CN=52596601-BAB4-4F3F-B182-E8F3F273B202")
        self.assertEqual(identity.attrib.get("Version"), "1.0.1.0")

        caps = root.find("appx:Capabilities", ns)
        if caps is None:
            caps = root.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Capabilities")
        self.assertIsNotNone(caps, "Capabilities element missing in AppxManifest.xml")
        cap_names = [c.attrib.get("Name") for c in list(caps)]
        self.assertIn("runFullTrust", cap_names, "runFullTrust capability must be present")

        app = root.find(".//appx:Application", ns)
        if app is None:
            app = root.find(".//{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Application")
        self.assertIsNotNone(app, "Application element missing in AppxManifest.xml")
        self.assertEqual(app.attrib.get("Executable"), "DokuZen-Pro-1.0.0-win64.exe")

        props = root.find("appx:Properties", ns)
        if props is None:
            props = root.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Properties")
        self.assertIsNotNone(props, "Properties element missing in AppxManifest.xml")
        logo_el = props.find("appx:Logo", ns)
        if logo_el is None:
            logo_el = props.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Logo")
        self.assertIsNotNone(logo_el, "Logo element missing in Properties")
        self.assertIn(logo_el.text, ("icons\\StoreLogo.png", "icons/StoreLogo.png"))

        resources_el = root.find("appx:Resources", ns)
        if resources_el is None:
            resources_el = root.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Resources")
        self.assertIsNotNone(resources_el, "Resources element missing in AppxManifest.xml")
        manifest_langs = {r.attrib.get("Language") for r in list(resources_el)}
        for req_l in ("de-DE", "en-US", "es-ES", "zh-CN", "ja-JP", "ru-RU"):
            self.assertIn(req_l, manifest_langs, f"Resource Language {req_l} missing in AppxManifest.xml")

    def test_store_packaging_provenance_is_explicit_and_legacy_manifest_is_not_active(self):
        legacy_manifest = PROJECT_ROOT / "store_package" / "DokuZen Pro" / "AppxManifest.xml"
        if legacy_manifest.exists():
            root = ET.fromstring(legacy_manifest.read_text(encoding="utf-8"))
            identity = root.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity")
            if identity is not None:
                self.assertNotEqual(
                    identity.attrib.get("Version"),
                    "1.0.1.0",
                    "Legacy manifest should not collide with active 1.0.1.0 package identity",
                )

    def test_release_staging_materials_completeness(self):
        staging_dir = PROJECT_ROOT / "releases" / "windowsstore"
        self.assertTrue(staging_dir.exists(), "releases/windowsstore directory missing")

        for fname in REQUIRED_RELEASE_STAGING:
            fpath = staging_dir / fname
            self.assertTrue(fpath.exists(), f"Missing staging file {fname}")
            self.assertGreater(fpath.stat().st_size, 0, f"Staging file {fname} is empty")

        store_logo = staging_dir / "StoreLogo.png"
        with Image.open(store_logo) as img:
            self.assertEqual(img.size, (50, 50), "StoreLogo.png in staging must be 50x50")

        staging_screenshots = staging_dir / "screenshots"
        self.assertTrue(staging_screenshots.exists(), "screenshots/ directory missing in staging")
        for ss_name in REQUIRED_SCREENSHOTS:
            ss_file = staging_screenshots / ss_name
            self.assertTrue(ss_file.exists(), f"Staging screenshot {ss_name} missing")
            with Image.open(ss_file) as img:
                self.assertEqual(img.size, (1920, 1080), f"Staging screenshot {ss_name} must be 1920x1080")

    def test_store_tile_icons_exist_and_have_correct_dimensions(self):
        icon_dir = PROJECT_ROOT / "store_package" / "DokuZen" / "icons"
        if not icon_dir.exists():
            icon_dir = PROJECT_ROOT / "assets" / "icons"
        self.assertTrue(icon_dir.exists(), "Icons directory missing")

        for icon_name, (expected_w, expected_h) in REQUIRED_ICONS.items():
            icon_file = icon_dir / icon_name
            self.assertTrue(icon_file.exists(), f"Store icon {icon_name} is missing")

            with Image.open(icon_file) as img:
                self.assertEqual(img.format, "PNG", f"{icon_name} must be PNG")
                self.assertEqual(img.size, (expected_w, expected_h), f"{icon_name} dimension mismatch")

    def test_store_screenshots_exist_and_have_1080p_resolution(self):
        screenshot_dir = PROJECT_ROOT / "screenshots" / "store"
        self.assertTrue(screenshot_dir.exists(), "screenshots/store directory is missing")

        for ss_name in REQUIRED_SCREENSHOTS:
            ss_file = screenshot_dir / ss_name
            self.assertTrue(ss_file.exists(), f"Store screenshot {ss_name} is missing")

            with Image.open(ss_file) as img:
                self.assertEqual(img.format, "PNG", f"{ss_name} must be PNG")
                w, h = img.size
                self.assertGreaterEqual(w, 1366, f"{ss_name} width is too small")
                self.assertGreaterEqual(h, 768, f"{ss_name} height is too small")
                self.assertEqual((w, h), (1920, 1080), f"{ss_name} expected 1920x1080")

    def test_store_readiness_script_gate_passes(self):
        findings = check_store_repository(PROJECT_ROOT)
        self.assertEqual(findings, [], f"check_store_repository reported findings: {findings}")

    def test_store_legal_and_support_documents_completeness(self):
        for doc_name in REQUIRED_DOCUMENTS:
            doc_file = PROJECT_ROOT / doc_name
            self.assertTrue(doc_file.exists(), f"Mandatory document {doc_name} is missing")
            content = doc_file.read_text(encoding="utf-8")
            self.assertGreater(len(content.strip()), 100, f"{doc_name} is too short")

    def test_store_listing_policy_10_1_3_keywords(self):
        listing_file = PROJECT_ROOT / "STORE_LISTING.md"
        self.assertTrue(listing_file.exists(), "STORE_LISTING.md is missing")
        content = listing_file.read_text(encoding="utf-8")

        keywords = parse_keywords_from_listing(content)
        for lang in ("de", "en", "es", "zh", "ja", "ru"):
            self.assertIn(lang, keywords, f"Keywords missing for language {lang}")
            kw_list = keywords[lang]
            self.assertGreaterEqual(len(kw_list), 1, f"At least 1 keyword required for {lang}")
            self.assertLessEqual(len(kw_list), 7, f"Partner Center Policy 10.1.3 allows max 7 keywords, found {len(kw_list)} for {lang}")
            for kw in kw_list:
                kw_lower = kw.lower()
                for forbidden in FORBIDDEN_TRADEMARK_KEYWORDS:
                    self.assertNotIn(
                        f" {forbidden} ",
                        f" {kw_lower} ",
                        f"Keyword {kw!r} contains prohibited trademark {forbidden!r}",
                    )

    def test_msix_release_bundle_structure_and_checksum(self):
        msix_file = PROJECT_ROOT / "releases" / "windowsstore" / "v1.0.1" / "DokuZen-1.0.1.0.msix"
        if not msix_file.exists():
            self.skipTest(f"MSIX package not built locally in working tree ({msix_file})")
        self.assertGreater(msix_file.stat().st_size, 50_000_000, "MSIX bundle size suspiciously small")

        # Verify ZIP/Appx internal structure
        with zipfile.ZipFile(msix_file, "r") as zf:
            names = set(zf.namelist())
            self.assertIn("AppxManifest.xml", names)
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("AppxBlockMap.xml", names)

            # Check manifest identity inside MSIX
            manifest_data = zf.read("AppxManifest.xml")
            root = ET.fromstring(manifest_data)
            identity = root.find("{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity")
            self.assertIsNotNone(identity)
            self.assertEqual(identity.attrib.get("Name"), "Geiger.DokuZen")
            self.assertEqual(identity.attrib.get("Publisher"), "CN=52596601-BAB4-4F3F-B182-E8F3F273B202")
            self.assertEqual(identity.attrib.get("Version"), "1.0.1.0")

        # Verify SHA256 checksum against SHA256SUMS.txt
        sums_file = msix_file.parent / "SHA256SUMS.txt"
        self.assertTrue(sums_file.exists(), "SHA256SUMS.txt is missing next to MSIX package")
        expected_hash = None
        for line in sums_file.read_text(encoding="utf-8").splitlines():
            if msix_file.name in line:
                expected_hash = line.split()[0].strip().lower()
                break
        self.assertIsNotNone(expected_hash, f"Hash for {msix_file.name} not found in SHA256SUMS.txt")
        actual_hash = hashlib.sha256(msix_file.read_bytes()).hexdigest().lower()
        self.assertEqual(actual_hash, expected_hash, "MSIX SHA256 checksum mismatch")


if __name__ == "__main__":
    unittest.main()
