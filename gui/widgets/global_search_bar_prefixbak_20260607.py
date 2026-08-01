#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Global Search Widget
========================================
Globales Suchfeld mit Auto-Complete und Ergebnis-Popup.
"""

from typing import Optional, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QFrame, QCompleter,
    QStyledItemDelegate, QStyleOptionViewItem, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QStringListModel, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QIcon

from utils.logger import LoggerMixin


class SearchResultItem(QListWidgetItem):
    """Spezielles Item für Suchergebnisse."""
    
    def __init__(self, result: dict):
        super().__init__()
        
        self.result = result
        
        # Icon basierend auf Kategorie
        category = result.get('category', 'other')
        icon_map = {
            'document': '📄',
            'text': '📝',
            'code': '💻',
            'image': '🖼️',
            'database': '🗃️',
            'archive': '📦',
            'other': '📁',
        }
        icon = icon_map.get(category, '📁')
        
        # Text formatieren
        name = result.get('name', '')
        path = result.get('path', '')
        
        # Nur Ordnername anzeigen
        folder = Path(path).parent.name if path else ''
        
        self.setText(f"{icon} {name}")
        self.setToolTip(f"{path}\n\nKategorie: {category}")
        
        # Daten speichern
        self.setData(Qt.ItemDataRole.UserRole, result)


class SearchResultDelegate(QStyledItemDelegate):
    """Custom Delegate für Suchergebnis-Darstellung."""
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Zeichnet das Suchergebnis."""
        painter.save()
        
        # Hintergrund
        if option.state & option.state.State_Selected:
            painter.fillRect(option.rect, QColor(51, 153, 255, 100))
        elif option.state & option.state.State_MouseOver:
            painter.fillRect(option.rect, QColor(200, 200, 200, 50))
        
        # Icon/Emoji und Text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        
        # Text zeichnen
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(QFont("Segoe UI", 10))
        
        text_rect = option.rect.adjusted(10, 5, -10, -5)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, text)
        
        # Score-Indikator (falls vorhanden)
        result = index.data(Qt.ItemDataRole.UserRole)
        if result and 'score' in result:
            score = result['score']
            if score > 0.5:
                # Grüner Punkt für hohe Relevanz
                painter.setBrush(QColor(76, 175, 80))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(option.rect.right() - 20, option.rect.center().y() - 4, 8, 8)
        
        painter.restore()
    
    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """Gibt die bevorzugte Größe zurück."""
        return QSize(option.rect.width(), 36)


class SearchResultsPopup(QFrame):
    """Popup-Frame für Suchergebnisse."""
    
    result_selected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("  Suchergebnisse")
        header.setStyleSheet("background: #f5f5f5; padding: 8px; font-weight: bold;")
        layout.addWidget(header)
        
        # Ergebnis-Liste
        self._results_list = QListWidget()
        self._results_list.setItemDelegate(SearchResultDelegate())
        self._results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._results_list.itemClicked.connect(self._on_item_clicked)
        self._results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._results_list)
        
        # Footer
        self._footer = QLabel("  0 Ergebnisse")
        self._footer.setStyleSheet("background: #f5f5f5; padding: 5px; color: #666; font-size: 11px;")
        layout.addWidget(self._footer)
        
        self.setFixedWidth(400)
        self.setMaximumHeight(400)
    
    def set_results(self, results: List[dict]):
        """Setzt die Suchergebnisse."""
        self._results_list.clear()
        
        for result in results:
            item = SearchResultItem(result)
            self._results_list.addItem(item)
        
        count = len(results)
        self._footer.setText(f"  {count} Ergebnis{'se' if count != 1 else ''}")
        
        # Höhe anpassen
        item_height = 36
        header_footer = 60
        max_items = 8
        height = min(count, max_items) * item_height + header_footer
        self.setFixedHeight(max(100, height))
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Item angeklickt."""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.result_selected.emit(result)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Doppelklick - Datei öffnen."""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result and 'path' in result:
            import os
            os.startfile(result['path'])
        self.hide()


