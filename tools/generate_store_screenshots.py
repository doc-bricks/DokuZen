"""Generate official 1920x1080 Windows Store screenshots for DokuZen.

Produces four screenshots from the real application widgets:
- 01_bibliothek.png: Main library view with categories and document catalog
- 02_ocr.png: OCR optical character recognition dialog and settings
- 03_schwaerzung.png: Redaction and PII detection tool with pattern rules
- 04_konvertierung.png: Multi-format document converter (PDF, DOCX, TXT, PNG)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
if os.name == "nt":
    windows_font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    if windows_font_dir.is_dir():
        os.environ.setdefault("QT_QPA_FONTDIR", str(windows_font_dir))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontInfo, QPainter, QPixmap, QLinearGradient, QBrush, QPen
from PySide6.QtWidgets import QApplication, QWidget, QDialog

from core.library.persistence import PersistenceManager
from gui.main_window import MainWindow
from gui.dialogs.ocr_dialog import OCRDialog
from gui.dialogs.redaction_dialog import RedactionDialog
from gui.dialogs.convert_dialog import ConvertDialog

OUTPUT_DIR = PROJECT_ROOT / "screenshots" / "store"


def _configure_windows_store_font(app: QApplication) -> None:
    """Load and require Segoe UI so headless captures never contain tofu glyphs."""
    if os.name != "nt":
        raise RuntimeError("Windows Store screenshots must be generated on Windows.")

    font_dir = Path(os.environ.get("QT_QPA_FONTDIR", ""))
    font_files = ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf")
    loaded = []
    for font_name in font_files:
        font_path = font_dir / font_name
        if font_path.is_file():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id >= 0:
                loaded.extend(QFontDatabase.applicationFontFamilies(font_id))

    if not any(family.casefold() == "segoe ui" for family in loaded):
        raise RuntimeError(f"Segoe UI could not be loaded from {font_dir}")

    app.setFont(QFont("Segoe UI", 10))
    if QFontInfo(app.font()).family().casefold() != "segoe ui":
        raise RuntimeError("Qt did not resolve the required Segoe UI font.")


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
    painter.drawText(60, 60, f"DokuZen  •  {title_hint}")

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
    _configure_windows_store_font(app)

    for obsolete_name in (
        "02_pdf_vorschau.png",
        "03_ocr_dialog.png",
        "04_schwaerzung.png",
        "05_konvertierung.png",
        "06_batch_verarbeitung.png",
    ):
        (OUTPUT_DIR / obsolete_name).unlink(missing_ok=True)

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
            # Screenshot 2: 02_ocr.png (OCR Dialog)
            # -------------------------------------------------------------
            print("Generating 02_ocr.png...")
            dlg_ocr = OCRDialog()
            dlg_ocr.resize(880, 680)
            if hasattr(dlg_ocr, "_file_path"):
                dlg_ocr._file_path.setText(str(pdf1))
            dlg_ocr.show()
            app.processEvents()

            dlg_pm3 = dlg_ocr.grab()
            canvas3 = _compose_on_backdrop(dlg_pm3, "OCR-Texterkennung & Durchsuchbare PDFs")
            canvas3.save(str(OUTPUT_DIR / "02_ocr.png"), "PNG")
            dlg_ocr.close()

            # -------------------------------------------------------------
            # Screenshot 3: 03_schwaerzung.png (Redaction Dialog)
            # -------------------------------------------------------------
            print("Generating 03_schwaerzung.png...")
            dlg_redact = RedactionDialog()
            dlg_redact.resize(920, 720)
            if hasattr(dlg_redact, "_file_path"):
                dlg_redact._file_path.setText(str(pdf1))
            dlg_redact.show()
            app.processEvents()

            dlg_pm4 = dlg_redact.grab()
            canvas4 = _compose_on_backdrop(dlg_pm4, "DSGVO-konforme Schwärzung & PII-Erkennung")
            canvas4.save(str(OUTPUT_DIR / "03_schwaerzung.png"), "PNG")
            dlg_redact.close()

            # -------------------------------------------------------------
            # Screenshot 4: 04_konvertierung.png (Convert Dialog)
            # -------------------------------------------------------------
            print("Generating 04_konvertierung.png...")
            dlg_conv = ConvertDialog()
            dlg_conv.resize(860, 640)
            if hasattr(dlg_conv, "_input_path"):
                dlg_conv._input_path.setText(str(pdf1))
            dlg_conv.show()
            app.processEvents()

            dlg_pm5 = dlg_conv.grab()
            canvas5 = _compose_on_backdrop(dlg_pm5, "Dokumenten-Konvertierung (PDF, DOCX, TXT, Bilder)")
            canvas5.save(str(OUTPUT_DIR / "04_konvertierung.png"), "PNG")
            dlg_conv.close()

            print(f"All 4 store screenshots generated successfully in {OUTPUT_DIR}.")

        finally:
            PersistenceManager.DEFAULT_STATE_FILE = orig_state


if __name__ == "__main__":
    generate_all_screenshots()
