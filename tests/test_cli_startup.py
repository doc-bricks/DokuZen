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

    def startup_annotate_path(self, path):
        self.calls.append(("annotate", path))

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

    def test_annotate_option_creates_annotate_command(self):
        args = parse_cli_args(["--annotate", "kommentar.pdf"])
        command = build_startup_command(args)
        self.assertEqual(command, StartupCommand("annotate", ("kommentar.pdf",)))

    def test_merge_option_keeps_all_paths(self):
        args = parse_cli_args(["--merge", "a.pdf", "b.pdf", "c.pdf"])
        command = build_startup_command(args)
        self.assertEqual(command, StartupCommand("merge", ("a.pdf", "b.pdf", "c.pdf")))

    def test_apply_startup_command_dispatches_to_window(self):
        window = FakeWindow()
        apply_startup_command(window, StartupCommand("ocr", ("scan.pdf",)))
        self.assertEqual(window.calls, [("ocr", "scan.pdf")])
        apply_startup_command(window, StartupCommand("annotate", ("annot.pdf",)))
        self.assertEqual(window.calls[-1], ("annotate", "annot.pdf"))

    def test_apply_startup_command_rejects_unknown_actions(self):
        window = FakeWindow()
        with self.assertRaises(ValueError):
            apply_startup_command(window, StartupCommand("unknown", tuple()))

    def test_cli_version_flag_exits_with_version_string(self):
        import io
        from contextlib import redirect_stdout
        from core import __version__

        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                parse_cli_args(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(f"DokuZen {__version__}", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
