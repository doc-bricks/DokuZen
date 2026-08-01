#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DokuZen Pro - OCR Module"""
from .engine import OCREngine, OCRResult, OCRPageResult, ocr_image, ocr_pdf, is_ocr_available

__all__ = [
    "OCREngine", "OCRResult", "OCRPageResult",
    "ocr_image", "ocr_pdf", "is_ocr_available"
]
