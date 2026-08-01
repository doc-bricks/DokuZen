# 📦 DokuZen Pro Suite – Final Documentation

## 1. Überblick

**Kurzbeschreibung:**  
DokuZen Pro ist eine umfassende Dokumenten- und Dateiverwaltungssuite, die 22 Text-, PDF- und Datei-Tools in einer einheitlichen Anwendung vereint.

| Feld | Wert |
|------|------|
| **Version** | 1.0.0 |
| **Stand** | 2026-01-09 |
| **Status** | Fertiggestellt (100%) |
| **Sprache** | Python 3.10+ |
| **Framework** | PyQt6 |
| **Codebase** | ~18.500 Zeilen / 81 Dateien |

---

## 2. Herkunft & Fusion

### 2.1 Ursprungstools

| # | Tool | Zeilen | Reifegrad | Kernfunktion |
|---|------|--------|-----------|--------------|
| 1 | DokuReader | 756 | 🟢 Master | Bibliotheksverwaltung |
| 2 | TextPool | 284 | 🟢 | Texte zusammenführen |
| 3 | StapelKönig V2.0 | 410 | 🟢 | PDF Merge mit D&D |
| 4 | TextSpawner | 442 | 🟡 Plugin | Clipboard → Datei |
| 5 | PylogText | 205 | 🟢 | .py/.log ↔ .txt |
| 6 | FormKonstrukteur V1.5 | 444 | 🟢 | Formular-Builder |
| 7 | PDFmarker2000 | 800 | 🟢 | Seiten markieren/extrahieren |
| 8 | pyCuttertxt | 200 | 🟢 | Python-Code zerschneiden |
| 9 | PDFtoPDFocr | 336 | 🟢 | OCR für PDFs |
| 10 | PDFSchwärzer Pro V2.5 | 1.259 | 🟢 Kern | Intelligente Schwärzung |
| 11 | PDFunlock | 177 | 🟢 | PDF entsperren |
| 12 | EncodingFixer | - | 🟢 | Encoding-Reparatur |
| 13 | PythonBox (A2 Editor) | - | 🟢 | Code-Editor |
| 14 | IcoBuilder | - | 🟢 | Bild→ICO |
| 15 | pic2pic | - | 🟢 | Bild-Konverter |
| 16 | SQLiteViewer | - | 🟢 | DB-Viewer |
| 17 | Ampelclip | - | 🟡 | Datenschutz-Ampel |
| 18 | ProSync | - | 🟡 | Sync-Engine |
| 19 | MediaBrain | - | 🟡 | Medien-Sammlung |
| 20 | UltimateKompilator | - | 🔵 Plugin | Python→EXE |
| 21 | ThirdPartyLicenses | - | 🔵 Plugin | Lizenz-Generator |
| 22 | Make23toVCF3 | - | 🔵 Plugin | Spezialformat |

### 2.2 Fusionsziel

> **"Eine zentrale Anlaufstelle für alle Dokumenten- und Textoperationen"**

Die Suite vereint Bibliotheksverwaltung, PDF-Werkstatt, OCR, Schwärzung, Konvertierung und Entwickler-Tools in einer Anwendung.

### 2.3 Synergien

| Synergie | Beschreibung |
|----------|--------------|
| 📚 **Unified Library** | Alle Dokumente an einem Ort mit Themen |
| 🔄 **Seamless Conversion** | Format-Wechsel ohne Tool-Wechsel |
| 🔐 **PDF-Pipeline** | OCR → Schwärzen → Extrahieren → Merge |
| 🖱️ **Context Menus** | Rechtsklick-Workflows für alle Formate |
| 🔔 **Background Services** | Datenschutz-Ampel, Sync, MediaBrain |

---

## 3. Features

### 3.1 Hauptfunktionen

