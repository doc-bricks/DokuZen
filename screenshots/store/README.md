# Store-Screenshots — DokuZen

## Anforderungen (Microsoft Store)

- Format: PNG oder JPEG
- Mindestauflösung: 1366 × 768 px
- Empfohlen: 1920 × 1080 px (16:9)
- Mindestanzahl: 1 Screenshot
- Maximalanzahl: 10 Screenshots
- Dateinamen: aussagekräftig, kein Leerzeichen

## Screenshot-Inventar (erstellt & verifiziert)

| Datei                          | Inhalt                                          | Auflösung   | Format | Status      |
|--------------------------------|-------------------------------------------------|-------------|--------|-------------|
| `01_bibliothek.png`            | Bibliotheksansicht mit Dokumentenliste          | 1920 × 1080 | PNG    | Verifiziert |
| `02_pdf_vorschau.png`          | PDF-Vorschau mit Seitenleiste                   | 1920 × 1080 | PNG    | Verifiziert |
| `03_ocr_dialog.png`            | OCR-Dialog mit Optionen & Texterkennung         | 1920 × 1080 | PNG    | Verifiziert |
| `04_schwaerzung.png`           | Schwärzungs-Werkzeug & PII-Erkennung            | 1920 × 1080 | PNG    | Verifiziert |
| `05_konvertierung.png`         | Konvertierungs-Dialog (PDF, DOCX, TXT, PNG)     | 1920 × 1080 | PNG    | Verifiziert |
| `06_batch_verarbeitung.png`    | Batch-Verarbeitung, Seiten-Auszug & Workshop    | 1920 × 1080 | PNG    | Verifiziert |

## Hinweise

- Screenshots unter Windows in nativer 1920 × 1080 Auflösung via PySide6 Offscreen Generator erzeugt (`tools/generate_store_screenshots.py`)
- Keine echten personenbezogenen Daten (ausschließlich neutrale Muster- und Demodaten)
- Deutschsprachige Store-UI im Dark-Teal Design-System

## Status

- [x] Screenshots erstellt (2026-08-14 via `tools/generate_store_screenshots.py`)
- [x] Qualität geprüft (Schärfe, 1080p, Valide PNG-Header, keine PII-Daten)
- [ ] In Store-Einreichung hochgeladen (erfordert manuelle Nutzer-Freigabe Partner Center)

