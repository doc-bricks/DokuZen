# DokuZen GUI-Funktions- & Aktionen-Audit-Protokoll (U1)
======================================================
**Datum:** 2026-09-26  
**Akteur:** Gemini Antigravity (Rolle: `SOFTWARE_ENTWICKLUNG`)  
**Bezug:** Nutzerauftrag U1 aus `WELLE-1-USERTEST 2026-08-14` & `AUFGABEN.txt`  
**Prüfbasis:** DokuZen v1.0.1 (Commit-Stand vor Integration)  
**Testsuite:** `tests/test_gui_menu_and_actions_coverage.py` (7/7 neu), Gesamtsuite: 451 passed, 1 skipped  

---

## 1. Übersicht & Zielsetzung

Gemäß Nutzeranweisung U1 wurde ein vollständiger Funktionstest aller Aktionen, Menüeinträge, Symbolleistenelemente, Reiter und Kontextmenüs durchgeführt. Anlass waren historische Befunde aus dem Welle-1-Usertest, bei denen Menüpunkte ohne Wirkung blieben (Signal nicht verbunden oder Dialog ohne Referenz) oder Auslöser ins Leere liefen.

---

## 2. Detaillierte Prüfung der Menüleiste (`QMenuBar`)

| Menü | Menüeintrag / Aktion | Shortcut | Slot / Handler | Getestet & Status |
|---|---|---|---|---|
| **Datei** | &Importieren... | Ctrl+I | `_on_import` | PASSED (Dialogaufruf, Dateifilter & Status-Update) |
| **Datei** | Ordner importieren... | — | `_on_import_folder` | PASSED (Glob aller `SUPPORTED_EXTENSIONS`, Batch-Add) |
| **Datei** | Smart Ingest (Dropzone)... | Ctrl+Shift+I | `_on_smart_ingest` | PASSED (Modal-Instanz, Auto-Convert & Summary-Callback) |
| **Datei** | Sammel-PDF exportieren... | — | `_on_export_pdf` | PASSED (CollectionExportDialog, Fallback auf Dokumente) |
| **Datei** | Arbeitsbereich exportieren... | Ctrl+Shift+E | `_on_export_workspace` | PASSED (dokuzen-workspace-v1.json, Redaction-Audit) |
| **Datei** | &Einstellungen... | Ctrl+, | `_on_settings` | PASSED (SettingsDialog, Dynamic Language Re-propagate) |
| **Datei** | &Beenden | Ctrl+Q | `close` | PASSED (closeEvent, Auto-Save-Timer-Shutdown) |
| **Bearbeiten** | &Suchen... | Ctrl+F | `_on_search_focus` | PASSED (Fokussiert & selektiert `_search_box`) |
| **Bearbeiten** | Alles auswählen | Ctrl+A | `_on_select_all` | PASSED (Selektiert alle Zeilen in `_table`) |
| **Ansicht** | &Aktualisieren | F5 | `_on_refresh` | PASSED (Refresht Library, Table & Statusbar) |
| **Ansicht** | Vorschau ein/aus | Ctrl+P | `_on_toggle_preview` | PASSED (Checkable Action, Splitter-Visibility Toggle) |
| **Themen** | &Neues Thema... | Ctrl+N | `_on_new_theme` | PASSED (QInputDialog, Persistence & ThemeManager) |
| **Werkzeuge** | PDF-&Werkstatt... | — | `_on_pdf_workshop` | PASSED (Init mit PDF-Auswahl, Refresh nach Abschluss) |
| **Werkzeuge** | PDFs &zusammenführen... | — | `_on_merge` | PASSED (Aktiviert Merge-Tab 0, Refresh nach Abschluss) |
| **Werkzeuge** | &OCR-Texterkennung... | — | `_on_ocr` | PASSED (OCRDialog mit Einzeldokument-Fallback) |
| **Werkzeuge** | PDF &schwärzen... | — | `_on_redaction` | PASSED (RedactionDialog mit Rect-Span-Matching) |
| **Werkzeuge** | Format-&Konvertierung... | — | `_on_convert` | PASSED (ConvertDialog für Multi-Dokument-Konvertierung) |
| **Werkzeuge** | Text-&Pooler... | — | `_on_text_pool` | PASSED (TextPoolDialog für Markdown/Code/Text) |
| **Werkzeuge** | &Code-Analyse (.py)... | — | `_on_code_analysis` | PASSED (CodeAnalysisDialog für Python-Skripte) |
| **Werkzeuge** | &Formular-Builder... | — | `_on_form_builder` | PASSED (FormBuilderDialog mit Refresh nach Save) |
| **Werkzeuge** | PDF-&Marker (M/D/K)... | — | `_on_pdf_marker` | PASSED (PDFMarkerDialog mit Refresh nach Save) |
| **Werkzeuge** | PDF-Seiten &verwalten... | — | `_on_pdf_pages` | PASSED (PDFPagesDialog mit Refresh nach Save) |
| **Werkzeuge** | PDF-&Annotationen... | — | `_on_pdf_annotate` | PASSED (PDFAnnotationDialog, 5 Tabs, Refresh nach Save) |
| **Werkzeuge** | PDF-Signatur &einbetten... | — | `_on_signature_overlay` | PASSED (SignatureOverlayDialog mit OCR-Vorprüfung) |
| **Werkzeuge** | &Bild-Werkzeuge... | — | `_on_image_tools` | PASSED (ImageConverterDialog mit Refresh nach Save) |
| **Werkzeuge** | SQLite-&Viewer... | — | `_on_sqlite_viewer` | PASSED (SQLiteViewerDialog mit Tabellen-Inspektion) |
| **Werkzeuge** | Python &Kompilieren... | — | `_on_pyinstaller` | PASSED (PyInstallerDialog mit Script-Initialisierung) |
| **Hilfe** | Über DokuZen | — | `_on_about` | PASSED (QMessageBox.about mit Version 1.0.1) |

