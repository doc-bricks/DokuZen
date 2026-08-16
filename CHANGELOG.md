# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Geändert / Changed (2026-08-16)
- **Discoverability, README-Design, Badges & Metadata Parity Check (Pfad B):**
  - Badges in `README.md` & `README_de.md` um Testsuite (275 Passed, 100% grün), Version (1.0.0), `doc-bricks` Ecosystem, `open-bricks` Umbrella und `llms.txt` Discovery synchronisiert.
  - Interaktive zweisprachige Mermaid Systemarchitektur-Diagramme (3-Panel GUI -> Core Engines -> Plugins & Background Services) integriert.
  - Geschwisterwerkzeuge-Matrix innerhalb der `doc-bricks`- und `open-bricks`-Ökosysteme (`PDFtoPDFocr`, `MediaBrain`, `TextBrain`, `DevCenter`, `CodeBox`) in beiden Sprachfassungen verlinkt.
  - Automatisierte Metadaten- & Manifest-Paritätstestsuite in `tests/test_metadata.py` implementiert (5/5 passed).
  - `pyproject.toml` um `[tool.ruff]` und `[tool.ruff.lint]` (py310, line-length 120, ruff check 100% sauber) sowie Changelog URL erweitert.
  - Whitespace- & Mojibake-Hygiene in `core/converter/formats.py`, `gui/panels/library_panel.py` und `plugins/special_text/encoding_fixer.py` bereinigt.
  - `llms.txt` Last-checked Timestamp auf `2026-08-16` und Teststand (275 passed) synchronisiert.

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
- **Tests:** `tests/test_image_converter_pdf_transparency.py` (3 Tests) prüft die Konvertierung von RGBA-PNG und P-Palette nach PDF sowie RGBA nach JPEG/BMP.

### Behoben / Fixed (2026-07-23)
- **PDF-Schwärzung (P0, Privacy/PII-Leak):** `RedactionApplier.redact_pdf()` meldete bisher unbedingt "Erfolg", auch wenn einzelne Treffer im PDF nicht wiedergefunden und daher NICHT geschwärzt wurden (z.B. IBANs mit internen Leerzeichen oder mehrzeilige Namen, da `page.search_for()` den Treffertext erneut sucht statt die ursprüngliche Fundstelle zu nutzen). Der Schwärzungs-Dialog zeigt jetzt bei unvollständiger Schwärzung eine deutliche Warnung statt einer falschen Erfolgsmeldung; `RedactionApplier` stellt dafür `last_redaction_stats` (total/redacted/missed) bereit und loggt eine Warnung mit Beispielen. Der eigentliche Architektur-Fix (Schwärzung per Span/Rect statt erneuter Textsuche) bleibt als separate, sicherheitskritische Aufgabe in `AUFGABEN.txt` offen.
- **Tests:** `tests/test_redaction_applier_partial_match.py` (3 Tests) sichert die neue Statistik gegen teilweisen Fund, vollständigen Fund und Zustandsreset zwischen Aufrufen ab.
- **Nachtrag (2026-08-02):** Der im ursprünglichen Eintrag noch als offen
  bezeichnete Span-/Rect-Architekturpfad ist im aktuellen Clone umgesetzt:
  `Match.rects` werden in `RedactionApplier.redact_pdf()` bevorzugt verwendet.
  `tests/test_redaction_span_rects.py` deckt den Pfad einschließlich einer
  mehrzeiligen IBAN ab. Dafür wurde kein neuer offener Task angelegt.

### Behoben / Fixed (2026-07-22)
- **PDF-Marker-Beschnittrand:** Das kompakte Zahlenfeld für den Beschnittrand hat jetzt deutschen Tooltip sowie Accessible Name und Description. Screenreader erhalten damit Kontext und Einheit, ohne das sichtbare Layout zu verändern.
- **Tests:** `tests/test_dialog_smoke.py` sichert den Assistive-Kontext des Beschnittrands ab.
- **PDF-Marker-Tastaturbedienung:** Seitenvorschauen sind jetzt per Tab erreichbar und lösen Auswahl auch mit Enter oder Leertaste aus. Ihre Markierung wird mit deutschem Accessible Name, Description und Tooltip beschrieben; die kompakte Thumbnail-Oberfläche bleibt unverändert.
- **Tests:** `tests/test_dialog_smoke.py` prüft Fokus, Screenreader-Kontext und Enter-/Leertastenbedienung der Seitenvorschau.
- **PDF-Marker: leerer Delete-Export:** Wenn alle Seiten als `Entfernen (D)` markiert sind, bricht der Export jetzt vor Dateiauswahl und `fitz.save()` mit einer verständlichen Warnung ab, statt mit `cannot save with zero pages` in den Fehlerdialog zu laufen.
- **Tests:** `tests/test_pdf_marker_empty_export.py` sichert den Delete-all-Pfad gegen leere Export-PDFs ab.
- **Pytest-Isolierung:** `tests/test_pdf_reader_search.py` hinterlässt keinen `fitz`-/Abhängigkeits-Stub und keinen Ersatz für `core.pdf.reader` mehr. Dadurch laufen die nachfolgenden echten PDF-Crop- und Seitenzahlentests auch in der vollständigen Sammlung stabil.

