#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Smart Ingest Package
==============================
Erkennung, Klassifikation, Konvertierung und Ingest für Dokumente.
"""

from .models import (
    FileType,
    IngestAction,
    IngestCandidate,
    IngestResult,
    IngestSummary,
)
from .detector import FormatDetector
from .scanner import FolderScanner
from .service import SmartIngestService

__all__ = [
    "FileType",
    "IngestAction",
    "IngestCandidate",
    "IngestResult",
    "IngestSummary",
    "FormatDetector",
    "FolderScanner",
    "SmartIngestService",
]
