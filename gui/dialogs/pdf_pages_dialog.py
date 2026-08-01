#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Pages Dialog
===================================
Seitenverwaltung mit Drag & Drop und Thumbnails.
"""

from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QMenu, QProgressDialog, QInputDialog, QGroupBox,
    QSpinBox, QCheckBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QSize, QMimeData, Signal
from PySide6.QtGui import QPixmap, QIcon, QDrag, QAction

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class ThumbnailListWidget(QListWidget):
    """
    Liste mit Drag & Drop Support für PDF-Seiten-Thumbnails.
    """
    
    pages_reordered = Signal(list)  # Neue Reihenfolge
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(120, 170))
        self.setSpacing(10)
        self.setMovement(QListWidget.Movement.Free)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Drag & Drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
    
    def dropEvent(self, event):
        """Behandelt Drop und emittiert neues Signal."""
        super().dropEvent(event)
        
        # Neue Reihenfolge ermitteln
        new_order = []
        for i in range(self.count()):
            item = self.item(i)
            original_index = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(original_index)
        
        self.pages_reordered.emit(new_order)


class PDFPagesDialog(QDialog, LoggerMixin):
    """
    Dialog zur Verwaltung von PDF-Seiten.
    
    Features:
    - Thumbnail-Übersicht aller Seiten
    - Drag & Drop zum Umordnen
    - Seiten löschen, extrahieren, drehen
    - Seiten duplizieren
    - Mehrfachauswahl
    """
    
    def __init__(self, parent=None, pdf_path: str = None):
        super().__init__(parent)
        
        self._pdf_path: Optional[str] = None
        self._doc = None
        self._page_order: List[int] = []  # Aktuelle Reihenfolge
        self._deleted_pages: List[int] = []  # Gelöschte Seiten (Original-Index)
        self._rotations: dict = {}  # page_index -> rotation
        
        self._setup_ui()
        
        if pdf_path:
            self._load_pdf(pdf_path)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("PDF-Seiten verwalten")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_open = QPushButton("PDF öffnen...")
        btn_open.clicked.connect(self._on_open)
        toolbar.addWidget(btn_open)
        
        self._pdf_label = QLabel("Keine PDF geladen")
        self._pdf_label.setStyleSheet("font-style: italic;")
        toolbar.addWidget(self._pdf_label)
        
        toolbar.addStretch()
        
        # Seiten-Info
        self._page_info = QLabel("")
        toolbar.addWidget(self._page_info)
        
        layout.addLayout(toolbar)
        
        # Thumbnail-Liste
        self._thumbnail_list = ThumbnailListWidget()
        self._thumbnail_list.pages_reordered.connect(self._on_pages_reordered)
        self._thumbnail_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._thumbnail_list.customContextMenuRequested.connect(self._show_context_menu)
        self._thumbnail_list.itemSelectionChanged.connect(self._update_selection_info)
        layout.addWidget(self._thumbnail_list)
        
        # Aktions-Leiste
        actions_group = QGroupBox("Aktionen")
        actions_layout = QHBoxLayout(actions_group)
        
        btn_rotate_left = QPushButton("↺ Links drehen")
        btn_rotate_left.clicked.connect(lambda: self._rotate_selected(-90))
        actions_layout.addWidget(btn_rotate_left)
        
        btn_rotate_right = QPushButton("↻ Rechts drehen")
        btn_rotate_right.clicked.connect(lambda: self._rotate_selected(90))
        actions_layout.addWidget(btn_rotate_right)
        
        btn_delete = QPushButton("🗑 Löschen")
        btn_delete.clicked.connect(self._delete_selected)
        actions_layout.addWidget(btn_delete)
        
        btn_extract = QPushButton("📤 Extrahieren...")
        btn_extract.clicked.connect(self._extract_selected)
        actions_layout.addWidget(btn_extract)
        
        btn_duplicate = QPushButton("📋 Duplizieren")
        btn_duplicate.clicked.connect(self._duplicate_selected)
        actions_layout.addWidget(btn_duplicate)
        
        actions_layout.addStretch()
        
        # Auswahl-Info
        self._selection_label = QLabel("Keine Auswahl")
        actions_layout.addWidget(self._selection_label)
        
        layout.addWidget(actions_group)
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        
        btn_reset = QPushButton("Zurücksetzen")
        btn_reset.clicked.connect(self._reset_changes)
        btn_layout.addWidget(btn_reset)
        
        btn_layout.addStretch()
        
        btn_save_as = QPushButton("Speichern unter...")
        btn_save_as.clicked.connect(self._save_as)
        btn_layout.addWidget(btn_save_as)
        
        btn_save = QPushButton("Speichern")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _on_open(self):
        """Öffnet eine PDF-Datei."""
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF öffnen", "",
            "PDF-Dateien (*.pdf)"
        )
        if path:
            self._load_pdf(path)
    
    def _load_pdf(self, path: str):
        """Lädt eine PDF-Datei."""
        if not PYMUPDF_AVAILABLE:
            QMessageBox.critical(self, "Fehler", "PyMuPDF nicht verfügbar!")
            return
        
        try:
            # Vorherige schließen
            if self._doc is not None:
                self._doc.close()
            
            self._doc = fitz.open(path)
            self._pdf_path = path
            self._pdf_label.setText(Path(path).name)
            
            # Reset
            self._page_order = list(range(len(self._doc)))
            self._deleted_pages = []
            self._rotations = {}
            
            self._load_thumbnails()
            self._update_page_info()
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"PDF konnte nicht geladen werden:\n{e}")
    
    def _load_thumbnails(self):
        """Lädt alle Seiten-Thumbnails."""
        if self._doc is None:
            return
        
        self._thumbnail_list.clear()
        
        progress = QProgressDialog("Lade Vorschau...", "Abbrechen", 0, len(self._doc), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        for i, page_idx in enumerate(self._page_order):
            if progress.wasCanceled():
                break
            
            progress.setValue(i)
            
            if page_idx in self._deleted_pages:
                continue
            
            page = self._doc[page_idx]
            
            # Rotation anwenden
            rotation = self._rotations.get(page_idx, 0)
            
            # Thumbnail erstellen
            mat = fitz.Matrix(0.2, 0.2)  # 20% Skalierung
            if rotation:
                mat = mat * fitz.Matrix(rotation)
            
            pix = page.get_pixmap(matrix=mat)
            
            # In QPixmap konvertieren
            img_data = pix.tobytes("ppm")
            qpixmap = QPixmap()
            qpixmap.loadFromData(img_data)
            
            # Item erstellen
            item = QListWidgetItem()
            item.setIcon(QIcon(qpixmap))
            item.setText(f"Seite {page_idx + 1}")
            item.setData(Qt.ItemDataRole.UserRole, page_idx)  # Original-Index speichern
            item.setToolTip(f"Seite {page_idx + 1}\n"
                           f"Größe: {page.rect.width:.0f} x {page.rect.height:.0f}")
            
            self._thumbnail_list.addItem(item)
        
        progress.setValue(len(self._doc))
    
    def _update_page_info(self):
        """Aktualisiert die Seiten-Info."""
        if self._doc is None:
            self._page_info.setText("")
            return
        
        total = len(self._doc)
        visible = total - len(self._deleted_pages)
        self._page_info.setText(f"{visible} von {total} Seiten")
    
    def _update_selection_info(self):
        """Aktualisiert die Auswahl-Info."""
        selected = self._thumbnail_list.selectedItems()
        if selected:
            self._selection_label.setText(f"{len(selected)} Seite(n) ausgewählt")
        else:
            self._selection_label.setText("Keine Auswahl")
    
    def _on_pages_reordered(self, new_order: List[int]):
        """Wird aufgerufen wenn Seiten neu geordnet wurden."""
        self._page_order = new_order
        self.logger.debug(f"Neue Reihenfolge: {new_order}")
    
    def _show_context_menu(self, position):
        """Zeigt Kontextmenü."""
        item = self._thumbnail_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self._thumbnail_list)

        action_rotate_left = menu.addAction("↺ Nach links drehen")
        action_rotate_left.triggered.connect(lambda: self._rotate_selected(-90))
        
        action_rotate_right = menu.addAction("↻ Nach rechts drehen")
        action_rotate_right.triggered.connect(lambda: self._rotate_selected(90))
        
        menu.addSeparator()
        
        action_delete = menu.addAction("🗑 Löschen")
        action_delete.triggered.connect(self._delete_selected)
        
        action_extract = menu.addAction("📤 Extrahieren...")
        action_extract.triggered.connect(self._extract_selected)
        
        action_duplicate = menu.addAction("📋 Duplizieren")
        action_duplicate.triggered.connect(self._duplicate_selected)
        
        menu.addSeparator()
        
        action_goto = menu.addAction("Gehe zu Seite...")
        action_goto.triggered.connect(self._goto_page)
        
        menu.exec(self._thumbnail_list.mapToGlobal(position))
    
    def _get_selected_indices(self) -> List[int]:
        """Gibt die Original-Indizes der ausgewählten Seiten zurück."""
        indices = []
        for item in self._thumbnail_list.selectedItems():
            original_idx = item.data(Qt.ItemDataRole.UserRole)
            indices.append(original_idx)
        return indices
    
    def _rotate_selected(self, angle: int):
        """Dreht ausgewählte Seiten."""
        indices = self._get_selected_indices()
        if not indices:
            return
        
        for idx in indices:
            current = self._rotations.get(idx, 0)
            self._rotations[idx] = (current + angle) % 360
        
        self._load_thumbnails()
    
    def _delete_selected(self):
        """Löscht ausgewählte Seiten."""
        indices = self._get_selected_indices()
        if not indices:
            return
        
        # Mindestens eine Seite muss bleiben
        remaining = len(self._page_order) - len(self._deleted_pages) - len(indices)
        if remaining < 1:
            QMessageBox.warning(self, "Fehler", "Mindestens eine Seite muss erhalten bleiben!")
            return
        
        reply = QMessageBox.question(
            self, "Seiten löschen",
            f"{len(indices)} Seite(n) wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._deleted_pages.extend(indices)
            
            # Aus Reihenfolge entfernen
            self._page_order = [p for p in self._page_order if p not in indices]
            
            self._load_thumbnails()
            self._update_page_info()
    
    def _extract_selected(self):
        """Extrahiert ausgewählte Seiten in neue PDF."""
        indices = self._get_selected_indices()
        if not indices:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Seiten extrahieren", "",
            "PDF-Dateien (*.pdf)"
        )
        
        if not path:
            return
        
        try:
            new_doc = fitz.open()
            try:
                for idx in sorted(indices):
                    new_doc.insert_pdf(self._doc, from_page=idx, to_page=idx)

                new_doc.save(path)
            finally:
                new_doc.close()

            QMessageBox.information(
                self, "Extrahiert",
                f"{len(indices)} Seite(n) extrahiert nach:\n{path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
    
    def _duplicate_selected(self):
        """Dupliziert ausgewählte Seiten."""
        selected_items = self._thumbnail_list.selectedItems()
        if not selected_items:
            return
        
        # Duplikate nach der letzten ausgewählten Seite einfügen
        last_row = max(self._thumbnail_list.row(item) for item in selected_items)
        
        for item in selected_items:
            original_idx = item.data(Qt.ItemDataRole.UserRole)
            
            # In Reihenfolge einfügen (als Referenz auf gleiche Seite)
            insert_pos = last_row + 1
            self._page_order.insert(insert_pos, original_idx)
            last_row += 1
        
        self._load_thumbnails()
        self._update_page_info()
    
    def _goto_page(self):
        """Springt zu einer bestimmten Seite."""
        if self._doc is None:
            return
        
        page_num, ok = QInputDialog.getInt(
            self, "Gehe zu Seite",
            "Seitennummer:",
            1, 1, len(self._doc)
        )
        
        if ok:
            # Seite in Liste finden
            for i in range(self._thumbnail_list.count()):
                item = self._thumbnail_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == page_num - 1:
                    self._thumbnail_list.setCurrentItem(item)
                    self._thumbnail_list.scrollToItem(item)
                    break
    
    def _reset_changes(self):
        """Setzt alle Änderungen zurück."""
        if self._doc is None:
            return
        
        reply = QMessageBox.question(
            self, "Zurücksetzen",
            "Alle Änderungen verwerfen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._page_order = list(range(len(self._doc)))
            self._deleted_pages = []
            self._rotations = {}
            self._load_thumbnails()
            self._update_page_info()
    
    def _save(self):
        """Speichert Änderungen in Original-Datei."""
        if not self._pdf_path:
            return
        
        reply = QMessageBox.question(
            self, "Speichern",
            f"Original-Datei überschreiben?\n{self._pdf_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._save_to_file(self._pdf_path)
    
    def _save_as(self):
        """Speichert unter neuem Namen."""
        if self._doc is None:
            return
        
        default_name = ""
        if self._pdf_path:
            p = Path(self._pdf_path)
            default_name = f"{p.stem}_bearbeitet.pdf"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Speichern unter", default_name,
            "PDF-Dateien (*.pdf)"
        )
        
        if path:
            self._save_to_file(path)
    
    def _save_to_file(self, path: str):
        """Speichert die bearbeitete PDF."""
        try:
            new_doc = fitz.open()
            try:
                for page_idx in self._page_order:
                    if page_idx in self._deleted_pages:
                        continue

                    # Seite kopieren
                    new_doc.insert_pdf(self._doc, from_page=page_idx, to_page=page_idx)

                    # Rotation anwenden
                    rotation = self._rotations.get(page_idx, 0)
                    if rotation:
                        new_page = new_doc[-1]
                        new_page.set_rotation(rotation)

                # BUGSWEEP-34 (KRIT): in Temp-Datei schreiben statt direkt nach `path`. Bei In-Place-
                # Save ist `path` die Datei, die self._doc per fitz.open noch GEOEFFNET haelt — fitz
                # kann dann nicht zuverlaessig dorthin schreiben (Save schlaegt fehl/korrumpiert das
                # Original). tmp + atomarer Replace loest das.
                tmp = Path(str(path) + ".tmp")
                new_doc.save(str(tmp))
            finally:
                new_doc.close()

            # Bei In-Place-Save das offene Quell-Dokument schliessen (gibt das File-Handle frei),
            # dann atomar ersetzen. closeEvent toleriert self._doc == None.
            same = bool(self._pdf_path) and Path(path).resolve() == Path(self._pdf_path).resolve()
            if same and self._doc is not None:
                self._doc.close()
                self._doc = None
            tmp.replace(path)

            QMessageBox.information(
                self, "Gespeichert",
                f"PDF gespeichert:\n{path}"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
    
    def closeEvent(self, event):
        """Cleanup beim Schließen."""
        if self._doc is not None:
            self._doc.close()
        super().closeEvent(event)