### Geändert / Changed (2026-07-16)
- **PDF-Marker-Notation mit A11y-Kontext:** Das neue Notationsfeld im PDF-Marker exponiert jetzt für Eingabe, Markierungsart und `Notation anwenden` klare Tooltips sowie Accessible Names und Descriptions. Die kompakte Oberfläche bleibt unverändert, aber Screenreader und Tastaturnutzung erhalten einen eindeutigen Bedienkontext für den frischen Branch-/Auszug-Pfad.
- **Tests:** `tests/test_dialog_smoke.py` prüft die Notationssteuerung jetzt explizit auf Tooltip-, Accessible-Name- und Description-Kontext.

### Hinzugefügt / Added (2026-07-15)
- **Text-Notation im PDF-Marker:** Der Marker-Dialog akzeptiert jetzt Seitenangaben wie `1-5, 7, 9-12` und wendet sie direkt auf `Auszug (M)`, `Entfernen (D)` oder `Behalten (K)` an. Damit lässt sich der offene Branch-/Auszug-Pfad erstmals nicht nur per Klick, sondern auch per wiederholbarer Textnotation steuern.
- **Tests:** `tests/test_pdf_marker_page_ranges.py` prüft den neuen Parserpfad inklusive Bounds-Checks und die Dialog-Anbindung; `tests/test_pdf_workshop_parse_range.py` bleibt dabei kompatibel.

### Hinzugefügt / Added (2026-07-12)
- **Drittanbieter-Lizenzinventar:** `THIRD_PARTY_LICENSES.txt` listet jetzt die direkten Runtime-Abhängigkeiten aus `requirements.txt` statt eines globalen Maschinen-Dumps. Die Datei hält PyMuPDF/AGPL, PyQt6-WebEngine/GPL und PySide6/Qt als zentrale Release-Grenzen fest.
- **Tests:** `tests/test_third_party_licenses.py` prüft, dass alle direkten Requirements im Inventar auftauchen und die Copyleft-/Store-Hinweise erhalten bleiben.

### Hinzugefügt / Added (2026-07-04)
- **Optionaler PDF-Beschnitt im Marker-Export:** `core/pdf/crop.py` ergänzt einen kleinen PyMuPDF-Utility-Pfad zum gleichmäßigen Beschneiden exportierter Seitenränder; der PDF-Marker-Dialog bietet dafür jetzt eine Checkbox mit konfigurierbarem Rand in Millimetern.
- **Tests:** `tests/test_pdf_crop.py` prüft Beschnitt, Schutz gegen zu große Ränder und die Dialog-Anbindung.

### Geändert / Changed (2026-07-04)
- **Kompakte Browse-Buttons im Einstellungsdialog:** Die vier `...`-Buttons für Bibliothek, Export, Spawner und Tesseract bleiben visuell kompakt, exponieren jetzt aber klare Tooltips sowie Accessible Names und Descriptions für Screenreader und Tastaturnutzung.
- **Tests:** `tests/test_dialog_smoke.py` prüft die vier kompakten Browse-Buttons jetzt explizit auf ihren Accessibility-Kontext.

### Hinzugefügt / Added (2026-07-03)
- **Optionale Seitenzahlen im PDF-Marker-Export:** `core/pdf/page_numbers.py` ergänzt einen kleinen PyMuPDF-Utility-Pfad für Seitenzahlen; der PDF-Marker-Dialog kann exportierte Auszüge jetzt per Checkbox mit `Seite X / Y` am unteren Seitenrand versehen.
- **Tests:** `tests/test_pdf_page_numbers.py` prüft sowohl die Seitenzahl-Utility als auch die Dialog-Anbindung.

### Hinzugefügt / Added (2026-06-29)
- **Signatur-Erkennung vor Overlay:** `SignatureOverlay.embed_signature_checked()` prüft Zielseiten vor dem Einbetten auf vorhandene Signaturhinweise. Der Check nutzt vorhandenen PDF-Text und optional den bestehenden OCR-Pfad; bei Treffer wird kein zusätzliches Overlay gesetzt und das Original unverändert in den Ausgabepfad übernommen.
- **GUI-Absicherung:** Der Signatur-Dialog hat eine aktivierte Vorabprüfungs-Checkbox und meldet klar, wenn eine Signatur bereits erkannt wurde.
- **Tests:** `tests/test_pdf_signature_overlay.py` deckt Erkennung, Skip-Pfad und reguläres Einbetten ab; Signatur-Testdatei jetzt 17 Tests.