| Bereich | Icon | Features |
|---------|------|----------|
| **Dokumentenbibliothek** | 📚 | Themen, Gelesen-Status, Suche, D&D Import |
| **PDF-Werkstatt** | 📄 | Merge, Split, OCR, Schwärzung, Unlock |
| **Konvertierung** | 🔄 | Word ↔ PDF ↔ Text, Bilder, Encoding |
| **Entwickler-Tools** | 🛠️ | Python→EXE, Lizenzen, Code-Splitter |
| **Hintergrunddienste** | 🔒 | Privacy Guard, Sync Engine, Media Brain |

### 3.2 Feature-Matrix

| Feature | Einzeltools | DokuZen Pro |
|---------|:-----------:|:---------------:|
| Bibliotheksverwaltung | 1 Tool | ✅ Integriert |
| PDF-Operationen | 5 Tools | ✅ PDF-Werkstatt |
| OCR | 2 Tools | ✅ Unified OCR |
| Konvertierung | 4 Tools | ✅ Convert-Dialog |
| Entwickler-Tools | 3 Tools | ✅ Dev-Plugin |
| Hintergrund-Services | 3 Tools | ✅ Background-Services |

### 3.3 Workflows (21 implementiert)

**Rechtsklick-Workflows:**
- Explorer-Hintergrund → "Text hier spawnen"
- Dokument-Kontextmenü (Öffnen, Konvertieren, PDF-Werkstatt, Status)
- Python-Kontextmenü (Editor, Encoding, Zerschneiden, Kompilieren)
- Bild-Kontextmenü (Konvertieren zu PNG/JPG/ICO/PDF)
- Datenbank-Kontextmenü (SQLite-Viewer, CSV-Export)

**Drag & Drop Workflows:**
- Dateien aufeinander → Fusion (StapelKönig)
- Dateien in TextPool → Zusammenführen
- Dateien in Bibliothek → Import

**Spezial-Workflows:**
- .py Zerschneiden (AST-basiert)
- Formular erstellen (Visual Builder)
- PDF-Seiten markieren (m/d/k Hotkeys)
- PDF Entsperren (Brute-Force Birthday)
- PDF Schwärzen (Fuzzy Matching, AES-256)

---

## 4. Architektur

### 4.1 Layer-Modell

```
┌─────────────────────────────────────────────────────────────────┐
│                         GUI Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ MainWindow  │  │   Panels    │  │        Dialogs          │  │
│  │             │  │  Library    │  │  Settings, PDF-Workshop │  │
│  │             │  │  Documents  │  │  Merge, OCR, Redaction  │  │
│  │             │  │  Preview    │  │  FormBuilder, Marker    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                       Core Layer                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Library  │  │   PDF    │  │   OCR    │  │  Redaction    │   │
│  │          │  │          │  │          │  │               │   │
│  │ Manager  │  │ Reader   │  │ Engine   │  │ Detector      │   │
│  │ Themes   │  │ Writer   │  │ Tesseract│  │ Fuzzy         │   │
│  │ Search   │  │ Merger   │  │ Language │  │ Applier       │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
│                                                                  │
│  ┌──────────┐  ┌──────────────────────────────────────────────┐ │
│  │Converter │  │                  Forms                       │ │
│  │ to_pdf   │  │  Builder, Templates, Fields, Export          │ │
│  │ from_pdf │  │                                              │ │
│  │ text     │  │                                              │ │
│  └──────────┘  └──────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Plugins Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Spawner   │  │ Background  │  │      Dev Tools          │  │
│  │ Tray, Hotkey│  │ Privacy     │  │ Kompilator, Licenses    │  │
│  │ Registry    │  │ Sync, Media │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Module

| Modul | Pfad | Beschreibung |
|-------|------|--------------|
| **Library Manager** | `core/library/manager.py` | Bibliotheksverwaltung |
| **PDF Reader** | `core/pdf/reader.py` | fitz, pypdf, pikepdf |
| **PDF Merger** | `core/pdf/merger.py` | StapelKönig-Logik |
| **PDF Splitter** | `core/pdf/splitter.py` | PDFmarker2000-Logik |
| **OCR Engine** | `core/ocr/engine.py` | Tesseract-Integration |
| **Redaction** | `core/redaction/` | Fuzzy-Schwärzung |
| **Converter** | `core/converter/` | Format-Wandlung |
| **Forms** | `core/forms/` | Formular-Builder |
| **Spawner** | `plugins/spawner/` | Tray, Registry, Hotkey |
| **Privacy Guard** | `plugins/background/privacy_guard/` | Ampelclip |
| **Sync Engine** | `plugins/background/sync_engine/` | ProSync |

### 4.3 Datenfluss

```
User Action → Context Menu → Core Module → File System
     ↓                          ↓
