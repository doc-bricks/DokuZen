# Windows Store — Vorbereitung DokuZen

Stand: 2026-09-20

---

## Identität

| Feld              | Wert                                         |
|-------------------|----------------------------------------------|
| Identity Name     | Geiger.DokuZen                               |
| Publisher         | CN=52596601-BAB4-4F3F-B182-E8F3F273B202      |
| Publisher Display | Geiger                                       |
| Version           | 1.0.1.0                                      |
| Executable        | DokuZen-Pro-1.0.0-win64.exe                  |

Publisher-Identität identisch mit ExplorerPro (gleiches Microsoft Partner Center
Konto). Werte verbatim aus `store_package.json` übernehmen.

## Aktiver und historischer Packaging-Vertrag

Der aktive Store-Pfad ist eindeutig:

- Aktives Manifest: `store_package/DokuZen/AppxManifest.xml`
- Aktive Store-Identität und Paketversion: `Geiger.DokuZen`, `1.0.1.0`
- Aktiver Executable-Vertrag: `DokuZen-Pro-1.0.0-win64.exe`
- Der Executable-Name ist ein bewusst beibehaltenes historisches Release-
  Namensschema. Das 1.0.1.0-MSIX verwendet dieses bestehende Binary-Schema;
  eine Umbenennung ist nicht durch diesen Eintrag autorisiert.
- `store_package/DokuZen Pro/AppxManifest.xml` ist das historische 1.0.0-
  Manifest und nicht der aktive Store-Eingang. Der Readiness-Gatekeeper prüft
  ausschließlich den oben genannten kanonischen Pfad und wählt keine
  verschachtelte Manifestdatei per Glob aus.

`build_exe.bat` bleibt deshalb bis zu einer ausdrücklich bestätigten neuen
Executable-Linie auf `VERSION=1.0.0` gepinnt. Eine künftige Änderung muss
Buildscript, `store_package.json`, aktives Manifest, Tests, MSIX-Inhalt und
Hash-/Provenienz-Dokumentation gemeinsam aktualisieren.

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
- [x] Partner Center Richtlinie 10.1.3 Keywords gehärtet (max. 7 Begriffe je Sprache, markenrechtsfrei) (2026-09-10)

### GitHub-Repository

- [x] Repository `doc-bricks/DokuZen` erstellt und `origin` auf
      `https://github.com/doc-bricks/DokuZen.git` verifiziert (2026-08-02)
- [x] Privacy-URL und Support-URL in `store_package.json` auf das bestehende
      Repository verifiziert (2026-08-02)

### Paketierung & Freigabe

- [x] `build_exe.bat` ausgeführt → `releases/v1.0.0/DokuZen-Pro-1.0.0-win64.exe` (99.3 MB)
- [x] `python tools\preflight.py` ausführen (Bestanden)
- [x] MSIX-Paket erzeugt: `releases/windowsstore/v1.0.1/DokuZen-1.0.1.0.msix` (98.8 MB, SHA256 verifiziert)
- [ ] WACK-Test (Windows App Certification Kit) auf Zielumgebung abschließen
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

- Task 1859 — Store-Screenshot-Paket erstellen (`[x] ERLEDIGT 2026-08-14`, 6/6 Screenshots 1920x1080)
- Task 1860 — Windows-Build und strikten Store-Preflight nachweisen (`[x] ERLEDIGT 2026-08-14`)
- Task 1861 — MSIX-Paket erzeugen und WACK/Store-Entscheidung vorbereiten (`[x] MSIX v1.0.1.0 erzeugt 2026-08-23; WACK-Zertifizierungstest auf Zielsystem offen`)

Die externe Store-Hochladung ist durch Task 1861 nicht autorisiert; dafür bleibt
eine ausgefüllte Nutzerentscheidung erforderlich.
