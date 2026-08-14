"""Generate official 1920x1080 Windows Store screenshots for DokuZen.

Produces:
- 01_bibliothek.png: Main library view with categories and document catalog
- 02_pdf_vorschau.png: PDF preview reader with sidebar and zoom controls
- 03_ocr_dialog.png: OCR optical character recognition dialog and settings
- 04_schwaerzung.png: Redaction and PII detection tool with pattern rules
- 05_konvertierung.png: Multi-format document converter (PDF, DOCX, TXT, PNG)
- 06_batch_verarbeitung.png: PDF Marker and multi-page workshop layout
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QLinearGradient, QBrush, QPen
from PySide6.QtWidgets import QApplication, QWidget, QDialog

from core.library.persistence import PersistenceManager
from gui.main_window import MainWindow
from gui.dialogs.ocr_dialog import OCRDialog
from gui.dialogs.redaction_dialog import RedactionDialog
from gui.dialogs.convert_dialog import ConvertDialog
from gui.dialogs.pdf_marker_dialog import PDFMarkerDialog

OUTPUT_DIR = PROJECT_ROOT / "screenshots" / "store"


def _create_sample_pdf(path: Path, title: str, paragraphs: list[str]) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Header / Accent bar
    rect_bar = fitz.Rect(50, 40, 545, 45)
    page.draw_rect(rect_bar, color=(0.17, 0.83, 0.75), fill=(0.17, 0.83, 0.75))

    # Title
    page.insert_text((50, 75), title, fontsize=20, fontname="helv", color=(0.1, 0.2, 0.25))

    y = 110
    for p in paragraphs:
        rect = fitz.Rect(50, y, 545, y + 100)
        page.insert_textbox(rect, p, fontsize=11, fontname="helv", color=(0.2, 0.25, 0.3))
        y += 75

    doc.save(str(path))
    doc.close()


def _compose_on_backdrop(dialog_pixmap: QPixmap, title_hint: str) -> QPixmap:
    """Composes a dialog window onto a modern 1920x1080 desktop canvas."""
    canvas = QPixmap(1920, 1080)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background gradient matching DokuZen theme
    grad = QLinearGradient(0, 0, 1920, 1080)
    grad.setColorAt(0.0, QColor(8, 20, 24))
    grad.setColorAt(0.5, QColor(14, 38, 44))
    grad.setColorAt(1.0, QColor(5, 14, 17))
    painter.fillRect(0, 0, 1920, 1080, grad)

    # Subtle header watermark
    painter.setPen(QColor(45, 212, 191, 40))
    painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    painter.drawText(60, 60, f"DokuZen Pro  •  {title_hint}")

    # Center dialog with soft shadow
    dw = dialog_pixmap.width()
    dh = dialog_pixmap.height()
    x = (1920 - dw) // 2
    y = (1080 - dh) // 2

    # Drop shadow
    painter.setBrush(QColor(0, 0, 0, 120))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(x - 12, y - 8, dw + 24, dh + 24, 12, 12)

    # Draw dialog
    painter.drawPixmap(x, y, dialog_pixmap)
    painter.end()

    return canvas


def generate_all_screenshots():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_file = tmp_path / "state.json"
        orig_state = PersistenceManager.DEFAULT_STATE_FILE
        PersistenceManager.DEFAULT_STATE_FILE = state_file

        try:
            # Prepare sample documents
            pdf1 = tmp_path / "Vertrag_Dienstleistung_2026.pdf"
            _create_sample_pdf(
                pdf1,
                "Dienstleistungsvereinbarung 2026",
                [
                    "Gegenstand des Vertrages ist die Bereitstellung von Software- und Dokumentenservices.",
                    "Alle Daten verbleiben vollständig auf der lokalen Arbeitsstation des Nutzers (100% Offline).",
                    "IBAN für Abrechnungen: DE89 3704 0044 0532 0130 00 (Musterangabe zur Schwärzungsprüfung).",
                    "Ansprechpartner: max.mustermann@beispiel-gmbh.de | Tel: +49 89 12345678",
                ],
            )

            pdf2 = tmp_path / "Jahresbericht_Finanzen_Q2.pdf"
            _create_sample_pdf(
                pdf2,
                "Finanzbericht Quartal 2",
                [
                    "Gesamtübersicht der operativen Betriebsausgaben und Erlöskorridore.",
                    "Die OCR-Texterkennung für alle gescannten Belege wurde lokal abgeschlossen.",
                ],
            )

            md1 = tmp_path / "Notizen_Dokumentenstruktur.md"
            md1.write_text(
                "# Notizen zur Dokumentenstruktur\n\n- [x] Lokale PDF-Bearbeitung\n- [x] OCR-Sprachmodelle deu+eng\n- [x] PII-Schwärzung mit Regex\n",
                encoding="utf-8",
            )

            # -------------------------------------------------------------
            # Screenshot 1: 01_bibliothek.png (1920x1080 MainWindow Library)
            # -------------------------------------------------------------
            print("Generating 01_bibliothek.png...")
            win1 = MainWindow()
            win1.resize(1920, 1080)
            win1.startup_import_paths((str(pdf1), str(pdf2), str(md1)))
            win1.show()
            app.processEvents()

            pm1 = win1.grab()
            pm1.save(str(OUTPUT_DIR / "01_bibliothek.png"), "PNG")
            win1.close()

            # -------------------------------------------------------------
            # Screenshot 2: 02_pdf_vorschau.png (1920x1080 MainWindow PDF Preview)
            # -------------------------------------------------------------
            print("Generating 02_pdf_vorschau.png...")
            win2 = MainWindow()
            win2.resize(1920, 1080)
            win2.startup_import_paths((str(pdf1), str(pdf2), str(md1)))
            win2.startup_open_path(str(pdf1))
            win2.show()
            app.processEvents()

            pm2 = win2.grab()
            pm2.save(str(OUTPUT_DIR / "02_pdf_vorschau.png"), "PNG")
            win2.close()

            # -------------------------------------------------------------
            # Screenshot 3: 03_ocr_dialog.png (OCR Dialog)
            # -------------------------------------------------------------
            print("Generating 03_ocr_dialog.png...")
            dlg_ocr = OCRDialog()
            dlg_ocr.resize(880, 680)
            if hasattr(dlg_ocr, "_file_path"):
                dlg_ocr._file_path.setText(str(pdf1))
            dlg_ocr.show()
            app.processEvents()

            dlg_pm3 = dlg_ocr.grab()
            canvas3 = _compose_on_backdrop(dlg_pm3, "OCR-Texterkennung & Durchsuchbare PDFs")
            canvas3.save(str(OUTPUT_DIR / "03_ocr_dialog.png"), "PNG")
            dlg_ocr.close()

            # -------------------------------------------------------------
            # Screenshot 4: 04_schwaerzung.png (Redaction Dialog)
            # -------------------------------------------------------------
            print("Generating 04_schwaerzung.png...")
            dlg_redact = RedactionDialog()
            dlg_redact.resize(920, 720)
            if hasattr(dlg_redact, "_file_path"):
                dlg_redact._file_path.setText(str(pdf1))
            dlg_redact.show()
            app.processEvents()

            dlg_pm4 = dlg_redact.grab()
            canvas4 = _compose_on_backdrop(dlg_pm4, "DSGVO-konforme Schwärzung & PII-Erkennung")
            canvas4.save(str(OUTPUT_DIR / "04_schwaerzung.png"), "PNG")
            dlg_redact.close()

            # -------------------------------------------------------------
            # Screenshot 5: 05_konvertierung.png (Convert Dialog)
            # -------------------------------------------------------------
            print("Generating 05_konvertierung.png...")
            dlg_conv = ConvertDialog()
            dlg_conv.resize(860, 640)
            if hasattr(dlg_conv, "_input_path"):
                dlg_conv._input_path.setText(str(pdf1))
            dlg_conv.show()
            app.processEvents()

            dlg_pm5 = dlg_conv.grab()
            canvas5 = _compose_on_backdrop(dlg_pm5, "Dokumenten-Konvertierung (PDF, DOCX, TXT, Bilder)")
            canvas5.save(str(OUTPUT_DIR / "05_konvertierung.png"), "PNG")
            dlg_conv.close()

            # -------------------------------------------------------------
            # Screenshot 6: 06_batch_verarbeitung.png (PDF Marker / Workshop)
            # -------------------------------------------------------------
            print("Generating 06_batch_verarbeitung.png...")
            dlg_marker = PDFMarkerDialog()
            dlg_marker.resize(1100, 780)
            dlg_marker.show()
            app.processEvents()

            dlg_pm6 = dlg_marker.grab()
            canvas6 = _compose_on_backdrop(dlg_pm6, "PDF-Werkstatt, Seiten-Auszug & Stapelverarbeitung")
            canvas6.save(str(OUTPUT_DIR / "06_batch_verarbeitung.png"), "PNG")
            dlg_marker.close()

            print(f"All 6 store screenshots generated successfully in {OUTPUT_DIR}.")

        finally:
            PersistenceManager.DEFAULT_STATE_FILE = orig_state


if __name__ == "__main__":
    generate_all_screenshots()
