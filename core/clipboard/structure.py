# -*- coding: utf-8 -*-
"""Textstruktur- und Überschriften-Analyse für DokuZen Clipboard Spawner."""

from __future__ import annotations

import re

_HEADING_MAX_LENGTH = 60
_SENTENCE_ENDINGS = ('.', '!', '?', ',', ';')


def analyze_structure(text: str) -> list[dict]:
    """Analysiert die Textstruktur und erkennt Überschriften vs. Absätze.

    Heuristiken für Überschriften:
    - Markdown-Überschriften (# Heading, ## Subheading, ...)
    - Vollständig in Großbuchstaben (mindestens 2 Zeichen)
    - Endet mit Doppelpunkt (':')
    - Kurz (< 60 Zeichen), beginnt mit Großbuchstabe, enthält Leerzeichen
      und endet nicht mit Satzzeichen (. ! ? , ;)

    Parameters
    ----------
    text:
        Zu analysierender Rohtext.

    Returns
    -------
    list[dict]
        Liste von Elementen im Format:
        [{"type": "heading"|"paragraph", "text": "..."}]
    """
    elements: list[dict] = []
    buffer: list[str] = []

    def flush_buffer():
        if buffer:
            elements.append({
                "type": "paragraph",
                "text": " ".join(buffer),
            })
            buffer.clear()

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            flush_buffer()
            continue

        # Prüfe auf Markdown-Überschrift
        md_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if md_match:
            flush_buffer()
            elements.append({
                "type": "heading",
                "text": md_match.group(2).strip(),
                "level": len(md_match.group(1)),
            })
            continue

        # Heuristische Überschriftserkennung
        is_upper_heading = stripped.isupper() and len(stripped) >= 2 and any(c.isalpha() for c in stripped)
        is_colon_heading = stripped.endswith(':') and len(stripped) < _HEADING_MAX_LENGTH and not stripped.startswith('http')
        is_title_heading = (
            len(stripped) < _HEADING_MAX_LENGTH
            and stripped[0].isupper()
            and ' ' in stripped
            and not any(stripped.endswith(p) for p in _SENTENCE_ENDINGS)
        )

        if is_upper_heading or is_colon_heading or is_title_heading:
            flush_buffer()
            clean_text = stripped.rstrip(':') if is_colon_heading else stripped
            elements.append({
                "type": "heading",
                "text": clean_text,
            })
        else:
            buffer.append(stripped)

    flush_buffer()
    return elements
