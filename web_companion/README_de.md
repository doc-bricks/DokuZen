# DokuZen Web Companion (PWA)

**Deutsch** | [English](README.md)

Der **DokuZen Web Companion** ist eine offline-fähige Progressive Web App (PWA), mit der exportierte DokuZen-Workspace-Snapshots auf Mobilgeräten und Zweitrechnern durchsucht und gelesen werden können — ohne Python-Laufzeitumgebung oder native Desktop-Abhängigkeiten.

---

## 🏛️ Architektur & Local-First Prinzipien

1. **100% Client-Seitige Ausführung:** Sämtliche Parsing- und Anzeigelogik läuft direkt im Browser über reines, modernes JavaScript (`app.js`, `library.js`). Es existiert kein externer Server, kein Telemetrie-Dienst und kein Netzwerk-Egress.
2. **Service Worker Offline-Cache (`sw.js`):** Nach dem ersten Aufruf werden sämtliche Ressourcen lokal vorgehalten; die PWA funktioniert vollständig ohne aktive Internetverbindung.
3. **Hermetischer Snapshot-Import:** Verarbeitet strukturierte JSON-Arbeitsbereichsdateien aus DokuZens *Workspace-Export*-Funktion, die gemäß Schema frei von absoluten Dateipfaden, Passwörtern und Binärdaten sind.
4. **Zero-Egress Sicherheitsinvarianten:** In Übereinstimmung mit den Sicherheitsrichtlinien des Projekts (`SECURITY.md`) verlassen keinerlei Dokumenteninhalte oder Metadaten das lokale Gerät.

---

## 🚀 Nutzung & Bereitstellung

### Lokale Ansicht
Öffnen Sie `index.html` direkt im Webbrowser oder starten Sie einen lokalen Hilfsserver:

```bash
# Optionaler lokaler Testserver
python -m http.server 8080 --directory web_companion
```

### Snapshot laden
1. Exportieren Sie einen Arbeitsbereichs-Snapshot aus DokuZen (`Werkzeuge` -> `Arbeitsbereich exportieren`).
2. Öffnen Sie den Web Companion und ziehen Sie die `.json`-Datei per Drag & Drop in das Fenster.
3. Durchsuchen Sie Themenordner, Dokumentmetadaten und geschwärzte Textansichten.

---

## 🔒 Datenschutz & Sicherheit

- **Lokal & Autark:** Baut keinerlei externe Verbindungen zu Drittanbietern auf.
- **Validierung:** Prüft eingehende Dateien gegen das definierte Snapshot-Schema (`validate_workspace_snapshot`).
- **CDN-Freiheit:** Alle Stylesheets (`style.css`), Skripte und App-Icons liegen hermetisch im Verzeichnis.
