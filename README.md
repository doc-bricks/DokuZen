
# DokuZen Pro

[Deutsch](README_de.md) | **English**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Pytest Status](https://img.shields.io/badge/pytest-212%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Ecosystem doc-bricks](https://img.shields.io/badge/ecosystem-doc--bricks-orange.svg)](https://github.com/doc-bricks)
[![Umbrella open-bricks](https://img.shields.io/badge/umbrella-open--bricks-blueviolet.svg)](https://github.com/open-bricks)

> [!NOTE]
> **AI / LLM Integration Index:** Machine-readable repository context and system boundaries are indexed in [`llms.txt`](llms.txt).

**Dokumenten- und Dateiverwaltungssuite** - Vereint 22 Text-, PDF- und Datei-Tools in einer Anwendung.

## Screenshot

![DokuZen Hauptfenster](screenshots/main.png)

## Features

### 📚 Dokumentenbibliothek
- Themenbasierte Organisation von Dokumenten
- Gelesen/Ungelesen-Status
- Schnelle Suche und Filterung
- Drag & Drop Import
- Die zuletzt gewählte Kategorie bleibt auch nach Umbenennen oder Löschen des
  aktiven Themas über Neustarts stabil und fällt sauber auf ein vorhandenes
  Thema zurück

### 📄 PDF-Werkstatt
- PDF zusammenführen und teilen
- OCR-Texterkennung
- Passwortschutz entfernen
- Schwärzung sensibler Daten
- Eigene Dialoge für OCR, Schwärzung, Konvertierung und Text-Pooling

### 🔄 Konvertierung
- Word ↔ PDF ↔ Text
- Bild-Konvertierung (PNG, JPG, ICO, WebP)
- Encoding-Reparatur

### 🛠️ Entwickler-Tools
- Python-Code zu EXE kompilieren
- Lizenz-Generierung
- Code-Splitter

### 🔒 Hintergrunddienste
- Privacy Guard (Datenschutz-Ampel)
- Sync Engine
- Media Brain

## Installation

### Voraussetzungen
- Python 3.10+
- PySide6 >= 6.5
- Tesseract OCR (optional, für OCR-Funktionen)
- PyMuPDF, pikepdf und Pillow laut `requirements.txt`
- `PyQt6-WebEngine` nur für erweiterte Vorschau-Use-Cases

### Setup
```bash
# Repository klonen oder herunterladen
cd DokuZen

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Abhängigkeiten installieren
pip install -r requirements.txt

# Starten
python main.py
```

Das mitgelieferte `start.bat` bevorzugt `venv\Scripts\python.exe` und fällt
sonst automatisch auf das System-Python zurück.
Der Launcher lädt Icons sowohl aus dem Quellbaum als auch aus dem PyInstaller-Bundle.

## GUI-CLI Startoptionen

DokuZen bietet jetzt kleine Startoptionen für die vorhandenen GUI-Workflows:

```bash
python main.py --import beispiel.pdf notiz.md
python main.py --open beispiel.pdf
python main.py --ocr scan.pdf
python main.py --redact vertrag.pdf
python main.py --merge teil1.pdf teil2.pdf
```

Die Optionen öffnen weiterhin die Desktop-App und springen direkt in den
gewählten Dialog oder laden die Datei in Vorschau/Bibliothek vor.
Eine projektlokale REST-API ist im aktuellen Stand nicht implementiert.

### Automationsgrenze (Readback 2026-08-11)

Der belegte Usecase ist eine lokale Desktop-Dokumenten- und PDF-Werkstatt.
Die fünf Optionen oben sind GUI-Startaktionen und kein headless Batch- oder
Remote-Vertrag. Es wurde kein konkreter Remote-, Agenten- oder anderer
Automationsbedarf nachgewiesen; deshalb werden derzeit weder eine
Headless-Batch-CLI noch eine REST-API als Produktbestandteil behauptet oder
als Template ergänzt. Ein späterer Ausbau braucht zuerst einen belegten
Usecase und ein freigegebenes Sicherheitsmodell für Authentifizierung,
Eingaben, Ausgaben und Ressourcenlimits sowie isolierte Tests.

## Projektstruktur

```
DokuZen/
├── main.py                 # Einstiegspunkt
├── requirements.txt        # Python-Abhängigkeiten
├── config/
│   ├── settings.json       # Einstellungen
│   └── wordlists/          # Blacklists für Schwärzung
├── core/                   # Backend (ohne GUI)
│   ├── library/            # Bibliotheksverwaltung
│   ├── pdf/                # PDF-Operationen
│   ├── ocr/                # Texterkennung
│   ├── redaction/          # Schwärzung
│   ├── converter/          # Format-Konvertierung
│   └── forms/              # Formular-Builder
├── gui/                    # PySide6 GUI
│   ├── main_window.py      # Hauptfenster
│   ├── panels/             # Die drei Hauptpanels
│   ├── dialogs/            # Popup-Dialoge
│   ├── widgets/            # Wiederverwendbare Widgets
│   └── context_menus/      # Rechtsklick-Menüs
├── plugins/                # Optionale Erweiterungen
│   ├── spawner/            # TextSpawner
│   ├── special_text/       # Code-Splitter etc.
│   ├── background/         # Hintergrunddienste
│   ├── dev_tools/          # Entwickler-Tools
│   └── special_formats/    # Spezialformate
├── utils/                  # Hilfsfunktionen
├── assets/                 # Icons, Styles
└── logs/                   # Log-Dateien
```

## Tastenkürzel

| Kürzel | Funktion |
|--------|----------|
| Ctrl+I | Dateien importieren |
| Ctrl+N | Neues Thema |
| Ctrl+F | Suchen |
| Ctrl+P | Vorschau ein/aus |
| Ctrl+, | Einstellungen |
| F5 | Aktualisieren |

## Lizenz

AGPL-3.0-or-later — GNU Affero General Public License v3.0 or later

Dieses Projekt verwendet PyMuPDF (AGPL-3.0). `THIRD_PARTY_LICENSES.txt` dokumentiert die direkten Runtime-Abhängigkeiten und die wichtigsten Copyleft-/Store-Grenzen. Vor einem öffentlichen Binary- oder Store-Release muss der Quellcode passend bereitgestellt und der Release-SBOM aus der echten Build-Umgebung erzeugt werden.

## Changelog

### Version 1.0.0
- Initiale Version
- Bibliotheksverwaltung mit Themen
- 3-Panel-Layout (Bibliothek, Liste, Vorschau)
- Grundlegende PDF-Vorschau
- Einstellungsdialog

---

## English

### Overview

DokuZen Pro is a document and file management suite combining 22 text, PDF, and file tools in a single application.

### Features

- **Document Library** -- Topic-based organization, read/unread status, search and filtering
- **PDF Workshop** -- Merge, split, OCR, password removal, redaction
- **Conversion** -- Word/PDF/Text, image formats (PNG, JPG, ICO, WebP), encoding repair
- **Developer Tools** -- Python-to-EXE compiler, license generator, code splitter
- **Background Services** -- Privacy Guard, Sync Engine, Media Brain

### Quick Start

```bash
pip install -r requirements.txt
python main.py
```

### Requirements

- Python 3.10+
- PySide6 >= 6.5
- Tesseract OCR (optional, for OCR features)

### Current automation entry points

- `python main.py --import file1.pdf notes.md`
- `python main.py --open file.pdf`
- `python main.py --ocr scan.pdf`
- `python main.py --redact contract.pdf`
- `python main.py --merge a.pdf b.pdf`

The current project does not ship a project-local REST API yet.

### Automation boundary (readback 2026-08-11)

The evidenced use case is a local desktop document and PDF workstation. The
five options above are GUI startup actions, not a headless batch or remote
contract. No concrete remote, agent, or other automation need was evidenced;
therefore the product currently claims neither a headless batch CLI nor a
REST API, and does not add an API template. A future expansion requires a
concrete use case, an approved security model for authentication, inputs,
outputs, and resource limits, plus isolated tests.

### Development smoke tests

```bash
python tests/test_source_platform_smoke.py
python -m unittest discover -s tests -v
```

The source smoke starts the app offscreen with an isolated temp state file,
imports a UTF-8 markdown file plus a real PDF, validates preview rendering,
and checks the Linux/macOS external open commands without touching the user's
real library state.

### License

AGPL-3.0-or-later

See `THIRD_PARTY_LICENSES.txt` for the direct runtime dependency inventory and release-license boundaries.
