#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PyInstaller Compiler Dialog
===============================================
GUI für PyInstaller-basierte Python-Kompilierung.
"""

from pathlib import Path
from typing import Optional, List, Dict
import subprocess
import sys
import shutil
import shlex

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QGroupBox, QFormLayout, QTextEdit,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QProgressBar, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, QProcess

from utils.logger import LoggerMixin


class CompileWorker(QThread):
    """Worker-Thread für PyInstaller-Kompilierung."""
    
    output = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, command: List[str], work_dir: str):
        super().__init__()
        self.command = command
        self.work_dir = work_dir
        self._cancelled = False
        self._process = None

    def cancel(self):
        # BUGSWEEP-33: erlaubt closeEvent, einen laufenden Build abzubrechen (terminiert den
        # Subprozess -> readline-Loop endet -> Thread kann sauber beendet/abgewartet werden).
        self._cancelled = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()

    def run(self):
        process = None
        try:
            # BUGSWEEP-33: encoding/errors explizit — text=True ohne encoding dekodiert PyInstaller-
            # stdout mit Windows-cp1252 -> UnicodeDecodeError bei Umlauten/UTF-8 -> Build-Abbruch.
            # creationflags=CREATE_NO_WINDOW (nur Windows) verhindert das Konsolenfenster-Popup.
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.work_dir,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
            self._process = process
            for line in iter(process.stdout.readline, ''):
                self.output.emit(line.rstrip())
            process.wait()
            if process.returncode == 0:
                self.finished.emit(True, "Kompilierung erfolgreich!")
            else:
                self.finished.emit(False, f"Fehler (Code {process.returncode})")
        except Exception as e:
            self.finished.emit(False, str(e))
        finally:
            if process is not None:
                if process.stdout:
                    process.stdout.close()
                if process.poll() is None:
                    process.terminate()
                    process.wait()


class PyInstallerDialog(QDialog, LoggerMixin):
    """
    PyInstaller GUI für Python-Kompilierung.
    
    Features:
    - Einzeldatei oder Ordner
    - Icon-Auswahl
    - Versteckte Imports
    - Daten-Dateien
    - Konsole ein/aus
    - UPX-Kompression
    """
    
    def __init__(self, parent=None, script_path: str = None):
        super().__init__(parent)
        
        self._worker: Optional[CompileWorker] = None
        self._pyinstaller_available = self._check_pyinstaller()
        
        self._setup_ui()
        
        if script_path:
            self._script_path.setText(script_path)
            self._update_output_name()

    def closeEvent(self, event):
        # BUGSWEEP-33: laufenden CompileWorker abbrechen + abwarten, sonst wird das QThread-Objekt
        # bei noch laufendem Thread zerstoert -> "QThread: Destroyed while thread is still running" / Crash.
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        super().closeEvent(event)
    
    def _check_pyinstaller(self) -> bool:
        """Prüft ob PyInstaller verfügbar ist."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            return False
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Python Kompilator")
        self.setMinimumSize(700, 600)
        self.resize(800, 700)
        
        layout = QVBoxLayout(self)
        
        # PyInstaller Status
        if not self._pyinstaller_available:
            warning = QLabel(
                "⚠️ PyInstaller nicht gefunden!\n"
                "Installation: pip install pyinstaller"
            )
            warning.setStyleSheet("background: #fff3cd; padding: 10px; border-radius: 5px;")
            layout.addWidget(warning)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        tabs.addTab(self._create_basic_tab(), "Basis")
        tabs.addTab(self._create_advanced_tab(), "Erweitert")
        tabs.addTab(self._create_data_tab(), "Daten & Imports")
        
        # Ausgabe
        output_group = QGroupBox("Ausgabe")
        output_layout = QVBoxLayout(output_group)
        
        self._output_text = QTextEdit()
        self._output_text.setReadOnly(True)
        self._output_text.setFontFamily("Consolas")
        self._output_text.setMaximumHeight(200)
        output_layout.addWidget(self._output_text)
        
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate
        self._progress.setVisible(False)
        output_layout.addWidget(self._progress)
        
        layout.addWidget(output_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_preview = QPushButton("Befehl anzeigen")
        btn_preview.clicked.connect(self._show_command)
        btn_layout.addWidget(btn_preview)
        
        btn_layout.addStretch()
        
        self._btn_compile = QPushButton("Kompilieren")
        self._btn_compile.clicked.connect(self._start_compile)
        self._btn_compile.setEnabled(self._pyinstaller_available)
        btn_layout.addWidget(self._btn_compile)
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _create_basic_tab(self) -> QWidget:
        """Erstellt den Basis-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Script
        script_group = QGroupBox("Python-Script")
        script_layout = QFormLayout(script_group)
        
        script_row = QHBoxLayout()
        self._script_path = QLineEdit()
        self._script_path.setPlaceholderText("Haupt-Script wählen (.py)...")
        self._script_path.textChanged.connect(self._update_output_name)
        script_row.addWidget(self._script_path)
        
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._browse_script)
        script_row.addWidget(btn_browse)
        
        script_layout.addRow("Script:", script_row)
        
        self._output_name = QLineEdit()
        self._output_name.setPlaceholderText("Name der EXE (ohne .exe)")
        script_layout.addRow("Ausgabe:", self._output_name)
        
        layout.addWidget(script_group)
        
        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QVBoxLayout(options_group)
        
        self._onefile = QCheckBox("Einzelne EXE-Datei (--onefile)")
        self._onefile.setChecked(True)
        options_layout.addWidget(self._onefile)
        
        self._noconsole = QCheckBox("Ohne Konsole (--noconsole / --windowed)")
        self._noconsole.setChecked(True)
        options_layout.addWidget(self._noconsole)
        
        self._clean = QCheckBox("Build-Cache leeren (--clean)")
        self._clean.setChecked(True)
        options_layout.addWidget(self._clean)
        
        self._noconfirm = QCheckBox("Ohne Bestätigung überschreiben (--noconfirm)")
        self._noconfirm.setChecked(True)
        options_layout.addWidget(self._noconfirm)
        
        layout.addWidget(options_group)
        
        # Icon
        icon_group = QGroupBox("Icon")
        icon_layout = QHBoxLayout(icon_group)
        
        self._icon_path = QLineEdit()
        self._icon_path.setPlaceholderText("Optional: ICO-Datei für die EXE...")
        icon_layout.addWidget(self._icon_path)
        
        btn_icon = QPushButton("...")
        btn_icon.setFixedWidth(30)
        btn_icon.clicked.connect(self._browse_icon)
        icon_layout.addWidget(btn_icon)
        
        layout.addWidget(icon_group)
        
        # Ausgabe-Ordner
        dist_group = QGroupBox("Ausgabe-Ordner")
        dist_layout = QHBoxLayout(dist_group)
        
        self._dist_path = QLineEdit()
        self._dist_path.setPlaceholderText("Standard: ./dist")
        dist_layout.addWidget(self._dist_path)
        
        btn_dist = QPushButton("...")
        btn_dist.setFixedWidth(30)
        btn_dist.clicked.connect(self._browse_dist)
        dist_layout.addWidget(btn_dist)
        
        layout.addWidget(dist_group)
        
        layout.addStretch()
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Erstellt den Erweitert-Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # UPX
        upx_group = QGroupBox("UPX-Kompression")
        upx_layout = QVBoxLayout(upx_group)
        
        self._use_upx = QCheckBox("UPX verwenden (kleinere EXE)")
        upx_layout.addWidget(self._use_upx)
        
        upx_path_layout = QHBoxLayout()
        upx_path_layout.addWidget(QLabel("UPX-Pfad:"))
        self._upx_path = QLineEdit()
        self._upx_path.setPlaceholderText("Optional: Pfad zu upx.exe")
        upx_path_layout.addWidget(self._upx_path)
        
        btn_upx = QPushButton("...")
        btn_upx.setFixedWidth(30)
        btn_upx.clicked.connect(self._browse_upx)
        upx_path_layout.addWidget(btn_upx)
        
        upx_layout.addLayout(upx_path_layout)
        layout.addWidget(upx_group)
        
        # Debug
        debug_group = QGroupBox("Debug")
        debug_layout = QVBoxLayout(debug_group)
        
        self._debug = QCheckBox("Debug-Modus (--debug all)")
        debug_layout.addWidget(self._debug)
        
        self._log_level = QComboBox()
        self._log_level.addItems(["WARN", "INFO", "DEBUG", "TRACE"])
        
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("Log-Level:"))
        log_layout.addWidget(self._log_level)
        log_layout.addStretch()
        debug_layout.addLayout(log_layout)
        
        layout.addWidget(debug_group)
        
        # Zusätzliche Optionen
        extra_group = QGroupBox("Zusätzliche Optionen")
        extra_layout = QVBoxLayout(extra_group)
        
        self._extra_args = QLineEdit()
        self._extra_args.setPlaceholderText("Weitere PyInstaller-Argumente...")
        extra_layout.addWidget(self._extra_args)
        
        layout.addWidget(extra_group)
        
        layout.addStretch()
        return widget
    
    def _create_data_tab(self) -> QWidget:
        """Erstellt den Daten & Imports Tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Versteckte Imports
        imports_group = QGroupBox("Versteckte Imports (--hidden-import)")
        imports_layout = QVBoxLayout(imports_group)
        
        self._hidden_imports = QListWidget()
        imports_layout.addWidget(self._hidden_imports)
        
        import_buttons = QHBoxLayout()
        
        self._import_input = QLineEdit()
        self._import_input.setPlaceholderText("Modul-Name eingeben...")
        import_buttons.addWidget(self._import_input)
        
        btn_add_import = QPushButton("Hinzufügen")
        btn_add_import.clicked.connect(self._add_hidden_import)
        import_buttons.addWidget(btn_add_import)
        
        btn_remove_import = QPushButton("Entfernen")
        btn_remove_import.clicked.connect(lambda: self._remove_selected(self._hidden_imports))
        import_buttons.addWidget(btn_remove_import)
        
        imports_layout.addLayout(import_buttons)
        
        # Häufige Imports
        common = QHBoxLayout()
        common.addWidget(QLabel("Häufig:"))
        for mod in ["PIL", "PyQt6", "numpy", "pandas", "requests"]:
            btn = QPushButton(mod)
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda checked, m=mod: self._add_import(m))
            common.addWidget(btn)
        common.addStretch()
        imports_layout.addLayout(common)
        
        layout.addWidget(imports_group)
        
        # Daten-Dateien
        data_group = QGroupBox("Daten-Dateien (--add-data)")
        data_layout = QVBoxLayout(data_group)
        
        self._data_files = QListWidget()
        data_layout.addWidget(self._data_files)
        
        data_buttons = QHBoxLayout()
        
        btn_add_file = QPushButton("Datei hinzufügen...")
        btn_add_file.clicked.connect(self._add_data_file)
        data_buttons.addWidget(btn_add_file)
        
        btn_add_folder = QPushButton("Ordner hinzufügen...")
        btn_add_folder.clicked.connect(self._add_data_folder)
        data_buttons.addWidget(btn_add_folder)
        
        btn_remove_data = QPushButton("Entfernen")
        btn_remove_data.clicked.connect(lambda: self._remove_selected(self._data_files))
        data_buttons.addWidget(btn_remove_data)
        
        data_layout.addLayout(data_buttons)
        layout.addWidget(data_group)
        
        return widget
    
    def _browse_script(self):
        """Wählt Python-Script."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Python-Script wählen", "",
            "Python-Dateien (*.py *.pyw)"
        )
        if path:
            self._script_path.setText(path)
    
    def _browse_icon(self):
        """Wählt Icon-Datei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Icon wählen", "",
            "ICO-Dateien (*.ico)"
        )
        if path:
            self._icon_path.setText(path)
    
    def _browse_dist(self):
        """Wählt Ausgabe-Ordner."""
        path = QFileDialog.getExistingDirectory(self, "Ausgabe-Ordner")
        if path:
            self._dist_path.setText(path)
    
    def _browse_upx(self):
        """Wählt UPX-Pfad."""
        path, _ = QFileDialog.getOpenFileName(
            self, "UPX wählen", "",
            "UPX (upx.exe)"
        )
        if path:
            self._upx_path.setText(path)
    
    def _update_output_name(self):
        """Aktualisiert den Ausgabenamen."""
        script = self._script_path.text()
        if script:
            name = Path(script).stem
            self._output_name.setText(name)
    
    def _add_hidden_import(self):
        """Fügt versteckten Import hinzu."""
        module = self._import_input.text().strip()
        if module:
            self._hidden_imports.addItem(module)
            self._import_input.clear()
    
    def _add_import(self, module: str):
        """Fügt Import aus Button hinzu."""
        # Prüfen ob schon vorhanden
        for i in range(self._hidden_imports.count()):
            if self._hidden_imports.item(i).text() == module:
                return
        self._hidden_imports.addItem(module)
    
    def _add_data_file(self):
        """Fügt Daten-Datei hinzu."""
        path, _ = QFileDialog.getOpenFileName(self, "Datei hinzufügen")
        if path:
            # Format: source;dest
            self._data_files.addItem(f"{path};.")
    
    def _add_data_folder(self):
        """Fügt Daten-Ordner hinzu."""
        path = QFileDialog.getExistingDirectory(self, "Ordner hinzufügen")
        if path:
            folder_name = Path(path).name
            self._data_files.addItem(f"{path};{folder_name}")
    
    def _remove_selected(self, list_widget: QListWidget):
        """Entfernt ausgewählte Items."""
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))
    
    def _build_command(self) -> List[str]:
        """Erstellt den PyInstaller-Befehl."""
        cmd = [sys.executable, "-m", "PyInstaller"]
        
        # Basis-Optionen
        if self._onefile.isChecked():
            cmd.append("--onefile")
        
        if self._noconsole.isChecked():
            cmd.append("--noconsole")
        
        if self._clean.isChecked():
            cmd.append("--clean")
        
        if self._noconfirm.isChecked():
            cmd.append("--noconfirm")
        
        # Name
        name = self._output_name.text().strip()
        if name:
            cmd.extend(["--name", name])
        
        # Icon
        icon = self._icon_path.text().strip()
        if icon:
            cmd.extend(["--icon", icon])
        
        # Ausgabe-Ordner
        dist = self._dist_path.text().strip()
        if dist:
            cmd.extend(["--distpath", dist])
        
        # UPX
        if self._use_upx.isChecked():
            upx = self._upx_path.text().strip()
            if upx:
                cmd.extend(["--upx-dir", str(Path(upx).parent)])
        else:
            cmd.append("--noupx")
        
        # Debug
        if self._debug.isChecked():
            cmd.extend(["--debug", "all"])
        
        cmd.extend(["--log-level", self._log_level.currentText()])
        
        # Versteckte Imports
        for i in range(self._hidden_imports.count()):
            module = self._hidden_imports.item(i).text()
            cmd.extend(["--hidden-import", module])
        
        # Daten-Dateien
        for i in range(self._data_files.count()):
            data = self._data_files.item(i).text()
            cmd.extend(["--add-data", data])
        
        # Zusätzliche Argumente
        extra = self._extra_args.text().strip()
        if extra:
            # BUGSWEEP-33: shlex statt naivem split() — sonst zerbrechen Pfade mit Leerzeichen
            # (z.B. --paths "C:\Mein Ordner") in falsche Einzelargumente. shlex wirft bei
            # unbalancierten Quotes ValueError (split() konnte nie werfen) -> Fallback auf
            # naive Zerlegung, damit ein kaputter Extra-String den Build-Klick nicht crasht.
            try:
                cmd.extend(shlex.split(extra, posix=False))
            except ValueError:
                cmd.extend(extra.split())
        
        # Script
        cmd.append(self._script_path.text())
        
        return cmd
    
    def _show_command(self):
        """Zeigt den Befehl an."""
        if not self._script_path.text():
            QMessageBox.warning(self, "Kein Script", "Bitte wählen Sie ein Python-Script.")
            return
        
        cmd = self._build_command()
        self._output_text.setText(" \\\n    ".join(cmd))
    
    def _start_compile(self):
        """Startet die Kompilierung."""
        script = self._script_path.text()
        if not script:
            QMessageBox.warning(self, "Kein Script", "Bitte wählen Sie ein Python-Script.")
            return
        
        if not Path(script).exists():
            QMessageBox.warning(self, "Nicht gefunden", f"Script nicht gefunden:\n{script}")
            return
        
        cmd = self._build_command()
        work_dir = str(Path(script).parent)
        
        self._output_text.clear()
        self._output_text.append("Starte Kompilierung...\n")
        self._output_text.append(" ".join(cmd) + "\n\n")
        
        self._progress.setVisible(True)
        self._btn_compile.setEnabled(False)
        
        self._worker = CompileWorker(cmd, work_dir)
        self._worker.output.connect(self._on_output)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
    
    def _on_output(self, line: str):
        """Ausgabe vom Compiler."""
        self._output_text.append(line)
        # Auto-Scroll
        scrollbar = self._output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_finished(self, success: bool, message: str):
        """Kompilierung beendet."""
        self._progress.setVisible(False)
        self._btn_compile.setEnabled(True)
        
        self._output_text.append(f"\n{'='*50}")
        self._output_text.append(message)
        
        if success:
            QMessageBox.information(self, "Fertig", message)
        else:
            QMessageBox.warning(self, "Fehler", message)
