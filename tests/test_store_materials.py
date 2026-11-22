"""
Tests für Windows-Store-Artefakte.
Prüft Vollständigkeit und Konsistenz der Store-Metadaten.
"""
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestStoreMaterials(unittest.TestCase):

    def test_store_package_json_exists_and_is_valid(self):
        path = PROJECT_ROOT / "store_package.json"
        self.assertTrue(path.exists(), "store_package.json fehlt")
        data = json.loads(path.read_text(encoding="utf-8"))
        required = [
            "app_name", "publisher", "publisher_display", "identity_name",
            "version", "description", "executable", "capabilities",
            "category", "age_rating", "privacy_url", "support_url", "license",
        ]
        for field in required:
            self.assertIn(field, data, f"Pflichtfeld '{field}' fehlt in store_package.json")

    def test_store_package_publisher_matches_expected(self):
        path = PROJECT_ROOT / "store_package.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        expected_cn = "CN=52596601-BAB4-4F3F-B182-E8F3F273B202"
        self.assertEqual(
            data["publisher"], expected_cn,
            "publisher CN stimmt nicht mit Partner-Center-Konto überein",
        )

    def test_store_package_executable_matches_build(self):
        path = PROJECT_ROOT / "store_package.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["executable"], "DokuZen-Pro-1.0.0-win64.exe",
            "executable in store_package.json stimmt nicht mit build_exe.bat überein",
        )

    def test_privacy_policy_exists_and_nonempty(self):
        path = PROJECT_ROOT / "PRIVACY_POLICY.md"
        self.assertTrue(path.exists(), "PRIVACY_POLICY.md fehlt")
        content = path.read_text(encoding="utf-8")
        self.assertGreater(len(content.strip()), 100, "PRIVACY_POLICY.md ist zu kurz / leer")

    def test_support_md_exists_and_nonempty(self):
        path = PROJECT_ROOT / "SUPPORT.md"
        self.assertTrue(path.exists(), "SUPPORT.md fehlt")
        content = path.read_text(encoding="utf-8")
        self.assertGreater(len(content.strip()), 100, "SUPPORT.md ist zu kurz / leer")

    def test_store_listing_exists_and_contains_six_tier2_languages(self):
        path = PROJECT_ROOT / "STORE_LISTING.md"
        self.assertTrue(path.exists(), "STORE_LISTING.md fehlt")
        content = path.read_text(encoding="utf-8")
        for heading in ("## Deutsch", "## English", "## Español", "## 简体中文", "## 日本語", "## Русский"):
            self.assertIn(heading, content, f"STORE_LISTING.md fehlt Abschnitt: {heading}")

    def test_store_package_json_has_six_tier2_languages(self):
        path = PROJECT_ROOT / "store_package.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        langs = data.get("languages", [])
        for expected in ("de-DE", "en-US", "es-ES", "zh-CN", "ja-JP", "ru-RU"):
            self.assertIn(expected, langs, f"Zielsprache {expected} fehlt in store_package.json")
        for lang_code in ("de", "en", "es", "zh", "ja", "ru"):
            desc_key = f"description_{lang_code}"
            kw_key = f"keywords_{lang_code}"
            self.assertIn(desc_key, data, f"Kurzbeschreibung {desc_key} fehlt")
            self.assertLessEqual(len(data[desc_key]), 100, f"{desc_key} überschreitet 100 Zeichen Limit")
            self.assertIn(kw_key, data, f"Keywords {kw_key} fehlen")
            self.assertEqual(len(data[kw_key]), 7, f"{kw_key} muss exakt 7 Keywords deklarieren")

    def test_store_staging_files_exist_for_all_six_languages(self):
        staging_dir = PROJECT_ROOT / "releases" / "windowsstore"
        for lang_code in ("de", "en", "es", "zh", "ja", "ru"):
            listing_file = staging_dir / f"store_listing_{lang_code}.md"
            self.assertTrue(listing_file.exists(), f"Staging-Datei {listing_file.name} fehlt")
            self.assertGreater(listing_file.stat().st_size, 50, f"Staging-Datei {listing_file.name} ist zu kurz")


if __name__ == "__main__":
    unittest.main()