Signals ← Status/Progress ←────┘
     ↓
GUI Update (Panels, Preview)
```

---

## 5. Projektstruktur

```
DokuZen/
├── main.py                 # Einstiegspunkt
├── start.bat               # Benutzerfreundlicher Start
├── requirements.txt        # Python-Abhängigkeiten
├── README.md               # Projektbeschreibung
│
├── config/
│   ├── settings.json       # Globale Einstellungen
│   ├── theme.json          # UI-Theme (Dark/Light)
│   ├── shortcuts.json      # Keyboard-Shortcuts
│   └── wordlists/          # Schwärzungs-Listen
│       ├── blacklist_default.txt
│       └── whitelist_default.txt
│
├── core/                   # Backend (ohne GUI)
│   ├── library/            # Bibliotheksverwaltung
│   │   ├── manager.py
│   │   ├── persistence.py
│   │   ├── search.py
│   │   └── themes.py
│   │
│   ├── pdf/                # PDF-Engine
│   │   ├── reader.py
│   │   ├── writer.py
│   │   ├── merger.py
│   │   ├── splitter.py
│   │   ├── security.py
│   │   ├── annotator.py
│   │   └── markers.py
│   │
│   ├── ocr/                # OCR-Engine
│   │   ├── engine.py
│   │   ├── tesseract.py
│   │   └── language.py
│   │
│   ├── redaction/          # Schwärzung
│   │   ├── detector.py
│   │   ├── fuzzy.py
│   │   ├── blacklist.py
│   │   └── applier.py
│   │
│   ├── converter/          # Format-Wandlung
│   │   ├── to_pdf.py
│   │   ├── from_pdf.py
│   │   ├── text_tools.py
│   │   ├── office.py
│   │   └── spawner.py
│   │
│   └── forms/              # Formulare
│       ├── builder.py
│       ├── templates.py
│       ├── fields.py
│       └── export.py
│
├── gui/                    # Frontend (PyQt6)
│   ├── main_window.py
│   ├── panels/
│   │   ├── library_panel.py
│   │   ├── document_list.py
│   │   └── preview_panel.py
│   │
│   ├── dialogs/
│   │   ├── settings_dialog.py
│   │   ├── pdf_workshop.py
│   │   ├── redaction_dialog.py
│   │   ├── ocr_dialog.py
│   │   ├── merge_dialog.py
│   │   ├── pool_dialog.py
│   │   ├── convert_dialog.py
│   │   ├── form_builder.py
│   │   ├── marker_dialog.py
│   │   └── unlock_dialog.py
│   │
│   ├── widgets/
│   │   ├── pdf_viewer.py
│   │   ├── mergeable_list.py
│   │   └── theme_tree.py
│   │
│   └── context_menus/
│       ├── document_menu.py
│       ├── theme_menu.py
│       └── page_menu.py
│
├── plugins/
│   ├── spawner/            # TextSpawner
│   │   ├── tray_plugin.py
│   │   ├── registry.py
│   │   └── hotkey.py
│   │
│   ├── background/         # Hintergrund-Services
│   │   ├── privacy_guard/
│   │   ├── sync_engine/
│   │   └── media_brain/
│   │
│   ├── dev_tools/          # Entwickler-Tools
│   │   ├── kompilator.py
│   │   └── license_gen.py
│   │
│   └── special_formats/
│       └── vcf_converter.py
│
├── utils/
│   ├── logger.py
│   ├── threading.py
│   └── temp_files.py
│
├── assets/
│   ├── icons/
│   └── styles/
│
└── logs/
```

---

## 6. Datenformate & Datenbanken

### 6.1 Formate

| Format | Verwendung |
|--------|------------|
| **JSON** | Settings, Bibliotheks-State, Marker-Dateien |
| **TXT** | Blacklists, Whitelists, Logs |
| **SQLite** | Optionale Indizierung |

### 6.2 Bibliotheks-State

```json
// .dokuzen_state.json
{
  "themes": [
    {"name": "Arbeit", "documents": ["path1", "path2"]},
    {"name": "Privat", "documents": ["path3"]}
  ],
  "read_status": {
    "path1": true,
    "path2": false
  }
}
```

### 6.3 Marker-Datei

```
// {pdf_name}_markers.txt
Seite 1: markiert
Seite 2: löschen
Seite 3: behalten
```

---

## 7. Workflows

### 7.1 Hauptworkflow

```
Dokument importieren → Thema zuweisen → Bearbeiten/Konvertieren
     ↓
