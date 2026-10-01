# DokuZen - Windows Store Build- & Packaging-Anleitung

## Voraussetzungen

1. Python 3.10+ mit PySide6, pypdfium2, pikepdf, Pillow, pytesseract
2. PyInstaller für den Desktop-Build (`build_exe.bat`)
3. Windows 10/11 SDK mit `makeappx.exe`, `signtool.exe` und `appcert.exe`
4. Lokaler Schreibpfad außerhalb synchronisierter Cloud-Ordner für MSIX-Artefakte, z. B. `C:\_Local_DEV\codex_build\dokuzen-store`

Die Befehle verwenden relative bzw. kanonische Pfade.
Setze `$projectRoot` auf den lokalen Checkout `C:\_Local_DEV\repos\DokuZen` und `$softwareRoot` auf den lokalen Pipeline-Ordner `C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE`.

---

## Schritt 0: Store-Material & Icons aktualisieren

```powershell
$projectRoot = "C:\_Local_DEV\repos\DokuZen"
Set-Location $projectRoot
$env:PYTHONIOENCODING="utf-8"

# Preflight-Store-Audit ausführen
python tools/check_store_readiness.py
pytest tests/test_store_readiness.py tests/test_store_materials.py
```

Erwartete Artefakte:
- `store_package\DokuZen\icons\icon_44x44.png`
- `store_package\DokuZen\icons\icon_50x50.png`
- `store_package\DokuZen\icons\StoreLogo.png` (50x50)
- `store_package\DokuZen\icons\icon_150x150.png`
- `store_package\DokuZen\icons\icon_310x150.png`
- `store_package\DokuZen\icons\icon_310x310.png`
- `releases\windowsstore\screenshots\*.png` (6 hochauflösende 1080p Store-Screenshots)
- `releases\windowsstore\StoreLogo.png` (50x50)

---

## Schritt 1: Desktop-EXE bauen

```powershell
Set-Location $projectRoot
cmd.exe /c build_exe.bat
```

Erwarteter Hauptpfad:
- `releases\v1.0.0\DokuZen-Pro-1.0.0-win64.exe` (oder Build-Output)

---

## Schritt 2: MSIX lokal außerhalb von OneDrive bauen

```powershell
$outputRoot = "C:\_Local_DEV\codex_build\dokuzen-store"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

python (Join-Path $softwareRoot "_STORE\store_packager.py") `
  $projectRoot `
  --output-dir $outputRoot `
  --app-name "DokuZen" `
  --version "1.0.1.0" `
  --publisher "CN=52596601-BAB4-4F3F-B182-E8F3F273B202" `
  --identity-name "Geiger.DokuZen" `
  --capabilities "runFullTrust"
```

Erwartetes MSIX-Paket:
- `C:\_Local_DEV\codex_build\dokuzen-store\DokuZen.msix`

---

## Schritt 3: Windows App Certification Kit (WACK) Lauf

In einer PowerShell-Konsole mit Administratorrechten:

```powershell
$softwareRoot = "C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE"
$msixPath = "C:\_Local_DEV\codex_build\dokuzen-store\DokuZen.msix"
$reportDir = Join-Path $projectRoot "releases\windowsstore\test_reports"

& (Join-Path $softwareRoot "_STORE\msstore_wack.ps1") `
  -MsixPath $msixPath `
  -ReportDir $reportDir
```

---

## Schritt 4: Partner Center Einreichung (Human-in-the-Loop)

Nach erfolgreichem WACK-Report und Freigabe durch den Nutzer:
1. Microsoft Partner Center öffnen
2. DokuZen (Store-ID `9PBLDN4QJDHN`) aufrufen
3. Neues Paket (`DokuZen.msix`) hochladen
4. Listing-Texte aus `releases\windowsstore\store_listing_de.md` und `store_listing_en.md` übernehmen
5. Screenshots aus `releases\windowsstore\screenshots\` hochladen
6. Zur Zertifizierung einreichen
