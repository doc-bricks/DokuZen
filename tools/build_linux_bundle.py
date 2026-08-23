#!/usr/bin/env python3
"""Build and validate the portable DokuZen Linux tarball."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path


APP_NAME = "dokuzen"
APP_VERSION = "1.0.0"
APPSTREAM_ID = "io.github.doc_bricks.DokuZen"


def validate_packaging_files(project_root: Path) -> list[str]:
    """Return packaging contract errors without mutating the checkout."""

    required = (
        "main.py",
        "LICENSE",
        "README.md",
        "README_de.md",
        "assets/icon.png",
        "assets/dokuzen.ico",
        "locales/translations.json",
        "config/settings.json",
        "packaging/linux/dokuzen.desktop",
        f"packaging/linux/{APPSTREAM_ID}.metainfo.xml",
        "packaging/linux/README.md",
    )
    errors = [f"missing: {relative}" for relative in required if not (project_root / relative).is_file()]

    desktop_path = project_root / "packaging/linux/dokuzen.desktop"
    if desktop_path.is_file():
        desktop = desktop_path.read_text(encoding="utf-8")
        for entry in ("[Desktop Entry]", "Type=Application", "Exec=dokuzen", "Icon=dokuzen"):
            if entry not in desktop:
                errors.append(f"desktop entry missing: {entry}")

    metainfo_path = project_root / "packaging/linux" / f"{APPSTREAM_ID}.metainfo.xml"
    if metainfo_path.is_file():
        try:
            root = ET.parse(metainfo_path).getroot()
        except ET.ParseError as exc:
            errors.append(f"invalid AppStream XML: {exc}")
        else:
            if root.findtext("id") != APPSTREAM_ID:
                errors.append("AppStream id does not match the packaging contract")
            launchable = root.find("launchable")
            if launchable is None or launchable.text != "dokuzen.desktop":
                errors.append("AppStream desktop launchable is missing")
    return errors


def build_pyinstaller_command(project_root: Path, *, dist_dir: Path, work_dir: Path) -> list[str]:
    """Create the shell-free PyInstaller invocation used by CI and local Linux builds."""

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir / "build"),
        "--specpath",
        str(work_dir),
    ]
    for source, destination in (("assets", "assets"), ("locales", "locales"), ("config", "config")):
        command.extend(("--add-data", f"{project_root / source}{os.pathsep}{destination}"))
    for module in ("torch", "pandas", "scipy", "matplotlib", "IPython", "pytest", "black", "pygame", "PyQt5", "PyQt6"):
        command.extend(("--exclude-module", module))
    command.append(str(project_root / "main.py"))
    return command


def _stage_linux_metadata(project_root: Path, bundle_dir: Path) -> None:
    share = bundle_dir / "share"
    applications = share / "applications"
    metainfo = share / "metainfo"
    icons = share / "icons" / "hicolor" / "512x512" / "apps"
    applications.mkdir(parents=True, exist_ok=True)
    metainfo.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)

    shutil.copy2(project_root / "packaging/linux/dokuzen.desktop", applications / "dokuzen.desktop")
    shutil.copy2(
        project_root / "packaging/linux" / f"{APPSTREAM_ID}.metainfo.xml",
        metainfo / f"{APPSTREAM_ID}.metainfo.xml",
    )
    shutil.copy2(project_root / "assets/icon.png", icons / "dokuzen.png")
    shutil.copy2(project_root / "packaging/linux/README.md", bundle_dir / "README-LINUX.md")
    for filename in ("LICENSE", "README.md", "README_de.md"):
        shutil.copy2(project_root / filename, bundle_dir / filename)


def _archive_bundle(bundle_dir: Path, dist_dir: Path) -> Path:
    architecture = platform.machine().lower() or "unknown"
    archive = dist_dir / f"DokuZen-{APP_VERSION}-linux-{architecture}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(bundle_dir, arcname=f"DokuZen-{APP_VERSION}")
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or build the portable DokuZen Linux tarball.")
    parser.add_argument("--check", action="store_true", help="Validate metadata only; do not build.")
    parser.add_argument("--dist-dir", type=Path, help="Artifact directory (default: dist/linux).")
    parser.add_argument("--work-dir", type=Path, help="PyInstaller work directory (default: build/linux).")
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[1]
    errors = validate_packaging_files(project_root)
    if errors:
        print("Linux packaging validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Linux packaging metadata: OK")
    if args.check:
        return 0
    if not sys.platform.startswith("linux"):
        print("Linux bundles must be built on Linux. Use --check for host-independent validation.", file=sys.stderr)
        return 2

    dist_dir = (args.dist_dir or project_root / "dist/linux").resolve()
    work_dir = (args.work_dir or project_root / "build/linux").resolve()
    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(project_root / "tools/preflight.py"), "--strict-build"], check=True)
    subprocess.run(
        build_pyinstaller_command(project_root, dist_dir=dist_dir, work_dir=work_dir),
        cwd=project_root,
        check=True,
    )
    bundle_dir = dist_dir / APP_NAME
    if not (bundle_dir / APP_NAME).is_file():
        print(f"PyInstaller did not create the expected launcher: {bundle_dir / APP_NAME}", file=sys.stderr)
        return 1
    _stage_linux_metadata(project_root, bundle_dir)
    archive = _archive_bundle(bundle_dir, dist_dir)
    print(f"Linux bundle: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
