#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Code Analysis Dialog
=======================================
Dialog zur Analyse und Zerlegung von Python-Code.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QTabWidget, QWidget, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from utils.logger import LoggerMixin
from plugins.special_text.code_splitter import CodeSplitter, CodeAnalysis, CodeElement, CodeElementType


class CodeAnalysisDialog(QDialog, LoggerMixin):
    """
    Dialog zur Code-Analyse.
    
    Features:
    - Python-Dateien analysieren
    - Klassen/Funktionen anzeigen
    - Code-Vorschau
    - In Komponenten zerlegen
    """
    
    def __init__(self, parent=None, initial_file: str = None):
        super().__init__(parent)
        
        self._splitter = CodeSplitter()
        self._analysis: Optional[CodeAnalysis] = None
        self._initial_file = initial_file
        
        self._setup_ui()
        
        if initial_file:
            self._input_path.setText(initial_file)
            self._on_analyze()
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("Python Code-Analyse")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Eingabe
        input_group = QGroupBox("Python-Datei")
        input_layout = QHBoxLayout(input_group)
        
        self._input_path = QLineEdit()
        self._input_path.setPlaceholderText("Python-Datei wählen...")
        input_layout.addWidget(self._input_path)
        
        btn_browse = QPushButton("Durchsuchen...")
        btn_browse.clicked.connect(self._on_browse)
        input_layout.addWidget(btn_browse)
        
        btn_analyze = QPushButton("Analysieren")
        btn_analyze.setStyleSheet("font-weight: bold;")
        btn_analyze.clicked.connect(self._on_analyze)
        input_layout.addWidget(btn_analyze)
        
        layout.addWidget(input_group)
        
        # Hauptsplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Linke Seite: Struktur-Baum
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        tree_group = QGroupBox("Code-Struktur")
        tree_layout = QVBoxLayout(tree_group)
        
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Element", "Zeilen", "Typ"])
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 60)
        self._tree.itemClicked.connect(self._on_tree_item_clicked)
        tree_layout.addWidget(self._tree)
        
        left_layout.addWidget(tree_group)
        
        # Statistik
        stats_group = QGroupBox("Statistik")
        stats_layout = QVBoxLayout(stats_group)
        
        self._stats_label = QLabel("Keine Datei analysiert")
        self._stats_label.setWordWrap(True)
        stats_layout.addWidget(self._stats_label)
        
        left_layout.addWidget(stats_group)
        
        splitter.addWidget(left_widget)
        
        # Rechte Seite: Tabs mit Code und Zusammenfassung
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tabs = QTabWidget()
        
        # Tab: Code-Vorschau
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)
        
        self._code_view = QTextEdit()
        self._code_view.setReadOnly(True)
        self._code_view.setFont(QFont("Consolas", 10))
        self._code_view.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        code_layout.addWidget(self._code_view)
        
        self._tabs.addTab(code_tab, "Code-Vorschau")
        
        # Tab: Zusammenfassung
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        
        self._summary_view = QTextEdit()
        self._summary_view.setReadOnly(True)
        self._summary_view.setFont(QFont("Consolas", 10))
        summary_layout.addWidget(self._summary_view)
        
        self._tabs.addTab(summary_tab, "Zusammenfassung")
        
        right_layout.addWidget(self._tabs)
        
        splitter.addWidget(right_widget)
        
        # Splitter-Größen
        splitter.setSizes([300, 700])
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        
        self._btn_split = QPushButton("In Dateien zerlegen...")
        self._btn_split.setEnabled(False)
        self._btn_split.clicked.connect(self._on_split)
        btn_layout.addWidget(self._btn_split)
        
        btn_export = QPushButton("Zusammenfassung exportieren...")
        btn_export.clicked.connect(self._on_export_summary)
        btn_layout.addWidget(btn_export)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _on_browse(self):
        """Wählt Python-Datei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Python-Datei wählen", "",
            "Python-Dateien (*.py);;Alle Dateien (*.*)"
        )
        if path:
            self._input_path.setText(path)
    
    def _on_analyze(self):
        """Analysiert die Datei."""
        filepath = self._input_path.text().strip()
        
        if not filepath:
            QMessageBox.warning(self, "Fehler", "Bitte Datei auswählen.")
            return
        
        path = Path(filepath)
        
        if not path.exists():
            QMessageBox.warning(self, "Fehler", "Datei nicht gefunden.")
            return
        
        # Prüfung auf Python-Datei (verhindert Absturz bei PDF etc.)
        if path.suffix.lower() != '.py':
            QMessageBox.warning(
                self, "Falscher Dateityp",
                f"Nur Python-Dateien (*.py) können analysiert werden.\n\n"
                f"Ausgewählt: {path.suffix or 'keine Endung'}"
            )
            return
        
        self._analysis = self._splitter.analyze_file(filepath)
        
        if not self._analysis:
            QMessageBox.critical(self, "Fehler", "Analyse fehlgeschlagen.")
            return
        
        self._update_tree()
        self._update_stats()
        self._update_summary()
        self._btn_split.setEnabled(True)
    
    def _update_tree(self):
        """Aktualisiert den Struktur-Baum."""
        self._tree.clear()
        
        if not self._analysis:
            return
        
        # Imports
        if self._analysis.imports:
            imports_item = QTreeWidgetItem(["Imports", str(len(self._analysis.imports)), ""])
            for imp in self._analysis.imports:
                child = QTreeWidgetItem([imp, "", "import"])
                imports_item.addChild(child)
            self._tree.addTopLevelItem(imports_item)
        
        # Konstanten
        constants = [e for e in self._analysis.elements if e.element_type == CodeElementType.CONSTANT]
        if constants:
            const_item = QTreeWidgetItem(["Konstanten", str(len(constants)), ""])
            for c in constants:
                child = QTreeWidgetItem([c.name, str(c.line_count), "const"])
                child.setData(0, Qt.ItemDataRole.UserRole, c)
                const_item.addChild(child)
            self._tree.addTopLevelItem(const_item)
        
        # Klassen
        for cls in self._analysis.classes:
            cls_item = QTreeWidgetItem([cls.name, f"{cls.start_line}-{cls.end_line}", "class"])
            cls_item.setData(0, Qt.ItemDataRole.UserRole, cls)
            
            # Decorators
            if cls.decorators:
                for dec in cls.decorators:
                    child = QTreeWidgetItem([f"@{dec}", "", "decorator"])
                    cls_item.addChild(child)
            
            self._tree.addTopLevelItem(cls_item)
        
        # Funktionen
        for func in self._analysis.functions:
            func_item = QTreeWidgetItem([f"{func.name}()", f"{func.start_line}-{func.end_line}", "function"])
            func_item.setData(0, Qt.ItemDataRole.UserRole, func)
            self._tree.addTopLevelItem(func_item)
        
        self._tree.expandAll()
    
    def _update_stats(self):
        """Aktualisiert die Statistik."""
        if not self._analysis:
            self._stats_label.setText("Keine Datei analysiert")
            return
        
        self._stats_label.setText(
            f"<b>Datei:</b> {Path(self._analysis.filepath).name}<br>"
            f"<b>Zeilen gesamt:</b> {self._analysis.total_lines}<br>"
            f"<b>Code-Zeilen:</b> {self._analysis.code_lines}<br>"
            f"<b>Kommentare:</b> {self._analysis.comment_lines}<br>"
            f"<b>Leerzeilen:</b> {self._analysis.blank_lines}<br>"
            f"<br>"
            f"<b>Klassen:</b> {len(self._analysis.classes)}<br>"
            f"<b>Funktionen:</b> {len(self._analysis.functions)}<br>"
            f"<b>Imports:</b> {len(self._analysis.imports)}"
        )
    
    def _update_summary(self):
        """Aktualisiert die Zusammenfassung."""
        if not self._analysis:
            self._summary_view.setText("")
            return
        
        summary = self._splitter.generate_summary(self._analysis)
        self._summary_view.setText(summary)
    
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Zeigt Code für ausgewähltes Element."""
        element = item.data(0, Qt.ItemDataRole.UserRole)
        
        if element and isinstance(element, CodeElement):
            self._code_view.setText(element.content)
            self._tabs.setCurrentIndex(0)  # Code-Tab aktivieren
    
    def _on_split(self):
        """Zerlegt Code in Dateien."""
        if not self._analysis:
            return
        
        output_dir = QFileDialog.getExistingDirectory(
            self, "Ausgabeverzeichnis wählen"
        )
        
        if not output_dir:
            return
        
        # BUGSWEEP-33: Schreib-/Encoding-Fehler abfangen (konsistent zu _on_export_summary) statt
        # unbehandelter Exception aus dem Button-Slot.
        try:
            created_files = self._splitter.split_to_files(
                self._analysis, output_dir,
                split_classes=True,
                split_functions=True
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Zerlegung fehlgeschlagen:\n{e}")
            return

        if created_files:
            QMessageBox.information(
                self, "Zerlegung abgeschlossen",
                f"{len(created_files)} Dateien erstellt:\n\n" +
                "\n".join(Path(f).name for f in created_files)
            )
        else:
            QMessageBox.warning(self, "Hinweis", "Keine Dateien erstellt.")
    
    def _on_export_summary(self):
        """Exportiert die Zusammenfassung."""
        if not self._analysis:
            QMessageBox.warning(self, "Fehler", "Keine Analyse vorhanden.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Zusammenfassung speichern", "",
            "Textdateien (*.txt);;Markdown (*.md)"
        )
        
        if path:
            summary = self._splitter.generate_summary(self._analysis)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(summary)
                QMessageBox.information(self, "Gespeichert", f"Datei gespeichert:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", str(e))
