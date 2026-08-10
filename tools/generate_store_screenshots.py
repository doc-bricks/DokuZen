#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the Windows Store screenshot set from the real DokuZen UI.

The generator deliberately uses a temporary state directory and synthetic
documents.  No user data, home-state file, network access, or release output
is touched.  The dialogs are populated with demo values only so the resulting
images are suitable for a Store listing without making a functional OCR or
conversion claim.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

import fitz  # PyMuPDF, already required by DokuZen
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QTableWidgetItem

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "screenshots" / "store"
CANVAS_SIZE = (1920, 1080)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def make_demo_pdf(path: Path, title: str, subtitle: str) -> None:
    """Write one clearly synthetic, PII-free PDF for the preview widgets."""

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(42, 42, 553, 126), color=(0.12, 0.28, 0.48), fill=(0.12, 0.28, 0.48))
    page.insert_text((66, 82), "DokuZen Pro", fontsize=22, color=(1, 1, 1), fontname="helv")
    page.insert_text((66, 108), title, fontsize=12, color=(0.86, 0.93, 1), fontname="helv")
    page.insert_text((50, 170), subtitle, fontsize=16, color=(0.10, 0.14, 0.20), fontname="helv")
    page.draw_line((50, 190), (545, 190), color=(0.35, 0.47, 0.60), width=1.2)
    lines = [
        "Dies ist ein synthetisches Musterdokument für die Store-Vorschau.",
        "Es enthält keine echten personenbezogenen Daten.",
        "Abschnitt 1    Lokale Dokumentenablage",
        "Abschnitt 2    PDF-Vorschau und Bearbeitung",
        "Abschnitt 3    Export und Stapelverarbeitung",
    ]
    y = 240
    for line in lines:
        page.insert_text((60, y), line, fontsize=12, color=(0.15, 0.18, 0.22), fontname="helv")
        y += 34
    page.draw_rect(fitz.Rect(50, 455, 545, 585), color=(0.79, 0.84, 0.90), fill=(0.95, 0.97, 0.99), width=1)
    page.insert_text((70, 490), "Beispielstatus", fontsize=11, color=(0.25, 0.35, 0.48), fontname="helv")
    page.insert_text((70, 523), "Bereit für lokale Bearbeitung", fontsize=14, color=(0.08, 0.38, 0.26), fontname="helv")
    page.insert_text((70, 555), "Demo-Daten · keine Netzwerkübertragung", fontsize=10, color=(0.35, 0.39, 0.44), fontname="helv")
    page.insert_text((50, 790), "DokuZen Pro · Beispieldaten · 10.08.2026", fontsize=9, color=(0.40, 0.44, 0.50), fontname="helv")
    document.save(str(path))
    document.close()


def process_events(app: QApplication) -> None:
    app.processEvents()
    app.processEvents()


