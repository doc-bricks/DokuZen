#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DokuZen Pro - PDF Module"""
from .processor import PDFProcessor, PDFInfo
from .reader import PDFReader, PDFPage, PDFMetadata
from .merger import PDFMerger, MergeResult, MergeItem
from .security import PDFSecurity, UnlockResult
from .annotations import PDFAnnotator, Annotation, AnnotationType, AnnotationColor, StampType
from .crop import PDFMarginCropper, crop_document_margins, crop_pdf_margins
from .page_ranges import parse_page_range_notation
from .page_numbers import PDFPageNumberer, add_page_numbers, add_page_numbers_to_document
from .signature import SignatureOverlay, embed_signature

__all__ = [
    "PDFProcessor",
    "PDFReader",
    "PDFInfo",
    "PDFPage",
    "PDFMetadata",
    "PDFMerger",
    "MergeResult",
    "MergeItem",
    "PDFSecurity",
    "UnlockResult",
    "PDFAnnotator",
    "Annotation",
    "AnnotationType",
    "AnnotationColor",
    "StampType",
    "PDFMarginCropper",
    "crop_document_margins",
    "crop_pdf_margins",
    "parse_page_range_notation",
    "PDFPageNumberer",
    "add_page_numbers",
    "add_page_numbers_to_document",
    "SignatureOverlay",
    "embed_signature",
]