class GlobalSearchBar(QWidget, LoggerMixin):
    """
    Globales Suchfeld mit Auto-Complete und Ergebnis-Popup.
    
    Features:
    - Debounced Suche (wartet auf Eingabe-Ende)
    - Auto-Complete-Vorschläge
    - Ergebnis-Popup mit Kategorien
    - Tastatur-Navigation
    """
    
    # Signale
    search_triggered = Signal(str)
    result_selected = Signal(dict)
    
    def __init__(self, search_engine=None, parent=None):
        super().__init__(parent)
        
        self._search_engine = search_engine
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_search)
        
        self._popup: Optional[SearchResultsPopup] = None
        self._last_query = ""
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Erstellt die UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Suchfeld
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 In allen Dokumenten & Versionen suchen...")
        self._search_input.setMinimumWidth(300)
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self._on_return_pressed)
        
        # Style
        self._search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 20px;
                background: #f8f8f8;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                background: white;
            }
        """)
        
        layout.addWidget(self._search_input)
        
        # Such-Button (optional)
        btn_search = QPushButton("Suchen")
        btn_search.clicked.connect(self._on_return_pressed)
        btn_search.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 20px;
                background: #1a73e8;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1557b0;
            }
        """)
        layout.addWidget(btn_search)
        
        # Auto-Completer
        self._completer = QCompleter([])
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._search_input.setCompleter(self._completer)
    
    def set_search_engine(self, engine):
        """Setzt die Such-Engine."""
        self._search_engine = engine
    
    def _on_text_changed(self, text: str):
        """Wird bei Textänderung aufgerufen."""
        if len(text) < 2:
            self._hide_popup()
            return
        
        # Debounce: Warte 300ms nach letzter Eingabe
        self._debounce_timer.start(300)
        
        # Auto-Complete aktualisieren
        if self._search_engine:
            suggestions = self._search_engine.suggest(text, limit=10)
            model = QStringListModel(suggestions)
            self._completer.setModel(model)
    
    def _on_return_pressed(self):
        """Enter gedrückt - Sofortige Suche."""
        self._debounce_timer.stop()
        self._do_search()
        self.search_triggered.emit(self._search_input.text())
    
    def _do_search(self):
        """Führt die Suche durch."""
        query = self._search_input.text().strip()
        
        if len(query) < 2:
            return
        
        if query == self._last_query:
            return
        
        self._last_query = query
        
        if not self._search_engine:
            self.logger.warning("Keine Such-Engine konfiguriert")
            return
        
        try:
            results = self._search_engine.search(query, limit=20)
            
            # Zu dict konvertieren falls nötig
            result_dicts = []
            for r in results:
                if hasattr(r, 'to_dict'):
                    result_dicts.append(r.to_dict())
                elif isinstance(r, dict):
                    result_dicts.append(r)
            
            self._show_results(result_dicts)
            
        except Exception as e:
            self.logger.error(f"Suchfehler: {e}")
    
    def _show_results(self, results: List[dict]):
        """Zeigt Suchergebnisse im Popup."""
        if not results:
            self._hide_popup()
            return
        
        if not self._popup:
            self._popup = SearchResultsPopup()
            self._popup.result_selected.connect(self._on_result_selected)
        
        self._popup.set_results(results)
        
        # Position berechnen
        global_pos = self._search_input.mapToGlobal(self._search_input.rect().bottomLeft())
        self._popup.move(global_pos.x(), global_pos.y() + 5)
        self._popup.show()
    
    def _hide_popup(self):
        """Versteckt das Popup."""
        if self._popup:
            self._popup.hide()
    
    def _on_result_selected(self, result: dict):
        """Ergebnis ausgewählt."""
        self.result_selected.emit(result)
    
    def clear(self):
        """Leert das Suchfeld."""
        self._search_input.clear()
        self._hide_popup()
        self._last_query = ""
    
    def set_query(self, query: str):
        """Setzt den Suchtext."""
        self._search_input.setText(query)
    
    def focus(self):
        """Setzt den Fokus auf das Suchfeld."""
        self._search_input.setFocus()
        self._search_input.selectAll()