def save_widget(widget, path: Path, title: str | None = None) -> None:
    """Save a widget as a crisp 1920x1080 Store image."""

    widget.show()
    QApplication.instance().processEvents()
    source = widget.grab()
    canvas = QPixmap(*CANVAS_SIZE)
    canvas.fill(QColor("#e9edf2"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # A small neutral window chrome makes dialog-only captures read as app UI.
    painter.fillRect(0, 0, CANVAS_SIZE[0], 52, QColor("#17324d"))
    if title:
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        painter.drawText(28, 33, f"DokuZen Pro  ·  {title}")
    max_width, max_height = 1780, 960
    scale = min(max_width / source.width(), max_height / source.height(), 1.0)
    target_width = int(source.width() * scale)
    target_height = int(source.height() * scale)
    target = QRectF(
        (CANVAS_SIZE[0] - target_width) / 2,
        78 + (max_height - target_height) / 2,
        target_width,
        target_height,
    )
    painter.setPen(QPen(QColor("#bec8d3"), 2))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(target.adjusted(-4, -4, 4, 4), 6, 6)
    painter.drawPixmap(target.toRect(), source)
    painter.end()
    if not canvas.save(str(path), "PNG"):
        raise RuntimeError(f"Konnte Screenshot nicht speichern: {path}")


def select_doc(window, row: int) -> None:
    table = window._document_panel._table
    table.selectRow(row)
    process_events(QApplication.instance())


def create_screenshots() -> list[Path]:
    from core.library.persistence import PersistenceManager
    from gui.dialogs.convert_dialog import ConvertDialog
    from gui.dialogs.ocr_dialog import OCRDialog
    from gui.dialogs.redaction_dialog import RedactionDialog
    from gui.main_window import MainWindow

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("DokuZen Pro")
    app.setApplicationVersion("1.0.0")

    paths: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="dokuzen-store-demo-") as temp_name:
        temp_dir = Path(temp_name)
        state_path = temp_dir / "state.json"
        original_state_file = PersistenceManager.DEFAULT_STATE_FILE
        PersistenceManager.DEFAULT_STATE_FILE = state_path
        try:
            pdf = temp_dir / "Beispielbericht.pdf"
            make_demo_pdf(pdf, "Beispielbericht", "Lokaler Dokumentenbericht")
            overview = temp_dir / "Projektuebersicht.pdf"
            make_demo_pdf(overview, "Projektübersicht", "Planung und Dokumentation")
            contract = temp_dir / "Mustervertrag.pdf"
            make_demo_pdf(contract, "Mustervertrag", "Synthetische Vertragsvorlage")
            note = temp_dir / "Sitzungsnotizen.txt"
            note.write_text("Beispielnotiz – keine personenbezogenen Daten.\n", encoding="utf-8")

            window = MainWindow()
            window.resize(*CANVAS_SIZE)
            window._library.add_documents([str(pdf), str(overview), str(contract), str(note)])
            window._document_panel.refresh()
            window._library_panel.refresh()
            window._update_statusbar()
            process_events(app)

            # 01 — actual DokuZen three-panel library with demo documents.
            window._preview_panel.clear()
            process_events(app)
            out = OUTPUT_DIR / "01_bibliothek.png"
            save_widget(window, out, "Bibliothek")
            paths.append(out)

            # 02 — actual PDF preview panel with the synthetic PDF.
            select_doc(window, 0)
            out = OUTPUT_DIR / "02_pdf_vorschau.png"
            save_widget(window, out, "PDF-Vorschau")
            paths.append(out)
            window.close()
            process_events(app)

            # 03 — actual OCR dialog.  The status makes the unavailable OCR
            # dependency explicit; the displayed text is static demo output.
            ocr = OCRDialog(initial_file=str(pdf))
            ocr.resize(1500, 840)
            ocr._input_path.setText("Beispielbericht.pdf")
            ocr._progress.setVisible(True)
            ocr._progress.setRange(0, 100)
            ocr._progress.setValue(100)
            ocr._status.setText("Demo-Vorschau · Tesseract für echte OCR erforderlich")
            ocr._result_text.setPlainText(
                "=== Seite 1 (Demo) ===\n\n"
                "DokuZen Pro – Lokaler Dokumentenbericht\n"
                "Beispieltext für die Store-Vorschau."
            )
            process_events(app)
            out = OUTPUT_DIR / "03_ocr_dialog.png"
            save_widget(ocr, out, "OCR-Texterkennung")
            paths.append(out)
            ocr.close()

            # 04 — actual redaction dialog with harmless, synthetic findings.
            redaction = RedactionDialog(initial_file=str(pdf))
            redaction.resize(1500, 840)
            redaction._input_path.setText("Beispielbericht.pdf")
            redaction._result_table.setRowCount(2)
            demo_rows = [("MUSTER-ID-001", "Blacklist", "98%"), ("BEISPIELWERT", "Blacklist", "96%")]
            for row, (value, kind, confidence) in enumerate(demo_rows):
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox.setCheckState(Qt.CheckState.Checked)
                redaction._result_table.setItem(row, 0, checkbox)
                redaction._result_table.setItem(row, 1, QTableWidgetItem("1"))
                redaction._result_table.setItem(row, 2, QTableWidgetItem(kind))
                redaction._result_table.setItem(row, 3, QTableWidgetItem(value))
                redaction._result_table.setItem(row, 4, QTableWidgetItem(confidence))
            redaction._status.setText("2 Demo-Treffer ausgewählt · Original bleibt unverändert")
            redaction._btn_redact.setEnabled(True)
            process_events(app)
            out = OUTPUT_DIR / "04_schwaerzung.png"
            save_widget(redaction, out, "PDF schwärzen")
            paths.append(out)
            redaction.close()

            # 05 — actual single-file conversion dialog with demo paths.
            convert = ConvertDialog(initial_files=[str(pdf)])
            convert.resize(1500, 840)
            convert._single_input.setText("Beispielbericht.pdf")
            convert._single_output.setText("Beispielbericht.docx")
            for index in range(convert._format_combo.count()):
                if convert._format_combo.itemText(index).startswith("DOCX"):
                    convert._format_combo.setCurrentIndex(index)
                    break
            convert._status.setText("Bereit · Demo-Ausgabe, noch nicht ausgeführt")
            process_events(app)
            out = OUTPUT_DIR / "05_konvertierung.png"
            save_widget(convert, out, "Format-Konvertierung")
            paths.append(out)
            convert.close()

            # 06 — actual batch mode with three synthetic files and a finished
            # progress bar.  No conversion is invoked by this generator.
            batch = ConvertDialog(initial_files=[str(pdf), str(overview), str(contract)])
            batch.resize(1500, 840)
            batch._radio_batch.setChecked(True)
            batch._on_mode_changed()
            batch._batch_output.setText("Beispielausgabe/")
            for index in range(batch._format_combo.count()):
                if batch._format_combo.itemText(index).startswith("DOCX"):
                    batch._format_combo.setCurrentIndex(index)
                    break
            batch._progress.setVisible(True)
            batch._progress.setRange(0, 3)
            batch._progress.setValue(3)
            batch._status.setText("Demo-Vorschau · 3 Dateien bereit")
            process_events(app)
            out = OUTPUT_DIR / "06_batch_verarbeitung.png"
            save_widget(batch, out, "Stapelverarbeitung")
            paths.append(out)
            batch.close()
            process_events(app)
        finally:
            PersistenceManager.DEFAULT_STATE_FILE = original_state_file
    return paths


if __name__ == "__main__":
    created = create_screenshots()
    for path in created:
        print(path)
