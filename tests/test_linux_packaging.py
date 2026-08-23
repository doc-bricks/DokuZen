import importlib.util
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "tools" / "build_linux_bundle.py"


def _load_build_module():
    spec = importlib.util.spec_from_file_location("dokuzen_linux_build", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_linux_packaging_metadata_is_complete():
    module = _load_build_module()

    errors = module.validate_packaging_files(PROJECT_ROOT)

    assert errors == []
    desktop = (PROJECT_ROOT / "packaging/linux/dokuzen.desktop").read_text(encoding="utf-8")
    assert "Exec=dokuzen" in desktop
    assert "Icon=dokuzen" in desktop
    assert "Categories=Office;Utility;" in desktop
    metainfo = (PROJECT_ROOT / "packaging/linux/io.github.doc_bricks.DokuZen.metainfo.xml").read_text(
        encoding="utf-8"
    )
    assert "<id>io.github.doc_bricks.DokuZen</id>" in metainfo
    assert "<launchable type=\"desktop-id\">dokuzen.desktop</launchable>" in metainfo


def test_pyinstaller_command_builds_linux_onedir_with_runtime_data(tmp_path):
    module = _load_build_module()

    command = module.build_pyinstaller_command(
        PROJECT_ROOT,
        dist_dir=tmp_path / "dist",
        work_dir=tmp_path / "work",
    )

    assert command[:3] == [sys.executable, "-m", "PyInstaller"]
    assert "--onedir" in command
    assert "--windowed" in command
    assert command[command.index("--name") + 1] == "dokuzen"
    add_data_values = [command[index + 1] for index, value in enumerate(command) if value == "--add-data"]
    assert f"{PROJECT_ROOT / 'assets'}{os.pathsep}assets" in add_data_values
    assert f"{PROJECT_ROOT / 'locales'}{os.pathsep}locales" in add_data_values
    assert f"{PROJECT_ROOT / 'config'}{os.pathsep}config" in add_data_values
    assert command[-1] == str(PROJECT_ROOT / "main.py")


def test_translation_system_uses_pyinstaller_runtime_root(tmp_path, monkeypatch):
    translations_dir = tmp_path / "locales"
    translations_dir.mkdir()
    translations_file = translations_dir / "translations.json"
    translations_file.write_text('{"Hallo": {"de": "Hallo", "en": "Hello"}}', encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    from translator import TranslationSystem

    translator = TranslationSystem("en")

    assert translator.translations_file == translations_file
    assert translator.t("Hallo") == "Hello"