Bibliothek durchsuchen → Vorschau → Aktion wählen
     ↓
PDF-Werkstatt (OCR, Schwärzen, Merge, Extract)
     ↓
Export / Speichern
```

### 7.2 PDF-Pipeline

```
PDF laden → OCR (falls Bild-PDF) → Schwärzen → Extrahieren → Merge → Export
```

### 7.3 Signale

| Signal | Trigger | Reaktion |
|--------|---------|----------|
| `document_added` | D&D Import | Liste aktualisieren |
| `theme_changed` | Theme-Wechsel | Dokumente filtern |
| `status_changed` | Gelesen-Toggle | Icon aktualisieren |
| `merge_requested` | Merge-Dialog | PDF erstellen |
| `operation_progress` | Lange Operation | Progress Bar |

---

## 8. Installation & Setup

### 8.1 Voraussetzungen

| Anforderung | Version |
|-------------|---------|
| Python | 3.10+ |
| OS | Windows 10/11 (primär) |
| Tesseract OCR | Optional (für OCR) |
| Poppler | Optional (für PDF-Vorschau) |

### 8.2 Installation

```bash
# Ordner öffnen
cd "C:\Users\User\OneDrive\.SOFTWARE\SUITEN\DokuZen"

# Virtuelle Umgebung (empfohlen)
python -m venv venv
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Starten
python main.py
# oder
start.bat
```

### 8.3 Abhängigkeiten

```
# GUI
PyQt6>=6.5.0
PyQt6-WebEngine>=6.5.0

# PDF
PyMuPDF>=1.23.0
pypdf>=3.0.0
pikepdf>=8.0.0
pdf2image>=1.16.0
reportlab>=4.0.0

# OCR
pytesseract>=0.3.10
Pillow>=10.0.0

# Office
python-docx>=1.0.0
pywin32>=306

# Text
pyperclip>=1.8.0
chardet>=5.0.0

# Utilities
pystray>=0.19.0
keyboard>=0.13.5
fuzzywuzzy>=0.18.0
```

---

## 9. Build & Deployment

### 9.1 PyInstaller

```bash
pyinstaller --onefile --windowed --icon=assets/icons/app_icon.ico main.py
```

---

## 10. Tests

```bash
# Import-Test
python -c "from gui.main_window import MainWindow; print('OK')"

