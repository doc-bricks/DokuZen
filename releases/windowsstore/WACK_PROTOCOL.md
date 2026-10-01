# DokuZen - WACK-Protokoll

## Ziel

Nach dem lokalen MSIX-Build soll der Windows App Certification Kit (WACK)-Lauf dokumentiert werden, damit Store-Submission und spätere Regressionen nachvollziehbar bleiben.

## Vorbereiteter Befehl

```powershell
$projectRoot = "C:\_Local_DEV\repos\DokuZen"
$softwareRoot = "C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE"
$outputRoot = "C:\_Local_DEV\codex_build\dokuzen-store"
$reportRoot = Join-Path $projectRoot "releases\windowsstore\test_reports"
Start-Process powershell -Verb RunAs -ArgumentList @(
  "-ExecutionPolicy Bypass",
  "-File $(Join-Path $softwareRoot '_STORE\msstore_wack.ps1')",
  "-MsixPath $(Join-Path $outputRoot 'DokuZen.msix')",
  "-ReportDir $reportRoot"
)
```

## Aktueller Status

- Stand dieses Laufs (2026-09-21): Preflight Store-Audit erfolgreich (vollständige Kriterien PASS, 0 Findings).
- Vollständige Test-Suite (413+ Tests) lokal 100% grün.
- Kacheln (44x44, 50x50 `StoreLogo.png`, 150x150, 310x150, 310x310) und 6x 1080p Screenshots maßhaltig vorhanden.
- Capabilities: `runFullTrust` deklariert (notwendig für lokale PDF-Verarbeitung, Tesseract-OCR und Windows Desktop-Dateizugriff).
- Packaging-Provenienz: Aktives Manifest `store_package/DokuZen/AppxManifest.xml` mit `Geiger.DokuZen`/`1.0.1.0`. Etablierter Executable-Name `DokuZen-Pro-1.0.0-win64.exe`.
- Verifizierter Status für WACK: WACK erfordert administrative Rechte (`RunAs`). In CI/Automationen ohne GUI-Elevation ist ein interaktiver Admin-Aufruf erforderlich.
- Erwartete Ablage:
  - XML-Report unter `releases\windowsstore\test_reports\`
  - Konsolenlog unter `releases\windowsstore\test_reports\`

## Eintrag für den nächsten WACK-Lauf

- Datum:
- MSIX-Pfad:
- WACK-Gesamtergebnis:
- Anzahl PASS:
- Anzahl FAIL:
- Anzahl WARNING:
- Relevante Findings:
- Nächste Korrektur:
