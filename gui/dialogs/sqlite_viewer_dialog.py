#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - SQLite Viewer Dialog
=======================================
Read-Only SQLite-Datenbank-Viewer.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit,
    QFileDialog, QMessageBox, QTabWidget, QWidget,
    QComboBox, QSpinBox, QGroupBox, QFormLayout,
    QHeaderView, QMenu, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction

from utils.logger import LoggerMixin


class QueryWorker(QThread):
    """Worker-Thread für SQL-Abfragen."""
    
    result_ready = Signal(list, list)  # columns, rows
    error_occurred = Signal(str)
    
    def __init__(self, db_path: str, query: str):
        super().__init__()
        self.db_path = db_path
        self.query = query
    
    def run(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(self.query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            self.result_ready.emit(columns, rows)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if conn:
                conn.close()


class SQLiteViewerDialog(QDialog, LoggerMixin):
    """
    Read-Only SQLite-Datenbank-Viewer.
    
    Features:
    - Tabellenstruktur anzeigen
    - Daten durchsuchen
    - SQL-Abfragen ausführen
    - Export als CSV
    """
    
    def __init__(self, parent=None, db_path: str = None):
        super().__init__(parent)
        
        self._db_path: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._worker: Optional[QueryWorker] = None
        
        self._setup_ui()
        
        if db_path:
            self._open_database(db_path)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("SQLite Viewer")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_open = QPushButton("Datenbank öffnen...")
        btn_open.clicked.connect(self._on_open)
        toolbar.addWidget(btn_open)
        
        toolbar.addWidget(QLabel("  Aktuelle DB:"))
        self._db_label = QLabel("Keine Datenbank geladen")
        self._db_label.setStyleSheet("font-style: italic;")
        toolbar.addWidget(self._db_label)
        
        toolbar.addStretch()
        
        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.clicked.connect(self._refresh)
        toolbar.addWidget(btn_refresh)
        
        layout.addLayout(toolbar)
        
        # Hauptbereich
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Links: Tabellen-Baum
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Tabellen:"))
        
        self._tables_tree = QTreeWidget()
        self._tables_tree.setHeaderLabels(["Name", "Typ"])
        self._tables_tree.setColumnWidth(0, 150)
        self._tables_tree.itemDoubleClicked.connect(self._on_table_double_clicked)
        self._tables_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tables_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        left_layout.addWidget(self._tables_tree)
        
        main_splitter.addWidget(left_widget)
        
        # Rechts: Tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tabs = QTabWidget()
        
        # Tab: Daten
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        # Tabellen-Auswahl
        table_select = QHBoxLayout()
        table_select.addWidget(QLabel("Tabelle:"))
        
        self._table_combo = QComboBox()
        self._table_combo.setMinimumWidth(200)
        self._table_combo.currentTextChanged.connect(self._on_table_selected)
        table_select.addWidget(self._table_combo)
        
        table_select.addWidget(QLabel("  Limit:"))
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(10, 10000)
        self._limit_spin.setValue(100)
        self._limit_spin.setSingleStep(100)
        table_select.addWidget(self._limit_spin)
        
        btn_load = QPushButton("Laden")
        btn_load.clicked.connect(self._load_table_data)
        table_select.addWidget(btn_load)
        
        table_select.addStretch()
        data_layout.addLayout(table_select)
        
        # Daten-Tabelle
        self._data_table = QTableWidget()
        self._data_table.setAlternatingRowColors(True)
        self._data_table.horizontalHeader().setStretchLastSection(True)
        self._data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._data_table.customContextMenuRequested.connect(self._show_data_context_menu)
        data_layout.addWidget(self._data_table)
        
        # Status
        self._data_status = QLabel("")
        data_layout.addWidget(self._data_status)
        
        self._tabs.addTab(data_tab, "Daten")
        
        # Tab: SQL
        sql_tab = QWidget()
        sql_layout = QVBoxLayout(sql_tab)
        
        sql_layout.addWidget(QLabel("SQL-Abfrage (nur SELECT):"))
        
        self._sql_edit = QTextEdit()
        self._sql_edit.setPlaceholderText("SELECT * FROM tabelle LIMIT 100")
        self._sql_edit.setMaximumHeight(100)
        sql_layout.addWidget(self._sql_edit)
        
        sql_buttons = QHBoxLayout()
        
        btn_execute = QPushButton("Ausführen (F5)")
        btn_execute.clicked.connect(self._execute_query)
        sql_buttons.addWidget(btn_execute)
        
        btn_clear = QPushButton("Leeren")
        btn_clear.clicked.connect(lambda: self._sql_edit.clear())
        sql_buttons.addWidget(btn_clear)
        
        sql_buttons.addStretch()
        sql_layout.addLayout(sql_buttons)
        
        # Ergebnis-Tabelle
        self._result_table = QTableWidget()
        self._result_table.setAlternatingRowColors(True)
        self._result_table.horizontalHeader().setStretchLastSection(True)
        sql_layout.addWidget(self._result_table)
        
        self._sql_status = QLabel("")
        sql_layout.addWidget(self._sql_status)
        
        self._tabs.addTab(sql_tab, "SQL")
        
        # Tab: Struktur
        structure_tab = QWidget()
        structure_layout = QVBoxLayout(structure_tab)
        
        self._structure_text = QTextEdit()
        self._structure_text.setReadOnly(True)
        self._structure_text.setFontFamily("Consolas")
        structure_layout.addWidget(self._structure_text)
        
        self._tabs.addTab(structure_tab, "Struktur")
        
        right_layout.addWidget(self._tabs)
        main_splitter.addWidget(right_widget)
        
        # Splitter-Größen
        main_splitter.setSizes([250, 850])
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        
        btn_export = QPushButton("Als CSV exportieren...")
        btn_export.clicked.connect(self._export_csv)
        btn_layout.addWidget(btn_export)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def keyPressEvent(self, event):
        """Tastaturkürzel."""
        if event.key() == Qt.Key.Key_F5:
            self._execute_query()
        else:
            super().keyPressEvent(event)
    
    def _on_open(self):
        """Öffnet eine Datenbank."""
        path, _ = QFileDialog.getOpenFileName(
            self, "SQLite-Datenbank öffnen", "",
            "SQLite-Datenbanken (*.db *.sqlite *.sqlite3);;Alle Dateien (*.*)"
        )
        if path:
            self._open_database(path)
    
    def _open_database(self, path: str):
        """Öffnet eine Datenbank."""
        try:
            # Alte Verbindung schließen
            if self._conn:
                self._conn.close()
            
            # Neue Verbindung (Read-Only)
            self._conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            self._db_path = path
            self._db_label.setText(Path(path).name)
            
            self._load_tables()
            self._load_structure()
            
            self.logger.info(f"Datenbank geöffnet: {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Datenbank konnte nicht geöffnet werden:\n{e}")
    
    def _load_tables(self):
        """Lädt die Tabellenliste."""
        if not self._conn:
            return
        
        self._tables_tree.clear()
        self._table_combo.clear()
        
        cursor = self._conn.cursor()
        
        # Tabellen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        tables_item = QTreeWidgetItem(["Tabellen", f"({len(tables)})"])
        tables_item.setExpanded(True)
        
        for (name,) in tables:
            # Spaltenanzahl
            cursor.execute(f"PRAGMA table_info({name})")
            columns = cursor.fetchall()
            
            item = QTreeWidgetItem([name, f"{len(columns)} Spalten"])
            
            # Spalten als Kinder
            for col in columns:
                col_name, col_type = col[1], col[2]
                col_item = QTreeWidgetItem([col_name, col_type])
                item.addChild(col_item)
            
            tables_item.addChild(item)
            self._table_combo.addItem(name)
        
        self._tables_tree.addTopLevelItem(tables_item)
        
        # Views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()
        
        if views:
            views_item = QTreeWidgetItem(["Views", f"({len(views)})"])
            for (name,) in views:
                item = QTreeWidgetItem([name, "VIEW"])
                views_item.addChild(item)
            self._tables_tree.addTopLevelItem(views_item)
        
        # Indizes
        cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY name")
        indexes = cursor.fetchall()
        
        if indexes:
            idx_item = QTreeWidgetItem(["Indizes", f"({len(indexes)})"])
            for name, tbl in indexes:
                if name:
                    item = QTreeWidgetItem([name, f"on {tbl}"])
                    idx_item.addChild(item)
            self._tables_tree.addTopLevelItem(idx_item)
    
    def _load_structure(self):
        """Lädt die Datenbankstruktur."""
        if not self._conn:
            return
        
        cursor = self._conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name")
        
        structure = []
        for (sql,) in cursor.fetchall():
            structure.append(sql + ";\n")
        
        self._structure_text.setText("\n".join(structure))
    
    def _on_table_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Doppelklick auf Tabelle."""
        parent = item.parent()
        if parent and parent.text(0) == "Tabellen":
            table_name = item.text(0)
            self._table_combo.setCurrentText(table_name)
            self._tabs.setCurrentIndex(0)  # Daten-Tab
            self._load_table_data()
    
    def _on_table_selected(self, table_name: str):
        """Tabelle ausgewählt."""
        pass  # Wird beim Klick auf "Laden" geladen
    
    def _load_table_data(self):
        """Lädt Tabellendaten."""
        if not self._conn:
            return
        
        table_name = self._table_combo.currentText()
        if not table_name:
            return
        
        limit = self._limit_spin.value()
        query = f"SELECT * FROM [{table_name}] LIMIT {limit}"
        
        self._execute_query_internal(query, self._data_table, self._data_status)
    
    def _execute_query(self):
        """Führt SQL-Abfrage aus."""
        if not self._conn:
            QMessageBox.warning(self, "Keine Datenbank", "Bitte öffnen Sie zuerst eine Datenbank.")
            return
        
        query = self._sql_edit.toPlainText().strip()
        if not query:
            return
        
        # Nur SELECT erlauben
        if not query.upper().startswith("SELECT"):
            QMessageBox.warning(self, "Nur Lesen", "Nur SELECT-Abfragen sind erlaubt.")
            return
        
        self._execute_query_internal(query, self._result_table, self._sql_status)
    
    def _execute_query_internal(self, query: str, table: QTableWidget, status: QLabel):
        """Führt eine Abfrage aus und zeigt das Ergebnis."""
        # BUGSWEEP-34 REVIEW-NOTIZ (NICHT auto-gefixt — Architektur, User-Entscheidung): die Klasse
        # QueryWorker(QThread) existiert genau, um grosse Abfragen auszulagern, wird aber NIE
        # instanziiert (self._worker bleibt None) — Queries laufen hier synchron im GUI-Thread ->
        # bei grossen Tabellen/Limits friert die UI ein. Entweder QueryWorker reaktivieren (Worker
        # oeffnet eine EIGENE Connection -> self._conn NICHT in den Worker reichen; closeEvent dann
        # um worker.quit()/wait() ergaenzen) oder QueryWorker entfernen, falls bewusst synchron.
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            # Tabelle füllen
            table.clear()
            table.setColumnCount(len(columns))
            table.setRowCount(len(rows))
            table.setHorizontalHeaderLabels(columns)
            
            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "NULL")
                    if value is None:
                        item.setForeground(Qt.GlobalColor.gray)
                    table.setItem(row_idx, col_idx, item)
            
            # Spaltenbreiten anpassen
            table.resizeColumnsToContents()
            
            status.setText(f"{len(rows)} Zeilen geladen")
            
        except Exception as e:
            status.setText(f"Fehler: {e}")
            QMessageBox.warning(self, "SQL-Fehler", str(e))
    
    def _refresh(self):
        """Aktualisiert die Ansicht."""
        if self._db_path:
            self._open_database(self._db_path)
    
    def _show_tree_context_menu(self, position):
        """Zeigt Kontextmenü für Tabellen-Baum."""
        item = self._tables_tree.itemAt(position)
        if not item:
            return
        
        parent = item.parent()
        if parent and parent.text(0) == "Tabellen":
            menu = QMenu(self._tables_tree)

            action_view = menu.addAction("Daten anzeigen")
            action_view.triggered.connect(lambda: self._view_table(item.text(0)))
            
            action_count = menu.addAction("Zeilen zählen")
            action_count.triggered.connect(lambda: self._count_rows(item.text(0)))
            
            menu.addSeparator()
            
            action_copy = menu.addAction("Name kopieren")
            action_copy.triggered.connect(lambda: QApplication.clipboard().setText(item.text(0)))
            
            menu.exec(self._tables_tree.mapToGlobal(position))
    
    def _show_data_context_menu(self, position):
        """Zeigt Kontextmenü für Daten-Tabelle."""
        menu = QMenu(self._data_table)

        action_copy = menu.addAction("Zelle kopieren")
        action_copy.triggered.connect(self._copy_cell)
        
        action_copy_row = menu.addAction("Zeile kopieren")
        action_copy_row.triggered.connect(self._copy_row)
        
        menu.exec(self._data_table.mapToGlobal(position))
    
    def _view_table(self, table_name: str):
        """Zeigt Tabellendaten."""
        self._table_combo.setCurrentText(table_name)
        self._tabs.setCurrentIndex(0)
        self._load_table_data()
    
    def _count_rows(self, table_name: str):
        """Zählt Zeilen einer Tabelle."""
        if not self._conn:
            return
        
        # BUGSWEEP-34: DB-Fehler (gesperrt/korrupt) abfangen statt unbehandelter Exception aus dem
        # Kontextmenue-Slot (konsistent zu _execute_query_internal).
        try:
            cursor = self._conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Zeilen zählen fehlgeschlagen:\n{e}")
            return

        QMessageBox.information(self, "Zeilenanzahl", f"Tabelle '{table_name}':\n{count:,} Zeilen")
    
    def _copy_cell(self):
        """Kopiert aktuelle Zelle."""
        item = self._data_table.currentItem()
        if item:
            QApplication.clipboard().setText(item.text())
    
    def _copy_row(self):
        """Kopiert aktuelle Zeile."""
        row = self._data_table.currentRow()
        if row >= 0:
            values = []
            for col in range(self._data_table.columnCount()):
                item = self._data_table.item(row, col)
                values.append(item.text() if item else "")
            QApplication.clipboard().setText("\t".join(values))
    
    def _export_csv(self):
        """Exportiert aktuelle Tabelle als CSV."""
        table = self._data_table if self._tabs.currentIndex() == 0 else self._result_table
        
        if table.rowCount() == 0:
            QMessageBox.warning(self, "Keine Daten", "Keine Daten zum Exportieren.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Als CSV exportieren", "",
            "CSV-Dateien (*.csv)"
        )
        
        if not path:
            return
        
        try:
            import csv
            
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                headers = []
                for col in range(table.columnCount()):
                    headers.append(table.horizontalHeaderItem(col).text())
                writer.writerow(headers)
                
                # Daten
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Export", f"Exportiert:\n{path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
    
    def closeEvent(self, event):
        """Cleanup beim Schließen."""
        if self._conn:
            self._conn.close()
        super().closeEvent(event)
