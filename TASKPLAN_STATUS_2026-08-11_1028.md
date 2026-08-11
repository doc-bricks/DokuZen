# TASKPLAN-Status — DokuZen — Task 1028

Stand: 2026-08-11 Europe/Berlin
Projekt: `C:\_Local_DEV\repos\DokuZen`
OneDrive-Spiegel: `C:\Users\lukas\OneDrive\.TOPICS\.SOFTWARE\DOCS\DEV_DokuZen`

## Entscheidung

DokuZen ist nach dem aktuellen Portierungsplan eine lokale Desktop-
Dokumenten- und PDF-Werkstatt. `main.py` stellt fünf GUI-Startaktionen bereit:
`--import`, `--open`, `--ocr`, `--redact` und `--merge`. Diese Aktionen starten
die PySide6-App und sind kein headless Batch- oder Remote-Vertrag.

Ein konkreter Remote-, Agenten- oder anderer Automationsbedarf ist in den
kanonischen Projektquellen und Tests nicht belegt. Deshalb bleiben eine
headless Batch-CLI und eine projektlokale REST-API vorerst außerhalb des
Produktumfangs. Es wird kein unsupported API-Claim und kein API-Template
ergänzt.

Ein späterer Ausbau darf erst nach einem belegten Usecase und einer
freigegebenen Sicherheitsentscheidung erfolgen. Diese muss mindestens
Authentifizierung, zulässige Eingaben und Ausgaben sowie Ressourcenlimits
festlegen; die Implementierung braucht isolierte Tests.

## Evidenz

- `README.md`, `README_de.md` und `llms.txt` beschreiben die fünf vorhandenen
  GUI-CLI-Optionen und die fehlende REST-API.
- `PORTIERUNGSPLAN.md` grenzt DokuZen als lokale Desktop-Workstation ab und
  fordert Headless/REST nur bei echtem Bedarf.
- `AUFGABEN.txt` führt Headless-Batch und REST weiterhin als konditionale
  Folgeaufgaben; ein konkreter Bedarf ist nicht eingetragen.
- `python main.py --help` zeigt genau diese fünf GUI-Startaktionen.
- `tests/test_cli_startup.py` prüft Parsing, Dispatch und unbekannte Aktionen.
- Der gezielte Lauf `python -m pytest -q -p no:cacheprovider tests/test_cli_startup.py tests/test_store_materials.py tests/test_third_party_licenses.py` ist mit 14 Tests und 26 Subtests grün.
- Ein enger Quellscan findet keinen Flask-/FastAPI-/uvicorn-/HTTP-Server-/REST-API-Einstiegspunkt.

## Grenze

Es wurden keine Produktquellen für eine REST-API oder headless Verarbeitung
geändert. Es gab keinen Release-, Upload- oder Push-Vorgang.
