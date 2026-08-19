<img src="assets/banner.png" width="100%" alt="DokuZen Banner">

# DokuZen

**Deutsch** | [English](README.md)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Pytest Status](https://img.shields.io/badge/pytest-276%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

[![Ecosystem doc-bricks](https://img.shields.io/badge/ecosystem-doc--bricks-orange.svg)](https://github.com/doc-bricks)
[![Umbrella open-bricks](https://img.shields.io/badge/umbrella-open--bricks-blueviolet.svg)](https://github.com/open-bricks)

> [!NOTE]
> **KI / LLM Integrations-Index:** Maschinenlesbarer Repository-Kontext und Systemgrenzen sind in [`llms.txt`](llms.txt) indexiert.

**Dokumenten- und Dateiverwaltungssuite** - Vereint 22 Text-, PDF- und Datei-Tools in einer Anwendung.

---

## Screenshot

![DokuZen Hauptfenster](README/screenshots/main.png)

---

## Features

### 📚 Dokumentenbibliothek
- Themenbasierte Organisation von Dokumenten
- Gelesen/Ungelesen-Status
- Schnelle Suche und Filterung (`Ctrl+F`)
- Drag & Drop Import
- Die zuletzt gewählte Kategorie bleibt auch nach Umbenennen oder Löschen des aktiven Themas über Neustarts stabil und fällt sauber auf ein vorhandenes Thema zurück

### 📄 PDF-Werkstatt
- PDF zusammenführen und teilen
- OCR-Texterkennung
- Passwortschutz entfernen
- Schwärzung sensibler Daten (Span/Rect-Präzision)
- Eigene Dialoge für OCR, Schwärzung, Konvertierung und Text-Pooling
- Signatur-Overlay mit automatischer Erkennung und Transparenz-Support
- Optionaler Beschnittrand und Seitennummerierung im Export

### 🔄 Konvertierung
- Word ↔ PDF ↔ Text
- Bild-Konvertierung (PNG, JPG, ICO, WebP; volle RGBA-Transparenzverarbeitung)
- Encoding-Reparatur

### 🛠️ Entwickler-Tools
- Python-Code zu EXE kompilieren
- Lizenz-Generierung
- Code-Splitter

### 🔒 Hintergrunddienste
- Privacy Guard (Datenschutz-Ampel)
- Sync Engine
- Media Brain

---

## Installation & Setup

### Voraussetzungen
- Python 3.10+
- PySide6 >= 6.5
- Tesseract OCR (optional, für OCR-Funktionen)
- PyMuPDF, pikepdf und Pillow laut `requirements.txt` / `pyproject.toml`

### Setup
```bash
# Repository klonen
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

Das mitgelieferte `start.bat` bevorzugt `venv\Scripts\python.exe` und fällt sonst automatisch auf das System-Python zurück.

---

## GUI-CLI Startoptionen

DokuZen bietet direkte Startoptionen für die vorhandenen GUI-Workflows:

```bash
python main.py --import beispiel.pdf notiz.md
python main.py --open beispiel.pdf
python main.py --ocr scan.pdf
python main.py --redact vertrag.pdf
python main.py --merge teil1.pdf teil2.pdf
```

---

## Tastenkürzel

| Kürzel | Funktion |
|--------|----------|
| `Ctrl+I` | Dateien importieren |
| `Ctrl+N` | Neues Thema |
| `Ctrl+F` | Suchen |
| `Ctrl+P` | Vorschau ein/aus |
| `Ctrl+,` | Einstellungen |
| `F5` | Aktualisieren |

---

## Lizenz & Drittanbieter

**AGPL-3.0-or-later** — GNU Affero General Public License v3.0 or later.
Siehe [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt) für das vollständige Runtime-Abhängigkeiten-Inventar.
