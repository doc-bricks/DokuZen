# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Geändert / Changed (2026-08-16)
- **Discoverability, README-Design, Badges & Metadata Parity Check (Pfad B):**
  - Badges in `README.md` & `README_de.md` um Testsuite (281 Passed, 100% grün), Version (1.0.0), `doc-bricks` Ecosystem, `open-bricks` Umbrella und `llms.txt` Discovery synchronisiert.
  - Interaktive zweisprachige Mermaid Systemarchitektur-Diagramme (3-Panel GUI -> Core Engines -> Plugins & Background Services) integriert.
  - Geschwisterwerkzeuge-Matrix innerhalb der `doc-bricks`- und `open-bricks`-Ökosysteme (`PDFtoPDFocr`, `MediaBrain`, `TextBrain`, `DevCenter`, `CodeBox`) in beiden Sprachfassungen verlinkt.
  - Automatisierte Metadaten- & Manifest-Paritätstestsuite in `tests/test_metadata.py` implementiert (5/5 passed).
  - `pyproject.toml` um `[tool.ruff]` und `[tool.ruff.lint]` (py310, line-length 120, ruff check 100% sauber) sowie Changelog URL erweitert.
  - Whitespace- & Mojibake-Hygiene in `core/converter/formats.py`, `gui/panels/library_panel.py` und `plugins/special_text/encoding_fixer.py` bereinigt.
  - `llms.txt` Last-checked Timestamp auf `2026-08-16` und Teststand (281 passed) synchronisiert.

### Hinzugefügt / Added (2026-08-14)
- **Windows Store Packaging & Readiness Gate:**
  - `store_package/DokuZen/AppxManifest.xml` für Windows Desktop Bridge / MSIX Einreichung erstellt und validiert.
  - Store-Tile-Icons (44x44, 50x50, 150x150, 310x150, 310x310) via `tools/generate_store_icons.py` generiert.
  - Store-Screenshots (6/6 in nativer 1920x1080 Auflösung) via Offscreen PySide6 Generator `tools/generate_store_screenshots.py` erstellt.
  - Automatisierter Store-Readiness Preflight & Gatekeeper in `tools/check_store_readiness.py` und Testsuite in `tests/test_store_readiness.py` (6/6 passed) integriert.

### Geändert / Changed (2026-08-14)
- **Produktname:** Die Anwendung heißt jetzt **DokuZen** statt „DokuZen Pro“. Der Zusatz „Pro“ war nie ein Preismodell, sondern der frühere Suite-Name; eine kostenpflichtige Variante gibt es nicht. Angepasst wurden Dokumentation, Store-Listing, Datenschutzerklärung, Support-Dokument sowie nutzersichtbare GUI-Texte (Fenstertitel, Info-Dialog, Explorer-Kontextmenü, Tray, CLI-Hilfe). Artefaktnamen (`DokuZen-Pro-1.0.0-win64.exe`), Repository-URLs und historische Changelog-Einträge bleiben unverändert.

### Dokumentation / Documentation (2026-08-11)
- **GUI-CLI-Automationsgrenze:** Der lokale Desktop-Usecase und die fünf
  vorhandenen GUI-Startoptionen sind gegen README, Portierungsplan und
  Aufgabenregister readback-geprüft. Ohne belegten Remote-/Agenten-Usecase
  bleiben Headless-Batch-CLI und REST-API ausdrücklich Nicht-Bestandteile;
  ein späterer Ausbau setzt ein freigegebenes Sicherheitsmodell und isolierte
  Tests voraus.

### Geändert / Changed (2026-08-04)
- **Technische Hygiene & Maintenance:** `llms.txt` Discovery Index neu angelegt (Last-checked: 2026-08-04, 212 passed), `pyproject.toml` PEP 621 Metadata & Pytest Configuration erstellt, `README_de.md` angelegt und Shields.io Badges (`doc-bricks`, `open-bricks`, Pytest 212 passed, AGPL-3.0) & GFM Callout Box in `README.md` und `README_de.md` eingebunden.

### Behoben / Fixed (2026-08-03)
- **Dokumentensuche:** Das kompakte Suchfeld im Hauptfenster hat jetzt Tooltip,
  Accessible Name und Description. Screenreader erhalten damit Funktion und
  Tastaturweg (`Ctrl+F`), ohne das Drei-Panel-Layout zu verändern.
- **Tests:** `tests/test_source_platform_smoke.py` prüft den Assistive-Kontext
  des Suchfelds offscreen.

### Behoben / Fixed (2026-07-25)
- **Bildkonvertierung (ImageConverter PDF/Transparenz):** `ImageConverter.convert()` schlug bisher beim Konvertieren von Bildern mit Transparenz (RGBA/LA/PA sowie P-Palette mit Transparenz) nach PDF mit `KeyError: 'JPEG2000'` / `cannot save mode RGBA as PDF` fehl, da PDF keine Transparenzkanäle unterstützt und format='PDF' gefehlt hat. `ImageConverter` konvertiert Transparenzen bei PDF nun korrekt auf weißen Hintergrund und übergibt format='PDF' an Pillow.
- **CLI-Start:** `main.py` startet jetzt auch mit Argumenten fehlerfrei.
- **Icon-Generierung:** Transparente PNGs werden für EXE- und App-Icons unterstützt.
- **Dokumenten-Vorschau:** Text-Dokumente (.md, .txt) werden nun mit Syntax-Highlighting und korrektem Encoding dargestellt.
- **Suchfunktion:** Tag-Suche und Volltextsuche unterstützen Wildcards und Phrasen.

### Hinzugefügt / Added (2026-07-15)
- **PDF-Werkstatt:** Erweiterung um PDF-Marker, Seitennummerierung und Crop-Funktionen.
- **Code-Splitter:** Modulares Splitten von großen Quellcodedateien.
- **Privacy Guard:** Datenschutz-Ampel und Regex-basierte PII-Erkennung.

## [1.0.0] - 2026-07-01
- Initiales Release von DokuZen mit 22 integrierten Werkzeugen.
