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

### Behoben / Fixed (2026-09-20, Bugsweep: Multi-Format Routing, PDF-Konvertierung & Pfadnormalisierung)
- **Multi-Format Ingest Routing (`core/ingest/detector.py`, `core/library/manager.py`):**
  - In `FormatDetector.is_convertible_to_pdf` stufte `ft in (FileType.OFFICE, ...)` Text-/Office-Formate wie `.odt`, `.rtf` und `.doc` fälschlich als konvertierbar ein; `determine_action` wies daraufhin `IngestAction.CONVERT_TO_PDF` zu, was beim Import mangels Konvertierungsunterstützung fehlschlug. Behoben durch Beschränkung auf tatsächliche Konverter-Formate.
  - Nicht nach PDF konvertierbare Office-Dateien werden nun sauber als `IngestAction.ADD_DIRECT` in die Bibliothek geroutet.
  - `LibraryManager.SUPPORTED_EXTENSIONS` um `.markdown`, `.htm`, `.tif` und `.webp` erweitert.
- **Erweiterte Format-Konvertierung (`core/converter/formats.py`):**
  - Unterstützung für `.markdown`, `.htm` und `.tif` im Format-Dispatcher ergänzt.
- **Robuste Duplikatserkennung auf Windows (`core/ingest/detector.py`, `core/ingest/service.py`):**
  - Duplikatsabgleich gegen `existing_paths` um `os.path.normcase()` ergänzt, wodurch Groß-/Kleinschreibungsunterschiede bei Laufwerksbuchstaben (`c:` vs. `C:`) und Pfadtrennzeichen unter Windows zuverlässig erkannt werden.
- **Scanner-Optimierung (`core/ingest/scanner.py`):**
  - Sofortiges Leeren von `dirs` bei `not recursive` oder Überschreiten von `max_depth`, um unnötige Unterordner-Descents abzufangen.
- **Regressionstests:**
  - 3 neue Tests in `tests/test_smart_ingest_regressions.py`; gesamte Suite wächst auf 411 bestanden, 1 übersprungen, 26 Subtests (100% grün).

### Hinzugefügt & Gehärtet / Added & Hardened (2026-09-19, Phase 4(3) Smart Ingest Dropzone mit automatischer Formaterkennung & Multi-Format-Routing)
- **Smart Ingest Core-Engine (`core/ingest/`):**
  - Neues modulares Kernpaket für mehrformatigen Datei- und Ordnerimport (`models.py`, `detector.py`, `scanner.py`, `service.py`, `__init__.py`).
  - `FormatDetector`: Automatische Formaterkennung über Dateiendung und Magic-Byte-Sniffing (PDF, Microsoft Office DOCX/XLSX, Raster- und Vektorbilder, Markdown, Plaintext, HTML, CSV/Tabellen, Code) inkl. SHA-256 Duplikatserkennung.
  - `FolderScanner`: Rekursives Scannen von Verzeichnisbäumen mit Tiefenbegrenzung (`max_depth`) und Filterung von Entwicklungsordnern (`.git`, `__pycache__`, `venv`, `node_modules`, `_archive`), temporären Office-Dateien (`~$*`, `*.tmp`) und System-Metadaten (`Thumbs.db`, `desktop.ini`).
  - `SmartIngestService`: Zentrale Orchestrierung zur Batch-Aufbereitung, Duplikatsprüfung gegen aktive Bibliotheken, automatischer Konvertierung nach PDF via `FormatConverter` und direktem Import in die DokuZen-Bibliothek.
