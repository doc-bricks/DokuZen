# Windows Store — Vorbereitung DokuZen

Stand: 2026-08-14

---

## Identität

| Feld              | Wert                                         |
|-------------------|----------------------------------------------|
| Identity Name     | Geiger.DokuZenPro                        |
| Publisher         | CN=52596601-BAB4-4F3F-B182-E8F3F273B202      |
| Publisher Display | Geiger                                       |
| Version           | 1.0.0.0                                      |
| Executable        | DokuZen-Pro-1.0.0-win64.exe              |

Publisher-Identität identisch mit ExplorerPro (gleiches Microsoft Partner Center
Konto). Werte verbatim aus `store_package.json` übernehmen.

---

## Checkliste: Vor Store-Einreichung

### Pflichtartefakte

- [x] `store_package.json` erstellt (2026-06-07)
- [x] `STORE_LISTING.md` erstellt — DE + EN Beschreibung (2026-06-07)
- [x] `PRIVACY_POLICY.md` erstellt (2026-06-07)
- [x] `SUPPORT.md` erstellt (2026-06-07)
- [x] `THIRD_PARTY_LICENSES.txt` als direkte Runtime-Inventur aus
      `requirements.txt` erstellt (2026-07-12; kein transitive SBOM)
- [x] `store_package/DokuZen/AppxManifest.xml` erstellt & validiert (2026-08-14)
- [x] Store-Tile-Icons (44x44, 50x50, 150x150, 310x150, 310x310) generiert (2026-08-14)
- [x] Store-Screenshots (6/6 in 1920x1080 PNG) generiert & verifiziert (2026-08-14)
- [x] Store-Readiness-Gate `tools/check_store_readiness.py` & Testsuite `tests/test_store_readiness.py` (2026-08-14)

### GitHub-Repository

- [x] Repository `doc-bricks/DokuZen` erstellt und `origin` auf
      `https://github.com/doc-bricks/DokuZen.git` verifiziert (2026-08-02)
- [x] Privacy-URL und Support-URL in `store_package.json` auf das bestehende
      Repository verifiziert (2026-08-02)

### Paketierung & Freigabe

- [ ] `build_exe.bat` ausführen → `releases/v1.0.0/DokuZen-Pro-1.0.0-win64.exe`
- [x] `python tools\preflight.py` ausführen (Bestanden)
- [ ] MSIX-Paket erzeugen (MakeAppx / Windows Application Packaging Project / WinStorePackager)
- [ ] WACK-Test (Windows App Certification Kit) bestehen
- [ ] Paket im Microsoft Partner Center hochladen (Manuelle Nutzer-Freigabe)


---

## Technische Hinweise

### Capabilities

`runFullTrust` — erforderlich für lokalen Dateisystemzugriff (keine Store-Sandbox).

### Kategorie

Productivity — entspricht dem Funktionsprofil (PDF-Bearbeitung, OCR, Konvertierung).

### Altersfreigabe

3+ — keine Gewalt, keine Erwachseneninhalte, keine Käufe.

### Anforderungen

- Windows 10 Version 1903 (Build 18362) oder höher
- x64-Prozessor
- 4 GB RAM empfohlen (für OCR-intensive Dokumente)
- ca. 150 MB Speicherplatz

---

## Verwandte Dateien

- `store_package.json` — maschinenlesbare Paket-Metadaten
- `STORE_LISTING.md` — Store-Beschreibung DE/EN
- `PRIVACY_POLICY.md` — Datenschutzerklärung
- `SUPPORT.md` — Support-Seite
- `THIRD_PARTY_LICENSES.txt` — direkte Runtime-Lizenzinventur
- `screenshots/store/README.md` — Screenshot-Inventar
- `build_exe.bat` — Build-Skript Windows
- `tools/preflight.py` — Pflicht-/Optional-/OCR-/Build-Preflight

## TASKWRITER-FORMALISIERUNG (2026-08-02)

Die noch offenen Store-Schritte sind im TASKPLAN-Projekt
`C:\_Local_DEV\repos\DokuZen` erfasst:

- Task 1859 — Store-Screenshot-Paket erstellen (`effort=medium`, `scope=local`)
- Task 1860 — Windows-Build und strikten Store-Preflight nachweisen (`effort=medium`, `scope=local`)
- Task 1861 — MSIX-/WACK-Freigabe als Store-Entscheidung vorbereiten (`effort=special`, `scope=local`)

Die externe Store-Hochladung ist durch Task 1861 nicht autorisiert; dafür bleibt
eine ausgefüllte Nutzerentscheidung erforderlich.
