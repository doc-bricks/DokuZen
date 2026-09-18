#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für die GUI-Aktion 'Arbeitsbereich exportieren' im Hauptfenster.
"""

from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

from gui.main_window import MainWindow
from core.library.manager import LibraryManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def clean_qsettings():
    settings = QSettings("Geiger", "DokuZen")
    old_geom = settings.value("geometry")
    yield settings
    if old_geom:
        settings.setValue("geometry", old_geom)
    else:
        settings.remove("geometry")


def test_main_window_has_export_workspace_action(qapp, tmp_path):
    """Prüft, dass die Aktion im Menü vorhanden und korrekt konfiguriert ist."""
    lib = LibraryManager(state_file=tmp_path / "state.json")
    win = MainWindow(lib)
    try:
        assert hasattr(win, "_action_export_workspace")
        assert win._action_export_workspace in win._menu_file.actions()
        assert win._action_export_workspace.shortcut().toString() == "Ctrl+Shift+E"
    finally:
        win.close()


def test_main_window_export_workspace_flow(qapp, tmp_path):
    """Testet den headless Export über _on_export_workspace()."""
    lib = LibraryManager(state_file=tmp_path / "state.json")
    win = MainWindow(lib)
    target_json = tmp_path / "exported_workspace.json"

    try:
        with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(target_json), "JSON (*.json)")):
            win._on_export_workspace()

        assert target_json.exists()
        content = target_json.read_text(encoding="utf-8")
        assert "dokuzen-workspace-v1" in content
    finally:
        win.close()


def test_main_window_geometry_persistence(qapp, tmp_path, clean_qsettings):
    """Testet, dass die Fenstergeometrie gespeichert und wiederhergestellt wird."""
    lib = LibraryManager(state_file=tmp_path / "state.json")
    win = MainWindow(lib)
    try:
        win.resize(1150, 750)
        saved_geom = win.saveGeometry()
        clean_qsettings.setValue("geometry", saved_geom)

        win2 = MainWindow(lib)
        try:
            assert win2.width() == 1150
            assert win2.height() == 750
        finally:
            win2.close()
    finally:
        win.close()
