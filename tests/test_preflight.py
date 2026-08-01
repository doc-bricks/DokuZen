import importlib.util
import unittest
from unittest import mock

from tools import preflight


class TestPreflight(unittest.TestCase):
    def test_required_runtime_missing_blocks_default(self):
        checks = [
            preflight.Check(
                name="PySide6",
                kind="required-runtime",
                target="PySide6",
                required_for="Desktop GUI",
                ok=False,
            )
        ]
        self.assertEqual(
            preflight.failing_checks(checks, strict_build=False, require_ocr=False),
            checks,
        )

    def test_optional_and_external_missing_are_degradations_by_default(self):
        checks = [
            preflight.Check(
                name="rapidfuzz",
                kind="optional-runtime",
                target="rapidfuzz",
                required_for="optional feature",
                ok=False,
                degradation="reduced matching",
            ),
            preflight.Check(
                name="tesseract",
                kind="external-tool",
                target="tesseract",
                required_for="OCR",
                ok=False,
                degradation="OCR unavailable",
            ),
        ]
        self.assertEqual(
            preflight.failing_checks(checks, strict_build=False, require_ocr=False),
            [],
        )

    def test_strict_build_blocks_missing_pyinstaller(self):
        check = preflight.Check(
            name="PyInstaller",
            kind="build-tool",
            target="PyInstaller",
            required_for="Windows build",
            ok=False,
        )
        self.assertEqual(
            preflight.failing_checks([check], strict_build=True, require_ocr=False),
            [check],
        )

    def test_require_ocr_blocks_missing_tesseract(self):
        check = preflight.Check(
            name="tesseract",
            kind="external-tool",
            target="tesseract",
            required_for="OCR",
            ok=False,
        )
        self.assertEqual(
            preflight.failing_checks([check], strict_build=False, require_ocr=True),
            [check],
        )

    def test_collect_checks_uses_importlib_and_path_lookup(self):
        def fake_find_spec(name):
            return object() if name == "PySide6" else None

        with mock.patch.object(importlib.util, "find_spec", side_effect=fake_find_spec):
            with mock.patch.object(preflight.shutil, "which", return_value=None):
                checks = preflight.collect_checks()

        by_name = {check.name: check for check in checks}
        self.assertTrue(by_name["PySide6"].ok)
        self.assertFalse(by_name["tesseract"].ok)


if __name__ == "__main__":
    unittest.main()