# Vollständiger Test
python -m pytest tests/ -v
```

---

## 11. Changelog

### 11.1 Zusammenfassung

| Phase | Status | Inhalt |
|-------|--------|--------|
| Phase 1: Fundament | ✅ 100% | Core, Library, Main Window |
| Phase 2: PDF-Engine | ✅ 100% | Reader, Writer, Merger, Viewer |
| Phase 3: GUI-Dialoge | ✅ 100% | Alle Dialoge implementiert |
| Phase 4: Plugins | ✅ 100% | Spawner, Special Text |
| Phase 5: Spezialfeatures | ✅ 100% | Forms, Marker, Unlock |
| Phase 6: Polish | ✅ 100% | Themes, Shortcuts, Testing |
| Phase 7: Erweiterte Tools | ✅ 100% | Dev-Tools, Background-Services |
| Phase 8: Knowledge Engine | ✅ 100% | Suche, Index, Watcher |

**Gesamt:** 81 Dateien | ~18.500 Zeilen | 21/21 Workflows

---

## 12. Roadmap

### ✅ Erledigt

- [x] Bibliotheksverwaltung mit Themen
- [x] PDF-Werkstatt (Merge, Split, OCR, Schwärzung)
- [x] Konvertierung (Word ↔ PDF ↔ Text ↔ Bild)
- [x] Formular-Builder
- [x] TextSpawner Plugin
- [x] Background-Services (Privacy, Sync, Media)
- [x] Developer-Tools Plugin
- [x] Knowledge Engine

### 🔮 Zukunft

- [ ] Cloud-Sync
- [ ] Mobile Companion
- [ ] AI-gestützte Dokumentenanalyse

---

## 13. Lizenz

**MIT License**

---

## 14. Tastenkürzel

| Kürzel | Funktion |
|--------|----------|
| `Ctrl+I` | Dateien importieren |
| `Ctrl+N` | Neues Thema |
| `Ctrl+F` | Suchen |
| `Ctrl+P` | Vorschau ein/aus |
| `Ctrl+,` | Einstellungen |
| `F5` | Aktualisieren |
| `m` | Seite markieren (PDF Marker) |
| `d` | Seite löschen (PDF Marker) |
| `k` | Seite behalten (PDF Marker) |

---

## 15. UI-Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DOKUZEN PRO - HAUPTFENSTER                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─ TOOLBAR ──────────────────────────────────────────────────────────┐ │
│  │ [📂 Öffnen] [📥 Import] [➕ Neu] │ [🔍 Suche...] │ [⚙️]           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ BIBLIOTHEK ─┐  ┌─ DOKUMENTE ────────────┐  ┌─ VORSCHAU ──────────┐ │
│  │              │  │                        │  │                     │ │
│  │ 📁 Alle      │  │ [Drag & Drop Zone]     │  │  ┌─────────────┐   │ │
│  │ 📁 Arbeit    │  │                        │  │  │   PREVIEW   │   │ │
│  │ 📁 Privat    │  │ ☐ Vertrag.pdf     ✓   │  │  │             │   │ │
│  │ 📁 Archiv    │  │ ☐ Rechnung.docx       │  │  └─────────────┘   │ │
│  │              │  │ ☐ Notizen.txt     ✓   │  │                     │ │
│  │ ─────────    │  │                        │  │  Seite: [< 1/5 >]  │ │
│  │ ⬚ Gelesen    │  │ [RECHTSKLICK-MENÜ]     │  │                     │ │
│  │ ⬚ Ungelesen  │  │                        │  │  ┌─ QUICK-ACTIONS ─┐│ │
│  │              │  │                        │  │  │[Schwärzen]      ││ │
│  │ [+ Thema]    │  │                        │  │  │[OCR]            ││ │
│  └──────────────┘  └────────────────────────┘  └─────────────────────┘ │
│                                                                         │
│  ┌─ STATUSLEISTE ─────────────────────────────────────────────────────┐ │
│  │ 47 Dokumente │ 12 gelesen │ Letzte Aktion: Vertrag.pdf geöffnet    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

*Generiert: 2026-01-09 | DokuZen Pro Suite | ~18.500 Zeilen / 81 Dateien*
