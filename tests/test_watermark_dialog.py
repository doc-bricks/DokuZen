#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für den WatermarkDialog (gui/dialogs/watermark_dialog.py) in DokuZen.

Validiert:
1. Dialog-Instanziierung und Fenstertitel.
2. Preset-Buttons für Schnellauswahl (ENTWURF, VERTRAULICH, etc.).
3. Umschalten zwischen In-Place- und Neuer Datei-Modus.
4. Umschalten zwischen Text- und Bild-Wasserzeichen.
5. Barrierefreiheits-Attribute (accessibleName, accessibleDescription, toolTip).
6. Erfolgreiches Ausführen von _apply_watermark mit Testdatei.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
import fitz

from gui.dialogs.watermark_dialog import WatermarkDialog


@pytest.fixture(scope="module")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def dialog_test_pdf(tmp_path) -> Path:
    """Erstellt ein Test-PDF für Dialog-Tests."""
    pdf_path = tmp_path / "dialog_sample.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_watermark_dialog_init_and_accessibility(qapp):
    """Prüft Initialisierung, Fenstertitel und Accessibility-Attribute."""
    dialog = WatermarkDialog()
    assert dialog.windowTitle() == "PDF-Wasserzeichen verwalten"
    assert dialog.accessibleName() == "PDF-Wasserzeichen verwalten"
    assert "Wasserzeichen" in dialog.accessibleDescription()

    # Bedienelemente prüfen
    assert dialog._radio_text.isChecked() is True
    assert dialog._radio_inplace.isChecked() is True
    assert dialog._edit_text.text() == "ENTWURF"
    assert dialog._slider_opacity.value() == 25
    assert dialog._spin_angle.value() == 45
    assert dialog._btn_apply.accessibleName() == "Wasserzeichen anwenden"

    dialog.close()


def test_watermark_dialog_presets(qapp):
    """Prüft die Preset-Buttons."""
    dialog = WatermarkDialog()
    dialog._set_preset_text("VERTRAULICH")
    assert dialog._edit_text.text() == "VERTRAULICH"

    dialog._set_preset_text("GEHEIM")
    assert dialog._edit_text.text() == "GEHEIM"
    dialog.close()


def test_watermark_dialog_mode_toggles(qapp, tmp_path):
    """Prüft das Umschalten von Modi."""
    dialog = WatermarkDialog()

    # In-Place vs. New File
    dialog._radio_new_file.setChecked(True)
    assert dialog._output_pdf.isEnabled() is True
    assert dialog._btn_browse_output.isEnabled() is True

    dialog._radio_inplace.setChecked(True)
    assert dialog._output_pdf.isEnabled() is False

    # Text vs. Image
    dialog._radio_image.setChecked(True)
    assert dialog._text_group.isHidden() is True
    assert dialog._image_group.isHidden() is False

    dialog._radio_text.setChecked(True)
    assert dialog._text_group.isHidden() is False
    assert dialog._image_group.isHidden() is True

    dialog.close()


def test_watermark_dialog_apply_execution(qapp, dialog_test_pdf):
    """Testet das erfolgreiche Anwenden des Wasserzeichens über den Dialog."""
    dialog = WatermarkDialog(pdf_path=str(dialog_test_pdf))
    dialog._edit_text.setText("DIALOG_APPLIED")

    with patch.object(QMessageBox, "information") as mock_info:
        dialog._apply_watermark()
        mock_info.assert_called_once()

    doc = fitz.open(str(dialog_test_pdf))
    assert "DIALOG_APPLIED" in doc[0].get_text()
    doc.close()
    dialog.close()
