#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Document Converter
====================================
Wrapper-Modul für die Dokumentkonvertierung.
Re-exportiert Klassen aus formats.py für Rückwaertskompatibilitaet.
"""

from .formats import (
    FormatConverter,
    ConversionResult,
    OutputFormat,
    convert_to_pdf,
    convert_to_text,
    batch_convert,
    PYMUPDF_AVAILABLE,
    DOCX_AVAILABLE,
    PIL_AVAILABLE,
    REPORTLAB_AVAILABLE,
)

# Alias für Rückwaertskompatibilitaet
DocumentConverter = FormatConverter

__all__ = [
    "DocumentConverter",
    "FormatConverter",
    "ConversionResult",
    "OutputFormat",
    "convert_to_pdf",
    "convert_to_text",
    "batch_convert",
]