- **Benutzeroberfläche & Dialoge (`gui/widgets/dropzone.py`, `gui/dialogs/smart_ingest_dialog.py`):**
  - Neues `SmartDropzoneWidget`: Visuell ansprechende Dropzone mit gestricheltem Rahmen, Status-Highlights bei Drag-Over, Format-Chips (`[PDF]`, `[Office/Word]`, `[Bilder]`, `[Text & Markdown]`, `[Ordner]`) und barrierefreier Tastaturnavigation (Leertaste/Enter öffnet Dateidialog).
  - Neuer `SmartIngestDialog`: Interaktiver Import-Manager mit Themen-Auswahl, Tabellenübersicht der Kandidaten (Dateiname, erkanntes Format, wählbare Ingest-Aktion via ComboBox, Dateigröße, Status), Optionen für automatische PDF-Konvertierung, Duplikatsüberspringen und rekursives Scannen sowie Live-Fortschrittsanzeige.
  - Integration in `MainWindow`: Neuer Menüeintrag `Datei -> Smart Ingest (Dropzone)...` (Tastenkürzel `Ctrl+Shift+I`), Symbolleisten-Button, Drag-and-Drop-Weiterleitung beliebiger Dateitypen oder Ordner an die Smart Ingest Pipeline.
  - Integration in `DocumentListPanel`: Erweiterung von `dropEvent`, sodass Ordner oder Nicht-PDFs nahtlos an den Smart Ingest Dialog übergeben werden.
- **Lokalisierung (I18N):**
  - 50 neue Übersetzungsschlüssel in allen 6 unterstützten Sprachen (`de`, `en`, `es`, `zh`, `ja`, `ru`) in `locales/translations.json` hinterlegt (Gesamtkatalog auf 266 Einträge erweitert).
- **Testabdeckung & Qualitätsnachweis:**
  - 16 neue Tests in `tests/test_smart_ingest.py` und `tests/test_smart_dropzone_and_dialog.py` sowie Dialog-Smoke-Test in `tests/test_dialog_smoke.py`.
  - Gesamttestsuite: 408 Tests bestanden, 1 übersprungen, 26 Subtests bestanden (100% grün).
  - Code-Qualität: 0 Ruff-Lints (`ruff check .` sauber), Python-Bytecode-Kompilierung fehlerfrei (`compileall`), Windows Store Readiness Prüfung erfolgreich (`check_store_readiness.py`).

### Hinzugefügt & Gehärtet / Added & Hardened (2026-09-19, Pfad B Marketing, Discoverability, Visual Architecture & Metadata Contract)
- **Marketing & Discoverability Contract (Pfad B):**
  - GitHub-Themenanreicherung auf 20/20 optimierte Schlagwörter (`desktop-app`, `document-processing`, `local-first`, `ocr`, `offline-first`, `pdf`, `pdf-tools`, `pyside6`, `python`, `redaction`, `windows`, `document-management`, `open-bricks`, `pdf-editor`, `pdf-merger`, `pikepdf`, `pymupdf`, `pytesseract`, `zero-egress`, `doc-bricks`).
  - Neue Dokumentation `MARKETING-LOG.txt` mit detaillierter Persona-Matrix (`[PERSONA-01]` bis `[PERSONA-04]`), High-Intent SEO-Suchbegriffen und 10-Dimensionen-Vergleichsmatrix (`INV-LOCAL-01` bis `INV-ARCH-10`) gegen 5 Alternativen (Adobe Acrobat Pro, Smallpdf/iLovePDF SaaS, PDF24 Creator, Master PDF Editor, Okular/Evince).
  - Neue Drittanbieter-Lizenzdokumentation `THIRD_PARTY_LICENSES.md` mit tabellarischer SPDX-Übersicht, Copyleft-Isolationsgrenzen und Nachweis der Zero-Egress-Invarianten.
  - Erweiterung von `pyproject.toml` [project.urls] um `"Third-Party Licenses"`, `"Marketing Log"` und `"LLM Ready"`.
  - Vollständige Harmonisierung der 18-Punkte-Schnellnavigation in `README.md` und `README_de.md` mit reziproken HTML-Ankern (`<a id="..."></a>`), Zielgruppen-Abschnitt, Vergleichsmatrix, 5-Schichten-Architekturdiagramm und rechtlichem Haftungsausschluss gem. § 521 BGB.
  - Aktualisierung des KI-Integrationsindexes `llms.txt` auf 391 bestandene Tests und neue Dokumentationsdateien.
