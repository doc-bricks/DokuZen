# DokuZen für Linux

Das portable Archiv enthält eine PyInstaller-onedir-Anwendung. Es benötigt
keine systemweite Python-Installation und läuft ohne Root-Rechte.

## Start

```bash
tar -xzf DokuZen-1.0.0-linux-*.tar.gz
cd DokuZen-1.0.0
./dokuzen
```

Tesseract bleibt eine optionale externe Systemabhängigkeit. Ohne das Paket
startet DokuZen normal; ausschließlich OCR-Funktionen sind eingeschränkt.
Unter Debian/Ubuntu kann Tesseract mit `sudo apt install tesseract-ocr`
installiert werden.

Die mitgelieferten Freedesktop-Dateien liegen unter `share/applications`,
`share/metainfo` und `share/icons`. Eine systemweite Installation ist nicht
Teil dieses portablen Bundles und wird nicht automatisch vorgenommen.
