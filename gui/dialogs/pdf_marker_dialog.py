#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Marker Dialog
====================================
Markiert PDF-Seiten für verschiedene Aktionen (Merge, Delete, Keep).
"""

from pathlib import Path
from typing import List, Optional, Dict, Set

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QSplitter, QWidget,
    QScrollArea, QFrame, QGridLayout, QCheckBox,
    QSpinBox, QComboBox, QLineEdit, QProgressBar
)
from PySide6.QtCore import Qt, QSize, Signal, QThread
from PySide6.QtGui import QPixmap, QImage, QColor, QIcon

from utils.logger import LoggerMixin, get_logger
from core.pdf.page_ranges import parse_page_range_notation

_logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PageThumbnail(QFrame):
    """Einzelne Seitenvorschau mit Markierung."""
    
    clicked = Signal(int)  # Seitennummer
    double_clicked = Signal(int)
    
    # Markierungsfarben
    MARKERS = {
        'none': QColor(255, 255, 255),
        'm': QColor(100, 200, 100),    # Merge (grün)
        'd': QColor(255, 100, 100),    # Delete (rot)
        'k': QColor(100, 150, 255),    # Keep (blau)
    }
    
    def __init__(self, page_num: int, pixmap: QPixmap = None, parent=None):
        super().__init__(parent)
        
        self.page_num = page_num
        self.marker = 'none'
        
        self.setFixedSize(120, 160)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Thumbnail
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setFixedSize(110, 130)
        self._image_label.setStyleSheet("background: white; border: 1px solid #ccc;")
        layout.addWidget(self._image_label)
        
        if pixmap:
            scaled = pixmap.scaled(108, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self._image_label.setPixmap(scaled)
        
        # Seitennummer
        self._page_label = QLabel(f"Seite {page_num + 1}")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._page_label)
        
        self._update_style()
    
    def set_marker(self, marker: str):
        """Setzt die Markierung."""
        self.marker = marker
        self._update_style()
    
    def _update_style(self):
        """Aktualisiert das Styling."""
        color = self.MARKERS.get(self.marker, self.MARKERS['none'])
        
        marker_text = {
            'none': '',
            'm': ' [M]',
            'd': ' [D]',
            'k': ' [K]'
        }
        
        self._page_label.setText(f"Seite {self.page_num + 1}{marker_text.get(self.marker, '')}")

        marker_description = {
            'none': 'nicht markiert',
            'm': 'als Auszug markiert',
            'd': 'zum Entfernen markiert',
            'k': 'zum Behalten markiert',
        }.get(self.marker, 'nicht markiert')
        page_description = f"Seite {self.page_num + 1}, {marker_description}"
        self.setAccessibleName(page_description)
        self.setAccessibleDescription(
            f"{page_description}. Mit Enter oder Leertaste für eine Aktion auswählen."
        )
        self.setToolTip(
            f"{page_description.capitalize()}. Mit Enter oder Leertaste auswählen."
        )
        
        if self.marker == 'none':
            self.setStyleSheet("")
        else:
            self.setStyleSheet(f"""
                PageThumbnail {{
                    background-color: {color.name()};
                    border: 2px solid {color.darker(130).name()};
                }}
            """)
    
    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.clicked.emit(self.page_num)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.page_num)
            event.accept()
            return
        super().keyPressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.page_num)


class ThumbnailLoader(QThread):
    """Lädt Thumbnails im Hintergrund."""
    
    thumbnail_ready = Signal(int, object)  # page_num, QPixmap
    finished_loading = Signal()
    
    def __init__(self, pdf_path: str, dpi: int = 72):
        super().__init__()
        self.pdf_path = pdf_path
        self.dpi = dpi
        self._cancelled = False
    
    def run(self):
        if not PYMUPDF_AVAILABLE:
            return
        
        try:
            doc = fitz.open(self.pdf_path)
            try:
                for page_num in range(len(doc)):
                    if self._cancelled:
                        break

                    page = doc[page_num]
                    mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                    pix = page.get_pixmap(matrix=mat)

                    # BUGSWEEP-34: KEIN QPixmap im Worker-Thread erzeugen (Qt: Pixmaps nur im
                    # GUI-Thread). Zudem referenziert QImage den pix.samples-Puffer, der in der
                    # nächsten Iteration freigegeben wird -> .copy() macht eine eigene Kopie.
                    # QPixmap.fromImage passiert im GUI-Slot _on_thumbnail_ready.
                    img = QImage(pix.samples, pix.width, pix.height,
                                pix.stride, QImage.Format.Format_RGB888)

                    self.thumbnail_ready.emit(page_num, img.copy())
            finally:
                doc.close()

        except Exception as e:
            _logger.warning(f"Thumbnail-Laden fehlgeschlagen: {e}")

        self.finished_loading.emit()
    
    def cancel(self):
        self._cancelled = True


class PDFMarkerDialog(QDialog, LoggerMixin):
    """
    Dialog zum Markieren von PDF-Seiten.
    
    Features:
    - Thumbnails aller Seiten
    - Markierungen: M=Merge, D=Delete, K=Keep
    - Tastaturkürzel
    - Aktionen basierend auf Markierungen
    """
    
    def __init__(self, parent=None, pdf_path: str = None):
        super().__init__(parent)
        
        self._pdf_path: Optional[str] = None
        self._page_count = 0
        self._thumbnails: List[PageThumbnail] = []
        self._selected_pages: Set[int] = set()
        self._loader: Optional[ThumbnailLoader] = None
        
        self._setup_ui()
        
        if pdf_path:
            self._load_pdf(pdf_path)
    
    def _setup_ui(self):
        """Erstellt die UI."""
        self.setWindowTitle("PDF-Marker")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        btn_open = QPushButton("PDF öffnen...")
        btn_open.clicked.connect(self._on_open)
        toolbar_layout.addWidget(btn_open)
        
        toolbar_layout.addWidget(QLabel("  Aktuelle Datei:"))
        self._file_label = QLabel("Keine Datei geladen")
        self._file_label.setStyleSheet("font-style: italic;")
        toolbar_layout.addWidget(self._file_label)
        
        toolbar_layout.addStretch()
        
        self._progress = QProgressBar()
        self._progress.setFixedWidth(150)
        self._progress.setVisible(False)
        toolbar_layout.addWidget(self._progress)
        
        layout.addLayout(toolbar_layout)
        
        # Hauptbereich
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Links: Thumbnail-Grid
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll-Bereich für Thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._thumbnail_container = QWidget()
        self._thumbnail_layout = QGridLayout(self._thumbnail_container)
        self._thumbnail_layout.setSpacing(8)
        scroll.setWidget(self._thumbnail_container)
        
        left_layout.addWidget(scroll)
        
        # Auswahl-Info
        self._selection_label = QLabel("Keine Seiten ausgewählt")
        left_layout.addWidget(self._selection_label)
        
        splitter.addWidget(left_widget)
        
        # Rechts: Aktionen
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Markierungen
        marker_group = QGroupBox("Markierungen (Tastenkürzel)")
        marker_layout = QVBoxLayout(marker_group)
        
        btn_mark_m = QPushButton("M - Merge (Zusammenführen)")
        btn_mark_m.setStyleSheet("background-color: #64c864;")
        btn_mark_m.clicked.connect(lambda: self._set_marker('m'))
        marker_layout.addWidget(btn_mark_m)
        
        btn_mark_d = QPushButton("D - Delete (Löschen)")
        btn_mark_d.setStyleSheet("background-color: #ff6464;")
        btn_mark_d.clicked.connect(lambda: self._set_marker('d'))
        marker_layout.addWidget(btn_mark_d)
        
        btn_mark_k = QPushButton("K - Keep (Behalten)")
        btn_mark_k.setStyleSheet("background-color: #6496ff;")
        btn_mark_k.clicked.connect(lambda: self._set_marker('k'))
        marker_layout.addWidget(btn_mark_k)
        
        btn_clear = QPushButton("Markierung entfernen")
        btn_clear.clicked.connect(lambda: self._set_marker('none'))
        marker_layout.addWidget(btn_clear)
        
        right_layout.addWidget(marker_group)
        
        # Auswahl
        select_group = QGroupBox("Auswahl")
        select_layout = QVBoxLayout(select_group)
        
        btn_select_all = QPushButton("Alle auswählen")
        btn_select_all.clicked.connect(self._select_all)
        select_layout.addWidget(btn_select_all)
        
        btn_select_none = QPushButton("Auswahl aufheben")
        btn_select_none.clicked.connect(self._select_none)
        select_layout.addWidget(btn_select_none)
        
        btn_invert = QPushButton("Auswahl umkehren")
        btn_invert.clicked.connect(self._invert_selection)
        select_layout.addWidget(btn_invert)
        
        # Bereich auswählen
        range_layout = QHBoxLayout()
        self._range_from = QSpinBox()
        self._range_from.setMinimum(1)
        range_layout.addWidget(QLabel("Von:"))
        range_layout.addWidget(self._range_from)
        
        self._range_to = QSpinBox()
        self._range_to.setMinimum(1)
        range_layout.addWidget(QLabel("Bis:"))
        range_layout.addWidget(self._range_to)
        
        select_layout.addLayout(range_layout)
        
        btn_select_range = QPushButton("Bereich auswählen")
        btn_select_range.clicked.connect(self._select_range)
        select_layout.addWidget(btn_select_range)

        notation_layout = QVBoxLayout()
        notation_layout.addWidget(QLabel("Seiten-Notation:"))

        notation_input_layout = QHBoxLayout()
        self._page_notation = QLineEdit()
        self._page_notation.setPlaceholderText("z. B. 1-5, 7, 9-12")
        self._page_notation.setToolTip(
            "Wendet Seiten per Textnotation auf eine Markierungsart an."
        )
        self._page_notation.setAccessibleName("Seiten-Notation")
        self._page_notation.setAccessibleDescription(
            "Eingabefeld für Seitenangaben wie 1-5, 7 oder 9-12."
        )
        notation_input_layout.addWidget(self._page_notation)

        self._notation_marker = QComboBox()
        self._notation_marker.addItem("Auszug (M)", "m")
        self._notation_marker.addItem("Entfernen (D)", "d")
        self._notation_marker.addItem("Behalten (K)", "k")
        self._notation_marker.setToolTip(
            "Legt fest, ob die Seiten als Auszug, Entfernen oder Behalten markiert werden."
        )
        self._notation_marker.setAccessibleName("Markierungsart für Seiten-Notation")
        self._notation_marker.setAccessibleDescription(
            "Wählt die Zielmarkierung für die eingegebene Seiten-Notation."
        )
        notation_input_layout.addWidget(self._notation_marker)
        notation_layout.addLayout(notation_input_layout)

        btn_apply_notation = QPushButton("Notation anwenden")
        btn_apply_notation.setToolTip(
            "Überträgt die Seiten-Notation auf die gewählte Markierungsart."
        )
        btn_apply_notation.setAccessibleName("Seiten-Notation anwenden")
        btn_apply_notation.setAccessibleDescription(
            "Markiert die eingegebenen Seiten als Auszug, Entfernen oder Behalten."
        )
        btn_apply_notation.clicked.connect(self._apply_page_notation)
        notation_layout.addWidget(btn_apply_notation)

        select_layout.addLayout(notation_layout)
        
        right_layout.addWidget(select_group)
        
        # Aktionen
        action_group = QGroupBox("Aktionen ausführen")
        action_layout = QVBoxLayout(action_group)
        
        btn_extract_marked = QPushButton("Markierte (M) extrahieren...")
        btn_extract_marked.clicked.connect(self._extract_marked)
        action_layout.addWidget(btn_extract_marked)
        
        btn_delete_marked = QPushButton("Markierte (D) löschen...")
        btn_delete_marked.clicked.connect(self._delete_marked)
        action_layout.addWidget(btn_delete_marked)
        
        btn_keep_marked = QPushButton("Nur (K) behalten...")
        btn_keep_marked.clicked.connect(self._keep_marked)
        action_layout.addWidget(btn_keep_marked)

        btn_split_doc = QPushButton("Dokument teilen (Split)...")
        btn_split_doc.setToolTip("Teilt das Dokument an der gewählten Seite in zwei neue Branch-Dokumente.")
        btn_split_doc.setAccessibleName("Dokument teilen (Split)")
        btn_split_doc.clicked.connect(self._split_at_selected_page)
        action_layout.addWidget(btn_split_doc)

        marker_file_layout = QHBoxLayout()
        btn_save_markers = QPushButton("Markierungen speichern...")
        btn_save_markers.setToolTip("Speichert Seiten-Markierungen in einer .dokuzen_marker Datei.")
        btn_save_markers.clicked.connect(self._save_markers_file)
        marker_file_layout.addWidget(btn_save_markers)

        btn_load_markers = QPushButton("Markierungen laden...")
        btn_load_markers.setToolTip("Lädt Seiten-Markierungen aus einer .dokuzen_marker Datei.")
        btn_load_markers.clicked.connect(self._load_markers_file)
        marker_file_layout.addWidget(btn_load_markers)
        action_layout.addLayout(marker_file_layout)

        self._add_page_numbers = QCheckBox("Seitenzahlen einfügen")
        self._add_page_numbers.setToolTip(
            "Fügt den exportierten PDFs unten mittig 'Seite X / Y' hinzu."
        )
        action_layout.addWidget(self._add_page_numbers)

        crop_layout = QHBoxLayout()
        self._crop_pages = QCheckBox("Seitenränder beschneiden")
        self._crop_pages.setToolTip(
            "Beschneidet exportierte Seiten gleichmäßig an allen Rändern."
        )
        crop_layout.addWidget(self._crop_pages)

        crop_layout.addWidget(QLabel("Rand:"))
        self._crop_margin_mm = QSpinBox()
        self._crop_margin_mm.setRange(1, 25)
        self._crop_margin_mm.setValue(5)
        self._crop_margin_mm.setSuffix(" mm")
        self._crop_margin_mm.setToolTip(
            "Legt den Beschnittrand für exportierte Seiten in Millimetern fest."
        )
        self._crop_margin_mm.setAccessibleName("Beschnittrand")
        self._crop_margin_mm.setAccessibleDescription(
            "Bestimmt den gleichmäßigen Beschnittrand der exportierten Seiten in Millimetern."
        )
        self._crop_margin_mm.setEnabled(False)
        self._crop_pages.toggled.connect(self._crop_margin_mm.setEnabled)
        crop_layout.addWidget(self._crop_margin_mm)
        crop_layout.addStretch()
        action_layout.addLayout(crop_layout)

        right_layout.addWidget(action_group)
        
        # Statistik
        stats_group = QGroupBox("Statistik")
        stats_layout = QVBoxLayout(stats_group)
        
        self._stats_label = QLabel("Keine Datei geladen")
        stats_layout.addWidget(self._stats_label)
        
        right_layout.addWidget(stats_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
        # Splitter-Größen
        splitter.setSizes([700, 300])
        
        # Buttons unten
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def keyPressEvent(self, event):
        """Tastaturkürzel."""
        key = event.key()
        
        if key == Qt.Key.Key_M:
            self._set_marker('m')
        elif key == Qt.Key.Key_D:
            self._set_marker('d')
        elif key == Qt.Key.Key_K:
            self._set_marker('k')
        elif key == Qt.Key.Key_Escape:
            self._set_marker('none')
        elif key == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._select_all()
        else:
            super().keyPressEvent(event)
    
    def _on_open(self):
        """Öffnet ein PDF."""
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF öffnen", "",
            "PDF-Dateien (*.pdf)"
        )
        if path:
            self._load_pdf(path)
    
    def _load_pdf(self, path: str):
        """Lädt ein PDF."""
        if not PYMUPDF_AVAILABLE:
            QMessageBox.critical(self, "Fehler", "PyMuPDF nicht verfügbar")
            return
        
        # Vorherigen Loader stoppen
        if self._loader and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait()
        
        self._pdf_path = path
        self._file_label.setText(Path(path).name)
        
        # Thumbnails löschen
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails.clear()
        self._selected_pages.clear()
        
        # Seitenanzahl ermitteln
        doc = None
        try:
            doc = fitz.open(path)
            self._page_count = len(doc)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return
        finally:
            if doc is not None:
                doc.close()

        # Leere Thumbnails erstellen
        cols = 5
        for i in range(self._page_count):
            thumb = PageThumbnail(i)
            thumb.clicked.connect(self._on_thumbnail_clicked)
            thumb.double_clicked.connect(self._on_thumbnail_double_clicked)
            
            row = i // cols
            col = i % cols
            self._thumbnail_layout.addWidget(thumb, row, col)
            self._thumbnails.append(thumb)
        
        # Spinbox-Bereiche setzen
        self._range_from.setMaximum(self._page_count)
        self._range_to.setMaximum(self._page_count)
        self._range_to.setValue(self._page_count)
        
        # Thumbnails im Hintergrund laden
        self._progress.setVisible(True)
        self._progress.setRange(0, self._page_count)
        self._progress.setValue(0)
        
        self._loader = ThumbnailLoader(path)
        self._loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._loader.finished_loading.connect(self._on_loading_finished)
        self._loader.start()
        
        self._update_stats()
    
    def _on_thumbnail_ready(self, page_num: int, image):
        """Thumbnail wurde geladen."""
        if page_num < len(self._thumbnails):
            # BUGSWEEP-34: QPixmap erst hier im GUI-Thread aus dem (kopierten) QImage erzeugen.
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(108, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self._thumbnails[page_num]._image_label.setPixmap(scaled)
            self._progress.setValue(page_num + 1)
    
    def _on_loading_finished(self):
        """Laden abgeschlossen."""
        self._progress.setVisible(False)
    
    def _on_thumbnail_clicked(self, page_num: int):
        """Thumbnail wurde angeklickt."""
        if page_num in self._selected_pages:
            self._selected_pages.remove(page_num)
            self._thumbnails[page_num].setStyleSheet("")
        else:
            self._selected_pages.add(page_num)
            thumb = self._thumbnails[page_num]
            if thumb.marker == 'none':
                thumb.setStyleSheet("border: 3px solid #333;")
        
        self._update_selection_label()
    
    def _on_thumbnail_double_clicked(self, page_num: int):
        """Doppelklick wechselt Markierung."""
        markers = ['none', 'm', 'd', 'k']
        current = self._thumbnails[page_num].marker
        next_idx = (markers.index(current) + 1) % len(markers)
        self._thumbnails[page_num].set_marker(markers[next_idx])
        self._update_stats()
    
    def _set_marker(self, marker: str):
        """Setzt Markierung für ausgewählte Seiten."""
        for page_num in self._selected_pages:
            self._thumbnails[page_num].set_marker(marker)
        self._update_stats()
    
    def _select_all(self):
        """Wählt alle Seiten aus."""
        self._selected_pages = set(range(self._page_count))
        for thumb in self._thumbnails:
            if thumb.marker == 'none':
                thumb.setStyleSheet("border: 3px solid #333;")
        self._update_selection_label()
    
    def _select_none(self):
        """Hebt Auswahl auf."""
        self._selected_pages.clear()
        for thumb in self._thumbnails:
            thumb._update_style()
        self._update_selection_label()
    
    def _invert_selection(self):
        """Kehrt Auswahl um."""
        all_pages = set(range(self._page_count))
        self._selected_pages = all_pages - self._selected_pages
        
        for i, thumb in enumerate(self._thumbnails):
            if i in self._selected_pages and thumb.marker == 'none':
                thumb.setStyleSheet("border: 3px solid #333;")
            else:
                thumb._update_style()
        
        self._update_selection_label()
    
    def _select_range(self):
        """Wählt einen Bereich aus."""
        from_page = self._range_from.value() - 1
        to_page = self._range_to.value()
        
        for i in range(from_page, min(to_page, self._page_count)):
            self._selected_pages.add(i)
            if self._thumbnails[i].marker == 'none':
                self._thumbnails[i].setStyleSheet("border: 3px solid #333;")
        
        self._update_selection_label()

    def _apply_page_notation(self):
        """Wendet eine Textnotation auf eine Markierungsart an."""
        if self._page_count <= 0 or not self._thumbnails:
            QMessageBox.warning(self, "Keine Datei", "Bitte zuerst ein PDF laden.")
            return

        notation = self._page_notation.text().strip()
        pages = parse_page_range_notation(notation, page_count=self._page_count)
        if not pages:
            QMessageBox.warning(
                self,
                "Ungültige Seitenangabe",
                "Bitte eine gültige Seiten-Notation wie '1-5, 7, 9-12' eingeben.",
            )
            return

        marker = self._notation_marker.currentData()
        self._select_none()
        self._selected_pages = {page - 1 for page in pages}
        self._set_marker(marker)
        self._update_selection_label()

    def _update_selection_label(self):
        """Aktualisiert Auswahl-Info."""
        count = len(self._selected_pages)
        if count == 0:
            self._selection_label.setText("Keine Seiten ausgewählt")
        elif count == 1:
            self._selection_label.setText("1 Seite ausgewählt")
        else:
            self._selection_label.setText(f"{count} Seiten ausgewählt")
    
    def _update_stats(self):
        """Aktualisiert Statistik."""
        if not self._thumbnails:
            self._stats_label.setText("Keine Datei geladen")
            return
        
        m_count = sum(1 for t in self._thumbnails if t.marker == 'm')
        d_count = sum(1 for t in self._thumbnails if t.marker == 'd')
        k_count = sum(1 for t in self._thumbnails if t.marker == 'k')
        
        self._stats_label.setText(
            f"<b>Gesamt:</b> {self._page_count} Seiten<br>"
            f"<b style='color: green;'>Merge (M):</b> {m_count}<br>"
            f"<b style='color: red;'>Delete (D):</b> {d_count}<br>"
            f"<b style='color: blue;'>Keep (K):</b> {k_count}"
        )
    
    def _get_pages_by_marker(self, marker: str) -> List[int]:
        """Gibt Seitennummern mit bestimmter Markierung zurück."""
        return [i for i, t in enumerate(self._thumbnails) if t.marker == marker]
    
    def _extract_marked(self):
        """Extrahiert markierte Seiten (M)."""
        pages = self._get_pages_by_marker('m')
        
        if not pages:
            QMessageBox.warning(self, "Keine Seiten", "Keine Seiten mit (M) markiert.")
            return
        
        self._extract_pages(pages, "Markierte Seiten extrahieren")
    
    def _delete_marked(self):
        """Löscht markierte Seiten (D)."""
        pages = self._get_pages_by_marker('d')
        
        if not pages:
            QMessageBox.warning(self, "Keine Seiten", "Keine Seiten mit (D) markiert.")
            return
        
        # Alle außer D behalten
        keep_pages = [i for i in range(self._page_count) if i not in pages]
        self._extract_pages(keep_pages, "Seiten löschen")
    
    def _keep_marked(self):
        """Behält nur markierte Seiten (K)."""
        pages = self._get_pages_by_marker('k')
        
        if not pages:
            QMessageBox.warning(self, "Keine Seiten", "Keine Seiten mit (K) markiert.")
            return
        
        self._extract_pages(pages, "Nur markierte behalten")
    
    def _split_at_selected_page(self):
        """Teilt das Dokument an der ausgewählten Seitennummer in zwei Branch-Dokumente."""
        if not self._pdf_path or self._page_count <= 1:
            QMessageBox.warning(self, "Teilen nicht möglich", "Es muss ein Dokument mit mindestens 2 Seiten geladen sein.")
            return

        if self._selected_pages:
            split_page = max(self._selected_pages) + 1
        else:
            split_page = self._range_from.value()

        if split_page >= self._page_count:
            split_page = self._page_count - 1
        if split_page < 1:
            split_page = 1

        from core.pdf.branching import split_at_page
        try:
            path1, path2 = split_at_page(self._pdf_path, split_page)
            QMessageBox.information(
                self,
                "Branch-Split erfolgreich",
                f"Dokument an Seite {split_page} geteilt:\n\n"
                f"Teil 1 (S. 1-{split_page}):\n{path1}\n\n"
                f"Teil 2 (S. {split_page + 1}-{self._page_count}):\n{path2}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Split-Fehler", str(e))

    def _save_markers_file(self):
        """Speichert Markierungen in einer .dokuzen_marker Datei."""
        if not self._pdf_path or not self._thumbnails:
            QMessageBox.warning(self, "Keine Markierungen", "Bitte zuerst ein Dokument laden.")
            return

        markers = {i: t.marker for i, t in enumerate(self._thumbnails) if t.marker != 'none'}
        if not markers:
            QMessageBox.information(self, "Keine Markierungen", "Keine Seiten zum Speichern markiert (M/D/K).")
            return

        default_name = f"{Path(self._pdf_path).name}.dokuzen_marker"
        path, _ = QFileDialog.getSaveFileName(
            self, "Markierungen speichern", default_name,
            "DokuZen Marker (*.dokuzen_marker);;Alle Dateien (*.*)"
        )
        if path:
            from core.pdf.branching import save_marker_file
            try:
                save_marker_file(self._pdf_path, markers, path)
                QMessageBox.information(self, "Erfolg", f"Markierungen gespeichert:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", str(e))

    def _load_markers_file(self):
        """Lädt Markierungen aus einer .dokuzen_marker Datei."""
        if not self._pdf_path or not self._thumbnails:
            QMessageBox.warning(self, "Kein Dokument", "Bitte zuerst ein PDF laden.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Markierungen laden", "",
            "DokuZen Marker (*.dokuzen_marker);;Alle Dateien (*.*)"
        )
        if path:
            from core.pdf.branching import load_marker_file
            try:
                markers = load_marker_file(path)
                for page_num, marker in markers.items():
                    if 0 <= page_num < len(self._thumbnails):
                        self._thumbnails[page_num].set_marker(marker)
                self._update_stats()
                QMessageBox.information(self, "Erfolg", f"Markierungen geladen aus:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", str(e))

    def _extract_pages(self, pages: List[int], title: str):
        """Extrahiert bestimmte Seiten."""
        if not pages:
            QMessageBox.warning(
                self,
                "Keine Exportseiten",
                "Es muss mindestens eine Seite im Export verbleiben.",
            )
            return

        from core.pdf.branching import generate_branch_path
        default_branch = generate_branch_path(self._pdf_path, "branch_auszug") if self._pdf_path else ""

        path, _ = QFileDialog.getSaveFileName(
            self, title, default_branch,
            "PDF-Dateien (*.pdf)"
        )
        
        if not path:
            return
        
        doc = None
        new_doc = None
        try:
            from core.pdf.crop import crop_document_margins
            from core.pdf.page_numbers import add_page_numbers_to_document

            doc = fitz.open(self._pdf_path)
            new_doc = fitz.open()
            for page_num in sorted(pages):
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            if self._crop_pages.isChecked():
                if not crop_document_margins(new_doc, margin_mm=float(self._crop_margin_mm.value())):
                    raise RuntimeError("Seitenränder konnten nicht beschnitten werden")

            if self._add_page_numbers.isChecked():
                if not add_page_numbers_to_document(new_doc):
                    raise RuntimeError("Seitenzahlen konnten nicht eingefügt werden")

            new_doc.save(path)

            QMessageBox.information(
                self, "Erfolg",
                f"{len(pages)} Seiten gespeichert:\n{path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
        finally:
            if new_doc is not None:
                new_doc.close()
            if doc is not None:
                doc.close()
    
    def closeEvent(self, event):
        """Cleanup beim Schließen."""
        if self._loader and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait()
        super().closeEvent(event)