- **Bugfixes & Robustheits-Härtung:**
  - `core/workspace_export.py`: Behebung des `AttributeError: 'ThemeManager' object has no attribute 'get_theme'` bei der Verarbeitung von `Theme`-Objektlisten in `build_workspace_snapshot()`.
  - `tests/test_export_action.py`: Absicherung gegen Qt Offscreen-Fenstergeometrie-Beschränkungen (`minimumSize` vs. 800x800 Virtual Screen) und synchrone `QSettings`-Synchronisation.

### Hinzugefügt & Gehärtet / Added & Hardened (2026-09-18, Phase 4(2) Workspace-Snapshot-Export & PWA Web Companion)
- **Workspace-Snapshot-Export (`core/workspace_export.py`):** Neues Kernmodul für den sicheren, redigierten Export des gesamten Arbeitsbereichs (`dokuzen-workspace-v1.json`).
  - Strikte Datenschutz-Redaction: Entfernt alle lokalen absoluten Pfade (`C:\...`), interne Dateisystemstrukturen, Rohdokumente und Zugangsdaten/Passwörter.
  - Sichere Whitelist für Konfigurationseinstellungen (`theme`, `language`, `ocr_language`, `duplicate_check`, `pdf_dpi` etc.); filtert verbotene Schlüssel wie Passwörter und Fensterkoordinaten.
  - Aggregation von Themen, Dokumenten-Metadaten (Dateiname, Typ, Größe, Tags, Notizen, Lesestatus) und Formular-Vorlagen.
  - Atomare Speicherung via temporärer Prozess-ID-Datei (`.tmp.<pid>`) und atomarem `replace()`.
- **GUI-Integration (`gui/main_window.py`):**
  - Neuer Menüeintrag `Datei -> Arbeitsbereich exportieren...` (Tastenkürzel `Ctrl+Shift+E`) mit nativem Speicherdialog, Fehlerbehandlung und Statusleisten-Rückmeldung.
  - Fenstergeometrie-Persistenz: Speichert und restauriert Position und Größe des Hauptfensters über `QSettings("Geiger", "DokuZen")`.
- **Lokalisierung (`locales/translations.json`):** 4 neue Übersetzungsbegriffe in 6 Sprachen (`de`, `en`, `es`, `zh`, `ja`, `ru`) hinterlegt.
- **PWA Web Companion (`web_companion/`):** Vollwertige offline-fähige Web-App zum Durchsuchen und Betrachten von Arbeitsbereichen ohne Desktop-Installation:
  - Responsive Benutzeroberfläche mit Theme-/Themenliste, Such- und Tagfilterung, Lesestatus-Filter und Formularübersicht.
  - Drag-and-Drop-Unterstützung für `dokuzen-workspace-v1.json`-Dateien und integrierter Demo-Modus.
  - Service-Worker (`sw.js`) und Web-Manifest (`manifest.webmanifest`) für vollwertige Offline-PWA-Installation auf Mobil- und Desktopgeräten.
- **Repository-Hygiene:** `core/library/persistence_prefixbak_20260607_162043.py` in `_archive/` überführt.
- **Testabdeckung:** 13 neue Unit- und Integrationstests (`tests/test_workspace_export.py`, `tests/test_export_action.py`, `tests/test_web_companion.py`). Testsuite wächst auf 388 bestandene Tests (100% grün).

### Hinzugefügt & Gehärtet / Added & Hardened (2026-09-16, TW-DZ-13 Sammel-PDF-Export & Dialog)
- **Sammel-PDF-Export-Engine (`core/pdf/collection.py`):** Neues Kernmodul für die Erstellung einheitlicher Dokumentenmappen (Binder) aus heterogenen Quellen (PDFs, Bilder, Markdown, Text und Office-Dateien).
  - Unterstützt native Einbettung mehrseitiger PDFs, automatische A4-Bildeinpassung mit Orientierungserkennung sowie formatierten Text- und Quellcode-Umbruch mit Kopfzeilen.
  - Generiert hierarchische PDF-Lesezeichen (TOC Bookmarks) für jedes eingebundene Dokument.
  - Integriert optionale fortlaufende Seitennummerierung (`PDFPageNumberer`).
  - Fehlertolerante Verarbeitung: überspringt unlesbare/verschlüsselte Dateien mit Protokollierung in `CollectionExportResult`.
