# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [1.0.1] - 2026-08-23

### Fixed
- **Store-Paket registrierte keinen `.pdf`-Handler:** Das `AppxManifest.xml` deklarierte
  weder `uap:FileTypeAssociation` noch `uap3:AppExecutionAlias`. Eine aus dem Store
  installierte App hätte keine Dateizuordnung mitgebracht und wäre nicht unter „Öffnen mit"
  erschienen. Ergänzt: `.pdf` sowie der Ausführungsalias `dokuzen.exe`.
- **Sprachverlust im Paket:** Das zuletzt gebaute MSIX enthielt nur `en-us`, obwohl das
  gepflegte Manifest `de-de` und `en-us` führte. `languages` ist jetzt in
  `store_package.json` hinterlegt, damit der Generator beide Sprachen erzeugt.

### Changed
- Paketversion auf `1.0.1.0`; `MaxVersionTested` von `10.0.19041.0` auf `10.0.22621.0`.
- Manifest wird jetzt aus `store_package.json` erzeugt (Generator store-packager 2.2.0)
  statt von Hand gepflegt.

### Notes
- **Nicht eingereicht.** DokuZen ist noch nicht im Store veröffentlicht: Es existiert eine
  offene Erstveröffentlichungs-Submission (`1152921505701654962`, Status `PendingCommit`)
  mit vier Validierungsfehlern (`InvalidCategory`, `NoValidPackages` ×2,
  `InvalidPricingAvailabilitySettings`). Diese Submission wurde bewusst nicht angetastet —
  eine Erstveröffentlichung braucht Kategorie, Preis und Alterseinstufung aus dem
  Partner Center. Das gebaute Paket liegt bereit unter
  `releases/windowsstore/v1.0.1/DokuZen-1.0.1.0.msix`.

## [Unreleased]

### Behoben & Gehärtet / Fixed & Hardened (2026-08-24, Security & License Compliance Audit)
- **Dependency-Floor-Härtung (OSV / GHSA Audit):** Mindestversionsgrenzen in `pyproject.toml` und `requirements.txt` gehärtet:
  - `Pillow>=12.0.0` schützt gegen 35+ bekannte CVEs/GHSAs älterer Versionen (Heap-Buffer-Overflows, Denial-of-Service, Command Injection).
  - `PyMuPDF>=1.24.0`, `pikepdf>=8.15.1`, `pytesseract>=0.3.13`, `reportlab>=4.2.0` und `pystray>=0.19.5` auf verifizierte, sichere Mindestversionen gehoben.
- **Third-Party License Inventory (`THIRD_PARTY_LICENSES.txt`):** Turnusgemäß auf den Stand `2026-08-24` auditiert; direkte Abhängigkeiten, Lizenzmodelle (AGPL/GPL/LGPL/Apache/MIT/BSD/0BSD/MPL) und Copyleft-Grenzwerte für Store- und Binärdistributionen verifiziert.
- **Sicherheits- & Lizenzvertrags-Testsuite:** Neue Testsuite `tests/test_security_license_contract.py` integriert (6 Tests: Dependency-Floor-Härtung, Lizenzinventar, zweisprachige `SECURITY.md` mit 48h-SLA und Zero-Egress Invarianten, Secret-/Token-/Pfad-Hygiene, `.gitignore`-Schutz gegen Sync-Konflikte und Locks, AGPL-3.0 SPDX-Parität).
- **Dateipfad- & Gitignore-Hygiene:** Legacy-Pfad in `SUITE_DOKUZEN_TEMPLATE.md` bereinigt; `.gitignore` um umfassende Schutzmuster (`*.conflict`, `*.sync-conflict-*`, `LOCK*.txt`, `.env`) erweitert.
- **Gesamtstatus:** 310/310 Tests bestanden (100% grün).

### Hinzugefügt / Added (2026-08-23, Linux-Portierung)
- **Portables Linux-Bundle:** `tools/build_linux_bundle.py` validiert den Paketvertrag und erzeugt unter Linux ein reproduzierbares PyInstaller-onedir-Archiv `DokuZen-1.0.0-linux-<architektur>.tar.gz`.
- **Freedesktop-/AppStream-Metadaten:** Desktop-Eintrag, 512px-Iconpfad und zweisprachige AppStream-Beschreibung unter `packaging/linux/` ergänzt.
- **CI-Artefaktpfad:** `.github/workflows/linux-bundle.yml` validiert Metadaten/Tests und baut bei manuellem Start oder Versionstag ein herunterladbares Linux-Artefakt.
- **Bundle-Ressourcen:** Assets, Konfiguration und der sechssprachige Übersetzungskatalog werden in das Bundle aufgenommen; `TranslationSystem` löst Ressourcen nun korrekt über PyInstallers `_MEIPASS` auf.
- **Contract-Tests:** Drei Tests sichern Metadaten, shell-freie PyInstaller-Argumente und Übersetzungs-Readback im Bundle; Gesamtstand 304 bestandene Tests.

