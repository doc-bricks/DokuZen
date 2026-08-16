# Store-Screenshots — DokuZen

## Anforderungen (Microsoft Store)

- Format: PNG oder JPEG
- Mindestauflösung: 1366 × 768 px
- Empfohlen: 1920 × 1080 px (16:9)
- Mindestanzahl: 1 Screenshot
- Maximalanzahl: 10 Screenshots
- Dateinamen: aussagekräftig, kein Leerzeichen

## Store-Screenshots (erstellt 2026-08-10)

| Datei                          | Inhalt                                          | Priorität |
|--------------------------------|-------------------------------------------------|-----------|
| `01_bibliothek.png`            | Bibliotheksansicht mit Dokumentenliste          | Pflicht   |
| `02_pdf_vorschau.png`          | PDF-Vorschau mit Seitenleiste                   | Pflicht   |
| `03_ocr_dialog.png`            | OCR-Dialog mit Fortschrittsanzeige              | Hoch      |
| `04_schwaerzung.png`           | Schwärzungs-Werkzeug aktiv                      | Hoch      |
| `05_konvertierung.png`         | Konvertierungs-Dialog (PDF → DOCX)              | Mittel    |
| `06_batch_verarbeitung.png`    | Batch-Verarbeitung mehrerer Dokumente           | Mittel    |

## Hinweise

- Screenshots unter Windows 10/11 in 1920 × 1080 erstellen
- Keine echten personenbezogenen Daten in Screenshot-Dokumenten verwenden
- Musterdokumente aus `tests/fixtures/` können als Demonstrationsdateien
  genutzt werden (sofern vorhanden)
- Für Store-Zertifizierung: deutschsprachige UI-Screenshots bevorzugt;
  englische Versionen optional für EN-Listing

## Erzeugung und Status

- [x] Screenshots erstellt (2026-08-10, jeweils 1920 × 1080 PNG)
- [x] Qualität geprüft (sichtbare UI, Lesbarkeit, keine echten PII; Demo-Hinweise
      transparent gekennzeichnet)
- [ ] In Store-Einreichung hochgeladen

Die sechs Aufnahmen werden reproduzierbar mit
`python tools\generate_store_screenshots.py` aus den echten DokuZen-PySide6-
Fenstern erzeugt. Der Generator verwendet ausschließlich temporäre, klar als
Demo markierte Beispieldokumente; OCR- und Konvertierungsdialoge werden nur
für die UI-Aufnahme befüllt und nicht ausgeführt. Eine Store-Hochladung ist
nicht Bestandteil dieses Tasks.
