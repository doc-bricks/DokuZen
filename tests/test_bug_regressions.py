"""Regressionstests — bugfix-library-transfer 2026-06-21."""
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
PDF_PAGES = ROOT / "gui" / "dialogs" / "pdf_pages_dialog.py"
SQLITE_VIEWER = ROOT / "gui" / "dialogs" / "sqlite_viewer_dialog.py"
MAIN_WINDOW = ROOT / "gui" / "main_window.py"
GLOBAL_SEARCH = ROOT / "gui" / "widgets" / "global_search_bar.py"
PREVIEW_PANEL = ROOT / "gui" / "panels" / "preview_panel.py"
PYINSTALLER_DLG = ROOT / "gui" / "dialogs" / "pyinstaller_dialog.py"
FORMS_BUILDER = ROOT / "core" / "forms" / "builder.py"
IMAGE_TOOLS = ROOT / "core" / "converter" / "image_tools.py"


class TestD1NoQMenuBare(unittest.TestCase):
    """BUG-D1: QMenu() ohne Parent-Argument — GC-Risiko."""

    def _count_bare_qmenu(self, path: Path):
        src = path.read_text(encoding="utf-8")
        occurrences = []
        start = 0
        while True:
            idx = src.find("QMenu()", start)
            if idx == -1:
                break
            line_no = src[:idx].count("\n") + 1
            occurrences.append(line_no)
            start = idx + 1
        return occurrences

    def test_pdf_pages_dialog_no_bare_qmenu(self):
        hits = self._count_bare_qmenu(PDF_PAGES)
        self.assertEqual(hits, [], f"QMenu() ohne Parent in pdf_pages_dialog.py, Zeilen: {hits} — BUG-D1")

    def test_sqlite_viewer_no_bare_qmenu(self):
        hits = self._count_bare_qmenu(SQLITE_VIEWER)
        self.assertEqual(hits, [], f"QMenu() ohne Parent in sqlite_viewer_dialog.py, Zeilen: {hits} — BUG-D1")


class TestD3SubprocessTimeouts(unittest.TestCase):
    """BUG-D3: subprocess.run ohne timeout= — GUI hängt bei blockiertem Kindprozess."""

    def _assert_timeout_after(self, path: Path, cmd_snippet: str, window: int = 200):
        src = path.read_text(encoding="utf-8")
        idx = src.find(cmd_snippet)
        self.assertGreater(idx, 0, f'"{cmd_snippet}" nicht in {path.name} gefunden')
        snippet = src[idx:idx + window]
        self.assertIn("timeout", snippet,
                      f'subprocess.run mit "{cmd_snippet}" ohne timeout= in {path.name} — BUG-D3')

    def test_main_window_open_has_timeout(self):
        self._assert_timeout_after(MAIN_WINDOW, '"open", doc_path')

    def test_main_window_xdg_open_has_timeout(self):
        self._assert_timeout_after(MAIN_WINDOW, '"xdg-open", doc_path')

    def test_global_search_open_has_timeout(self):
        self._assert_timeout_after(GLOBAL_SEARCH, '"open", path')

    def test_global_search_xdg_open_has_timeout(self):
        self._assert_timeout_after(GLOBAL_SEARCH, '"xdg-open", path')

    def test_preview_panel_open_has_timeout(self):
        self._assert_timeout_after(PREVIEW_PANEL, '"open", self._current_path')

    def test_preview_panel_xdg_open_has_timeout(self):
        self._assert_timeout_after(PREVIEW_PANEL, '"xdg-open", self._current_path')

    def test_pyinstaller_dialog_version_check_has_timeout(self):
        self._assert_timeout_after(PYINSTALLER_DLG, '"PyInstaller", "--version"')


class TestU2FormsBuilderJsonLoad(unittest.TestCase):
    """BUG-U2: json.load ohne JSONDecodeError-Handler in core/forms/builder.py."""

    def test_load_has_json_error_handler(self):
        src = FORMS_BUILDER.read_text(encoding="utf-8")
        idx = src.find("def load(")
        self.assertGreater(idx, 0, "def load() nicht in builder.py gefunden")
        snippet = src[idx:idx + 300]
        self.assertIn("JSONDecodeError", snippet,
                      "FormTemplate.load(): json.load ohne JSONDecodeError-Handler — BUG-U2")


class TestU3ImageToolsEncoding(unittest.TestCase):
    """BUG-U3: open() ohne encoding= bei site.webmanifest-Schreiben in image_tools.py."""

    def test_manifest_open_has_encoding(self):
        src = IMAGE_TOOLS.read_text(encoding="utf-8")
        idx = src.find("site.webmanifest")
        self.assertGreater(idx, 0, '"site.webmanifest" nicht in image_tools.py gefunden')
        snippet = src[idx:idx + 200]
        self.assertIn("encoding", snippet,
                      "open(manifest_path, 'w') ohne encoding= in image_tools.py — BUG-U3")


if __name__ == "__main__":
    unittest.main()
