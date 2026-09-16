#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Collection / Binder PDF Exporter
==============================================
Führt mehrere Dokumente (PDFs, Bilder, Text/Markdown) zu einem
einheitlichen Sammel-PDF (Binder) zusammen, inklusive Lesezeichen (TOC),
optionaler Seitennummerierung und robuster Formatkonvertierung.
"""

from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from typing import List, Optional, Sequence, Tuple, Union

from utils.logger import LoggerMixin, get_logger
from core.pdf.page_numbers import add_page_numbers_to_document

_logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class CollectionExportOptions:
    """Konfigurationsoptionen für den Sammel-PDF-Export."""
    add_bookmarks: bool = True
    add_page_numbers: bool = False
    page_number_pattern: str = "Seite {page} / {total}"
    title: Optional[str] = None
    page_width: float = 595.0   # A4 Standardbreite (pt)
    page_height: float = 842.0  # A4 Standardhöhe (pt)
    margin: float = 36.0        # 0.5 Zoll Rand (pt)


@dataclass
class CollectionExportResult:
    """Ergebnis des Sammel-PDF-Exports."""
    success: bool
    output_path: str
    total_pages: int = 0
    document_count: int = 0
    skipped_files: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CollectionExporter(LoggerMixin):
    """
    Kombiniert Dokumente unterschiedlicher Formate zu einer konsolidierten Sammel-PDF.

    Unterstützte Quellformate:
    - PDF (.pdf)
    - Bilder (.png, .jpg, .jpeg, .bmp, .webp, .tiff)
    - Text & Markdown (.txt, .md, .log, .json, .xml)
    - Word (.docx, falls python-docx verfügbar)
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff",
        ".txt", ".md", ".log", ".json", ".xml",
        ".docx",
    }

    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF ist nicht verfügbar")

    def export(
        self,
        documents: Sequence[Union[str, Path]],
        output_path: Union[str, Path],
        options: Optional[CollectionExportOptions] = None,
    ) -> CollectionExportResult:
        """
        Exportiert eine Liste von Dokumenten als konsolidiertes Sammel-PDF.

        Args:
            documents: Liste von Dateipfaden
            output_path: Zieldateipfad für die Sammel-PDF
            options: Optionale Konfigurationsparameter

        Returns:
            CollectionExportResult
        """
        if not PYMUPDF_AVAILABLE:
            return CollectionExportResult(
                success=False,
                output_path=str(output_path),
                error="PyMuPDF ist nicht verfügbar.",
            )

        if not documents:
            return CollectionExportResult(
                success=False,
                output_path=str(output_path),
                error="Keine Dokumente zum Exportieren angegeben.",
            )

        opts = options or CollectionExportOptions()
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        output_doc = None
        temp_files: List[Path] = []
        skipped: List[str] = []
        toc_entries: List[List[Union[int, str]]] = []
        doc_count = 0

        try:
            output_doc = fitz.open()

            for doc_entry in documents:
                p = Path(doc_entry)
                if not p.exists() or not p.is_file():
                    self.logger.warning("Datei übersprungen (nicht gefunden): %s", p)
                    skipped.append(str(p))
                    continue

                start_page_1_based = len(output_doc) + 1
                ext = p.suffix.lower()
                pages_added = 0

                if ext == ".pdf":
                    pages_added = self._insert_pdf(output_doc, p)
                elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}:
                    pages_added = self._insert_image(output_doc, p, opts)
                elif ext in {".txt", ".md", ".log", ".json", ".xml"}:
                    pages_added = self._insert_text(output_doc, p, opts)
                elif ext == ".docx":
                    pages_added = self._insert_docx(output_doc, p, temp_files)
                else:
                    self.logger.warning("Nicht unterstütztes Format übersprungen: %s", p)
                    skipped.append(str(p))
                    continue

                if pages_added > 0:
                    doc_count += 1
                    # Lesezeichen für dieses Dokument hinterlegen
                    title = p.stem.replace("_", " ")
                    toc_entries.append([1, title, start_page_1_based])
                else:
                    skipped.append(str(p))

            total_pages = len(output_doc)
            if total_pages == 0:
                return CollectionExportResult(
                    success=False,
                    output_path=str(output_path),
                    document_count=0,
                    skipped_files=skipped,
                    error="Es konnten keine gültigen Seiten aus den angegebenen Dokumenten exportiert werden.",
                )

            # Inhaltsverzeichnis / Bookmarks eintragen
            if opts.add_bookmarks and toc_entries:
                try:
                    output_doc.set_toc(toc_entries)
                except Exception as exc:
                    self.logger.warning("Lesezeichen konnten nicht gesetzt werden: %s", exc)

            # Fortlaufende Seitennummern hinzufügen
            if opts.add_page_numbers:
                add_page_numbers_to_document(
                    output_doc,
                    pattern=opts.page_number_pattern,
                )

            # PDF Metadaten setzen
            meta = output_doc.metadata or {}
            meta["title"] = opts.title or out_p.stem.replace("_", " ")
            meta["creator"] = "DokuZen Sammel-PDF Export"
            meta["producer"] = "PyMuPDF / DokuZen"
            output_doc.set_metadata(meta)

            # Speichern
            output_doc.save(str(out_p), garbage=3, deflate=True)
            self.logger.info(
                "Sammel-PDF erfolgreich erstellt: %s (%d Seiten aus %d Dokumenten)",
                out_p,
                total_pages,
                doc_count,
            )

            return CollectionExportResult(
                success=True,
                output_path=str(out_p),
                total_pages=total_pages,
                document_count=doc_count,
                skipped_files=skipped,
            )

        except Exception as exc:
            self.logger.error("Fehler beim Sammel-PDF-Export: %s", exc, exc_info=True)
            return CollectionExportResult(
                success=False,
                output_path=str(output_path),
                total_pages=len(output_doc) if output_doc else 0,
                document_count=doc_count,
                skipped_files=skipped,
                error=str(exc),
            )

        finally:
            if output_doc:
                output_doc.close()
            # Temporäre Konvertierungsdateien bereinigen
            for tf in temp_files:
                try:
                    if tf.exists():
                        tf.unlink()
                except OSError:
                    pass

    def _insert_pdf(self, output_doc, path: Path) -> int:
        """Fügt ein PDF-Dokument ein."""
        src_doc = None
        try:
            src_doc = fitz.open(str(path))
            if src_doc.is_encrypted:
                if not src_doc.authenticate(""):
                    self.logger.warning("Verschlüsseltes PDF ohne Passwort übersprungen: %s", path)
                    return 0

            page_count = len(src_doc)
            if page_count > 0:
                output_doc.insert_pdf(src_doc)
            return page_count
        except Exception as exc:
            self.logger.error("Fehler beim Einfügen von PDF %s: %s", path, exc)
            return 0
        finally:
            if src_doc:
                src_doc.close()

    def _insert_image(self, output_doc, path: Path, opts: CollectionExportOptions) -> int:
        """Bettet ein Bild auf einer standardisierten Seite ein."""
        try:
            w = opts.page_width
            h = opts.page_height
            margin = opts.margin

            # Optional: Bild-Dimensionen ermitteln, um Hoch- vs. Querformat zu bestimmen
            if PIL_AVAILABLE:
                try:
                    with Image.open(str(path)) as img:
                        img_w, img_h = img.size
                        if img_w > img_h and w < h:
                            # Bild ist im Querformat -> Seite ins Querformat drehen
                            w, h = h, w
                except Exception:
                    pass

            page = output_doc.new_page(width=w, height=h)
            rect = fitz.Rect(margin, margin, w - margin, h - margin)
            page.insert_image(rect, filename=str(path), keep_proportion=True)
            return 1
        except Exception as exc:
            self.logger.error("Fehler beim Einbetten des Bildes %s: %s", path, exc)
            return 0

    def _insert_text(self, output_doc, path: Path, opts: CollectionExportOptions) -> int:
        """Bettet Text- oder Markdown-Inhalte formatiert auf PDF-Seiten ein."""
        try:
            raw_data = path.read_bytes()
            try:
                text = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_data.decode("latin-1", errors="replace")

            if not text.strip():
                # Leere Textdatei als leere Seite mit Titel einfügen
                page = output_doc.new_page(width=opts.page_width, height=opts.page_height)
                header_rect = fitz.Rect(
                    opts.margin,
                    opts.margin,
                    opts.page_width - opts.margin,
                    opts.margin + 24,
                )
                page.insert_textbox(
                    header_rect,
                    path.name,
                    fontsize=12,
                    fontname="helv",
                    color=(0.2, 0.2, 0.4),
                )
                return 1

            lines = text.splitlines()
            w = opts.page_width
            h = opts.page_height
            margin = opts.margin
            line_height = 14.0
            usable_height = h - (2 * margin) - 30.0
            lines_per_page = max(10, int(usable_height / line_height))

            pages_created = 0
            idx = 0
            total_lines = len(lines)

            while idx < total_lines:
                page = output_doc.new_page(width=w, height=h)
                pages_created += 1

                # Dokumenten-Kopfzeile
                header_text = f"{path.name} (Abschnitt {pages_created})" if pages_created > 1 else path.name
                header_rect = fitz.Rect(margin, margin, w - margin, margin + 20)
                page.insert_textbox(
                    header_rect,
                    header_text,
                    fontsize=11,
                    fontname="helv",
                    color=(0.3, 0.3, 0.5),
                )

                # Trennlinie unter Header
                shape = page.new_shape()
                shape.draw_line(
                    fitz.Point(margin, margin + 22),
                    fitz.Point(w - margin, margin + 22),
                )
                shape.finish(color=(0.7, 0.7, 0.7), width=0.5)
                shape.commit()

                # Textblock einfügen
                chunk = lines[idx:idx + lines_per_page]
                chunk_text = "\n".join(chunk)
                body_rect = fitz.Rect(margin, margin + 28, w - margin, h - margin)
                page.insert_textbox(
                    body_rect,
                    chunk_text,
                    fontsize=9.5,
                    fontname="couri" if path.suffix.lower() in {".log", ".json", ".xml"} else "helv",
                    color=(0.1, 0.1, 0.1),
                )

                idx += lines_per_page

            return pages_created

        except Exception as exc:
            self.logger.error("Fehler beim Konvertieren der Textdatei %s: %s", path, exc)
            return 0

    def _insert_docx(self, output_doc, path: Path, temp_files: List[Path]) -> int:
        """Konvertiert DOCX zu einer temporären PDF und fügt sie ein."""
        try:
            from core.converter.formats import FormatConverter, OutputFormat
            converter = FormatConverter()
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                temp_pdf = Path(tmp.name)
            temp_files.append(temp_pdf)

            res = converter.convert(str(path), str(temp_pdf), OutputFormat.PDF)
            if res.success and temp_pdf.exists():
                return self._insert_pdf(output_doc, temp_pdf)
            else:
                self.logger.warning("DOCX-Konvertierung fehlgeschlagen: %s (%s)", path, res.error)
                return 0
        except Exception as exc:
            self.logger.warning("DOCX-Import nicht verfügbar oder fehlgeschlagen: %s", exc)
            return 0


def export_collection_pdf(
    documents: Sequence[Union[str, Path]],
    output_path: Union[str, Path],
    options: Optional[CollectionExportOptions] = None,
) -> CollectionExportResult:
    """
    Bequemlichkeitsfunktion zum Exportieren einer Dokumentenliste als Sammel-PDF.
    """
    exporter = CollectionExporter()
    return exporter.export(documents, output_path, options=options)
