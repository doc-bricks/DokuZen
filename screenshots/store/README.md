# Store-Screenshots — DokuZen

## Anforderungen (Microsoft Store)

- Format: PNG oder JPEG
- Mindestauflösung: 1366 × 768 px
- Empfohlen: 1920 × 1080 px (16:9)
- Mindestanzahl: 1 Screenshot
- Maximalanzahl: 10 Screenshots
- Dateinamen: aussagekräftig, kein Leerzeichen

## Screenshot-Inventar (erstellt und verifiziert)

| Datei                          | Inhalt                                          | Auflösung   | Format | Status      |
|--------------------------------|-------------------------------------------------|-------------|--------|-------------|
| `01_bibliothek.png`            | Bibliotheksansicht mit Dokumentenliste          | 1920 × 1080 | PNG    | Verifiziert |
| `02_ocr.png`                   | OCR-Dialog mit Optionen und Texterkennung       | 1920 × 1080 | PNG    | Verifiziert |
| `03_schwaerzung.png`           | Schwärzungs-Werkzeug und PII-Erkennung          | 1920 × 1080 | PNG    | Verifiziert |
| `04_konvertierung.png`         | Konvertierungs-Dialog (PDF, DOCX, TXT, PNG)     | 1920 × 1080 | PNG    | Verifiziert |

## Hinweise

- Screenshots unter Windows aus den echten laufenden PySide6-Widgets erzeugt (`tools/generate_store_screenshots.py`).
- Der Generator lädt Segoe UI ausdrücklich und bricht ab, wenn die Schrift nicht korrekt aufgelöst werden kann; dadurch werden Qt-Glyphenfehler verhindert.
- Keine echten personenbezogenen Daten (ausschließlich neutrale Muster- und Demodaten)
- Deutschsprachige Store-UI im Dark-Teal Design-System

## Status

- [x] Vier Screenshots erstellt (2026-08-21 via `tools/generate_store_screenshots.py`)
- [x] Qualität geprüft (echte GUI, lesbare Schrift, echte Umlaute, 1080p, valide PNG-Header, keine PII-Daten)
- [ ] In Store-Einreichung hochgeladen (erfordert manuelle Nutzer-Freigabe Partner Center)