- **Interaktiver Konfigurationsdialog (`gui/dialogs/collection_export_dialog.py`):**
  - Übersichtliche Liste aller Mappendokumente mit Reihenfolge-Steuerung (`Nach oben` / `Nach unten`).
  - Dokumenten-Auswahl per Checkboxen, Hinzufügen weiterer Dateien über System-Dateidialog und Entfernen.
  - Konfiguration von Lesezeichen/TOC und Seitennummern mit Formatvorlagen (`Seite {page} / {total}`).
  - Direkte Rückmeldung, Fortschrittsanzeige und Option zum unmittelbaren Öffnen der generierten PDF.
- **MainWindow & Kontextmenü-Integration (`gui/main_window.py`, `gui/panels/document_list.py`):**
  - Menüpunkt `Datei -> Sammel-PDF exportieren...` von Platzhalter auf den interaktiven Exportdialog umgestellt (mit Fallback auf selektierte Dokumente oder alle Dokumente des aktiven Themas).
  - Kontextmenü in der Dokumententabelle um `Als Sammel-PDF exportieren...` für markierte Dateien erweitert.
- **Mehrsprachigkeit & Lokalisierung (`locales/translations.json`):** 37 neue Übersetzungsbegriffe für alle Dialog- und Aktionsbereiche in 6 Sprachen (`de`, `en`, `es`, `zh`, `ja`, `ru`) hinterlegt.
- **Testabdeckung (`tests/test_pdf_collection.py`, `tests/test_dialog_smoke.py`):** 10 neue Unit- und GUI-Integrationstests (Gesamtsuite: 375 bestanden, 1 übersprungen, 26 Subtests, 100% grün).

### Hinzugefügt & Gehärtet / Added & Hardened (2026-09-12, Phase 4 Clipboard Spawner & Multi-Format Export)
- **Clipboard-to-File Modul (`core/clipboard`):** Neues Kernmodul für das Speichern von Zwischenablage-Inhalten:
  - `structure.py`: Robuste Text- und Überschriftenanalyse mit Heuristiken für Markdown-Header (`#`), Versalzeilen, Doppelpunkt-Endungen und Titelzeilen.
  - `naming.py`: Intelligente Dateinamenerzeugung (`slugify_filename`) aus Überschriften oder Textanfang mit Umlautnormalisierung (ä/ö/ü/ß), Längenbegrenzung, Kollisionsschutz (`unique_path`) und Zeitstempel-Fallbacks.
  - `manager.py`: Mehrformat-Exportunterstützung für `TXT`, `MD`, `PDF` (ReportLab), `DOCX` (python-docx) und `RTF` (inkl. voller Unicode- und Astral-Plane-Emoji-Escapes) mit atomarer `.tmp`-Speicherung und `replace()`.
- **Spawner-Plugin-Integration (`plugins/spawner/clipboard_monitor.py`):** `ClipboardSaver` um automatische Slug-Benennung, strukturierte Formatierung (`design=True`) sowie direkte `save_as_docx`, `save_as_rtf` und `save_content`-Methoden abwärtskompatibel erweitert.
- **Unit- & Regressionstests (`tests/test_clipboard_spawner.py`):** 17 neue Tests für Struktur-Erkennung, Namensgenerierung, Dateikollisionen, alle 5 Exportformate und ClipboardSaver-Integration (Testsuite auf 357 bestandene Tests gehoben).


