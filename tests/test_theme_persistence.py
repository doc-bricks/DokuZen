import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.library.manager import LibraryManager


class ThemePersistenceTest(unittest.TestCase):
    def test_renaming_current_theme_persists_selection_after_restart(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_file = tmp_path / "state.json"
            document_path = tmp_path / "sample.pdf"
            document_path.write_bytes(b"%PDF-1.4\n")

            manager = LibraryManager(state_file)
            self.assertTrue(manager.initialize())
            self.assertTrue(manager.themes.create_theme("Arbeit"))
            self.assertTrue(manager.themes.set_current_theme("Arbeit"))
            self.assertTrue(manager.add_document(str(document_path)))
            self.assertTrue(manager.themes.rename_theme("Arbeit", "Privat"))
            self.assertTrue(manager.save())

            restarted = LibraryManager(state_file)
            self.assertTrue(restarted.initialize())

            self.assertEqual(restarted.themes.get_current_theme(), "Privat")
            self.assertEqual([doc.path for doc in restarted.get_documents()], [str(document_path.resolve())])

    def test_deleted_current_theme_falls_back_to_existing_theme_after_restart(self):
        with TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"

            manager = LibraryManager(state_file)
            self.assertTrue(manager.initialize())
            self.assertTrue(manager.themes.create_theme("Arbeit"))
            self.assertTrue(manager.themes.create_theme("Privat"))
            self.assertTrue(manager.themes.set_current_theme("Privat"))
            self.assertTrue(manager.themes.delete_theme("Privat"))
            self.assertTrue(manager.save())

            restarted = LibraryManager(state_file)
            self.assertTrue(restarted.initialize())

            current_theme = restarted.themes.get_current_theme()
            self.assertIsNotNone(current_theme)
            self.assertIn(current_theme, restarted.themes.get_theme_names())


if __name__ == "__main__":
    unittest.main()