### Geändert / Changed (2026-08-23)
- **Discoverability, Visual Showcase, Mermaid Architecture, Lifecycle & Security Gate (Pfad B):**
  - **Visuelle Showcase-Galerie:** Hochauflösende 1080p Store-Screenshots (`01_bibliothek.png`, `02_pdf_vorschau.png`, `03_ocr_dialog.png`, `04_schwaerzung.png`, `05_konvertierung.png`, `06_batch_verarbeitung.png`) mit zweisprachigen Detailbeschreibungen in `README.md` & `README_de.md` integriert.
  - **Interaktive Mermaid-Diagramme:** Schichtenarchitektur (`flowchart TD` für 3-Panel PySide6 GUI, Core Processing Engines und lokales Storage/MSIX Subsystem) und End-to-End Dokumenten- & PDF-Verarbeitungszyklus (`sequenceDiagram`) integriert.
  - **Zweisprachige Schnellnavigation & Badges:** Strukturierte 12-Punkte-Navigation in `README.md` & `README_de.md` eingebunden; Shields.io Badges für CI (`source-platform-smoke.yml`), Teststatus (`301 passed | 100%`), Python Matrix (`3.10-3.13`), Plattformen (`Windows | macOS | Linux`), Datenschutz (`100% Local-First | Zero-Egress`) und Sicherheit synchronisiert.
  - **Sicherheitsrichtlinie (`SECURITY.md`):** Auf vollständigen zweisprachigen Standard mit Zero-Egress, Non-Elevation, destruktiver Schwärzung und direkten Sicherheitskontakten (`security@open-bricks.org`, `security@doc-bricks.org`, `security@ellmos.ai`, `support@lukasgeiger.com`) gehärtet.
  - **Ökosystem-Matrix:** Umfassende Geschwisterwerkzeuge-Matrix mit 13 Partner-Repositories über `doc-bricks`, `file-bricks`, `dev-bricks` und `open-bricks` verankert.
  - **Metadaten- & Invarianten-Vertragstestsuite:** `tests/test_metadata.py` um Contract-Tests für zweisprachige Parität, Mermaid-Syntax, Showcase-Grafiken, Sibling-URLs, Sicherheitsinvarianten, Offline Zero-Egress Invarianten (0 Netzwerkimporte über alle 76 Quelldateien) und CI-Workflow-Integrität auf 12 Tests erweitert (12/12 passed, 301 Tests gesamt).
  - **`pyproject.toml` & `llms.txt`:** PEP 621 Standard Classifiers (`Python 3.13`, `OS Independent`, `Windows`, `Linux`, `MacOS`), `[project.urls]` (`Security`, `Umbrella`) und `llms.txt` Last-checked Timestamp auf `2026-08-23` synchronisiert.

### Behoben / Fixed (2026-08-21)
- **Format-Konvertierung (FormatConverter Robustheit & Edge-Cases):**
  - **Grayscale- und Alpha-PDFs:** Bei der Konvertierung von PDF zu JPEG/BMP/WEBP führte ein 1-Kanal-Grayscale-Pixmap zu `ValueError: not enough image data` und ein Alpha-/RGBA-Pixmap zu Farbkanalverzerrungen. Pixmaps werden nun kanalgenau decodiert und transparente Ebenen sauber mit weißem Hintergrund komponiert.
  - **PDF mit 0 Seiten:** Leere PDF-Dokumente werden vor dem Zugriff auf Seite 0 abgefangen und liefern ein kontrolliertes `ConversionResult(False, ...)` statt eines unbehandelten `IndexError`.
  - **Bildkonvertierung mit Palette & Alpha:** Konvertierung von Bildern im Palette-Modus (`P`) oder mit Alphakanal (`LA`, `PA`, `RGBA`) nach JPEG, BMP oder PDF schlug mit `cannot write mode P/LA as JPEG` fehl; diese Modi werden nun verlustfrei auf weißem Hintergrund zusammengeführt. Dateihandles werden über Kontextmanager sicher geschlossen.
  - **Markdown- und HTML-Konvertierung:** Vollständige Unterstützung für Markdown-Ausgabe (`OutputFormat.MD`) aus PDF, DOCX, TXT und HTML sowie Konvertierung von `.html`-Eingabedateien (`_convert_from_html`) implementiert.
  - **Regressionstests:** Umfassende Testsuite in `tests/test_converter_formats_robustness.py` (9 Tests) integriert.

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