### Gehärtet & Bereinigt / Hardened & Cleaned (2026-09-07, Pfad A Repository-Hygiene & CI-Härtung)
- **CI-Workflow-Härtung (.github/workflows/source-platform-smoke.yml):** Concurrency Group mit cancel-in-progress: true hinzugefügt, um redundante CI-Läufe abzubrechen; automatisches Ruff Linting (python -m ruff check .) als Gatekeeper in CI verankert; tests/test_security_license_contract.py in den CI-Testschritt aufgenommen.
- **Sicherheitsrichtlinie (SECURITY.md):** Strukturierte Tabelle für unterstützte Versionen (Supported Versions >= 1.0.x) ergänzt.
- **Metadaten- & Badges-Parität:** Version-Badges in README.md und README_de.md von 1.0.0 auf 1.0.1 synchronisiert; llms.txt Last-checked Datum auf 2026-09-07 und Ecosystem-Version auf 1.0.1 aktualisiert.
- **Vertragstest-Erweiterung (tests/test_metadata.py):** CI-Workflow-Integritätstest erweitert um Prüfungen für Concurrency, Ruff-Linting und Security-Contract-Ausführung; Version-Badge-Paritätsprüfungen gegen pyproject.toml und llms.txt-Zeitstempel 2026-09-07 verankert.


### Behoben & Gehärtet / Fixed & Hardened (2026-08-24, Bugsearch & Robustness Audit)
- **PDF-Stempel & Annotationen (`core/pdf/annotations.py`):** `add_stamp()` löst vordefinierte `StampType`-Enums, Namen und Integer-IDs nun robust auf PyMuPDF-Stempelkonstanten (`STAMP_*`) auf, statt String-Literale direkt als Dateipfad an PyMuPDF zu übergeben (behebt `FileNotFoundError: [Errno 2] No such file or directory: 'Approved'`).
- **In-Place PDF-Speichern (`core/pdf/annotations.py`, `core/pdf/signature.py`, `core/pdf/crop.py`, `core/pdf/page_numbers.py`, `core/redaction/detector.py`):** Bei identischem Ein- und Ausgabepfad (`output_path == pdf_path`) wird die Datei nun atomar über ein temporäres Dokument im Zielordner gespeichert und nach Schließen des PyMuPDF-Dokument-Handles ersetzt (behebt `ValueError: save to original must be incremental` und Windows-Dateisperren).
- **Integrations- & Regressionstestsuite:** 21 neue Tests in `tests/test_pdf_annotations_real.py` und `tests/test_pdf_signature_overlay.py` hinzugefügt; Testsuite auf 331 bestandene Tests (100% grün) erweitert.

### Behoben & Gehärtet / Fixed & Hardened (2026-08-24, Security & License Compliance Audit)
- **Dependency-Floor-Härtung (OSV / GHSA Audit):** Mindestversionsgrenzen in `pyproject.toml` und `requirements.txt` gehärtet:
  - `Pillow>=12.0.0` schützt gegen 35+ bekannte CVEs/GHSAs älterer Versionen (Heap-Buffer-Overflows, Denial-of-Service, Command Injection).
  - `PyMuPDF>=1.24.0`, `pikepdf>=8.15.1`, `pytesseract>=0.3.13`, `reportlab>=4.2.0` und `pystray>=0.19.5` auf verifizierte, sichere Mindestversionen gehoben.
- **Third-Party License Inventory (`THIRD_PARTY_LICENSES.txt`):** Turnusgemäß auf den Stand `2026-08-24` auditiert; direkte Abhängigkeiten, Lizenzmodelle (AGPL/GPL/LGPL/Apache/MIT/BSD/0BSD/MPL) und Copyleft-Grenzwerte für Store- und Binärdistributionen verifiziert.
- **Sicherheits- & Lizenzvertrags-Testsuite:** Neue Testsuite `tests/test_security_license_contract.py` integriert (6 Tests: Dependency-Floor-Härtung, Lizenzinventar, zweisprachige `SECURITY.md` mit 48h-SLA und Zero-Egress Invarianten, Secret-/Token-/Pfad-Hygiene, `.gitignore`-Schutz gegen Sync-Konflikte und Locks, AGPL-3.0 SPDX-Parität).
- **Dateipfad- & Gitignore-Hygiene:** Legacy-Pfad in `SUITE_DOKUZEN_TEMPLATE.md` bereinigt; `.gitignore` um umfassende Schutzmuster (`*.conflict`, `*.sync-conflict-*`, `LOCK*.txt`, `.env`) erweitert.
- **Gesamtstatus:** 331/331 Tests bestanden (100% grün).

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
