<img src="assets/banner.png" width="100%" alt="DokuZen Banner">

# DokuZen

[Deutsch](README_de.md) | **English**

[![CI](https://github.com/doc-bricks/DokuZen/actions/workflows/source-platform-smoke.yml/badge.svg)](https://github.com/doc-bricks/DokuZen/actions/workflows/source-platform-smoke.yml)
[![Pytest Status](https://img.shields.io/badge/pytest-331%20passed%20%7C%20100%25-brightgreen.svg)](https://docs.pytest.org/)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/doc-bricks/DokuZen)
[![Privacy](https://img.shields.io/badge/privacy-100%25%20Local--First%20%7C%20Zero--Egress-success.svg)](SECURITY.md)
[![Security](https://img.shields.io/badge/security-Bilingual%20Policy%20%7C%20Non--Elevation-informational.svg)](SECURITY.md)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](pyproject.toml)
[![License AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Ecosystem doc-bricks](https://img.shields.io/badge/ecosystem-doc--bricks-orange.svg)](https://github.com/doc-bricks)
[![Umbrella open-bricks](https://img.shields.io/badge/umbrella-open--bricks-blueviolet.svg)](https://github.com/open-bricks)
[![LLM Ready llms.txt](https://img.shields.io/badge/LLM--Ready-llms.txt-blue.svg)](llms.txt)

> [!NOTE]
> **AI / LLM Integration Index:** Machine-readable repository context, API boundaries, and architecture contracts are indexed in [`llms.txt`](llms.txt).

**DokuZen** is a cross-platform, local-first desktop document management and processing suite built with Python and PySide6, combining **22 specialized text, PDF, OCR, and file utilities** into a single unified workspace.

---

## 🧭 Quick Navigation

- 📸 [Visual Showcase Gallery](#-visual-showcase-gallery)
- 🏛️ [System Architecture](#️-system-architecture)
- 🔄 [Document & PDF Processing Lifecycle](#-document--pdf-processing-lifecycle)
- ✨ [Core Features & Utilities](#-core-features--utilities)
- 🚀 [Installation & Quick Start](#-installation--quick-start)
- 🖥️ [GUI-CLI Direct Entry Points](#️-gui-cli-direct-entry-points)
- 🌐 [Ecosystem & Sibling Tools](#-ecosystem--sibling-tools)
- 🔒 [Privacy & Security Invariants](#-privacy--security-invariants)
- 🧪 [Testing & Verification](#-testing--verification)
- ⌨️ [Keyboard Shortcuts](#️-keyboard-shortcuts)
- 🪟 [Windows Store & Packaging](#-windows-store--packaging)
- 🐧 [Portable Linux Bundle](#-portable-linux-bundle)
- 📄 [License & Third-Party Dependencies](#-license--third-party-dependencies)

---

## 📸 Visual Showcase Gallery

| Feature Overview | Detail View |
|:---:|:---:|
| ![Main Interface](screenshots/main.png)<br/><sub>**DokuZen Main Interface** — 3-Panel workspace with library taxonomy, document list, and high-fidelity preview.</sub> | ![Library Taxonomy](screenshots/store/01_bibliothek.png)<br/><sub>**Document Library** — Thematic categorisation, tag filtering, and unread tracking across document collections.</sub> |
| ![PDF Preview](screenshots/store/02_pdf_vorschau.png)<br/><sub>**High-Speed PDF Preview** — Multi-page navigation, continuous zoom, and native PyMuPDF offscreen rendering.</sub> | ![Tesseract OCR Dialog](screenshots/store/03_ocr_dialog.png)<br/><sub>**OCR & Layout Extraction** — Scanned image to searchable PDF conversion with language auto-detection.</sub> |
| ![PII Redaction Dialog](screenshots/store/04_schwaerzung.png)<br/><sub>**Permanent Redaction** — Regex- and span-based PII black-fill sanitization with irreversible stream cleanup.</sub> | ![Multi-Format Converter](screenshots/store/05_konvertierung.png)<br/><sub>**Format Converter** — Bidirectional DOCX ↔ PDF ↔ Markdown ↔ TXT with RGBA transparency preservation.</sub> |
| ![Batch Processing](screenshots/store/06_batch_verarbeitung.png)<br/><sub>**Batch Operations & Merger** — Multi-file merge, split, stamp, and signature overlay pipeline.</sub> | *(All screenshots rendered in native 1080p high resolution)* |

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph UI ["PySide6 Desktop User Interface"]
        LP["Library Panel<br/>(Thematic Taxonomy & State)"]
        DP["Document List Panel<br/>(Metadata, Search & Sorting)"]
        PP["Preview Panel<br/>(Fitz / WebView / Syntax Engine)"]
        DLG["Specialized Dialogs<br/>(OCR, Redaction, Merge, Converter, Settings)"]
    end

    subgraph Core ["Core Processing Engines"]
        LIB["Library Manager<br/>(Persistence, Tag Index & State)"]
        PDF["PDF Workshop<br/>(Merge, Split, Crop, Rotate, Overlay)"]
        OCR["OCR Engine<br/>(Tesseract Subprocess & Text Layer)"]
        CVT["Format Converter<br/>(DOCX ↔ PDF ↔ MD ↔ TXT, Image Alpha)"]
        SEC["Security & Unlock<br/>(Pikepdf Session-Key Isolation)"]
        RED["Redaction Engine<br/>(Destructive Black-Fill Sanitization)"]
    end

    subgraph Storage ["Local Storage & Packaging Subsystem"]
        STATE["dokuzen_state.json<br/>(Local-First User State)"]
        FS["Local File System Boundary<br/>(Zero-Egress / Sandboxed Paths)"]
        MSIX["MSIX Packaging Bridge<br/>(Windows Store Manifest & Preflight)"]
    end

    LP --> LIB
    DP --> LIB
    PP --> PDF
    PP --> CVT
    DLG --> OCR
    DLG --> RED
    DLG --> SEC
    DLG --> PDF
    PDF --> FS
    CVT --> FS
    LIB --> STATE
    MSIX -.-> UI
```

---

## 🔄 Document & PDF Processing Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Desktop User
    participant GUI as PySide6 Main Window
    participant Router as Format & Task Router
    participant Engine as Core Engine (PDF/OCR/Converter)
    participant FS as Local File System Boundary

    User->>GUI: Ingest Document (Drag & Drop / Ctrl+I / CLI Flag)
    GUI->>Router: Detect MIME Type & Header Signature
    alt PDF Stream / Document
        Router->>Engine: Parse via PyMuPDF / pikepdf with Thread Guard
        Engine-->>GUI: Render Offscreen Page Pixmaps & Extract Text Layers
        GUI-->>User: Display High-Fidelity Preview & Page Navigation
    else Image / OCR Scan
        Router->>Engine: Dispatch to Tesseract OCR Subprocess
        Engine-->>GUI: Bounding-Box Layout & Textual Layer Generated
    else Format Conversion
        Router->>Engine: Convert (DOCX / Markdown / TXT / Alpha Image)
        Engine-->>GUI: Transformed Output Ready for Inspection
    end

    opt Redaction / Signature / Split & Merge
        User->>GUI: Apply PII Redaction Pattern / Signature Stamp
        GUI->>Engine: Destructive Vector & Pixel Overlay
    end

    User->>GUI: Trigger Save / Export
    GUI->>FS: Atomic Write to Local Disk (Zero Egress, Closed File Descriptors)
    FS-->>User: File Saved Successfully with 100% Offline Guarantee
```

---

## ✨ Core Features & Utilities

### 📚 Document Library
- **Thematic Organisation**: Categorize documents by topics and tags with persistent category selection across restarts.
- **Read / Unread State**: Track review progress across large document collections.
- **Fast Search & Filtering**: Instant filter by name, content, and metadata with `Ctrl+F` global shortcut.
- **Drag & Drop Import**: Direct file ingestion into active categories with automatic type recognition.

### 📄 PDF Workshop
- **Merge & Split**: Combine multiple PDF streams or split at specific page boundaries and ranges.
- **Tesseract OCR Integration**: Generate searchable PDFs and extract textual layers with bounding-box precision.
- **Sanitization & Redaction**: Regex- and span-based PII redaction with irreversible black-fill sanitization.
- **Signature & Stamp Overlay**: Stamp transparent PNG signatures or metadata badges onto target pages.
- **Password Removal**: Decrypt password-protected files via `pikepdf` with session key guards.

### 🔄 Multi-Format Converter
- **Word ↔ PDF ↔ Markdown ↔ Plain Text**: Seamless bidirectional document format transitions.
- **Image Conversion**: PNG, JPG, ICO, WebP with full RGBA transparency preservation on conversion to PDF.
- **Encoding Repair**: Automatic Mojibake and UTF-8/Latin-1 encoding restoration.

### 🛠️ Developer & Productivity Tools
- **Python to EXE Compiler**: PyInstaller bundling UI with icon embedding and dependency detection.
- **License Generator**: Standardized open-source license creation.
- **Code Splitter**: Clean split of multi-class Python source files into modular units.

### 🔒 Background Services & Packaging
- **Privacy Guard**: Visual privacy monitor alerting on sensitive data exposure.
- **Sync Engine**: Local-first synchronization helper.
- **Media Brain**: Integrated asset extraction and indexing.
- **Windows Store Bridge**: MSIX Packaging Manifest & automated preflight readiness checks.

---

## 🚀 Installation & Quick Start

### Requirements
- Python 3.10+
- PySide6 >= 6.5.0
- Tesseract OCR (optional, for OCR capabilities)
- Dependencies listed in `requirements.txt` / `pyproject.toml`

### Installation

```bash
# Clone the repository
git clone https://github.com/doc-bricks/DokuZen.git
cd DokuZen

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start DokuZen
python main.py
```

*Note: On Windows, you can also launch directly via `start.bat`.*

---

## 🖥️ GUI-CLI Direct Entry Points

DokuZen provides direct CLI flags that launch the desktop application and navigate immediately into specific workflows:

```bash
# Import documents into library
python main.py --import document.pdf notes.md

# Open document in preview panel
python main.py --open manual.pdf

# Launch OCR Dialog with preloaded file
python main.py --ocr scan.pdf

# Launch Redaction Dialog
python main.py --redact contract.pdf

# Launch PDF Merger Dialog
python main.py --merge part1.pdf part2.pdf
```

> [!NOTE]
> **Automation Boundary:** The evidenced use case is a local desktop document and PDF workstation. The CLI entry points above are GUI startup shortcuts. Headless batch CLI and REST API endpoints remain intentionally unasserted until explicit remote use cases and approved security models are established.

---

## 🌐 Ecosystem & Sibling Tools

DokuZen is maintained under the **`doc-bricks`** ecosystem, part of the **`open-bricks`** family of local-first tools:

| Repository | Purpose | Status |
|---|---|---|
| [doc-bricks/DokuZen](https://github.com/doc-bricks/DokuZen) | All-in-One Document & PDF Management Suite | Active / 1.0.0 |
| [doc-bricks/CleanMarkdown](https://github.com/doc-bricks/CleanMarkdown) | Distraction-Free Markdown Editor & PDF Exporter | Active / 1.0.0 |
| [doc-bricks/FormularErstellen](https://github.com/doc-bricks/FormularErstellen) | Interactive PDF & AcroForm Form Designer | Active / 1.5.0 |
| [doc-bricks/UniversalDocsGrabber](https://github.com/doc-bricks/UniversalDocsGrabber) | Automated IMAP Document Ingestion & PWA Hub | Active / 1.1.4 |
| [doc-bricks/PDFtoPDFocr](https://github.com/doc-bricks/PDFtoPDFocr) | OCR Conversion & Searchable PDF Engine | Active / 1.1.3 |
| [doc-bricks/DokuReader](https://github.com/doc-bricks/DokuReader) | Lightweight Multi-Format Document Reader | Active / 1.0.0 |
| [doc-bricks/MediaBrain](https://github.com/doc-bricks/MediaBrain) | Multi-format Media & Metadata Extraction | Active / 0.1.0 |
| [doc-bricks/TextBrain](https://github.com/doc-bricks/TextBrain) | AI-assisted Text Analysis & Extraction | Active / 0.1.0 |
| [file-bricks/WinStorePackager](https://github.com/file-bricks/WinStorePackager) | MSIX Packaging & Windows Store Tooling | Active / 3.1.0 |
| [file-bricks/ProSync](https://github.com/file-bricks/ProSync) | Local Backup & WAL-Protected Sync | Active / 3.2.1 |
| [file-bricks/ExplorerPro](https://github.com/file-bricks/ExplorerPro) | Multi-Tab Local-First File Manager | Active / 1.0.3 |
| [dev-bricks/DevCenter](https://github.com/dev-bricks/DevCenter) | Developer Productivity Hub & Dashboard | Active / 1.0.0 |
| [open-bricks/.github](https://github.com/open-bricks/.github) | Umbrella Organisation & Open Standards | Active |

---

## 🔒 Privacy & Security Invariants

DokuZen is committed to uncompromising privacy and security:

- **100% Local-First & Zero-Egress**: All document operations, conversions, and OCR recognitions occur exclusively on your local CPU/GPU. No document content or telemetry is ever sent over the network.
- **Unprivileged User Mode**: DokuZen runs without administrative or root privileges (Non-Elevation).
- **Destructive Redaction**: Redactions are applied directly to vector streams and image rasters, preventing reverse extraction of sanitized text.
- **Deterministic File Cleanup**: All intermediate temporary files are cleaned up atomically upon operation completion.

Detailed security and disclosure policies are available in [`SECURITY.md`](SECURITY.md).

---

## 🧪 Testing & Verification

DokuZen maintains an automated test suite covering unit operations, GUI dialog smoke tests, PDF encryption lifecycles, and metadata parity:

```bash
# Run complete test suite
python -m pytest

# Run offscreen platform smoke tests
python tests/test_source_platform_smoke.py

# Run Windows Store readiness gatekeeper
python tools/check_store_readiness.py

# Validate the portable Linux bundle contract (host-independent)
python tools/build_linux_bundle.py --check

# Run linting gatekeeper
python -m ruff check .
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+I` | Import Files into Active Category |
| `Ctrl+N` | Create New Theme / Category |
| `Ctrl+F` | Focus Search Filter |
| `Ctrl+P` | Toggle Preview Panel |
| `Ctrl+,` | Open Preferences Dialog |
| `F5` | Refresh Document Index |

---

## 🪟 Windows Store & Packaging

DokuZen includes complete Microsoft Windows Store (MSIX) packaging infrastructure:
- **Manifest**: `store_package/DokuZen/AppxManifest.xml` (`Geiger.DokuZen`, `runFullTrust`)
- **Assets**: 1080p store screenshots in `screenshots/store/` and high-DPI icon assets (44x44, 50x50, 150x150, 310x150, 310x310)
- **Validation**: Automated preflight validation script via `tools/check_store_readiness.py`

---

## 🐧 Portable Linux Bundle

DokuZen has a reproducible PyInstaller-onedir packaging path for Linux. A
dedicated workflow builds `DokuZen-1.0.0-linux-<architecture>.tar.gz` with the
application, assets, six-language catalog, configuration, Freedesktop desktop
entry, AppStream metadata, license, and bilingual documentation.

```bash
# Metadata/contract check on any host
python tools/build_linux_bundle.py --check

# Actual bundle build on Linux
python tools/build_linux_bundle.py
```

Tesseract remains an optional external dependency; DokuZen starts without it,
while OCR features remain unavailable until Tesseract is installed. See
[`packaging/linux/README.md`](packaging/linux/README.md) for extraction and
startup instructions.

---

## 📄 License & Third-Party Dependencies

DokuZen is licensed under the **GNU Affero General Public License v3.0 or later ([AGPL-3.0-or-later](LICENSE))**.

Direct third-party libraries and runtime copyleft boundaries are documented in [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt).

