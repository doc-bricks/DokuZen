#!/usr/bin/env python3
"""DokuZen local runtime/build preflight.

Separates required runtime imports, optional/degraded features, build tooling,
and external OCR binaries. The default check fails only when required runtime
packages are missing. Use --strict-build before freezing a Windows release.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Check:
    name: str
    kind: str
    target: str
    required_for: str
    ok: bool
    degradation: str = ""


REQUIRED_RUNTIME = [
    ("PySide6", "Desktop GUI"),
    ("fitz", "Core PDF rendering/manipulation via PyMuPDF"),
    ("pikepdf", "Encrypted-PDF fallback/unlock"),
    ("PIL", "Image processing via Pillow"),
    ("pytesseract", "OCR Python wrapper"),
]

OPTIONAL_RUNTIME = [
    ("PyQt6", "Extended preview path unavailable"),
    ("rapidfuzz", "Fuzzy redaction/search helpers use exact or reduced matching"),
    ("keyboard", "Global hotkeys unavailable"),
    ("appdirs", "Platform-specific app-dir helper unavailable"),
]

BUILD_TOOLS = [
    ("PyInstaller", "Windows single-file EXE build"),
]

EXTERNAL_TOOLS = [
    ("tesseract", "OCR engine binary not found; OCR is unavailable until installed"),
]


def _module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _module_checks(items: Iterable[tuple[str, str]], kind: str) -> list[Check]:
    checks: list[Check] = []
    for module, purpose in items:
        checks.append(
            Check(
                name=module,
                kind=kind,
                target=module,
                required_for=purpose,
                ok=_module_available(module),
            )
        )
    return checks


def collect_checks() -> list[Check]:
    checks = _module_checks(REQUIRED_RUNTIME, "required-runtime")
    checks.extend(
        Check(
            name=module,
            kind="optional-runtime",
            target=module,
            required_for="optional feature",
            ok=_module_available(module),
            degradation=degradation,
        )
        for module, degradation in OPTIONAL_RUNTIME
    )
    checks.extend(_module_checks(BUILD_TOOLS, "build-tool"))
    checks.extend(
        Check(
            name=tool,
            kind="external-tool",
            target=tool,
            required_for="OCR",
            ok=shutil.which(tool) is not None,
            degradation=degradation,
        )
        for tool, degradation in EXTERNAL_TOOLS
    )
    return checks


def print_report(checks: list[Check]) -> None:
    print("DokuZen preflight")
    print("=================")
    for check in checks:
        state = "OK" if check.ok else "MISSING"
        print(f"[{state}] {check.kind}: {check.name} -- {check.required_for}")
        if not check.ok and check.degradation:
            print(f"       degradation: {check.degradation}")


def failing_checks(
    checks: list[Check],
    *,
    strict_build: bool,
    require_ocr: bool,
) -> list[Check]:
    failures = [check for check in checks if check.kind == "required-runtime" and not check.ok]
    if strict_build:
        failures.extend(check for check in checks if check.kind == "build-tool" and not check.ok)
    if require_ocr:
        failures.extend(
            check for check in checks
            if check.kind == "external-tool" and check.name == "tesseract" and not check.ok
        )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run DokuZen runtime/build preflight checks.")
    parser.add_argument(
        "--strict-build",
        action="store_true",
        help="Fail when build tooling such as PyInstaller is missing.",
    )
    parser.add_argument(
        "--require-ocr",
        action="store_true",
        help="Treat the external Tesseract binary as required instead of degraded OCR.",
    )
    args = parser.parse_args(argv)

    checks = collect_checks()
    print_report(checks)
    failures = failing_checks(
        checks,
        strict_build=args.strict_build,
        require_ocr=args.require_ocr,
    )
    if failures:
        print()
        print("Blocking failures:")
        for check in failures:
            print(f"- {check.kind}: {check.name} ({check.required_for})")
        return 1

    missing_optional = [check for check in checks if not check.ok and check.kind != "required-runtime"]
    if missing_optional:
        print()
        print("Preflight passed with degraded optional features.")
    else:
        print()
        print("Preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
