import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import StartupCommand, apply_startup_command, build_startup_command, parse_cli_args


class FakeWindow:
    def __init__(self):
        self.calls = []

    def startup_import_paths(self, paths):
        self.calls.append(("import", tuple(paths)))

    def startup_open_path(self, path):
        self.calls.append(("open", path))

    def startup_ocr_path(self, path):
        self.calls.append(("ocr", path))

    def startup_redaction_path(self, path):
        self.calls.append(("redact", path))

    def startup_merge_paths(self, paths):
        self.calls.append(("merge", tuple(paths)))


class CliStartupTest(unittest.TestCase):
    def test_positional_paths_become_import_command(self):
        args = parse_cli_args(["eins.pdf", "zwei.md"])
        command = build_startup_command(args)
        self.assertEqual(command, StartupCommand("import", ("eins.pdf", "zwei.md")))

    def test_open_option_creates_open_command(self):
        args = parse_cli_args(["--open", "bericht.pdf"])
        command = build_startup_command(args)
        self.assertEqual(command, StartupCommand("open", ("bericht.pdf",)))

    def test_merge_option_keeps_all_paths(self):
        args = parse_cli_args(["--merge", "a.pdf", "b.pdf", "c.pdf"])
        command = build_startup_command(args)
        self.assertEqual(command, StartupCommand("merge", ("a.pdf", "b.pdf", "c.pdf")))

    def test_apply_startup_command_dispatches_to_window(self):
        window = FakeWindow()
        apply_startup_command(window, StartupCommand("ocr", ("scan.pdf",)))
        self.assertEqual(window.calls, [("ocr", "scan.pdf")])

    def test_apply_startup_command_rejects_unknown_actions(self):
        window = FakeWindow()
        with self.assertRaises(ValueError):
            apply_startup_command(window, StartupCommand("unknown", tuple()))


if __name__ == "__main__":
    unittest.main()
