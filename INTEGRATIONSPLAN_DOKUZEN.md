# 🏗️ INTEGRATIONSPLAN: DokuZen

> **Version:** 1.1.0  
> **Erstellt:** 2025-01-02  
> **Aktualisiert:** 2026-01-02  
> **Status:** 🔄 IN ENTWICKLUNG  
> **Log-Datei:** `INTEGRATION_LOG.md`

---

## 🎯 AKTUELLER FORTSCHRITT

```
Phase 1: Fundament         ██████████ 100% ✅
Phase 2: PDF-Engine        ██████████ 100% ✅
Phase 3: GUI-Dialoge       ██████████ 100% ✅
Phase 4: Plugins           ██████████ 100% ✅
Phase 5: Spezialfeatures   ██████████ 100% ✅
Phase 6: Polish            ██████████ 100% ✅
Phase 7: Erweiterte Tools  ██████████ 100% ✅
Phase 8: Knowledge Engine  ██████████ 100% ✅

🎉 PROJEKT VOLLSTÄNDIG ABGESCHLOSSEN!
Gesamt: ~81 Dateien | ~18.500 Zeilen Code | 21/21 Workflows (100%)
+ Knowledge Engine (Suche, Index, Watcher)
+ PDF-Annotationen (Adobe-Annäherung)
```

---

## 📋 INHALTSVERZEICHNIS

