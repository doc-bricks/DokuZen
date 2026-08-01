import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


class TestThirdPartyLicenses(unittest.TestCase):
    def test_inventory_exists_and_covers_direct_requirements(self):
        inventory = PROJECT_ROOT / "THIRD_PARTY_LICENSES.txt"
        self.assertTrue(inventory.exists(), "THIRD_PARTY_LICENSES.txt fehlt")
        content = inventory.read_text(encoding="utf-8")
        normalized_content = _normalize_package_name(content)

        requirements = PROJECT_ROOT / "requirements.txt"
        direct_packages = []
        for raw_line in requirements.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            package = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip()
            if package:
                direct_packages.append(package)

        self.assertGreater(len(direct_packages), 5)
        for package in direct_packages:
            with self.subTest(package=package):
                self.assertIn(_normalize_package_name(package), normalized_content)

    def test_inventory_documents_license_boundaries(self):
        content = (PROJECT_ROOT / "THIRD_PARTY_LICENSES.txt").read_text(
            encoding="utf-8"
        )
        required_fragments = [
            "AGPL-3.0",
            "GPL-3.0-only",
            "LGPL-3.0-only",
            "MPL-2.0",
            "not a frozen transitive SBOM",
            "PyMuPDF/Artifex",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, content)

    def test_inventory_is_not_global_environment_dump(self):
        content = (PROJECT_ROOT / "THIRD_PARTY_LICENSES.txt").read_text(
            encoding="utf-8"
        )
        forbidden_fragments = [
            "1822 Pakete",
            "globales Python",
            "site-packages",
            "C:\\Users\\",
        ]
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, content)


if __name__ == "__main__":
    unittest.main()
