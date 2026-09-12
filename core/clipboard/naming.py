# -*- coding: utf-8 -*-
"""Dateinamen- und Pfad-Hilfsfunktionen für DokuZen Clipboard Spawner."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

_UMLAUT_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
}

_INVALID_CHARS_RE = re.compile(r'[^a-zA-Z0-9_\-]')
_MULTI_UNDERSCORE_RE = re.compile(r'_+')


def slugify_filename(
    text: str,
    words: int = 3,
    maxlen: int = 50,
) -> str:
    """Erstellt einen sicheren, lesbaren Dateinamen aus dem Anfang eines Textes.

    Parameters
    ----------
    text:
        Quelltext (z. B. Überschrift oder Textanfang).
    words:
        Anzahl der zu berücksichtigenden Wörter (Standard: 3).
    maxlen:
        Maximale Zeichenlänge des Dateinamens (Standard: 50).

    Returns
    -------
    str
        Sicherer Dateiname ohne Dateiendung.
    """
    if not text:
        return datetime.now().strftime("clipboard_%Y%m%d_%H%M%S")

    # Erstes nicht-leeres Zeilensegment / Überschrift ermitteln
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return datetime.now().strftime("clipboard_%Y%m%d_%H%M%S")

    raw_segment = lines[0]
    # Markdown-Überschriften-Präfixe (#, ##, etc.) entfernen
    raw_segment = re.sub(r'^#+\s*', '', raw_segment)

    # Umlaute ersetzen
    for umlaut, repl in _UMLAUT_MAP.items():
        raw_segment = raw_segment.replace(umlaut, repl)

    # Diakritische Zeichen normalisieren (z.B. é -> e)
    norm = unicodedata.normalize("NFKD", raw_segment)
    ascii_text = norm.encode("ascii", "ignore").decode("ascii")

    # Wörter extrahieren
    token_list = [t for t in ascii_text.split() if t]
    if not token_list:
        return datetime.now().strftime("clipboard_%Y%m%d_%H%M%S")

    selected_tokens = token_list[:words]
    combined = "_".join(selected_tokens)

    # Ungültige Zeichen durch Unterstriche ersetzen
    slug = _INVALID_CHARS_RE.sub('_', combined)
    slug = _MULTI_UNDERSCORE_RE.sub('_', slug).strip('_')

    if not slug or slug.lower() in ("dokument", "document", "datei", "file"):
        return datetime.now().strftime("clipboard_%Y%m%d_%H%M%S")

    if len(slug) > maxlen:
        slug = slug[:maxlen].rstrip('_')

    return slug or datetime.now().strftime("clipboard_%Y%m%d_%H%M%S")


def unique_path(base: Path, ext: str) -> Path:
    """Generiert einen eindeutigen Dateipfad (hängt _1, _2, ... an, falls bereits vorhanden).

    Parameters
    ----------
    base:
        Basis-Pfad (ohne Endung oder mit generischem Namen).
    ext:
        Dateiendung (mit oder ohne führenden Punkt).

    Returns
    -------
    Path
        Eindeutiger Zieldateipfad.
    """
    norm_ext = ext if ext.startswith('.') else f".{ext}"
    target = base.with_suffix(norm_ext)
    if not target.exists():
        return target

    parent = base.parent
    stem = base.stem
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{norm_ext}"
        if not candidate.exists():
            return candidate
        counter += 1
