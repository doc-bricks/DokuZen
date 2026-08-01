#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DokuZen Pro - Dialoge Module"""
from .convert_dialog import ConvertDialog
from .ocr_dialog import OCRDialog
from .redaction_dialog import RedactionDialog
from .pdf_workshop import PDFWorkshopDialog
from .text_pool_dialog import TextPoolDialog
from .settings_dialog import SettingsDialog
from .form_builder_dialog import FormBuilderDialog
from .pdf_marker_dialog import PDFMarkerDialog
from .sqlite_viewer_dialog import SQLiteViewerDialog
from .image_converter_dialog import ImageConverterDialog
from .pyinstaller_dialog import PyInstallerDialog
from .pdf_pages_dialog import PDFPagesDialog
from .code_analysis_dialog import CodeAnalysisDialog

__all__ = [
    "ConvertDialog",
    "OCRDialog",
    "RedactionDialog",
    "PDFWorkshopDialog",
    "TextPoolDialog",
    "SettingsDialog",
    "FormBuilderDialog",
    "PDFMarkerDialog",
    "SQLiteViewerDialog",
    "ImageConverterDialog",
    "PyInstallerDialog",
    "PDFPagesDialog",
    "CodeAnalysisDialog",
]