1. [Projektübersicht](#1-projektübersicht)
2. [Workflow-Erhaltung](#2-workflow-erhaltung)
3. [Architektur](#3-architektur)
4. [Modul-Mapping](#4-modul-mapping)
5. [Implementierungsplan](#5-implementierungsplan)
6. [Technische Spezifikationen](#6-technische-spezifikationen)
7. [Risiken & Mitigationen](#7-risiken--mitigationen)

---

## 1. PROJEKTÜBERSICHT

### 1.1 Ziel
Vereinigung von **11 Text- und PDF-Tools** zu einer einheitlichen Suite namens **DokuZen**.

### 1.2 Quellentools

| # | Tool | Pfad | Zeilen | Status |
|---|------|------|--------|--------|
| 1 | DokuReader | `Modul 1\Basis\` | 756 | 🟢 Master-Basis |
| 2 | TextPool | `Modul 1\poolen\` | 284 | 🟢 Integrieren |
| 3 | StapelKönig | `Modul 1\stapeln\` | 410 | 🟢 Integrieren |
| 4 | TextSpawner | `Modul 1\erstellen aus Zwischenablage\` | 442 | 🟡 Als Plugin |
| 5 | PylogText | `Modul 1\konvertieren\` | 205 | 🟢 Integrieren |
| 6 | FormKonstrukteur | `Modul 1\Formular erstellen\` | 444 | 🟢 Integrieren |
| 7 | PDFmarker2000 | `Modul 1\Auszüge erstellen\` | ~800 | 🟢 Integrieren |
| 8 | pyCuttertxt | `Modul 1\.py schneiden\` | ~200 | 🟢 Integrieren |
| 9 | PDFtoPDFocr | `Modul 2\alpha_PDFtoPDFocr\` | 336 | 🟢 Integrieren |
| 10 | PDFSchwärzer Pro | `Modul 2\PDFSchwärzer Pro\` | 1259 | 🟢 Kern-Engine |
| 11 | PDFunlock | `Modul 2\PDFunlock\` | 177 | 🟢 Integrieren |

### 1.3 Eliminierte Tools

| Tool | Grund | Ersatz durch |
|------|-------|--------------|
| PDFAuszug | Vollständig in PDFmarker2000 enthalten | PDFmarker2000 |

---

## 2. WORKFLOW-ERHALTUNG

### ⚠️ KRITISCH: Diese Workflows müssen 1:1 erhalten bleiben!


### 2.1 🖱️ RECHTSKLICK-WORKFLOWS

#### A) Explorer-Hintergrund-Rechtsklick (TextSpawner)
```
WORKFLOW: "Text hier spawnen"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. User klickt rechts im Explorer-Hintergrund
2. Menüpunkt "Text hier spawnen" erscheint
3. Zwischenablage wird als Datei gespeichert
4. Format: TXT/PDF/DOCX/RTF (konfigurierbar)
5. Speicherort: Aktueller Ordner

IMPLEMENTIERUNG:
├── Registry-Keys unter HKCU\Software\Classes
│   ├── Directory\Background\shell\TextSpawner
│   └── DesktopBackground\Shell\TextSpawner
├── Befehl: "{python}" "{script}" --paste "%V"
└── Modul: plugins/spawner/registry.py
```

#### B) Datei-Rechtsklick im DokuReader
```
WORKFLOW: Dokument-Kontextmenü
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rechtsklick auf Dokument zeigt:
├── 📂 Öffnen (Standardprogramm)
├── 👁️ Vorschau
├── ─────────────────────
├── ✓ Als gelesen markieren
├── ○ Als ungelesen markieren
├── ─────────────────────
├── 🔄 Konvertieren →
│   ├── zu PDF
│   ├── zu DOCX
│   └── zu TXT
├── 🔧 PDF-Werkstatt →
│   ├── Schwärzen
│   ├── Seiten markieren
│   ├── Zusammenführen
│   ├── Extrahieren
│   └── Entsperren
├── ─────────────────────
└── 🗑️ Aus Bibliothek entfernen

IMPLEMENTIERUNG:
├── gui/context_menus/document_menu.py
├── Signal: customContextMenuRequested
└── Actions: QAction mit Slots
```

---

### 2.2 📦 DRAG & DROP WORKFLOWS

#### A) Dateien aufeinander ziehen → Fusion (StapelKönig)
```
WORKFLOW: Drop-to-Merge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. User zieht Datei A auf Datei B
2. Ziel (B) wird gelb hervorgehoben (HIGHLIGHT_COLOR = #FFFFAA)
3. Bei Drop: A wird VOR B eingefügt
4. Nach Sortierung: "Stapeln" erzeugt Merge-PDF

IMPLEMENTIERUNG:
├── dragEnterEvent: Prüfe ob URLs vorhanden
├── dragMoveEvent: Highlight-Zielitem
├── dropEvent: 
│   ├── Wenn Ziel-Item existiert: Insert vor Ziel
│   └── Sonst: Append am Ende
├── Visuelles Feedback:
│   └── item.setBackground(QColor(255, 255, 170))
└── Modul: gui/widgets/mergeable_list.py
```

#### B) Dateien in TextPool ziehen → Zusammenführen
```
WORKFLOW: Drop-to-Pool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. .txt Dateien in Liste ziehen
2. Interne Reihenfolge per Drag ändern
3. "Start" → Alle Inhalte zusammenführen

IMPLEMENTIERUNG:
├── setDragDropMode(QListWidget.InternalMove)
├── Externe Drops: event.mimeData().urls()
├── Filter: supported_exts = {".txt"}
└── Modul: gui/dialogs/pool_dialog.py
```

#### C) Dateien in Bibliothek ziehen (DokuReader)
```
WORKFLOW: Drop-to-Library
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Dateien auf Thema ziehen
2. Verweise werden erstellt (Originale bleiben)
3. Doppelte werden automatisch erkannt

IMPLEMENTIERUNG:
├── Optional: tkinterdnd2 (Tkinter) ODER
├── PyQt6: setAcceptDrops(True)
├── Duplikat-Check: if path not in current_paths
└── Modul: gui/panels/library_panel.py
```

---

### 2.3 📋 ZWISCHENABLAGE-WORKFLOWS

#### A) Clipboard → Datei spawnen (TextSpawner)
```
WORKFLOW: Instant-Spawn
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Tray-Icon zeigt Menü
2. "Jetzt spawnen" klicken
3. Zwischenablage → Datei im konfigurierten Format
4. Speicherort: Aktueller Explorer-Ordner ODER Desktop

IMPLEMENTIERUNG:
├── Tray: pystray.Icon
├── Clipboard: pyperclip.paste()
├── Explorer-Pfad: win32gui (aktives Explorer-Fenster)
├── Dateiname: slugify(text[:50]) + timestamp
└── Modul: plugins/spawner/tray_plugin.py
```

#### B) Hotkey-Spawning
```
WORKFLOW: Tastenkürzel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Konfigurierbarer Hotkey (z.B. Ctrl+Shift+V)
2. Clipboard → Datei sofort

IMPLEMENTIERUNG:
├── keyboard oder pynput Bibliothek
├── Config: {"hotkey": "ctrl+shift+v"}
└── Modul: plugins/spawner/hotkey.py
```

---

### 2.4 🔍 SPEZIAL-WORKFLOWS

#### A) .py Zerschneiden (pyCuttertxt)
```
WORKFLOW: Python-Projekt aufteilen
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. .py Datei laden
2. Automatische Erkennung:
   ├── Imports
   ├── Klassen
   ├── Funktionen
   └── Main-Block
3. Export als separate .txt Dateien pro Abschnitt

IMPLEMENTIERUNG:
├── Parser: ast.parse() oder Regex
├── Output: Ordner mit Projektname + Timestamp
└── Modul: plugins/special_text/code_splitter.py
```

#### B) Formular erstellen (FormKonstrukteur)
```
WORKFLOW: Visual Form Builder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Felder hinzufügen:
   ├── Textfeld
   ├── Datum
   ├── Checkbox
   └── Bild
2. Live-Vorschau (HTML)
3. Export: PDF oder DOCX

IMPLEMENTIERUNG:
├── Template-System: JSON Schema
├── Preview: QWebEngineView oder temp HTML
├── Export: pdfkit (wkhtmltopdf) oder ReportLab
└── Modul: gui/dialogs/form_builder.py
```

#### C) PDF-Seiten markieren & extrahieren (PDFmarker2000)
```
WORKFLOW: Visual Page Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. PDF in Vorschau laden
2. Seiten markieren mit:
   ├── [M] Markiert (zum Extrahieren)
   ├── [D] Löschen
   └── [K] Behalten (default)
3. Hotkeys: m, d, k
4. Cluster-Erkennung: Zusammenhängende Seiten → eine PDF
5. Export: Einzelne PDFs pro Cluster

IMPLEMENTIERUNG:
├── Marker-Datei: {pdf_name}_markers.txt
│   Format: "Seite 1: markiert\nSeite 2: löschen\n..."
├── Cluster-Algo: find_contiguous_ranges()
├── Export: fitz.Document.insert_pdf()
└── Modul: gui/dialogs/pdf_marker.py
```

---

### 2.5 🔐 PDF-SICHERHEITS-WORKFLOWS

#### A) PDF Entsperren (PDFunlock)
```
WORKFLOW: Brute-Force Birthday
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Verschlüsselte PDF laden
2. Bekanntes Passwort eingeben ODER
3. Geburtstags-Range eingeben:
   ├── Von: 01.01.1950
   └── Bis: 31.12.2005
4. Automatisch DDMMYYYY Kombinationen testen
5. Bei Erfolg: Entschlüsselte PDF speichern

IMPLEMENTIERUNG:
├── Formate: DDMMYYYY, MMDDYYYY, YYYYMMDD
├── Progress: QProgressBar
├── Threading: QThread für Non-Blocking
└── Modul: core/pdf/security.py
```

#### B) PDF Schwärzen (PDFSchwärzer Pro)
```
WORKFLOW: Smart Redaction
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. PDF laden
2. Wortlisten definieren:
   ├── Blacklist (schwärzen)
   └── Whitelist (ignorieren)
3. OCR bei Bild-PDFs
4. Fuzzy Matching für Tippfehler
5. Preview mit Markierungen
6. Export: Geschwärztes PDF (AES-256 verschlüsselt)

IMPLEMENTIERUNG:
├── OCR: pytesseract
├── Fuzzy: fuzzywuzzy oder rapidfuzz
├── Schwärzung: fitz.Page.add_redact_annot()
├── Verschlüsselung: pikepdf.Encryption
└── Modul: core/redaction/
```

---


## 3. ARCHITEKTUR

### 3.1 Projektstruktur

```
DokuZen/
├── main.py                          # Einstiegspunkt
├── config/
│   ├── settings.json               # Globale Einstellungen
│   ├── theme.json                  # UI-Theme (Dark/Light)
│   ├── shortcuts.json              # Keyboard-Shortcuts
│   └── wordlists/                  # Schwärzungs-Listen
│       ├── blacklist_default.txt
│       └── whitelist_default.txt
│
├── core/                            # ══════ BACKEND (keine GUI!) ══════
│   ├── __init__.py
│   │
│   ├── library/                    # [DokuReader Logik]
│   │   ├── manager.py              # Bibliotheksverwaltung
│   │   ├── persistence.py          # JSON State (.dokubibliothek_state.json)
│   │   ├── search.py               # Suche & Filter
│   │   └── themes.py               # Themen-CRUD
│   │
│   ├── pdf/                        # ══════ PDF-Engine-Pool ══════
│   │   ├── reader.py               # Lesen: fitz, pypdf, pikepdf
│   │   ├── writer.py               # Erstellen/Modifizieren
│   │   ├── merger.py               # [StapelKönig] Zusammenführen
│   │   ├── splitter.py             # [PDFmarker2000] Extrahieren
│   │   ├── security.py             # [PDFunlock] Ver-/Entschlüsselung
│   │   ├── annotator.py            # Markierungen, Seitenzahlen
│   │   └── markers.py              # Marker-Datei Handling
│   │
│   ├── ocr/                        # ══════ OCR-Engine ══════
│   │   ├── engine.py               # [PDFtoPDFocr + Schwärzer]
│   │   ├── language.py             # Sprachpakete (deu, eng, ...)
│   │   ├── tesseract.py            # Tesseract-Wrapper
│   │   └── postprocess.py          # Nachbearbeitung
│   │
│   ├── redaction/                  # ══════ Schwärzen ══════
│   │   ├── detector.py             # Wortsuche
│   │   ├── fuzzy.py                # Fuzzy Matching
│   │   ├── blacklist.py            # Listenverwaltung
│   │   └── applier.py              # Schwärzung anwenden
│   │
│   ├── converter/                  # ══════ Format-Wandlung ══════
│   │   ├── to_pdf.py               # Alles → PDF
│   │   ├── from_pdf.py             # PDF → Alles
│   │   ├── text_tools.py           # [PylogText] .py/.log/.txt
│   │   ├── office.py               # Word COM / LibreOffice
│   │   └── spawner.py              # [TextSpawner] Clipboard → Datei
│   │
│   └── forms/                      # ══════ Formulare ══════
│       ├── builder.py              # [FormKonstrukteur] Logik
│       ├── templates.py            # Template-Management
│       ├── fields.py               # Feldtypen
│       └── export.py               # PDF/DOCX Export
│
├── gui/                             # ══════ FRONTEND (PyQt6) ══════
│   ├── __init__.py
│   ├── main_window.py              # Hauptfenster
│   ├── resources.py                # Qt-Ressourcen
│   │
│   ├── panels/                     # ══════ Hauptbereiche ══════
│   │   ├── library_panel.py        # Links: Themen/Ordner/Filter
│   │   ├── document_list.py        # Mitte: Dokumentliste
│   │   └── preview_panel.py        # Rechts: Vorschau
│   │
│   ├── dialogs/                    # ══════ Popup-Fenster ══════
│   │   ├── settings_dialog.py      # Einstellungen
│   │   ├── pdf_workshop.py         # PDF-Werkstatt (Tabs)
│   │   ├── redaction_dialog.py     # Schwärzungs-Dialog
│   │   ├── ocr_dialog.py           # OCR-Einstellungen
│   │   ├── merge_dialog.py         # [StapelKönig] Merge-Dialog
│   │   ├── pool_dialog.py          # [TextPool] Pool-Dialog
│   │   ├── convert_dialog.py       # Konvertierungs-Optionen
│   │   ├── form_builder.py         # [FormKonstrukteur] Editor
│   │   ├── marker_dialog.py        # [PDFmarker2000] Seiten markieren
│   │   ├── unlock_dialog.py        # [PDFunlock] Entsperr-Dialog
│   │   └── code_splitter_dialog.py # [pyCuttertxt] .py zerschneiden
│   │
│   ├── widgets/                    # ══════ Wiederverwendbar ══════
│   │   ├── pdf_viewer.py           # PDF-Vorschau Widget
│   │   ├── progress_widget.py      # Fortschrittsanzeige
│   │   ├── file_list.py            # Dateiliste mit D&D
│   │   ├── mergeable_list.py       # [StapelKönig] D&D-Merge-Liste
│   │   ├── status_bar.py           # Statusleiste
│   │   └── theme_tree.py           # Themen-Baumansicht
│   │
│   └── context_menus/              # ══════ Rechtsklick-Menüs ══════
│       ├── document_menu.py        # Dokument-Kontextmenü
│       ├── theme_menu.py           # Themen-Kontextmenü
│       └── page_menu.py            # Seiten-Kontextmenü
│
├── plugins/                         # ══════ ERWEITERUNGEN ══════
│   ├── __init__.py
│   ├── base_plugin.py              # Plugin-Interface
│   │
│   ├── spawner/                    # [TextSpawner] Tray-App
│   │   ├── __init__.py
│   │   ├── tray_plugin.py          # Tray-Icon & Menü
│   │   ├── clipboard_monitor.py    # Zwischenablage überwachen
│   │   ├── registry.py             # Windows-Registry (Kontextmenü)
│   │   └── hotkey.py               # Globale Hotkeys
│   │
│   └── special_text/               # Spezial-Text-Tools
│       ├── __init__.py
│       └── code_splitter.py        # [pyCuttertxt] .py zerschneiden
│
├── utils/                           # ══════ HILFSFUNKTIONEN ══════
│   ├── __init__.py
│   ├── logger.py                   # Rotating Logs
│   ├── threading.py                # Worker-Threads
│   ├── temp_files.py               # Temp-Management
│   ├── platform.py                 # OS-Erkennung
│   └── validators.py               # Input-Validierung
│
└── assets/
    ├── icons/
    │   ├── app_icon.ico
    │   ├── tray_icon.ico
    │   └── ... (alle Tool-Icons)
    └── styles/
        ├── dark.qss
        └── light.qss
```

---

### 3.2 Dependency-Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                            │                                     │
│              ┌─────────────┴─────────────┐                       │
│              ▼                           ▼                       │
│      ┌───────────────┐           ┌───────────────┐               │
│      │  gui/         │           │  plugins/     │               │
│      │  main_window  │           │  spawner/     │               │
│      └───────┬───────┘           └───────────────┘               │
│              │                                                   │
│    ┌─────────┼─────────┬─────────────┐                           │
│    ▼         ▼         ▼             ▼                           │
│ ┌──────┐ ┌──────┐ ┌──────────┐ ┌───────────┐                     │
│ │panels│ │dialogs│ │widgets   │ │context_   │                    │
│ │      │ │      │ │          │ │menus      │                     │
│ └──┬───┘ └──┬───┘ └────┬─────┘ └───────────┘                     │
│    │        │          │                                         │
│    └────────┴──────────┴─────────────┐                           │
│                                      ▼                           │
│                            ┌─────────────────┐                   │
│                            │     core/       │                   │
│                            └────────┬────────┘                   │
│         ┌──────────┬───────────┬────┴────┬──────────┬──────┐     │
│         ▼          ▼           ▼         ▼          ▼      ▼     │
│    ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌─────┐ ┌─────┐  │
│    │library │ │pdf/    │ │ocr/     │ │redact/ │ │conv/│ │forms│  │
│    └────────┘ └────────┘ └─────────┘ └────────┘ └─────┘ └─────┘  │
│                                                                  │
│    ══════════════════════════════════════════════════════════    │
│                            utils/                                │
│         logger │ threading │ temp_files │ platform               │
└─────────────────────────────────────────────────────────────────┘
```

---


## 4. MODUL-MAPPING

### 4.1 Detailliertes Mapping: Alt → Neu

| Altes Tool | Alte Datei | Neue Location | Erhaltene Workflows |
|------------|------------|---------------|---------------------|
| **DokuReader** | `Basis\DokuReader.py` | `gui/main_window.py` + `core/library/` | Rechtsklick, D&D, Themen, Gelesen-Status |
| **TextPool** | `poolen\TextPool.py` | `core/converter/text_tools.py` + `gui/dialogs/pool_dialog.py` | D&D Reihenfolge, Zusammenführen |
| **StapelKönig** | `stapeln\StapelKönig V2.0.py` | `core/pdf/merger.py` + `gui/dialogs/merge_dialog.py` | Drop-to-Merge, Gelbe Highlight |
| **TextSpawner** | `erstellen aus Zwischenablage\TxtSpawnerNew.py` | `plugins/spawner/` | Tray, Registry-Kontextmenü, Hotkey |
| **PylogText** | `konvertieren\logtotxt.py` | `core/converter/text_tools.py` | Batch .py/.log ↔ .txt |
| **FormKonstrukteur** | `Formular erstellen\FormConstructor V1.5.py` | `core/forms/` + `gui/dialogs/form_builder.py` | Visual Builder, Templates, Export |
| **PDFmarker2000** | `Auszüge erstellen\pdfmarker2000.py` | `core/pdf/splitter.py` + `gui/dialogs/marker_dialog.py` | Hotkeys (m,d,k), Cluster-Export |
| **pyCuttertxt** | `.py schneiden\pyCuttertxt.py` | `plugins/special_text/code_splitter.py` | Auto-Parse, Ordner-Export |
| **PDFtoPDFocr** | `alpha_PDFtoPDFocr\PDFtoPDFocr_2.py` | `core/ocr/` | Auto-Sprach-Download, Batch |
| **PDFSchwärzer Pro** | `PDFSchwärzer Pro\PDF schwärzer pro V2_5.py` | `core/redaction/` + `core/ocr/` | Fuzzy, Black/Whitelist, AES-256 |
| **PDFunlock** | `PDFunlock\PDFunlockBirthday.py` | `core/pdf/security.py` | Brute-Force Birthday, Config |

---

### 4.2 Workflow-Integration in GUI

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DOKUZEN PRO - HAUPTFENSTER                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ TOOLBAR ──────────────────────────────────────────────────────────┐ │
│  │ [📂 Öffnen] [📥 Import] [➕ Neu] │ [🔍 Suche...] │ [⚙️]           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ BIBLIOTHEK ─┐  ┌─ DOKUMENTE ────────────┐  ┌─ VORSCHAU ──────────┐ │
│  │              │  │                        │  │                     │ │
│  │ 📁 Alle      │  │ [Drag & Drop Zone]     │  │  ┌─────────────┐   │ │
│  │ 📁 Arbeit    │  │                        │  │  │             │   │ │
│  │ 📁 Privat    │  │ ☐ Vertrag.pdf     ✓   │  │  │   PREVIEW   │   │ │
│  │ 📁 Archiv    │  │ ☐ Rechnung.docx       │  │  │             │   │ │
│  │              │  │ ☐ Notizen.txt     ✓   │  │  └─────────────┘   │ │
│  │ ─────────    │  │                        │  │                     │ │
│  │ ⬚ Gelesen    │  │ [RECHTSKLICK-MENÜ]     │  │  Seite: [< 1/5 >]  │ │
│  │ ⬚ Ungelesen  │  │ ├─ Öffnen              │  │                     │ │
│  │              │  │ ├─ Konvertieren →      │  │  ┌─ QUICK-ACTIONS ─┐│ │
│  │ [+ Thema]    │  │ ├─ PDF-Werkstatt →     │  │  │[Markieren]      ││ │
│  │              │  │ └─ Status →            │  │  │[Extrahieren]    ││ │
│  │              │  │                        │  │  │[Schwärzen]      ││ │
│  │              │  │                        │  │  │[OCR]            ││ │
│  └──────────────┘  └────────────────────────┘  └─────────────────────┘ │
│                                                                         │
│  ┌─ STATUSLEISTE ─────────────────────────────────────────────────────┐ │
│  │ 47 Dokumente │ 12 gelesen │ Letzte Aktion: Vertrag.pdf geöffnet    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

TRAY-ICON (TextSpawner Plugin)
┌──────────────────────┐
│ 📄 Jetzt spawnen     │  → Clipboard → Datei
│ ─────────────────    │
│ Format: TXT ▼        │
│ ─────────────────    │
│ ⚙️ Einstellungen    │
│ 🚪 Beenden          │
└──────────────────────┘
```

---

## 5. IMPLEMENTIERUNGSPLAN

### 5.1 Phasen-Übersicht

```
PHASE 1: Fundament ════════════════════════════════════════════ [Woche 1-2]
│
├── □ Projektstruktur anlegen
├── □ core/library/ (DokuReader-Logik)
├── □ gui/main_window.py Basis
├── □ gui/panels/ Grundlayout
├── □ Config-System
└── □ utils/logger.py

PHASE 2: PDF-Kern ═════════════════════════════════════════════ [Woche 3-4]
│
├── □ core/pdf/reader.py
├── □ core/pdf/writer.py
├── □ core/pdf/merger.py (StapelKönig)
├── □ gui/widgets/pdf_viewer.py
├── □ gui/widgets/mergeable_list.py (D&D mit Highlight)
└── □ gui/dialogs/merge_dialog.py

PHASE 3: OCR & Schwärzung ═════════════════════════════════════ [Woche 5-6]
│
├── □ core/ocr/engine.py
├── □ core/ocr/tesseract.py
├── □ core/redaction/detector.py
├── □ core/redaction/fuzzy.py
├── □ gui/dialogs/ocr_dialog.py
└── □ gui/dialogs/redaction_dialog.py

PHASE 4: Konvertierung ════════════════════════════════════════ [Woche 7]
│
├── □ core/converter/to_pdf.py
├── □ core/converter/from_pdf.py
├── □ core/converter/text_tools.py (PylogText + TextPool)
├── □ core/converter/office.py
└── □ gui/dialogs/convert_dialog.py + pool_dialog.py

PHASE 5: Spezialfeatures ══════════════════════════════════════ [Woche 8]
│
├── □ core/pdf/security.py (Unlock)
├── □ core/pdf/splitter.py (Marker)
├── □ core/forms/ (FormKonstrukteur)
├── □ gui/dialogs/form_builder.py
├── □ gui/dialogs/marker_dialog.py
└── □ gui/dialogs/unlock_dialog.py

PHASE 6: Plugins & Polish ═════════════════════════════════════ [Woche 9-10]
│
├── □ plugins/spawner/ (Tray-Icon, Registry, Hotkey)
├── □ plugins/special_text/ (.py schneiden)
├── □ gui/context_menus/ (Rechtsklick-Menüs)
├── □ Keyboard-Shortcuts
├── □ Theme-System (Dark/Light)
└── □ Testing & Bugfixes
```

---

### 5.2 Detaillierte Tasks

#### PHASE 1: Fundament

| Task | Priorität | Abhängigkeit | Geschätzt |
|------|-----------|--------------|-----------|
| Projektordner & __init__.py | 🔴 Kritisch | - | 1h |
| config/settings.json Schema | 🔴 Kritisch | - | 2h |
| utils/logger.py (Rotating) | 🔴 Kritisch | - | 2h |
| core/library/persistence.py | 🔴 Kritisch | - | 3h |
| core/library/manager.py | 🔴 Kritisch | persistence.py | 4h |
| core/library/themes.py | 🟡 Hoch | manager.py | 2h |
| gui/main_window.py Skeleton | 🔴 Kritisch | - | 4h |
| gui/panels/library_panel.py | 🔴 Kritisch | themes.py | 4h |
| gui/panels/document_list.py | 🔴 Kritisch | manager.py | 4h |
| gui/panels/preview_panel.py | 🟡 Hoch | - | 3h |

#### PHASE 2: PDF-Kern

| Task | Priorität | Abhängigkeit | Geschätzt |
|------|-----------|--------------|-----------|
| core/pdf/reader.py | 🔴 Kritisch | - | 4h |
| core/pdf/writer.py | 🔴 Kritisch | reader.py | 3h |
| core/pdf/merger.py | 🔴 Kritisch | reader.py, writer.py | 5h |
| core/pdf/markers.py | 🟡 Hoch | - | 2h |
| gui/widgets/pdf_viewer.py | 🔴 Kritisch | reader.py | 6h |
| gui/widgets/mergeable_list.py | 🔴 Kritisch | - | 4h |
| gui/dialogs/merge_dialog.py | 🟡 Hoch | merger.py, mergeable_list | 4h |
| Drop-to-Merge Highlight | 🟡 Hoch | mergeable_list.py | 2h |

#### PHASE 3-6: [Analog strukturiert]

---


## 6. TECHNISCHE SPEZIFIKATIONEN

### 6.1 Abhängigkeiten

```python
# requirements.txt

# === GUI ===
PyQt6>=6.5.0
PyQt6-WebEngine>=6.5.0  # Für Form-Preview

# === PDF ===
PyMuPDF>=1.23.0         # fitz - Hauptbibliothek
pypdf>=3.0.0            # Merging/Splitting
pikepdf>=8.0.0          # Verschlüsselung
pdf2image>=1.16.0       # PDF → Bild
reportlab>=4.0.0        # PDF-Erstellung

# === OCR ===
pytesseract>=0.3.10
Pillow>=10.0.0

# === Office ===
python-docx>=1.0.0      # DOCX lesen/schreiben
odfpy>=1.4.0            # ODT lesen
pywin32>=306            # Word COM (Windows)

# === Text ===
pyperclip>=1.8.0        # Clipboard
chardet>=5.0.0          # Encoding-Erkennung

# === Utilities ===
pystray>=0.19.0         # Tray-Icon
keyboard>=0.13.5        # Globale Hotkeys
fuzzywuzzy>=0.18.0      # Fuzzy Matching
python-Levenshtein>=0.21.0  # Für fuzzywuzzy Speed
```

### 6.2 Konfigurationsschema

```json
// config/settings.json
{
  "version": "1.0.0",
  "app": {
    "theme": "light",
    "language": "de",
    "last_directory": "",
    "window_state": {
      "geometry": [100, 100, 1400, 900],
      "maximized": false,
      "panel_sizes": [200, 600, 400]
    }
  },
  "library": {
    "state_file": "~/.dokuzen_state.json",
    "auto_save": true,
    "duplicate_check": true
  },
  "spawner": {
    "enabled": true,
    "format": "TXT",
    "design_mode": false,
    "hotkey": "ctrl+shift+v",
    "registry_enabled": true
  },
  "pdf": {
    "default_encryption": "AES-256",
    "compression": true,
    "ocr_language": "deu+eng"
  },
  "redaction": {
    "default_blacklist": "config/wordlists/blacklist_default.txt",
    "default_whitelist": "config/wordlists/whitelist_default.txt",
    "fuzzy_threshold": 80,
    "master_password": null
  },
  "logging": {
    "level": "INFO",
    "max_size_mb": 2,
    "backup_count": 4,
    "file": "logs/dokuzen.log"
  }
}
```

### 6.3 Signale & Slots (PyQt6)

```python
# Zentrale Signale für Workflow-Integration

class DocumentSignals(QObject):
    # Bibliothek
    document_added = Signal(str)        # Pfad
    document_removed = Signal(str)      # Pfad
    theme_changed = Signal(str)         # Theme-Name
    status_changed = Signal(str, bool)  # Pfad, is_read
    
    # PDF-Operationen
    merge_requested = Signal(list)      # Liste von Pfaden
    extract_requested = Signal(str, list)  # PDF-Pfad, Seitennummern
    redact_requested = Signal(str)      # PDF-Pfad
    unlock_requested = Signal(str)      # PDF-Pfad
    
    # Spawner
    clipboard_spawn = Signal(str, str)  # Text, Format
    
    # Progress
    operation_started = Signal(str)     # Operation-Name
    operation_progress = Signal(int)    # Prozent
    operation_finished = Signal(bool, str)  # Erfolg, Nachricht
```

---

## 7. RISIKEN & MITIGATIONEN

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| PyQt6 Migration komplex | 🟡 Mittel | 🔴 Hoch | Schrittweise migrieren, alte Tools parallel |
| Registry-Zugriff scheitert | 🟢 Niedrig | 🟡 Mittel | Try/Except, Admin-Rechte prüfen |
| Tesseract nicht installiert | 🟡 Mittel | 🟡 Mittel | Graceful Degradation, Installationshinweis |
| Word COM nicht verfügbar | 🟡 Mittel | 🟡 Mittel | LibreOffice als Fallback |
| Workflow-Bruch bei Integration | 🔴 Hoch | 🔴 Hoch | Jede Workflow einzeln testen vor Merge |
| Performance bei großen PDFs | 🟡 Mittel | 🟡 Mittel | Threading, Lazy Loading, Caching |

---

## 8. ERFOLGSKRITERIEN

### 8.1 Funktionale Kriterien

- [ ] Alle 10 Workflows aus Abschnitt 2 funktionieren identisch
- [ ] Rechtsklick-Menüs zeigen alle Optionen
- [ ] Drag & Drop mit visueller Rückmeldung
- [ ] Zwischenablage → Datei in < 1 Sekunde
- [ ] PDF-Merge behält Reihenfolge
- [ ] OCR erkennt deutsch + englisch
- [ ] Schwärzung irreversibel

### 8.2 Nicht-funktionale Kriterien

- [ ] Start-Zeit < 3 Sekunden
- [ ] RAM-Verbrauch < 500 MB (ohne große PDFs)
- [ ] Keine UI-Freezes bei Operationen > 1 Sekunde
- [ ] Logs rotieren bei 2 MB
- [ ] Config überlebt Crashes

---

## 9. ANHANG

### 9.1 Referenz: Alte Tool-Pfade

```
C:\Users\User\OneDrive\.SOFTWARE\TOOLS\TEXT\
├── Modul 1 VERWALTEN und GUI\
│   ├── Basis\DokuReader.py
│   ├── poolen\TextPool.py
│   ├── stapeln\StapelKönig V2.0.py
│   ├── erstellen aus Zwischenablage\TxtSpawnerNew.py
│   ├── konvertieren\logtotxt.py
│   ├── Formular erstellen\FormConstructor V1.5.py
│   ├── Auszüge erstellen\pdfmarker2000.py
│   └── .py schneiden\pyCuttertxt.py
│
└── Modul 2 BACKEND BEARBEITEN\
    ├── alpha_PDFtoPDFocr\PDFtoPDFocr_2.py
    ├── PDFSchwärzer Pro\PDF schwärzer pro V2_5.py
    └── PDFunlock\PDFunlockBirthday.py
```

### 9.2 Kontakt & Verantwortlichkeit

- **Projektverantwortlich:** User
- **Log-Datei:** `INTEGRATION_LOG.md`
- **Erstellt:** 2025-01-02

---

*Dieses Dokument wird laufend aktualisiert. Änderungen werden in der Log-Datei protokolliert.*



---

## 10. ERWEITERUNG: NEUE TOOLS (aus `_neu/`)

> **Hinzugefügt:** 2025-01-02  
> **Referenz:** INTEGRATIONSBEWERTUNG_NEUE_TOOLS.md

### 10.1 Neue Quellentools

| # | Tool | Pfad | Status | Kategorie |
|---|------|------|--------|-----------|
| 12 | EncodingFixer | `_neu\EncodingFixer\` | 🟢 INTEGRIEREN | Text-Reparatur |
| 13 | PythonBox (A2 Editor) | `_neu\A2 Editor\` | 🟢 INTEGRIEREN | Code-Editor |
| 14 | IcoBuilder | `_neu\IcoBuilder.py` | 🟢 INTEGRIEREN | Bild→ICO |
| 15 | pic2pic | `_neu\pic2pic.py` | 🟢 INTEGRIEREN | Bild-Konverter |
| 16 | SQLiteViewer | `_neu\SQLiteViewer.py` | 🟢 INTEGRIEREN | DB-Viewer |
| 17 | Ampelclip | `_neu\B3_Ampelclip\` | 🟡 HINTERGRUND | Datenschutz |
| 18 | ProSync | `_neu\A2 ProSync\` | 🟡 HINTERGRUND | Sync-Engine |
| 19 | MediaBrain | `_neu\A1 MediaBrain\` | 🟡 HINTERGRUND | Medien-Sammlung |
| 20 | UltimateKompilator | `_neu\UltimateKompilator.py` | 🔵 PLUGIN | Dev-Tools |
| 21 | generate_third_party_licenses | `_neu\generate_third_party_licenses.py` | 🔵 PLUGIN | Dev-Tools |
| 22 | Make23toVCF3 | `_neu\Make23toVCF3.py` | 🔵 PLUGIN | Spezialformat |
| 23 | ProFiler | `_neu\A1 ProFiler\` | 🔴 EIGENSTÄNDIG | Zu komplex |
| 24 | SoftwCenter | `_neu\B1_SoftwCenter\` | 🔴 EIGENSTÄNDIG | Anderer Zweck |

---

### 10.2 Erweiterte Workflows

#### A) Rechtsklick auf .py Datei
```
WORKFLOW: Python-Entwickler-Kontext
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rechtsklick auf .py zeigt:
├── 📂 Öffnen (PythonBox Editor)
├── 🔧 Encoding reparieren       [EncodingFixer]
├── ✂️ Zerschneiden              [pyCuttertxt]
├── 📜 Lizenzen generieren       [generate_third_party_licenses]
├── 📦 Kompilieren → EXE         [UltimateKompilator]
└── 🔄 Konvertieren → TXT        [PylogText]

IMPLEMENTIERUNG:
├── gui/context_menus/python_menu.py
├── Condition: file.suffix == '.py'
└── Dev-Tools nur wenn Plugin aktiv
```

#### B) Rechtsklick auf Bilddatei
```
WORKFLOW: Bild-Konvertierung
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rechtsklick auf Bild zeigt:
├── 📂 Öffnen (Standardprogramm)
├── 🔄 Konvertieren zu →
│   ├── PNG
│   ├── JPG
│   ├── WebP
│   ├── BMP
│   ├── ICO                      [IcoBuilder]
│   └── PDF
└── ✂️ Größe ändern              [pic2pic]

IMPLEMENTIERUNG:
├── core/converter/image_tools.py
├── gui/context_menus/image_menu.py
└── Pillow als Engine
```

#### C) Rechtsklick auf Datenbank
```
WORKFLOW: SQLite-Viewer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rechtsklick auf .db/.sqlite zeigt:
├── 📂 Öffnen (SQLiteViewer)
├── 📤 Export als CSV
└── 📤 Export als Excel

IMPLEMENTIERUNG:
├── gui/dialogs/sqlite_viewer.py
├── Read-Only als Standard
└── SQL-Query-Modus optional
```

---

### 10.3 Hintergrund-Services

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EINSTELLUNGEN → HINTERGRUND-SERVICES                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ DATENSCHUTZ ──────────────────────────────────────────────────────┐ │
│  │ [✓] Datenschutz-Ampel aktivieren                                   │ │
│  │     Überwacht Zwischenablage auf sensible Daten                    │ │
│  │     Tray-Icon: 🔴 Rot / 🟡 Gelb / 🟢 Grün                          │ │
│  │     [Blacklist bearbeiten...] [Whitelist bearbeiten...]            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ SYNCHRONISATION ──────────────────────────────────────────────────┐ │
│  │ [✓] ProSync aktivieren                                             │ │
│  │     Synchronisiert Bibliothek-Ordner automatisch                   │ │
│  │     [Sync-Verbindungen verwalten...]                               │ │
│  │     [Intervall: 15 min ▼]                                          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ MEDIEN ───────────────────────────────────────────────────────────┐ │
│  │ [ ] MediaBrain aktivieren                                          │ │
│  │     Sammelt Medien aus Streaming-Diensten                          │ │
│  │     [MediaBrain-Dashboard öffnen...]                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│                                          [Übernehmen] [Abbrechen]       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 10.4 Erweiterte Architektur

```
plugins/
├── ... [bestehend]
│
├── background/                  # Hintergrund-Services
│   ├── __init__.py
│   ├── base_service.py          # Abstract Base Class
│   │
│   ├── privacy_guard/           # [Ampelclip]
│   │   ├── __init__.py
│   │   ├── clipboard_monitor.py
│   │   ├── ampel_tray.py
│   │   ├── detector.py
│   │   └── config.py
│   │
│   ├── sync_engine/             # [ProSync]
│   │   ├── __init__.py
│   │   ├── sync_worker.py
│   │   ├── db_safety.py         # WAL-Checkpoint
│   │   ├── connection_manager.py
│   │   └── config.py
│   │
│   └── media_brain/             # [MediaBrain]
│       ├── __init__.py
│       ├── core.py
│       ├── providers/
│       │   ├── netflix.py
│       │   ├── youtube.py
│       │   └── spotify.py
│       └── config.py
│
├── dev_tools/                   # Developer-Plugin
│   ├── __init__.py
│   ├── kompilator.py            # [UltimateKompilator]
│   ├── license_gen.py           # [generate_third_party_licenses]
│   ├── publisher.py             # [WindowsStorePublisher_3]
│   └── manifest.json
│
└── special_formats/             # Spezialformate-Plugin
    ├── __init__.py
    ├── vcf_converter.py         # [Make23toVCF3]
    └── manifest.json
```

---

### 10.5 Neue Phase 7

```
PHASE 7: Erweiterte Tools & Services ══════════════════════ [Woche 11-12]
│
├── □ core/converter/encoding.py (EncodingFixer)
├── □ core/converter/image_tools.py (IcoBuilder + pic2pic)
├── □ gui/dialogs/code_editor.py (PythonBox)
├── □ gui/dialogs/sqlite_viewer.py
├── □ gui/dialogs/encoding_dialog.py
├── □ gui/context_menus/python_menu.py
├── □ gui/context_menus/image_menu.py
├── □ plugins/background/base_service.py
├── □ plugins/background/privacy_guard/
├── □ plugins/background/sync_engine/
├── □ plugins/dev_tools/
└── □ Einstellungen-Dialog für Background-Services
```

---

