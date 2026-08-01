# Windows Store — Vorbereitung DokuZen Pro

Stand: 2026-07-12

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
- [ ] Screenshots erstellt (siehe `screenshots/store/README.md`)

### GitHub-Repository

- [ ] Repository `doc-bricks/DokuZen` erstellen
- [ ] Privacy-URL und Support-URL in `store_package.json` verifizieren
      (aktuell provisorisch: `doc-bricks/DokuZen`)

### Paketierung

- [ ] `build_exe.bat` ausführen → `releases/v1.0.0/DokuZen-Pro-1.0.0-win64.exe`
- [ ] `python tools\preflight.py --strict-build` ausführen; bei OCR-Pflicht
      zusätzlich `python tools\preflight.py --strict-build --require-ocr`
- [ ] MSIX-Paket erzeugen (MakeAppx / Windows Application Packaging Project)
- [ ] WACK-Test (Windows App Certification Kit) bestehen
- [ ] Paket im Microsoft Partner Center hochladen

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
