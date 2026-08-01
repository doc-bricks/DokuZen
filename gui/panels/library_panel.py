#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Library Panel
===============================
Zeigt die Themen-Bibliothek als Baumansicht.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QInputDialog, QMessageBox, QLabel, QHBoxLayout,
    QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from utils.logger import LoggerMixin


class LibraryPanel(QWidget, LoggerMixin):
    """
    Panel zur Anzeige der Themen-Bibliothek.
    
    Signale:
        theme_selected(str): Wird emittiert wenn ein Thema ausgewählt wird
    """
    
    theme_selected = Signal(str)
    
    def __init__(self, library_manager, parent=None):
        super().__init__(parent)
        
        self._library = library_manager
        self._setup_ui()
        self._connect_signals()
        self._populate()
        
        self.logger.debug("LibraryPanel erstellt")
    
    def _setup_ui(self):
        """Erstellt die UI-Elemente."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("<b>Bibliothek</b>")
        header_layout.addWidget(header_label)
        
        # Plus-Button für neues Thema
        self._btn_add = QPushButton("+")
        self._btn_add.setFixedSize(24, 24)
        self._btn_add.setToolTip("Neues Thema erstellen (Ctrl+N)")
        self._btn_add.setAccessibleName("Neues Thema erstellen")
        self._btn_add.setAccessibleDescription(
            "Öffnet einen Dialog zum Anlegen eines neuen Bibliotheksthemas."
        )
        self._btn_add.clicked.connect(self.create_new_theme)
        header_layout.addWidget(self._btn_add)
        
        layout.addLayout(header_layout)
        
        # Baum-Widget
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setIndentation(15)
        self._tree.setAnimated(True)
        layout.addWidget(self._tree)
    
    def _connect_signals(self):
        """Verbindet Signale."""
        self._tree.currentItemChanged.connect(self._on_item_changed)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def _populate(self):
        """Füllt den Baum mit Themen."""
        self._tree.clear()
        
        current_theme = self._library.themes.get_current_theme()
        
        for theme in self._library.themes.get_all_themes():
            item = QTreeWidgetItem()
            item.setText(0, f"{theme.name} ({theme.document_count})")
            item.setData(0, Qt.ItemDataRole.UserRole, theme.name)
            
            # Ungelesene hervorheben
            if theme.unread_count > 0:
                item.setToolTip(0, f"{theme.unread_count} ungelesen")
            
            self._tree.addTopLevelItem(item)
            
            # Aktuelles Thema auswählen
            if theme.name == current_theme:
                self._tree.setCurrentItem(item)
    
    def refresh(self):
        """Aktualisiert die Anzeige."""
        self._populate()
    
    def create_new_theme(self):
        """Öffnet Dialog für neues Thema."""
        name, ok = QInputDialog.getText(
            self,
            "Neues Thema",
            "Name des Themas:",
            text=""
        )
        
        if ok and name.strip():
            if self._library.themes.create_theme(name.strip()):
                self.refresh()
                self.logger.info(f"Neues Thema erstellt: {name}")
            else:
                QMessageBox.warning(
                    self,
                    "Fehler",
                    f"Thema '{name}' existiert bereits oder ist ungültig."
                )
    
    def _on_item_changed(self, current, previous):
        """Reagiert auf Auswahländerung."""
        if current:
            theme_name = current.data(0, Qt.ItemDataRole.UserRole)
            if theme_name:
                self.theme_selected.emit(theme_name)
    
    def _on_item_double_clicked(self, item, column):
        """Doppelklick zum Umbenennen."""
        theme_name = item.data(0, Qt.ItemDataRole.UserRole)
        if theme_name and theme_name not in self._library.themes.RESERVED_THEMES:
            self._rename_theme(theme_name)
    
    def _show_context_menu(self, position):
        """Zeigt Kontextmenü."""
        item = self._tree.itemAt(position)
        if not item:
            return
        
        theme_name = item.data(0, Qt.ItemDataRole.UserRole)
        if not theme_name:
            return
        
        menu = QMenu(self)

        # BUGSWEEP-32: QActions an `menu` parenten, nicht an `self` (sonst QAction-Leak je Rechtsklick).
        # Umbenennen
        action_rename = QAction("Umbenennen...", menu)
        action_rename.triggered.connect(lambda: self._rename_theme(theme_name))
        if theme_name in self._library.themes.RESERVED_THEMES:
            action_rename.setEnabled(False)
        menu.addAction(action_rename)

        # Löschen
        action_delete = QAction("Löschen", menu)
        action_delete.triggered.connect(lambda: self._delete_theme(theme_name))
        if theme_name in self._library.themes.RESERVED_THEMES:
            action_delete.setEnabled(False)
        menu.addAction(action_delete)

        menu.addSeparator()

        # Neues Thema
        action_new = QAction("Neues Thema...", menu)
        action_new.triggered.connect(self.create_new_theme)
        menu.addAction(action_new)
        
        menu.exec(self._tree.mapToGlobal(position))
        # BUGSWEEP-32: Menü + Kind-QActions freigeben (sonst QMenu-Akkumulation auf self).
        menu.deleteLater()
    
    def _rename_theme(self, old_name: str):
        """Benennt ein Thema um."""
        new_name, ok = QInputDialog.getText(
            self,
            "Thema umbenennen",
            "Neuer Name:",
            text=old_name
        )
        
        if ok and new_name.strip() and new_name.strip() != old_name:
            if self._library.themes.rename_theme(old_name, new_name.strip()):
                self.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Fehler",
                    f"Konnte Thema nicht umbenennen."
                )
    
    def _delete_theme(self, name: str):
        """Löscht ein Thema."""
        # Bestätigung
        docs = self._library.get_documents(name)
        msg = f"Thema '{name}' wirklich löschen?"
        if docs:
            msg += f"\n\nDas Thema enthält {len(docs)} Dokument(e)."
        
        result = QMessageBox.question(
            self,
            "Thema löschen",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            if self._library.themes.delete_theme(name):
                self.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Fehler",
                    "Konnte Thema nicht löschen."
                )
