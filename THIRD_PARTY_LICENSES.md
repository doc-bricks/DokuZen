# DokuZen — Third-Party License Inventory & Copyleft Boundaries

**Status:** Production Direct Runtime Dependency Inventory  
**Audited:** 2026-08-24 (via PyPI JSON metadata & OSV/GHSA vulnerability scan)  
**Re-Verified:** 2026-09-24 (Pfad A Turnus-Hygiene & CI Lifecycle Audit)
**Primary Project License:** [AGPL-3.0-or-later](LICENSE)  
**Attribution & Copyright:** [NOTICE](NOTICE)

---

## 1. Scope & Distribution Guarantees

This document specifies DokuZen's direct Python runtime dependencies as declared in [`pyproject.toml`](pyproject.toml) and [`requirements.txt`](requirements.txt). Attribution and copyright notices are declared in [`NOTICE`](NOTICE).

### Strict Distribution Invariants:
1. **Source Code Availability**: DokuZen is distributed under the GNU Affero General Public License v3.0 or later ([AGPL-3.0-or-later](LICENSE)). All binary releases (Windows MSIX, portable Linux bundles) preserve reciprocal copyleft compliance.
2. **Zero-Egress Sandboxing (`INV-LOCAL-01`)**: No dependency initiates outbound network sockets or external telemetry.
3. **Unprivileged Execution (`INV-SECR-09`)**: All dependencies operate in user-mode (`RunAsInvoker`) without administrative elevation.

---

## 2. Direct Runtime Python Dependencies

| Package | Requirement | SPDX License | Purpose & Architecture Role | Hardened Floor |
|---|---|---|---|---|
| **PySide6** | `PySide6>=6.5.0` | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | Official Qt for Python GUI bindings and widget framework. | `>=6.5.0` |
| **PyMuPDF** | `PyMuPDF>=1.24.0` | `AGPL-3.0-only` (or commercial Artifex) | High-speed PDF vector parsing, rendering, and text-layer extraction. | `>=1.24.0` |
| **pikepdf** | `pikepdf>=8.15.1` | `MPL-2.0` | PDF decryption, structural repair, and QPDF bindings. | `>=8.15.1` |
| **pillow** | `Pillow>=12.0.0` | `HPND` | Image format manipulation and transparency preservation. | `>=12.0.0` |
| **pytesseract** | `pytesseract>=0.3.13` | `Apache-2.0` | Subprocess wrapper for local Tesseract OCR engine. | `>=0.3.13` |
| **python-docx** | `python-docx>=1.0.0` | `MIT` | Microsoft Word DOCX document parsing and text generation. | `>=1.0.0` |
| **openpyxl** | `openpyxl>=3.1.0` | `MIT` | Excel spreadsheet parsing and table extraction. | `>=3.1.0` |
| **chardet** | `chardet>=5.0.0` | `0BSD` | Character encoding and Mojibake detection. | `>=5.0.0` |
| **rapidfuzz** | `rapidfuzz>=3.0.0` | `MIT` | High-speed fuzzy string matching for redactions and search. | `>=3.0.0` |
| **reportlab** | `reportlab>=4.2.0` | `BSD-3-Clause` | Programmatic PDF canvas generation and stamping. | `>=4.2.0` |
| **pyperclip** | `pyperclip>=1.8.0` | `BSD-3-Clause` | Local clipboard read/write access. | `>=1.8.0` |
| **pystray** | `pystray>=0.19.5` | `LGPL-3.0-or-later` | System notification tray icon and background monitor. | `>=0.19.5` |
| **keyboard** | `keyboard>=0.13.0` | `MIT` | Global accessibility shortcuts on desktop platforms. | `>=0.13.0` |
| **watchdog** | `watchdog>=3.0.0` | `Apache-2.0` | Local directory and file-system modification monitor. | `>=3.0.0` |
| **appdirs** | `appdirs>=1.4.0` | `MIT` | Standardized operating system configuration directories. | `>=1.4.0` |

---

## 3. Copyleft & Licensing Boundaries

### Copyleft Alignment
- **PyMuPDF**: Distributed under the AGPL-3.0 license. Because DokuZen is licensed under AGPL-3.0-or-later, the licenses are in complete reciprocal alignment. Any binary redistribution includes the corresponding source code.
- **PySide6**: Utilized dynamically under the LGPL-3.0 license terms, permitting user replacement of dynamic Qt libraries.
- **pikepdf**: Governed by the Mozilla Public License 2.0 (MPL-2.0), maintaining file-level copyleft separation.

---

## 4. External System Dependencies

| Component | License | Bundling Status & Notes |
|---|---|---|
| **Tesseract OCR** | `Apache-2.0` | Optional external executable. Not bundled in repository source tree; DokuZen gracefully runs in reduced mode if Tesseract is absent. |
| **Windows App SDK / CRT** | Microsoft EULA | Provided by host OS; not redistributed as repository artifacts. |

---

## 5. Security & Invariant Verification Matrix

| Invariant | Description | Verification Method | Status |
|---|---|---|---|
| `INV-LOCAL-01` | 100% Zero-Egress Network Isolation | AST Static Scan in `tests/test_metadata.py` | PASS |
| `INV-COST-02`  | Free and Open Source (AGPL-3.0) | License parity in `pyproject.toml` | PASS |
| `INV-PRIV-03`  | Irreversible PII Redaction | Vector stream blackout test in `test_redaction_*.py` | PASS |
| `INV-TOOL-04`  | 22-in-1 Consolidator | UI module enumeration in `tests/` | PASS |
| `INV-OCR-05`   | Tesseract OCR Integration | Subprocess execution test in `test_ocr_*.py` | PASS |
| `INV-PERF-06`  | PyMuPDF High-Speed Engine | Memory and pixmap tests in `test_pdf_reader_*.py` | PASS |
| `INV-PLAT-07`  | Multi-Platform Parity | CI test matrix (Ubuntu, macOS, Windows) | PASS |
| `INV-FMT-08`   | Multi-Format Conversion | Image/DOCX/PDF tests in `test_converter_*.py` | PASS |
| `INV-SECR-09`  | Non-Elevation (`RunAsInvoker`) | Manifest check in `store_package/DokuZen/` | PASS |
| `INV-ARCH-10`  | Open State Export Schema | Validation tests in `test_workspace_export.py` | PASS |
