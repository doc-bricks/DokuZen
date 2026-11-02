#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF-Sicherheits- & Passwort-Dialog
===============================================
Dialog zur Verwaltung von PDF-Verschlüsselung, Berechtigungen und Entsperrung
mit voller WCAG 2.1 AA Barrierefreiheit, In-Place-Schutz und 6-Sprachen-Parität.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.pdf.security import (
    PDFSecurity,
    EncryptionMethod,
    Permission,
    SecurityInfo,
    PYMUPDF_AVAILABLE,
    PIKEPDF_AVAILABLE,
)
from translator import tr
from utils.logger import LoggerMixin


class SecurityDialog(QDialog, LoggerMixin):
    """
    Dialog zum Verschlüsseln, Schützen und Entsperren von PDFs.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        pdf_path: Optional[str] = None,
        default_tab: Optional[int | str] = None,
    ):
        super().__init__(parent)
        self._security = PDFSecurity()
        self._initial_tab = default_tab
        self._setup_ui()

        if pdf_path:
            self._input_pdf.setText(pdf_path)
            self._on_input_pdf_changed(pdf_path)

        if default_tab is not None:
            if isinstance(default_tab, str) and default_tab.lower() in ("unlock", "decrypt", "entsperren"):
                self._tabs.setCurrentIndex(1)
            elif isinstance(default_tab, int) and 0 <= default_tab < self._tabs.count():
                self._tabs.setCurrentIndex(default_tab)

    def _setup_ui(self) -> None:
        """Erstellt alle barrierefreien UI-Elemente und Layouts."""
        self.setWindowTitle(tr("PDF-Sicherheit verwalten"))
        self.setAccessibleName("PDF-Sicherheit verwalten")
        self.setAccessibleDescription(
            "Dialog zum Verschlüsseln, Setzen von Berechtigungen und Entsperren von PDF-Dateien."
        )
        self.setMinimumSize(580, 680)
        self.resize(620, 720)

        main_layout = QVBoxLayout(self)

        # === 1. Dateien-Gruppe ===
        files_group = QGroupBox(tr("Dateien"), self)
        files_form = QFormLayout(files_group)

        # Eingabe-PDF
        input_row = QHBoxLayout()
        self._input_pdf = QLineEdit(self)
        self._input_pdf.setPlaceholderText(tr("PDF auswählen …"))
        self._input_pdf.setAccessibleName("Eingabe-PDF")
        self._input_pdf.setAccessibleDescription("Pfad zur zu sichernden oder zu entsperrenden PDF-Datei.")
        self._input_pdf.setToolTip("Pfad zur zu bearbeitenden PDF-Datei.")
        self._input_pdf.textChanged.connect(self._on_input_pdf_changed)
        input_row.addWidget(self._input_pdf)

        btn_browse_input = QPushButton(tr("Durchsuchen..."), self)
        btn_browse_input.setAccessibleName("Eingabe-PDF durchsuchen")
        btn_browse_input.setAccessibleDescription("Öffnet einen Dateidialog zur Auswahl der Eingabe-PDF.")
        btn_browse_input.setToolTip("PDF-Datei auf der Festplatte auswählen.")
        btn_browse_input.clicked.connect(self._browse_input_pdf)
        input_row.addWidget(btn_browse_input)
        files_form.addRow(tr("Eingabe-PDF:"), input_row)

        # Statusanzeige / Banner
        self._status_banner = QLabel(tr("Status: Nicht geschützt (Vollzugriff)"), self)
        self._status_banner.setAccessibleName("Sicherheitsstatus")
        self._status_banner.setAccessibleDescription("Zeigt den aktuellen Verschlüsselungs- und Sperrstatus der PDF an.")
        self._status_banner.setStyleSheet(
            "QLabel { padding: 6px 10px; border-radius: 4px; font-weight: bold; "
            "background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }"
        )
        files_form.addRow(tr("Sicherheitsstatus:"), self._status_banner)

        # Speichermodus (In-Place vs. Neue Datei)
        mode_row = QHBoxLayout()
        self._radio_inplace = QRadioButton(tr("In-Place speichern (Quelldatei überschreiben)"), self)
        self._radio_inplace.setAccessibleName("In-Place speichern")
        self._radio_inplace.setAccessibleDescription("Wendet Sicherheitseinstellungen direkt auf die Quelldatei an.")
        self._radio_inplace.setToolTip("Überschreibt die Original-PDF sicher über eine temporäre Datei.")
        self._radio_inplace.setChecked(True)
        self._radio_inplace.toggled.connect(self._toggle_output_mode)
        mode_row.addWidget(self._radio_inplace)

        self._radio_new_file = QRadioButton(tr("Neue Datei speichern"), self)
        self._radio_new_file.setAccessibleName("Neue Datei speichern")
        self._radio_new_file.setAccessibleDescription("Erstellt eine neue Datei mit den gewählten Sicherheitseinstellungen.")
        self._radio_new_file.setToolTip("Speichert das Ergebnis in einer neuen PDF-Datei.")
        mode_row.addWidget(self._radio_new_file)
        files_form.addRow(tr("Speichermodus:"), mode_row)

        # Ausgabepfad
        output_row = QHBoxLayout()
        self._output_pdf = QLineEdit(self)
        self._output_pdf.setPlaceholderText(tr("Ausgabepfad wählen …"))
        self._output_pdf.setAccessibleName("Ausgabe-PDF")
        self._output_pdf.setAccessibleDescription("Zielpfad für die neue geschützte oder entsperrte PDF-Datei.")
        self._output_pdf.setToolTip("Dateipfad der neuen PDF-Datei.")
        self._output_pdf.setEnabled(False)
        output_row.addWidget(self._output_pdf)

        self._btn_browse_output = QPushButton(tr("Durchsuchen..."), self)
        self._btn_browse_output.setAccessibleName("Ausgabe-PDF durchsuchen")
        self._btn_browse_output.setAccessibleDescription("Öffnet Dateidialog zum Festlegen des Ausgabepfads.")
        self._btn_browse_output.setToolTip("Speicherort für die neue PDF-Datei wählen.")
        self._btn_browse_output.setEnabled(False)
        self._btn_browse_output.clicked.connect(self._browse_output_pdf)
        output_row.addWidget(self._btn_browse_output)
        files_form.addRow(tr("Ausgabe-PDF:"), output_row)

        main_layout.addWidget(files_group)

        # === 2. Tabs für Modi ===
        self._tabs = QTabWidget(self)
        self._tabs.setAccessibleName("Sicherheitsmodus-Reiter")
        
        # --- Tab 1: Verschlüsseln & Schützen ---
        tab_encrypt = QWidget(self)
        tab_encrypt_layout = QVBoxLayout(tab_encrypt)

        # Passwort-Gruppe
        pw_group = QGroupBox(tr("Passwortschutz"), tab_encrypt)
        pw_form = QFormLayout(pw_group)

        # Benutzer-Passwort
        user_pw_row = QHBoxLayout()
        self._edit_user_pw = QLineEdit(pw_group)
        self._edit_user_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_user_pw.setAccessibleName("Benutzer-Passwort")
        self._edit_user_pw.setAccessibleDescription("Passwort, das beim Öffnen der PDF-Datei eingegeben werden muss.")
        self._edit_user_pw.setToolTip("Passwort zum Öffnen des Dokuments.")
        user_pw_row.addWidget(self._edit_user_pw)

        self._btn_toggle_user_pw = QPushButton("👁", pw_group)
        self._btn_toggle_user_pw.setFixedWidth(36)
        self._btn_toggle_user_pw.setAccessibleName("Passwort anzeigen/verbergen")
        self._btn_toggle_user_pw.setToolTip(tr("Passwort anzeigen/verbergen"))
        self._btn_toggle_user_pw.clicked.connect(lambda: self._toggle_echo_mode(self._edit_user_pw))
        user_pw_row.addWidget(self._btn_toggle_user_pw)
        pw_form.addRow(tr("Benutzer-Passwort (zum Öffnen):"), user_pw_row)

        # Benutzer-Passwort wiederholen
        self._edit_user_pw_confirm = QLineEdit(pw_group)
        self._edit_user_pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_user_pw_confirm.setAccessibleName("Benutzer-Passwort wiederholen")
        self._edit_user_pw_confirm.setAccessibleDescription("Wiederholen Sie das Benutzer-Passwort zur Bestätigung.")
        self._edit_user_pw_confirm.setToolTip("Geben Sie das Benutzer-Passwort zur Überprüfung erneut ein.")
        pw_form.addRow(tr("Passwort wiederholen:"), self._edit_user_pw_confirm)

        # Eigentümer-Passwort
        owner_pw_row = QHBoxLayout()
        self._edit_owner_pw = QLineEdit(pw_group)
        self._edit_owner_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_owner_pw.setAccessibleName("Eigentümer-Passwort")
        self._edit_owner_pw.setAccessibleDescription("Passwort zum Ändern der Berechtigungen oder zum Aufheben des Schutzes.")
        self._edit_owner_pw.setToolTip("Passwort zur Verwaltung von Rechten und Einschränkungen.")
        owner_pw_row.addWidget(self._edit_owner_pw)

        self._btn_toggle_owner_pw = QPushButton("👁", pw_group)
        self._btn_toggle_owner_pw.setFixedWidth(36)
        self._btn_toggle_owner_pw.setAccessibleName("Passwort anzeigen/verbergen")
        self._btn_toggle_owner_pw.setToolTip(tr("Passwort anzeigen/verbergen"))
        self._btn_toggle_owner_pw.clicked.connect(lambda: self._toggle_echo_mode(self._edit_owner_pw))
        owner_pw_row.addWidget(self._btn_toggle_owner_pw)
        pw_form.addRow(tr("Eigentümer-Passwort (für Rechte):"), owner_pw_row)

        # Eigentümer-Passwort wiederholen
        self._edit_owner_pw_confirm = QLineEdit(pw_group)
        self._edit_owner_pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_owner_pw_confirm.setAccessibleName("Eigentümer-Passwort wiederholen")
        self._edit_owner_pw_confirm.setAccessibleDescription("Wiederholen Sie das Eigentümer-Passwort zur Bestätigung.")
        self._edit_owner_pw_confirm.setToolTip("Geben Sie das Eigentümer-Passwort zur Überprüfung erneut ein.")
        pw_form.addRow(tr("Passwort wiederholen:"), self._edit_owner_pw_confirm)

        # Verschlüsselungsmethode
        self._combo_method = QComboBox(pw_group)
        self._combo_method.addItem("AES-256 (Empfohlen / Standard)", "AES-256")
        self._combo_method.addItem("AES-128", "AES-128")
        self._combo_method.addItem("RC4-128 (Legacy)", "RC4-128")
        self._combo_method.setAccessibleName("Verschlüsselungsmethode")
        self._combo_method.setAccessibleDescription("Wählt den Verschlüsselungsalgorithmus und die Schlüssellänge.")
        self._combo_method.setToolTip("Standard ist AES-256 für höchste Sicherheit.")
        pw_form.addRow(tr("Verschlüsselungsmethode:"), self._combo_method)

        tab_encrypt_layout.addWidget(pw_group)

        # Berechtigungen-Gruppe
        self._group_perms = QGroupBox(tr("Erlaubte Aktionen (Berechtigungen)"), tab_encrypt)
        perms_layout = QVBoxLayout(self._group_perms)

        perms_grid = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()

        self._chk_print = QCheckBox(tr("Drucken erlauben"), self._group_perms)
        self._chk_print.setChecked(True)
        self._chk_print.setAccessibleName("Drucken erlauben")
        self._chk_print.setToolTip("Erlaubt das Ausdrucken der PDF-Datei.")
        col1.addWidget(self._chk_print)

        self._chk_print_hq = QCheckBox(tr("In hoher Qualität drucken"), self._group_perms)
        self._chk_print_hq.setChecked(True)
        self._chk_print_hq.setAccessibleName("In hoher Qualität drucken")
        self._chk_print_hq.setToolTip("Erlaubt hochauflösenden Druck.")
        col1.addWidget(self._chk_print_hq)

        self._chk_copy = QCheckBox(tr("Kopieren von Inhalt erlauben"), self._group_perms)
        self._chk_copy.setChecked(True)
        self._chk_copy.setAccessibleName("Kopieren von Inhalt erlauben")
        self._chk_copy.setToolTip("Erlaubt das Kopieren von Text und Grafiken in die Zwischenablage.")
        col1.addWidget(self._chk_copy)

        self._chk_modify = QCheckBox(tr("Dokumentänderung erlauben"), self._group_perms)
        self._chk_modify.setChecked(False)
        self._chk_modify.setAccessibleName("Dokumentänderung erlauben")
        self._chk_modify.setToolTip("Erlaubt das Ändern des Dokuments (Seiten drehen, einfügen, löschen).")
        col1.addWidget(self._chk_modify)

        self._chk_annotate = QCheckBox(tr("Kommentare & Annotationen erlauben"), self._group_perms)
        self._chk_annotate.setChecked(True)
        self._chk_annotate.setAccessibleName("Kommentare & Annotationen erlauben")
        self._chk_annotate.setToolTip("Erlaubt das Hinzufügen von Notizen, Markierungen und Kommentaren.")
        col2.addWidget(self._chk_annotate)

        self._chk_fill_forms = QCheckBox(tr("Formulare ausfüllen erlauben"), self._group_perms)
        self._chk_fill_forms.setChecked(True)
        self._chk_fill_forms.setAccessibleName("Formulare ausfüllen erlauben")
        self._chk_fill_forms.setToolTip("Erlaubt das Ausfüllen vorhandener interaktiver Formularfelder.")
        col2.addWidget(self._chk_fill_forms)

        self._chk_extract = QCheckBox(tr("Barrierefreier Inhaltsextrakt (Screenreader)"), self._group_perms)
        self._chk_extract.setChecked(True)
        self._chk_extract.setAccessibleName("Barrierefreier Inhaltsextrakt")
        self._chk_extract.setToolTip("Erlaubt Bildschirmleseprogrammen den Zugriff auf Dokumentinhalte für Barrierefreiheit.")
        col2.addWidget(self._chk_extract)

        self._chk_assemble = QCheckBox(tr("Seiten zusammenstellen erlauben"), self._group_perms)
        self._chk_assemble.setChecked(False)
        self._chk_assemble.setAccessibleName("Seiten zusammenstellen erlauben")
        self._chk_assemble.setToolTip("Erlaubt das Zusammenfügen und Organisieren von Seiten.")
        col2.addWidget(self._chk_assemble)

        perms_grid.addLayout(col1)
        perms_grid.addLayout(col2)
        perms_layout.addLayout(perms_grid)

        # Schnell-Auswahl Buttons für Berechtigungen
        perms_btn_row = QHBoxLayout()
        btn_all = QPushButton(tr("Alle erlauben"), self._group_perms)
        btn_all.setAccessibleName("Alle Berechtigungen erlauben")
        btn_all.clicked.connect(self._select_all_permissions)
        perms_btn_row.addWidget(btn_all)

        btn_default = QPushButton(tr("Standardrechte"), self._group_perms)
        btn_default.setAccessibleName("Standardberechtigungen setzen")
        btn_default.clicked.connect(self._select_default_permissions)
        perms_btn_row.addWidget(btn_default)

        btn_none = QPushButton(tr("Alle sperren"), self._group_perms)
        btn_none.setAccessibleName("Alle Berechtigungen sperren")
        btn_none.clicked.connect(self._select_no_permissions)
        perms_btn_row.addWidget(btn_none)

        perms_layout.addLayout(perms_btn_row)
        tab_encrypt_layout.addWidget(self._group_perms)

        self._tabs.addTab(tab_encrypt, tr("Verschlüsseln & Schützen"))

        # --- Tab 2: Entsperren / Passwort entfernen ---
        tab_unlock = QWidget(self)
        tab_unlock_layout = QVBoxLayout(tab_unlock)

        unlock_group = QGroupBox(tr("Passwortschutz aufheben"), tab_unlock)
        unlock_form = QFormLayout(unlock_group)

        desc_label = QLabel(
            tr("Entfernt den Passwortschutz oder Berechtigungsbeschränkungen aus der PDF.\n"
               "Die resultierende PDF-Datei ist unverschlüsselt und frei zugänglich."),
            unlock_group
        )
        desc_label.setWordWrap(True)
        unlock_form.addRow(desc_label)

        unlock_pw_row = QHBoxLayout()
        self._edit_unlock_pw = QLineEdit(unlock_group)
        self._edit_unlock_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_unlock_pw.setPlaceholderText(tr("Passwort eingeben …"))
        self._edit_unlock_pw.setAccessibleName("Entsperr-Passwort")
        self._edit_unlock_pw.setAccessibleDescription("Passwort zum Entsperren der geschützten PDF-Datei.")
        self._edit_unlock_pw.setToolTip("Geben Sie das Passwort der geschützten PDF ein.")
        unlock_pw_row.addWidget(self._edit_unlock_pw)

        self._btn_toggle_unlock_pw = QPushButton("👁", unlock_group)
        self._btn_toggle_unlock_pw.setFixedWidth(36)
        self._btn_toggle_unlock_pw.setAccessibleName("Passwort anzeigen/verbergen")
        self._btn_toggle_unlock_pw.setToolTip(tr("Passwort anzeigen/verbergen"))
        self._btn_toggle_unlock_pw.clicked.connect(lambda: self._toggle_echo_mode(self._edit_unlock_pw))
        unlock_pw_row.addWidget(self._btn_toggle_unlock_pw)
        unlock_form.addRow(tr("Passwort:"), unlock_pw_row)

        note_label = QLabel(
            tr("Hinweis: Wenn die PDF nur mit einem Eigentümer-Passwort geschützt ist (Rechtebeschränkung), kann das Feld leer gelassen werden."),
            unlock_group
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #64748b; font-size: 11px;")
        unlock_form.addRow(note_label)

        tab_unlock_layout.addWidget(unlock_group)
        tab_unlock_layout.addStretch()

        self._tabs.addTab(tab_unlock, tr("Entsperren / Passwort entfernen"))

        main_layout.addWidget(self._tabs)

        # === 3. Dialog-Aktionsbuttons ===
        btn_layout = QHBoxLayout()
        self._btn_apply = QPushButton(tr("Sicherheit anwenden"), self)
        self._btn_apply.setDefault(True)
        self._btn_apply.setAccessibleName("Aktion ausführen")
        self._btn_apply.setAccessibleDescription("Führt die Verschlüsselung oder Entsperrung aus.")
        self._btn_apply.clicked.connect(self._apply_action)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        btn_layout.addWidget(self._btn_apply)

        self._btn_close = QPushButton(tr("Schließen"), self)
        self._btn_close.setAccessibleName("Schließen")
        self._btn_close.setAccessibleDescription("Schließt das Dialogfenster.")
        self._btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_close)

        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # UI-Logik & Interaktionen
    # ------------------------------------------------------------------

    def _toggle_output_mode(self, checked: bool) -> None:
        """Aktiviert/Deaktiviert das Ausgabefeld je nach In-Place-Einstellung."""
        is_inplace = self._radio_inplace.isChecked()
        self._output_pdf.setEnabled(not is_inplace)
        self._btn_browse_output.setEnabled(not is_inplace)

    def _toggle_echo_mode(self, line_edit: QLineEdit) -> None:
        """Schaltet zwischen Klartext und Passwort-Sternchen um."""
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def _on_tab_changed(self, index: int) -> None:
        """Passt den Button-Text an den ausgewählten Modus an."""
        if not hasattr(self, "_btn_apply"):
            return
        if index == 0:
            self._btn_apply.setText(tr("Sicherheit anwenden"))
            self._btn_apply.setAccessibleName("Sicherheit anwenden")
        else:
            self._btn_apply.setText(tr("Entsperren"))
            self._btn_apply.setAccessibleName("Entsperren")

    def _select_all_permissions(self) -> None:
        """Aktiviert alle Berechtigungs-Checkboxen."""
        for chk in (
            self._chk_print, self._chk_print_hq, self._chk_copy, self._chk_modify,
            self._chk_annotate, self._chk_fill_forms, self._chk_extract, self._chk_assemble
        ):
            chk.setChecked(True)

    def _select_default_permissions(self) -> None:
        """Setzt die Standardberechtigungen (Drucken, Kopieren, Annotationen, Formulare, Barrierefreiheit)."""
        self._chk_print.setChecked(True)
        self._chk_print_hq.setChecked(True)
        self._chk_copy.setChecked(True)
        self._chk_modify.setChecked(False)
        self._chk_annotate.setChecked(True)
        self._chk_fill_forms.setChecked(True)
        self._chk_extract.setChecked(True)
        self._chk_assemble.setChecked(False)

    def _select_no_permissions(self) -> None:
        """Deaktiviert alle Berechtigungen für maximale Einschränkung."""
        for chk in (
            self._chk_print, self._chk_print_hq, self._chk_copy, self._chk_modify,
            self._chk_annotate, self._chk_fill_forms, self._chk_extract, self._chk_assemble
        ):
            chk.setChecked(False)

    def _on_input_pdf_changed(self, text: str) -> None:
        """Inspiziert die PDF und aktualisiert Pfade und Status."""
        p_str = text.strip()
        if not p_str or not Path(p_str).is_file():
            self._status_banner.setText(tr("Status: Nicht geschützt (Vollzugriff)"))
            self._status_banner.setStyleSheet(
                "QLabel { padding: 6px 10px; border-radius: 4px; font-weight: bold; "
                "background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }"
            )
            return

        p = Path(p_str)
        if self._radio_new_file.isChecked() and not self._output_pdf.text().strip():
            default_out = str(p.with_stem(f"{p.stem}_secured"))
            self._output_pdf.setText(default_out)

        self._inspect_pdf(p_str)

    def _inspect_pdf(self, path: str) -> None:
        """Prüft Sicherheitsinformationen der PDF und aktualisiert das UI."""
        info = self._security.get_security_info(path)
        if not info:
            return

        if info.is_encrypted:
            method_label = info.encryption_method or "AES-256"
            if info.needs_password:
                self._status_banner.setText(
                    f"{tr('Status: Passwortgeschützt / Verschlüsselt')} ({method_label})"
                )
                self._status_banner.setStyleSheet(
                    "QLabel { padding: 6px 10px; border-radius: 4px; font-weight: bold; "
                    "background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }"
                )
            else:
                self._status_banner.setText(
                    f"{tr('Status: Nur Einschränkungen aktiv (Eigentümer-Schutz)')} ({method_label})"
                )
                self._status_banner.setStyleSheet(
                    "QLabel { padding: 6px 10px; border-radius: 4px; font-weight: bold; "
                    "background-color: #fffbeb; color: #92400e; border: 1px solid #fde68a; }"
                )
            # Wenn noch nicht explizit Tab gewählt wurde, auf Entsperren umschalten
            if self._initial_tab is None:
                self._tabs.setCurrentIndex(1)
        else:
            self._status_banner.setText(tr("Status: Nicht geschützt (Vollzugriff)"))
            self._status_banner.setStyleSheet(
                "QLabel { padding: 6px 10px; border-radius: 4px; font-weight: bold; "
                "background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }"
            )

    def _browse_input_pdf(self) -> None:
        """Öffnet Dateidialog für Eingabe-PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("PDF-Dateien"),
            self._input_pdf.text() or "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self._input_pdf.setText(file_path)
            self._on_input_pdf_changed(file_path)

    def _browse_output_pdf(self) -> None:
        """Öffnet Dateidialog für Ausgabe-PDF."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Speichern unter"),
            self._output_pdf.text() or "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self._output_pdf.setText(file_path)

    def _get_active_permissions(self) -> list[str]:
        """Gibt die Liste der ausgewählten Berechtigungs-Strings zurück."""
        perms = []
        if self._chk_print.isChecked():
            perms.append("print")
        if self._chk_print_hq.isChecked():
            perms.append("print_highres")
        if self._chk_copy.isChecked():
            perms.append("copy")
        if self._chk_modify.isChecked():
            perms.append("modify")
        if self._chk_annotate.isChecked():
            perms.append("annotate")
        if self._chk_fill_forms.isChecked():
            perms.append("fill_forms")
        if self._chk_extract.isChecked():
            perms.append("extract")
        if self._chk_assemble.isChecked():
            perms.append("assemble")
        return perms

    def _apply_action(self) -> None:
        """Führt je nach aktivem Tab Verschlüsselung oder Entsperrung aus."""
        src = self._input_pdf.text().strip()
        if not src:
            QMessageBox.warning(self, tr("Hinweis"), tr("Bitte wählen Sie eine Eingabe-PDF aus."))
            return

        if not os.path.exists(src):
            QMessageBox.critical(self, tr("Fehler"), tr("Eingabedatei nicht gefunden."))
            return

        if self._radio_inplace.isChecked():
            dst = src
        else:
            dst = self._output_pdf.text().strip()
            if not dst:
                QMessageBox.warning(self, tr("Hinweis"), tr("Bitte geben Sie einen Ausgabepfad an."))
                return

        current_tab = self._tabs.currentIndex()

        # Modus 1: Verschlüsseln & Schützen
        if current_tab == 0:
            user_pw = self._edit_user_pw.text()
            user_pw_confirm = self._edit_user_pw_confirm.text()
            owner_pw = self._edit_owner_pw.text()
            owner_pw_confirm = self._edit_owner_pw_confirm.text()

            if not user_pw and not owner_pw:
                QMessageBox.warning(
                    self,
                    tr("Hinweis"),
                    tr("Bitte vergeben Sie mindestens ein Benutzer- oder Eigentümer-Passwort.")
                )
                return

            if user_pw and user_pw != user_pw_confirm:
                QMessageBox.warning(
                    self,
                    tr("Hinweis"),
                    tr("Passwörter stimmen nicht überein.") + " (" + tr("Benutzer-Passwort") + ")"
                )
                return

            if owner_pw and owner_pw != owner_pw_confirm:
                QMessageBox.warning(
                    self,
                    tr("Hinweis"),
                    tr("Passwörter stimmen nicht überein.") + " (" + tr("Eigentümer-Passwort") + ")"
                )
                return

            method_str = str(self._combo_method.currentData())
            perms = self._get_active_permissions()

            res = self._security.encrypt(
                input_path=src,
                output_path=dst,
                user_password=user_pw,
                owner_password=owner_pw,
                method=method_str,
                permissions=perms,
            )

            if res.success:
                QMessageBox.information(
                    self,
                    tr("Erfolg"),
                    tr("PDF erfolgreich verschlüsselt.") + (f"\n{dst}" if dst != src else "")
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    tr("Fehler"),
                    res.error or tr("Verschlüsselung fehlgeschlagen.")
                )

        # Modus 2: Entsperren / Passwort entfernen
        else:
            unlock_pw = self._edit_unlock_pw.text()
            res = self._security.unlock(
                input_path=src,
                output_path=dst,
                password=unlock_pw,
            )

            if res.success:
                QMessageBox.information(
                    self,
                    tr("Erfolg"),
                    tr("PDF erfolgreich entsperrt.") + (f"\n{dst}" if dst != src else "")
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    tr("Fehler"),
                    res.error or tr("Konnte PDF nicht entsperren")
                )
