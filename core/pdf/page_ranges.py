#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hilfsfunktionen für einfache PDF-Seiten-Notation."""

from typing import List, Optional


def parse_page_range_notation(text: str, page_count: Optional[int] = None) -> List[int]:
    """
    Parst Seitenangaben wie ``1,3,5-10`` in sortierte 1-basierte Seitenzahlen.

    Gibt bei leerem oder ungültigem Input ``[]`` zurück.
    """
    if not text or not text.strip():
        return []

    pages = set()

    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue

        if "-" in part:
            halves = part.split("-", 1)
            if len(halves) != 2:
                return []

            start_text = halves[0].strip()
            end_text = halves[1].strip()
            if not start_text or not end_text:
                return []

            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError:
                return []

            if start < 1 or end < start:
                return []

            if page_count is not None and end > page_count:
                return []

            pages.update(range(start, end + 1))
            continue

        try:
            page = int(part)
        except ValueError:
            return []

        if page < 1:
            return []

        if page_count is not None and page > page_count:
            return []

        pages.add(page)

    return sorted(pages)


__all__ = ["parse_page_range_notation"]