### Hinzugefügt / Added (2026-06-28)
- **Signatur-Overlay:** `core/pdf/signature.py` — neues Modul `SignatureOverlay` + Hilfsfunktion `embed_signature()`. Bettet PNG- (inkl. Alpha-Kanal/Transparenz) und JPG-Signaturen via PyMuPDF auf wählbarer Seite und in frei einstellbarer Position/Größe in PDFs ein; optionale Seitenverhältnis-Beibehaltung via Pillow.
- **GUI-Dialog:** `gui/dialogs/signature_overlay_dialog.py` — modaler Dialog mit Positions-Voreinstellungen (Unten links, Mitte, rechts; Benutzerdefiniert), X/Y/Breite/Höhe-Reglern und automatischer Seitenanzahl-Anzeige.
- **Menü-Eintrag:** "Werkzeuge → PDF-Signatur einbetten…" (`main_window.py`) mit Weiterleitung der aktuell ausgewählten PDF an den Dialog.
- **Tests:** `tests/test_pdf_signature_overlay.py` — 14 Tests (Kern, Fehlerfall, Klasse); 14/14 grün.

### Geändert / Changed
- **Produktumbenennung:** DokuZentrum → DokuZen (2026-06-27). Projektordner `DEV_DokuZentrum_SUITE` → `DEV_DokuZen`. Alle Branding-Strings, App-Namen (`setApplicationName`/`setOrganizationName`), Icons (`DokuZen.ico`), State-Datei (`.dokuzen_state.json`), Log-Datei (`logs/dokuzen.log`), Store-Artefakte und Dokumentation aktualisiert. Backward-Compat-Migration: bestehende `.dokuzentrum_state.json` wird beim ersten Start automatisch nach `.dokuzen_state.json` kopiert. Alle 212 Tests bleiben grün.

### Hinzugefügt / Added
- Desktop-Portierungsplan für Windows, macOS und Linux ergänzt.
- Mobile/Web als Nicht-Ziele festgehalten, weil die Kern-Usecases lokale Desktop-Datei-, PDF-, OCR- und Shell-Workflows sind.
- Kleine GUI-CLI für `--import`, `--open`, `--ocr`, `--redact` und `--merge` ergänzt.
- Neuer Source-Smoke `tests/test_source_platform_smoke.py` für offscreen Desktop-Start, UTF-8-Import, PDF-Vorschau und Linux/macOS-Öffnungspfade mit isolierter Temp-State-Datei.
- Windows-Store-Basisartefakte erstellt: `store_package.json`, `STORE_LISTING.md` (DE+EN), `PRIVACY_POLICY.md` (DE+EN), `SUPPORT.md`, `WINDOWS_STORE_PREP.md`, `screenshots/store/README.md` (2026-06-07).
- `tests/test_store_materials.py` mit 6 Tests für Store-Artefakte hinzugefügt (lokal 6/6 grün, 2026-06-07).
- GitHub Actions CI `.github/workflows/source-platform-smoke.yml`: Matrix ubuntu-latest + macos-latest, reduzierte Deps ohne PyQt6-WebEngine; lokal verifiziert, CI-Aktivierung nach Repo-Erstellung (2026-06-07).

### Geändert / Changed
- Launcher sucht Icons jetzt sowohl im Quellbaum als auch im PyInstaller-Bundle.
- README auf den aktuellen Dialog- und Launch-Stand nachgezogen.
- Themenauswahl bleibt nach Umbenennen oder Löschen des aktiven Themas über Neustarts konsistent; README dokumentiert den aktuellen Bibliotheksstand.
- API/CLI-Dokumentation von alten Template-Claims auf den realen Projektstand korrigiert.
- Linux-Portierungsaufgabe von reiner Planung auf einen lokal reproduzierbaren Source-Smoke konkretisiert.

### Behoben / Fixed
- Fehlende `QWidget`-Imports in den Dialogen für Konvertierung, Schwärzung, OCR und Text-Pool behoben.
- Regressionstest für Dialog-Instanziierung ergänzt.
- Regressionstests für persistente Themenauswahl nach Rename/Delete ergänzt.
- Neuer CLI-Startpfad ist mit Regressionstests für Parsing und Dispatch abgesichert.
- Das Windows-Explorer-Untermenü `DokuZen Pro` für PDF-Aktionen wird jetzt nur noch unter `.pdf` statt global unter `*\\shell` registriert; OCR-, Entsperr- und Schwärzungsaktionen erscheinen damit nicht mehr irreführend bei beliebigen Nicht-PDF-Dateien.
- `tests/test_registry_cascading_menu.py` prüft jetzt die `.pdf`-Bindung für Registrierung, Deregistrierung, Statusabfrage und den konkreten `SystemFileAssociations\\.pdf\\shell`-Pfad.

## [1.0.0] - YYYY-MM-DD

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