---

## 3. Symbolleiste (`QToolBar`) & Suchleiste

- **Import-Button (`_btn_import`):** Text "Importieren", Tooltip mit Tastenkürzel "Ctrl+I", löst `_on_import` aus.
- **Smart-Ingest-Button (`_btn_smart_ingest`):** Text "Smart Ingest", Tooltip mit "Ctrl+Shift+I", öffnet `SmartIngestDialog`.
- **Neues Thema (`_btn_new_theme`):** Text "Neues Thema", Tooltip mit "Ctrl+N", öffnet Themadialog.
- **Aktualisieren (`_btn_refresh`):** Text "Aktualisieren", Tooltip mit "F5", stößt UI- und Daten-Refresh an.
- **Suchfeld (`_search_box`):**
  - Placeholder: `"Suchen..."`
  - Accessible Name: `"Dokumente durchsuchen"`
  - Accessible Description: `"Filtert die angezeigten Dokumente beim Eingeben. Mit Ctrl+F fokussieren."`
  - Reagiert auf `textChanged` mit normalisiertem Lowercase-Suchquery im `LibraryManager`.

---

## 4. Bedienpanels & Kontextmenüs

### 4.1 `LibraryPanel`
- **Plus-Button (`_btn_add`):** Text `"+"`, löst `create_new_theme()` aus.
- **Themenbaum (`_tree`):**
  - Zeigt Themen mit Dokumentenzähler und Tooltip bei ungelesenen Dokumenten.
  - Doppelklick stößt Umbenennung an (außer bei geschützten Standardthemen).
  - Kontextmenü bietet Umbenennen und Löschen.

### 4.2 `DocumentListPanel`
- **Filter-Dropdown (`_filter_combo`):**
  - Optionen: `Alle` (FilterMode.ALL), `Ungelesen` (FilterMode.UNREAD), `Gelesen` (FilterMode.READ).
  - **Behobener Bug:** Signal-Signatur `_on_filter_changed(self, index=None)` akzeptiert nun den von PySide6 übergebenen Int-Index ohne `TypeError`.
- **Sortier-Dropdown (`_sort_combo`):**
  - Optionen: `Name`, `Datum`, `Größe`, `Typ`.
  - **Behobener Bug:** Signal-Signatur `_on_sort_changed(self, index=None)` gehärtet.
- **Kontextmenü (`create_context_menu`):**
  - Einzelauswahl PDF: Öffnen, Sammel-PDF, PDF annotieren, PDF-Seiten verwalten, PDF schwärzen, OCR-Texterkennung, PDF-Signatur einbetten, Gelesen/Ungelesen, Entfernen.
  - Mehrfachauswahl PDF: Ausgewählte PDFs zusammenführen (Merge), Sammel-PDF, Gelesen/Ungelesen, Entfernen.
  - Alle Aktionen dynamisch übersetzt, an `menu` geparentet (kein Memory-Leak).

### 4.3 `PreviewPanel`
- **Öffnen-Button (`_btn_open`):** Nur aktiv, wenn ein Dokument geladen ist; startet Standard-Betrachter (OS-spezifisch: `os.startfile`, `open`, `xdg-open`).
- **Vorschau-Typen:**
  - Seite 0: Kein Dokument ausgewählt (Platzhalter)
  - Seite 1: Text-Vorschau (mit Encoding-Fallback UTF-8 / Latin-1 / CP1252)
  - Seite 2: Bild-Vorschau (skalierte Pixmap mit AspectRatio)
  - Seite 3: Nicht unterstützt (Hinweis "Doppelklick zum Öffnen")

---

## 5. Mehrsprachigkeit (`retranslate_ui`) & Barrierefreiheit

- Vollständiger Re-Translation-Zyklus über alle 6 Zielsprachen (`de`, `en`, `es`, `zh`, `ja`, `ru`) durchlaufen und validiert.
- Menütitel, Aktionen, Buttons, Tooltips und Statusleiste passen sich zur Laufzeit unterbrechungsfrei an.
- Sämtliche Dialoge und interaktiven Steuerelemente verfügen über barrierefreie `accessibleName`- und `accessibleDescription`-Eigenschaften.

---

## 6. Fazit

Alle 28 Menüpunkte, 5 Toolbar-Elemente, 3 Panel-Bereiche und 17 Dialogaufrufe sind lückenlos angebunden, werfen keine unbehandelten Ausnahmen und aktualisieren den Anwendungszustand unmittelbar. Nutzerauftrag U1 ist damit für DokuZen v1.0.1 vollständig erfüllt und automatisiert abgesichert.
