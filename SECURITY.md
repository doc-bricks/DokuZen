# Sicherheitsrichtlinie / Security Policy

## Deutsch

### Sicherheitsphilosophie & Local-First Invarianten

DokuZen ist von Grund auf als 100% lokale, sichere Desktop-Dokumentensuite konzipiert:
- **Zero-Egress & 100% Offline**: Dokumente, PDF-Dateien, OCR-Scans und Metadaten verbleiben vollständig auf dem lokalen Rechner und werden zu keinem Zeitpunkt an externe Server übertragen.
- **Benutzerrechte & Non-Elevation**: DokuZen läuft vollständig im Standard-Benutzermodus (User-Space) und erfordert zu keinem Zeitpunkt Administrator- oder Root-Rechte.
- **Sichere Dokumentenverarbeitung**: PDF-, Word- und Bildverarbeitungsoperationen (über `PyMuPDF`/`fitz`, `pikepdf`, `python-docx` und `Pillow`) nutzen defensive Fehlerbehandlung und garantierte Dateideskriptor-Freigaben (Deterministic Cleanup).
- **Zerstörende Schwärzung**: Die Schwärzungs-Engine entfernt sensible Daten (PII) unwiderruflich aus dem Dokumenten-Stream mit schwarzer Pixel- und Vektorüberdeckung ohne verbleibende Textspuren.

### Sicherheitslücke melden

Wenn Sie in DokuZen eine Sicherheitslücke oder ein potenzielles Sicherheitsrisiko finden:

1. Bitte **kein** öffentliches Issue im GitHub-Tracker eröffnen.
2. Nutzen Sie das private Sicherheitsmeldeportal von GitHub: [Security Advisories](https://github.com/doc-bricks/DokuZen/security/advisories).
3. Alternativ per E-Mail an: `security@open-bricks.org`, `security@doc-bricks.org`, `security@ellmos.ai` oder `support@lukasgeiger.com`.
4. Bitte fügen Sie eine Beschreibung des Problems, Reproduktionsschritte und die betroffene Version bei.

### Relevante Sicherheitsbereiche

- Lokales Öffnen, Speichern und Konvertieren von Dokumenten (Pfadsicherheit / Traversal-Schutz)
- PDF-Verschlüsselungs-, Entsperr- und Signaturroutinen (`pikepdf` Session-Key Guards)
- OCR- und Textextraktions-Pipelines (`pytesseract` Subprozess-Grenzen)
- Persistenz- und Konfigurationsdateien (`dokuzen_state.json`, `settings.json`)

### Reaktionszeit

Kritische Sicherheitsmeldungen werden innerhalb von 48 Stunden bestätigt und mit höchster Priorität behoben.

---

## English

### Security Philosophy & Local-First Invariants

DokuZen is architected from the ground up as a 100% local, secure desktop document suite:
- **Zero-Egress & 100% Offline**: Documents, PDF streams, OCR scans, and metadata remain strictly on the local machine and are never transmitted to external servers.
- **User-Mode Execution & Non-Elevation**: DokuZen operates entirely in standard user space without requiring administrative or elevated privileges.
- **Defensive Document Parsing**: PDF, Word, and image processing operations (via `PyMuPDF`/`fitz`, `pikepdf`, `python-docx`, and `Pillow`) employ defensive error guards and deterministic file handle closure.
- **Permanent Redaction**: The redaction engine irrevocably sanitizes sensitive PII from document streams with destructive black-fill overlay and purge of underlying textual layers.

### Reporting a Vulnerability

If you discover a security vulnerability or potential risk in DokuZen:

1. Do **not** open a public issue on GitHub.
2. Use GitHub's private vulnerability reporting: [Security Advisories](https://github.com/doc-bricks/DokuZen/security/advisories).
3. Alternatively, reach out via email: `security@open-bricks.org`, `security@doc-bricks.org`, `security@ellmos.ai`, or `support@lukasgeiger.com`.
4. Include a detailed description, step-by-step reproduction guide, and affected version.

### Key Security Boundaries

- Local document ingestion, saving, and format transitions (path sanitization / directory traversal prevention)
- PDF encryption, decryption, and signature handling (`pikepdf` session-key isolation)
- OCR and layout extraction pipelines (`pytesseract` subprocess boundaries)
- State persistence and configuration management (`dokuzen_state.json`, `settings.json`)

### Response Time

Critical security advisories are acknowledged within 48 hours and resolved with top priority.

