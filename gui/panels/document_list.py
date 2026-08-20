#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Document List Panel
=====================================
Zeigt die Dokumentenliste des aktuellen Themas.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QMenu, QHeaderView, QLabel, QComboBox, QAbstractItemView,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, QMimeData, QUrl
from PySide6.QtGui import QAction, QDrag, QColor

from utils.logger import LoggerMixin
from core.library.manager import FilterMode, SortMode
from translator import tr


class DocumentListPanel(QWidget, LoggerMixin):
    """
    Panel zur Anzeige der Dokumentenliste.
    
    Signale:
        document_selected(str): Wenn ein Dokument ausgewählt wird
        document_double_clicked(str): Bei Doppelklick auf ein Dokument
    """
    
    document_selected = Signal(str)
    document_double_clicked = Signal(str)
    
    # Spalten-Definitionen (kanonische Keys)
    COLUMN_KEYS = ["Name", "Typ", "Größe", "Hinzugefügt", "Status"]
    
    def __init__(self, library_manager, parent=None):
        super().__init__(parent)
        
        self._library = library_manager
        self._setup_ui()
        self._connect_signals()
        self.refresh()
        
        self.logger.debug("DocumentListPanel erstellt")
    
    def _setup_ui(self):
        """Erstellt die UI-Elemente."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header mit Filter
        header_layout = QHBoxLayout()
        
        self._header_label = QLabel(f"<b>{tr('Dokumente')}</b>")
        header_layout.addWidget(self._header_label)
        
        header_layout.addStretch()
        
        # Filter-Dropdown
        self._filter_label = QLabel(f"{tr('Filter')}:")
        header_layout.addWidget(self._filter_label)
        self._filter_combo = QComboBox()
        self._filter_combo.addItem(tr("Alle"), FilterMode.ALL)
        self._filter_combo.addItem(tr("Ungelesen"), FilterMode.UNREAD)
        self._filter_combo.addItem(tr("Gelesen"), FilterMode.READ)
        self._filter_combo.setFixedWidth(100)
        header_layout.addWidget(self._filter_combo)
        
        # Sortierung
        self._sort_label = QLabel(f"{tr('Sortierung')}:")
        header_layout.addWidget(self._sort_label)
        self._sort_combo = QComboBox()
        self._sort_combo.addItem(tr("Name"), SortMode.NAME)
        self._sort_combo.addItem(tr("Datum"), SortMode.DATE_ADDED)
        self._sort_combo.addItem(tr("Größe"), SortMode.SIZE)
        self._sort_combo.addItem(tr("Typ"), SortMode.TYPE)
        self._sort_combo.setFixedWidth(100)
        header_layout.addWidget(self._sort_combo)
        
        layout.addLayout(header_layout)
        
        # Tabelle
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMN_KEYS))
        self._table.setHorizontalHeaderLabels([tr(col) for col in self.COLUMN_KEYS])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(False)  # Wir sortieren selbst
        self._table.setDragEnabled(True)
        self._table.setAcceptDrops(True)
        self._table.setDropIndicatorShown(True)
        
        # Spaltenbreiten
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)   # Typ
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Größe
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # Datum
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Status
        
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 70)
        
        layout.addWidget(self._table)
        
        # Status-Label
        self._status_label = QLabel(f"0 {tr('Dokumente')}")
        layout.addWidget(self._status_label)
    
    def _connect_signals(self):
        """Verbindet Signale."""
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(self._on_double_click)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
    
    def refresh(self):
        """Aktualisiert die Dokumentenliste."""
        self._table.setRowCount(0)
        
        documents = self._library.get_documents()
        
        for row, doc in enumerate(documents):
            self._table.insertRow(row)
            
            # Name
            name_item = QTableWidgetItem(doc.name)
            name_item.setData(Qt.ItemDataRole.UserRole, doc.path)
            name_item.setToolTip(doc.path)
            if not doc.exists:
                name_item.setForeground(QColor(200, 50, 50))
                name_item.setToolTip(f"NICHT GEFUNDEN: {doc.path}")
            self._table.setItem(row, 0, name_item)
            
            # Typ
            type_item = QTableWidgetItem(doc.extension.upper().replace(".", ""))
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, type_item)
            
            # Größe
            size_item = QTableWidgetItem(doc.size_human)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 2, size_item)
            
            # Datum
            date_str = doc.added.strftime("%d.%m.%Y")
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, date_item)
            
            # Status
            status_item = QTableWidgetItem("✓" if doc.is_read else "○")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if doc.is_read:
                status_item.setForeground(QColor(50, 150, 50))
            self._table.setItem(row, 4, status_item)
        
        # Status aktualisieren
        self._status_label.setText(f"{len(documents)} {tr('Dokument(e)')}")
    
    def retranslate_ui(self):
        """Aktualisiert alle UI-Texte im DocumentListPanel dynamisch."""
        if hasattr(self, "_header_label"):
            self._header_label.setText(f"<b>{tr('Dokumente')}</b>")
        if hasattr(self, "_filter_label"):
            self._filter_label.setText(f"{tr('Filter')}:")
        if hasattr(self, "_sort_label"):
            self._sort_label.setText(f"{tr('Sortierung')}:")
            
        if hasattr(self, "_filter_combo"):
            current_filter = self._filter_combo.currentData()
            self._filter_combo.blockSignals(True)
            self._filter_combo.clear()
            self._filter_combo.addItem(tr("Alle"), FilterMode.ALL)
            self._filter_combo.addItem(tr("Ungelesen"), FilterMode.UNREAD)
            self._filter_combo.addItem(tr("Gelesen"), FilterMode.READ)
            idx = self._filter_combo.findData(current_filter)
            if idx >= 0:
                self._filter_combo.setCurrentIndex(idx)
            self._filter_combo.blockSignals(False)
            
        if hasattr(self, "_sort_combo"):
            current_sort = self._sort_combo.currentData()
            self._sort_combo.blockSignals(True)
            self._sort_combo.clear()
            self._sort_combo.addItem(tr("Name"), SortMode.NAME)
            self._sort_combo.addItem(tr("Datum"), SortMode.DATE_ADDED)
            self._sort_combo.addItem(tr("Größe"), SortMode.SIZE)
            self._sort_combo.addItem(tr("Typ"), SortMode.TYPE)
            idx = self._sort_combo.findData(current_sort)
            if idx >= 0:
                self._sort_combo.setCurrentIndex(idx)
            self._sort_combo.blockSignals(False)
            
        if hasattr(self, "_table"):
            self._table.setHorizontalHeaderLabels([tr(col) for col in self.COLUMN_KEYS])
            
        self.refresh()
    
    def _on_selection_changed(self):
        """Reagiert auf Auswahländerung."""
        paths = self.get_selected_paths()
        if paths:
            self.document_selected.emit(paths[0])
    
    def _on_double_click(self, item):
        """Reagiert auf Doppelklick."""
        row = item.row()
        name_item = self._table.item(row, 0)
        if name_item:
            path = name_item.data(Qt.ItemDataRole.UserRole)
            if path:
                self.document_double_clicked.emit(path)
    
    def _on_filter_changed(self):
        """Reagiert auf Filter-Änderung."""
        mode = self._filter_combo.currentData()
        self._library.set_filter(mode)
        self.refresh()
    
    def _on_sort_changed(self):
        """Reagiert auf Sortier-Änderung."""
        mode = self._sort_combo.currentData()
        self._library.set_sort(mode)
        self.refresh()
    
    def _show_context_menu(self, position):
        """Zeigt Kontextmenü für Dokumente."""
        paths = self.get_selected_paths()
        if not paths:
            return
        
        menu = QMenu(self)

        # BUGSWEEP-32: QActions an `menu` (lokal, nach exec verworfen) parenten, nicht an `self` —
        # sonst akkumulieren bei jedem Rechtsklick QAction-Kinder am Panel (Speicher-Leak über Laufzeit).
        # Öffnen
        action_open = QAction(tr("Öffnen"), menu)  # QAction("Öffnen", menu)
        action_open.triggered.connect(lambda: self.document_double_clicked.emit(paths[0]))
        menu.addAction(action_open)

        menu.addSeparator()

        # Gelesen/Ungelesen markieren
        action_read = QAction(tr("Als gelesen markieren"), menu)
        action_read.triggered.connect(lambda: self._mark_as_read(paths, True))
        menu.addAction(action_read)

        action_unread = QAction(tr("Als ungelesen markieren"), menu)
        action_unread.triggered.connect(lambda: self._mark_as_read(paths, False))
        menu.addAction(action_unread)

        menu.addSeparator()

        # Aus Bibliothek entfernen
        action_remove = QAction(tr("Aus Bibliothek entfernen"), menu)
        action_remove.triggered.connect(lambda: self._remove_documents(paths))
        menu.addAction(action_remove)
        
        menu.exec(self._table.mapToGlobal(position))
        # BUGSWEEP-32: Menü (und seine jetzt als Kinder gehaltenen QActions) freigeben — sonst
        # akkumuliert pro Rechtsklick ein QMenu als Kind von self bis zum Programmende.
        menu.deleteLater()
    
    def _mark_as_read(self, paths: List[str], is_read: bool):
        """Markiert Dokumente als gelesen/ungelesen."""
        for path in paths:
            self._library.set_read_status(path, is_read)
        self.refresh()
    
    def _remove_documents(self, paths: List[str]):
        """Entfernt Dokumente aus der Bibliothek."""
        if len(paths) == 1:
            msg = f"'{Path(paths[0]).name}' {tr('aus der Bibliothek entfernen?')}"
        else:
            msg = f"{len(paths)} {tr('Dokumente aus der Bibliothek entfernen?')}"
        
        msg += f"\n\n{tr('Die Dateien werden nicht gelöscht.')}"
        
        result = QMessageBox.question(
            self,
            tr("Entfernen bestätigen"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            for path in paths:
                self._library.remove_document(path)
            self.refresh()
    
    # === Drag & Drop ===
    
    def dragEnterEvent(self, event):
        """Akzeptiert Datei-Drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Verarbeitet gedroppte Dateien."""
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(url.toLocalFile())
        
        if files:
            success, failed = self._library.add_documents(files)
            self.refresh()
    
    # === Public API ===
    
    def get_selected_paths(self) -> List[str]:
        """Gibt die Pfade der ausgewählten Dokumente zurück."""
        paths = []
        for item in self._table.selectedItems():
            if item.column() == 0:  # Nur erste Spalte zählen
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    paths.append(path)
        return paths
    
    def select_all(self):
        """Wählt alle Dokumente aus."""
        self._table.selectAll()
