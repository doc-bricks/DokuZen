# -*- coding: utf-8 -*-
"""Regressionstests — DokuZen Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 32, PARTIAL Block 4a = gui/-Shell).

shortcuts/theme sind ohne laufende QApplication importierbar -> echte Tests. Rest statisch
(red-on-revert via B4A_SRC -> PRE-Backup-block4a).

  BUG-32 shortcuts (HIGH): deepcopy der DEFAULT_SHORTCUTS -> keine Cross-Instance-Pollution,
        reset_to_defaults stellt wieder her.
  BUG-32 theme_manager: from_dict ohne KeyError (.get) + save_theme atomar (tmp+os.replace).
  BUG-32 main_window: closeEvent stoppt _auto_save_timer.
  BUG-32 panels: QActions ans Menü geparentet (kein QAction-Leak).
"""
import os
import sys
from pathlib import Path

import pytest

_PROJ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(_PROJ))

_SRC = Path(os.environ.get("B4A_SRC", _PROJ))


def read(rel):
    return (_SRC / rel).read_text(encoding="utf-8")


# --- echte Tests ---
def test_bug32_shortcuts_no_cross_instance_pollution():
    from gui.utils.shortcuts import ShortcutManager
    m1 = ShortcutManager()
    default = m1.get_shortcut("nav.next_page")  # "PgDown"
    assert default is not None
    m1.set_shortcut("nav.next_page", "Ctrl+Shift+F12")
    # frische Instanz darf NICHT mit-mutiert sein (vor Fix: shallow dict -> geteiltes Objekt -> mutiert)
    m2 = ShortcutManager()
    assert m2.get_shortcut("nav.next_page") == default, "Cross-Instance-Pollution (shallow copy)"


def test_bug32_shortcuts_reset_restores():
    from gui.utils.shortcuts import ShortcutManager
    m = ShortcutManager()
    default = m.get_shortcut("nav.goto_page")  # "Ctrl+G"
    m.set_shortcut("nav.goto_page", "Ctrl+Shift+F11")
    assert m.get_shortcut("nav.goto_page") == "Ctrl+Shift+F11"
    m.reset_to_defaults()
    # vor Fix: reset zeigt wieder auf mutiertes geteiltes Objekt -> wirkungslos
    assert m.get_shortcut("nav.goto_page") == default, "reset_to_defaults wirkungslos"


def test_bug32_theme_from_dict_no_keyerror():
    from gui.utils.theme_manager import Theme
    t = Theme.from_dict({})  # vor Fix: KeyError('name')
    assert t.name == ""


# --- statische Assertions (red-on-revert via B4A_SRC -> PRE) ---
def test_bug32_static_shortcuts_deepcopy():
    src = read("gui/utils/shortcuts.py")
    assert "copy.deepcopy(self.DEFAULT_SHORTCUTS)" in src, "BUG-32 deepcopy fehlt"
    assert "import copy" in src, "BUG-32 import copy fehlt"


def test_bug32_static_theme_atomic_and_get():
    src = read("gui/utils/theme_manager.py")
    assert "os.replace(tmp_path, filepath)" in src, "BUG-32 save_theme atomar fehlt"
    assert 'data.get("name", "")' in src, "BUG-32 from_dict .get fehlt"
    # from_dict gibt jetzt name="" statt KeyError -> _load_custom_themes muss Phantom-Theme abfangen
    assert "if not theme.name:" in src, "BUG-32 Phantom-Theme-Guard in _load_custom_themes fehlt"


def test_bug32_static_closeevent_timer_stop():
    src = read("gui/main_window.py")
    assert "self._auto_save_timer.stop()" in src, "BUG-32 closeEvent Timer-Stop fehlt"


def test_bug32_static_qaction_parented_to_menu():
    dl = read("gui/panels/document_list.py")
    assert 'QAction("Öffnen", menu)' in dl, "BUG-32 document_list QAction nicht ans Menü geparentet"
    assert 'QAction("Öffnen", self)' not in dl, "BUG-32 alter QAction(...,self) noch da"
    assert "menu.deleteLater()" in dl, "BUG-32 document_list menu.deleteLater() fehlt (Menü leakt sonst weiter)"
    lp = read("gui/panels/library_panel.py")
    assert 'QAction("Umbenennen...", menu)' in lp, "BUG-32 library_panel QAction nicht ans Menü geparentet"
    assert "menu.deleteLater()" in lp, "BUG-32 library_panel menu.deleteLater() fehlt"


def test_bug32_review_notiz_search_threading():
    src = read("gui/widgets/global_search_bar.py")
    assert "BUGSWEEP-32 REVIEW-NOTIZ" in src, "Suggest/Threading Review-Notiz fehlt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
