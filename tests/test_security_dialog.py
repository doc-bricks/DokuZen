#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für den SecurityDialog (DokuZen TW-DZ-17).
================================================
Validiert:
1. Instanziierung, Fenstertitel und WCAG 2.1 AA Barrierefreiheit (AccessibleName, AccessibleDescription, ToolTips).
2. Umschaltung des Speichermodus (In-Place vs. Neue Datei).
3. Tab-Umschaltung und dynamische Button-Beschriftung ("Sicherheit anwenden" vs. "Entsperren").
4. Berechtigungs-Helfer (Alle auswählen, Standardrechte, Alle sperren).
5. Passwort-Sichtbarkeits-Umschaltung (EchoMode).
6. Automatische PDF-Inspektion und Status-Banner-Aktualisierung.
7. Eingabevalidierung (leere Passwörter, Passwort-Fehlabgleich).
8. End-to-End Anwenden von Verschlüsselung und Entsperrung über den Dialog.
"""

import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

import fitz
from gui.dialogs.security_dialog import SecurityDialog
from core.pdf.security import PDFSecurity, is_pdf_locked


class TestSecurityDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.dialog = SecurityDialog()

    def tearDown(self):
        self.dialog.close()
        self.temp_dir.cleanup()

    def _create_sample_pdf(self, filename: str = "dialog_sample.pdf") -> Path:
        pdf_path = self.work_dir / filename
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "DokuZen Security Dialog Test")
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_dialog_accessibility_and_properties(self):
        """Prüft Fenstertitel, Barrierefreiheit und Tooltips der Basiselemente."""
        self.assertEqual(self.dialog.windowTitle(), "PDF-Sicherheit verwalten")
        self.assertEqual(self.dialog.accessibleName(), "PDF-Sicherheit verwalten")
        self.assertIn("Verschlüsseln", self.dialog.accessibleDescription())

        # In-Place Radio Button
        self.assertTrue(self.dialog._radio_inplace.isChecked())
        self.assertEqual(self.dialog._radio_inplace.accessibleName(), "In-Place speichern")
        self.assertFalse(self.dialog._output_pdf.isEnabled())

        # Eingabefeld
        self.assertEqual(self.dialog._input_pdf.accessibleName(), "Eingabe-PDF")
        self.assertTrue(bool(self.dialog._input_pdf.toolTip()))

        # Passwörter
        self.assertEqual(self.dialog._edit_user_pw.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(self.dialog._edit_owner_pw.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(self.dialog._edit_unlock_pw.echoMode(), QLineEdit.EchoMode.Password)

    def test_output_mode_toggle(self):
        """Prüft Aktivierung und Deaktivierung des Ausgabepfad-Feldes."""
        self.dialog._radio_new_file.setChecked(True)
        self.assertTrue(self.dialog._output_pdf.isEnabled())
        self.assertTrue(self.dialog._btn_browse_output.isEnabled())

        self.dialog._radio_inplace.setChecked(True)
        self.assertFalse(self.dialog._output_pdf.isEnabled())
        self.assertFalse(self.dialog._btn_browse_output.isEnabled())

    def test_tab_switching_updates_apply_button_text(self):
        """Prüft, ob der Aktionsbutton seinen Text dynamisch anpasst."""
        self.dialog._tabs.setCurrentIndex(0)
        self.assertEqual(self.dialog._btn_apply.text(), "Sicherheit anwenden")

        self.dialog._tabs.setCurrentIndex(1)
        self.assertEqual(self.dialog._btn_apply.text(), "Entsperren")

    def test_permission_helpers(self):
        """Prüft Schnell-Auswahlmethoden für Berechtigungen."""
        # Alle auswählen
        self.dialog._select_all_permissions()
        self.assertTrue(self.dialog._chk_print.isChecked())
        self.assertTrue(self.dialog._chk_modify.isChecked())
        self.assertTrue(self.dialog._chk_assemble.isChecked())

        # Alle abwählen
        self.dialog._select_no_permissions()
        self.assertFalse(self.dialog._chk_print.isChecked())
        self.assertFalse(self.dialog._chk_copy.isChecked())
        self.assertFalse(self.dialog._chk_modify.isChecked())

        # Standardrechte
        self.dialog._select_default_permissions()
        self.assertTrue(self.dialog._chk_print.isChecked())
        self.assertTrue(self.dialog._chk_copy.isChecked())
        self.assertTrue(self.dialog._chk_annotate.isChecked())
        self.assertTrue(self.dialog._chk_fill_forms.isChecked())
        self.assertTrue(self.dialog._chk_extract.isChecked())
        self.assertFalse(self.dialog._chk_modify.isChecked())
        self.assertFalse(self.dialog._chk_assemble.isChecked())

    def test_toggle_echo_mode(self):
        """Prüft die Passwort-Sichtbarkeits-Umschaltung."""
        self.assertEqual(self.dialog._edit_user_pw.echoMode(), QLineEdit.EchoMode.Password)
        self.dialog._btn_toggle_user_pw.click()
        self.assertEqual(self.dialog._edit_user_pw.echoMode(), QLineEdit.EchoMode.Normal)
        self.dialog._btn_toggle_user_pw.click()
        self.assertEqual(self.dialog._edit_user_pw.echoMode(), QLineEdit.EchoMode.Password)

    def test_inspect_pdf_unencrypted_and_encrypted(self):
        """Prüft Status-Banner-Aktualisierung bei ungeschützten und geschützten PDFs."""
        src = self._create_sample_pdf("inspect_test.pdf")

        # 1. Plain PDF
        self.dialog._input_pdf.setText(str(src))
        self.assertIn("Nicht geschützt", self.dialog._status_banner.text())

        # 2. Encrypted PDF
        sec = PDFSecurity()
        enc = self.work_dir / "inspect_enc.pdf"
        sec.encrypt(src, enc, user_password="pass123")

        dialog_enc = SecurityDialog(pdf_path=str(enc))
        self.assertIn("Passwortgeschützt", dialog_enc._status_banner.text())
        # Sollte automatisch auf Entsperren-Tab (1) gewechselt haben
        self.assertEqual(dialog_enc._tabs.currentIndex(), 1)
        dialog_enc.close()

    def test_apply_validation_empty_passwords(self):
        """Leere Passwörter im Verschlüsseln-Tab lösen eine Warnung aus."""
        src = self._create_sample_pdf("val_empty.pdf")
        self.dialog._input_pdf.setText(str(src))
        self.dialog._tabs.setCurrentIndex(0)
        self.dialog._edit_user_pw.setText("")
        self.dialog._edit_owner_pw.setText("")

        with patch.object(QMessageBox, "warning") as mock_warn:
            self.dialog._apply_action()
            mock_warn.assert_called_once()

    def test_apply_validation_password_mismatch(self):
        """Nicht übereinstimmende Passwörter lösen eine Warnung aus."""
        src = self._create_sample_pdf("val_mismatch.pdf")
        self.dialog._input_pdf.setText(str(src))
        self.dialog._tabs.setCurrentIndex(0)
        self.dialog._edit_user_pw.setText("passA")
        self.dialog._edit_user_pw_confirm.setText("passB")

        with patch.object(QMessageBox, "warning") as mock_warn:
            self.dialog._apply_action()
            mock_warn.assert_called_once()

    def test_apply_encrypt_and_unlock_flow(self):
        """Führt eine vollständige Verschlüsselung und anschließende Entsperrung über den Dialog aus."""
        src = self._create_sample_pdf("full_flow.pdf")
        self.dialog._input_pdf.setText(str(src))
        self.dialog._radio_inplace.setChecked(True)
        self.dialog._tabs.setCurrentIndex(0)
        self.dialog._edit_user_pw.setText("flowPw123")
        self.dialog._edit_user_pw_confirm.setText("flowPw123")

        with patch.object(QMessageBox, "information"):
            with patch.object(self.dialog, "accept") as mock_accept:
                self.dialog._apply_action()
                mock_accept.assert_called_once()

        self.assertTrue(is_pdf_locked(str(src)))

        # Nun Entsperren
        dialog_unlock = SecurityDialog(pdf_path=str(src), default_tab="unlock")
        self.assertEqual(dialog_unlock._tabs.currentIndex(), 1)
        dialog_unlock._edit_unlock_pw.setText("flowPw123")

        with patch.object(QMessageBox, "information"):
            with patch.object(dialog_unlock, "accept") as mock_accept_unlock:
                dialog_unlock._apply_action()
                mock_accept_unlock.assert_called_once()

        self.assertFalse(is_pdf_locked(str(src)))
        dialog_unlock.close()


if __name__ == "__main__":
    unittest.main()
