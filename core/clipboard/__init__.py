# -*- coding: utf-8 -*-
"""DokuZen Clipboard Spawner Paket.

Bietet Text- und Überschriften-Analyse, sichere Slug-Namensgenerierung und
Mehrformat-Speicherung aus der Zwischenablage.
"""

from core.clipboard.naming import slugify_filename, unique_path
from core.clipboard.structure import analyze_structure
from core.clipboard.manager import ClipboardManager, FORMATS

__all__ = [
    "ClipboardManager",
    "FORMATS",
    "analyze_structure",
    "slugify_filename",
    "unique_path",
]
