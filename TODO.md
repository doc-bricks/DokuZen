# TODO — DokuZen

Diese Datei ist die TASKWRITER-Erfassung zum Bundle vom 2026-09-05. Die
kanonischen Aufgaben stehen im TASKPLAN-Register; hier bleiben IDs, Quellen und
der Review-Nachweis.

## Offene TASKPLAN-Aufgaben

- [x] #372 Aktive Versionsquelle über GUI, Build, Linux und Dokumentation
  synchronisieren -- DONE 2026-09-10 (core.__version__ = "1.0.1", main.py --version,
  About-Dialog, config/settings.json, tools/build_linux_bundle.py, AppStream
  metainfo, packaging README, README badges & text, tests/test_metadata.py Parity-Gating).
- [ ] #373 Aktive Store-Vorbereitung und historische DokuZen-Pro-Artefakte
  abgleichen.
- [ ] #374 GitHub-Actions auf verifizierte unveränderliche SHAs pinnen.

## TASKWRITER-Review — 2026-09-05

- Bundle: `9ca4284f-a3b3-4488-a193-54ab1202aea1` · selector review
  `sha256-v1:5e4bb64e278f24c26226f028e3290ee47432f938c5ce0b5b532e49c1d9b5778a`
- Projekt/Stand: `C:\_Local_DEV\repos\DokuZen`, Branch `main`, `b3e4ee0`,
  `main...origin/main`, Arbeitsbaum vor dem TASKWRITER-Schreiben sauber.
- Gelesene Kontrollen: README EN/DE, `llms.txt`, `CHANGELOG.md`,
  `pyproject.toml`, `requirements.txt`, `PRIVACY_POLICY.md`, `SECURITY.md`,
  `SUPPORT.md`, `STORE_LISTING.md`, `THIRD_PARTY_LICENSES.txt`,
  `WINDOWS_STORE_PREP.md`, `store_package.json`, beide Appx-Manifeste,
  `SUITE_DOKUZEN_TEMPLATE.md`, alle Workflows, Tests und Packaging-Skripte;
  kein projektlokales `AGENTS.md` oder `CLAUDE.md` gefunden.
- Verifikation: `python -m pytest -q` — 304 bestanden, 26 Subtests;
  `python -m compileall -q core gui plugins utils main.py tests tools scripts`;
  `python -m ruff check .`; `python tools/build_linux_bundle.py --check`;
  `python tools/check_store_readiness.py` — alle Readiness-Gates bestanden.
- Befund Versionsdrift: PyProject `1.0.1`, Store/aktives Manifest `1.0.1.0`,
  aber GUI, Windows-Build, Linux-Bundle, README-Badges und mehrere
  Vorbereitungstexte führen noch `1.0.0` oder `DokuZen Pro`.
- Befund CI-Supply-Chain: `source-platform-smoke.yml` und
  `linux-bundle.yml` verwenden mutable `actions/checkout@v4`,
  `actions/setup-python@v5` und `actions/upload-artifact@v4`.
- Keine Aufgaben ausgeführt, kein Build-/Store-/Upload-/Release-Schritt
  ausgelöst; der TASKWRITER-Lock wird vor dem Review entfernt.
