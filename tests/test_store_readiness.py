"""Unit and regression tests for DokuZen Windows Store release packaging.

Verifies:
- store_package.json schema, publisher CN, version parity, https URLs
- AppxManifest.xml schema, capabilities (runFullTrust), executable parity
- Store tile icons (44x44, 50x50, 150x150, 310x150, 310x310) dimensions and PNG headers
- Store screenshots (1920x1080 PNG) completeness and aspect ratio
- Store readiness check gate passes with 0 findings
"""

from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]

from tools.check_store_readiness import (
    REQUIRED_DOCUMENTS,
    REQUIRED_ICONS,
    REQUIRED_SCREENSHOTS,
    check_store_repository,
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

    def test_appx_manifest_xml_structure_and_identity(self):
        manifest_file = PROJECT_ROOT / "store_package" / "DokuZen" / "AppxManifest.xml"
        self.assertTrue(manifest_file.exists(), "AppxManifest.xml is missing under store_package/DokuZen/")

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

    def test_store_tile_icons_exist_and_have_correct_dimensions(self):
        icon_dir = PROJECT_ROOT / "store_package" / "DokuZen" / "icons"
        self.assertTrue(icon_dir.exists(), "store_package/DokuZen/icons directory is missing")

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


if __name__ == "__main__":
    unittest.main()
