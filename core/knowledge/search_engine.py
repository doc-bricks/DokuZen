#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Search Engine (Knowledge Engine)
===================================================
Globale Suche über alle indizierten Dateien.
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from utils.logger import LoggerMixin
from .file_index import FileIndex, FileMetadata, FileCategory


class SearchField(Enum):
    """Durchsuchbare Felder."""
    NAME = "name"
    PATH = "path"
    EXTENSION = "extension"
    TAGS = "tags"
    PDF_TITLE = "pdf_title"
    PDF_AUTHOR = "pdf_author"
    ALL = "all"


class SortOrder(Enum):
    """Sortierreihenfolge."""
    RELEVANCE = "relevance"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    DATE_ASC = "date_asc"
    DATE_DESC = "date_desc"
    SIZE_ASC = "size_asc"
    SIZE_DESC = "size_desc"


@dataclass
class SearchResult:
    """Ein Suchergebnis."""
    metadata: FileMetadata
    score: float
    highlights: Dict[str, str] = field(default_factory=dict)
    match_fields: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary."""
        return {
            'path': self.metadata.path,
            'name': self.metadata.name,
            'score': self.score,
            'category': self.metadata.category.value,
            'size_bytes': self.metadata.size_bytes,
            'modified_at': self.metadata.modified_at.isoformat(),
            'highlights': self.highlights,
            'match_fields': self.match_fields,
            'metadata': self.metadata.to_dict(),
        }


@dataclass
class SearchQuery:
    """Strukturierte Suchanfrage."""
    text: str
    fields: List[SearchField] = field(default_factory=lambda: [SearchField.ALL])
    categories: List[FileCategory] = field(default_factory=list)
    extensions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    pdf_has_text: Optional[bool] = None
    limit: int = 50
    offset: int = 0
    sort_by: SortOrder = SortOrder.RELEVANCE


class SearchEngine(LoggerMixin):
    """
    Such-Engine für die Knowledge Engine.
    
    Features:
    - Volltextsuche über Dateinamen, Pfade, Tags
    - Gewichtetes Ranking
    - Filter nach Kategorie, Extension, Datum, Größe
    - Highlighting der Treffer
    - Fuzzy-Matching
    """
    
    # Gewichtung der Felder
    FIELD_WEIGHTS = {
        'name': 0.4,
        'path': 0.1,
        'extension': 0.05,
        'tags': 0.25,
        'pdf_title': 0.15,
        'pdf_author': 0.05,
    }
    
    def __init__(self, file_index: FileIndex):
        """
        Initialisiert die Search Engine.
        
        Args:
            file_index: FileIndex-Instanz
        """
        self._index = file_index
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Führt eine einfache Suche durch.
        
        Args:
            query: Suchbegriff
            **kwargs: Zusätzliche Filter (siehe SearchQuery)
            
        Returns:
            Liste von SearchResult
        """
        search_query = SearchQuery(
            text=query,
            limit=kwargs.get('limit', 50),
            offset=kwargs.get('offset', 0),
            sort_by=kwargs.get('sort_by', SortOrder.RELEVANCE),
        )
        
        # Optionale Filter
        if 'categories' in kwargs:
            search_query.categories = kwargs['categories']
        if 'extensions' in kwargs:
            search_query.extensions = kwargs['extensions']
        if 'tags' in kwargs:
            search_query.tags = kwargs['tags']
        if 'date_from' in kwargs:
            search_query.date_from = kwargs['date_from']
        if 'date_to' in kwargs:
            search_query.date_to = kwargs['date_to']
        
        return self.advanced_search(search_query)
    
    def advanced_search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Führt eine erweiterte Suche durch.
        
        Args:
            query: Strukturierte Suchanfrage
            
        Returns:
            Liste von SearchResult
        """
        # SQL-Query bauen
        sql_parts = ["SELECT * FROM files WHERE 1=1"]
        params = []
        
        # Text-Suche
        if query.text:
            text_conditions = []
            search_term = f"%{query.text.lower()}%"
            
            if SearchField.ALL in query.fields or SearchField.NAME in query.fields:
                text_conditions.append("lower(name) LIKE ?")
                params.append(search_term)
            
            if SearchField.ALL in query.fields or SearchField.PATH in query.fields:
                text_conditions.append("lower(path) LIKE ?")
                params.append(search_term)
            
            if SearchField.ALL in query.fields or SearchField.PDF_TITLE in query.fields:
                text_conditions.append("lower(pdf_title) LIKE ?")
                params.append(search_term)
            
            if SearchField.ALL in query.fields or SearchField.PDF_AUTHOR in query.fields:
                text_conditions.append("lower(pdf_author) LIKE ?")
                params.append(search_term)
            
            if text_conditions:
                sql_parts.append(f"AND ({' OR '.join(text_conditions)})")
        
        # Kategorie-Filter
        if query.categories:
            placeholders = ','.join(['?' for _ in query.categories])
            sql_parts.append(f"AND category IN ({placeholders})")
            params.extend([c.value for c in query.categories])
        
        # Extension-Filter
        if query.extensions:
            placeholders = ','.join(['?' for _ in query.extensions])
            sql_parts.append(f"AND extension IN ({placeholders})")
            params.extend([ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                          for ext in query.extensions])
        
        # Datum-Filter
        if query.date_from:
            sql_parts.append("AND modified_at >= ?")
            params.append(query.date_from.isoformat())
        
        if query.date_to:
            sql_parts.append("AND modified_at <= ?")
            params.append(query.date_to.isoformat())
        
        # Größe-Filter
        # BUGSWEEP-30 (MITTEL): is not None statt truthy — sonst wird der gültige Wert 0
        # verschluckt (max_size=0 = "nur 0-Byte-Dateien" griffe nie).
        if query.min_size is not None:
            sql_parts.append("AND size_bytes >= ?")
            params.append(query.min_size)

        if query.max_size is not None:
            sql_parts.append("AND size_bytes <= ?")
            params.append(query.max_size)
        
        # PDF-Filter
        if query.pdf_has_text is not None:
            sql_parts.append("AND pdf_has_text = ?")
            params.append(1 if query.pdf_has_text else 0)
        
        # Sortierung
        order_clause = self._get_order_clause(query.sort_by)
        sql_parts.append(order_clause)
        
        # Limit & Offset
        sql_parts.append("LIMIT ? OFFSET ?")
        params.extend([query.limit, query.offset])
        
        # Query ausführen
        sql = " ".join(sql_parts)
        
        try:
            with self._index._lock:  # BUGSWEEP-30: gemeinsame Sperre mit Watcher-Thread
                rows = self._index._conn.execute(sql, params).fetchall()
        except Exception as e:
            self.logger.error(f"Such-Fehler: {e}")
            return []
        
        # Ergebnisse verarbeiten
        results = []
        for row in rows:
            metadata = self._index._row_to_metadata(row)
            
            # Score berechnen
            score = self._calculate_score(metadata, query.text)
            
            # Highlights erstellen
            highlights = self._create_highlights(metadata, query.text)
            
            # Match-Felder bestimmen
            match_fields = self._get_match_fields(metadata, query.text)
            
            results.append(SearchResult(
                metadata=metadata,
                score=score,
                highlights=highlights,
                match_fields=match_fields
            ))
        
        # Tag-Suche (separat, da JOIN nötig)
        if query.tags or (SearchField.ALL in query.fields and query.text):
            results = self._add_tag_matches(results, query)
        
        # Nach Score sortieren falls Relevanz gewählt
        if query.sort_by == SortOrder.RELEVANCE:
            results.sort(key=lambda r: r.score, reverse=True)
        
        return results
    
    def _get_order_clause(self, sort_by: SortOrder) -> str:
        """Erstellt die ORDER BY Klausel."""
        order_map = {
            SortOrder.RELEVANCE: "ORDER BY modified_at DESC",  # Fallback
            SortOrder.NAME_ASC: "ORDER BY name ASC",
            SortOrder.NAME_DESC: "ORDER BY name DESC",
            SortOrder.DATE_ASC: "ORDER BY modified_at ASC",
            SortOrder.DATE_DESC: "ORDER BY modified_at DESC",
            SortOrder.SIZE_ASC: "ORDER BY size_bytes ASC",
            SortOrder.SIZE_DESC: "ORDER BY size_bytes DESC",
        }
        return order_map.get(sort_by, "ORDER BY modified_at DESC")
    
    def _calculate_score(self, metadata: FileMetadata, query_text: str) -> float:
        """Berechnet den Relevanz-Score."""
        if not query_text:
            return 1.0
        
        score = 0.0
        query_lower = query_text.lower()
        
        # Name-Match
        if query_lower in metadata.name.lower():
            # Exakter Match am Anfang = höchster Score
            if metadata.name.lower().startswith(query_lower):
                score += self.FIELD_WEIGHTS['name'] * 1.5
            else:
                score += self.FIELD_WEIGHTS['name']
        
        # Path-Match
        if query_lower in metadata.path.lower():
            score += self.FIELD_WEIGHTS['path']
        
        # Tag-Match
        for tag in metadata.tags:
            if query_lower in tag.lower():
                score += self.FIELD_WEIGHTS['tags']
                break
        
        # PDF-Metadaten
        if metadata.pdf_title and query_lower in metadata.pdf_title.lower():
            score += self.FIELD_WEIGHTS['pdf_title']
        
        if metadata.pdf_author and query_lower in metadata.pdf_author.lower():
            score += self.FIELD_WEIGHTS['pdf_author']
        
        return min(score, 1.0)  # Max 1.0
    
    def _create_highlights(self, metadata: FileMetadata, query_text: str) -> Dict[str, str]:
        """Erstellt Highlighting für Treffer."""
        if not query_text:
            return {}
        
        highlights = {}
        query_lower = query_text.lower()
        
        # Name highlighten
        if query_lower in metadata.name.lower():
            highlights['name'] = self._highlight_text(metadata.name, query_text)
        
        # Path highlighten (nur relevanten Teil)
        if query_lower in metadata.path.lower():
            # Zeige Ordner + Dateiname
            path = Path(metadata.path)
            folder = path.parent.name
            highlights['path'] = f".../{folder}/{path.name}"
        
        # PDF-Titel
        if metadata.pdf_title and query_lower in metadata.pdf_title.lower():
            highlights['pdf_title'] = self._highlight_text(metadata.pdf_title, query_text)
        
        return highlights
    
    def _highlight_text(self, text: str, query: str) -> str:
        """Fügt Highlight-Marker hinzu."""
        # Case-insensitive Ersetzung mit Originalschreibweise
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(lambda m: f"**{m.group()}**", text)
    
    def _get_match_fields(self, metadata: FileMetadata, query_text: str) -> List[str]:
        """Bestimmt in welchen Feldern der Treffer ist."""
        if not query_text:
            return []
        
        fields = []
        query_lower = query_text.lower()
        
        if query_lower in metadata.name.lower():
            fields.append('name')
        if query_lower in metadata.path.lower():
            fields.append('path')
        if metadata.pdf_title and query_lower in metadata.pdf_title.lower():
            fields.append('pdf_title')
        if metadata.pdf_author and query_lower in metadata.pdf_author.lower():
            fields.append('pdf_author')
        for tag in metadata.tags:
            if query_lower in tag.lower():
                fields.append('tags')
                break
        
        return fields
    
    def _add_tag_matches(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Fügt Tag-basierte Matches hinzu."""
        # Bereits gefundene Pfade
        found_paths = {r.metadata.path for r in results}
        
        if query.tags:
            # Suche nach spezifischen Tags
            tag_sql = """
                SELECT DISTINCT f.* FROM files f
                JOIN file_tags ft ON f.id = ft.file_id
                JOIN tags t ON ft.tag_id = t.id
                WHERE t.name IN ({})
            """.format(','.join(['?' for _ in query.tags]))

            with self._index._lock:  # BUGSWEEP-30
                rows = self._index._conn.execute(tag_sql, query.tags).fetchall()

            for row in rows:
                if row['path'] not in found_paths:
                    metadata = self._index._row_to_metadata(row)
                    results.append(SearchResult(
                        metadata=metadata,
                        score=self.FIELD_WEIGHTS['tags'],
                        match_fields=['tags']
                    ))

        elif query.text and SearchField.ALL in query.fields:
            # Freitext-Suche: Tag-Namen nach Suchbegriff durchsuchen
            tag_text_sql = """
                SELECT DISTINCT f.* FROM files f
                JOIN file_tags ft ON f.id = ft.file_id
                JOIN tags t ON ft.tag_id = t.id
                WHERE lower(t.name) LIKE ?
            """
            with self._index._lock:  # BUGSWEEP-30
                rows = self._index._conn.execute(
                    tag_text_sql, (f"%{query.text.lower()}%",)
                ).fetchall()

            for row in rows:
                if row['path'] not in found_paths:
                    metadata = self._index._row_to_metadata(row)
                    results.append(SearchResult(
                        metadata=metadata,
                        score=self.FIELD_WEIGHTS['tags'],
                        match_fields=['tags']
                    ))

        return results
    
    def suggest(self, partial: str, limit: int = 10) -> List[str]:
        """
        Gibt Vorschläge für Auto-Complete.
        
        Args:
            partial: Teilstring
            limit: Maximale Anzahl Vorschläge
            
        Returns:
            Liste von Vorschlägen
        """
        suggestions = set()
        search_term = f"%{partial.lower()}%"
        
        # Dateinamen
        with self._index._lock:  # BUGSWEEP-30
            rows = self._index._conn.execute("""
                SELECT DISTINCT name FROM files
                WHERE lower(name) LIKE ?
                LIMIT ?
            """, (search_term, limit)).fetchall()

        for row in rows:
            suggestions.add(row['name'])

        # Tags
        with self._index._lock:  # BUGSWEEP-30
            rows = self._index._conn.execute("""
                SELECT DISTINCT name FROM tags
                WHERE lower(name) LIKE ?
                LIMIT ?
            """, (search_term, limit)).fetchall()
        
        for row in rows:
            suggestions.add(f"tag:{row['name']}")
        
        return sorted(suggestions)[:limit]
    
    def search_recent(self, days: int = 7, limit: int = 20) -> List[SearchResult]:
        """Sucht kürzlich geänderte Dateien."""
        date_from = datetime.now() - timedelta(days=days)
        return self.search("", date_from=date_from, sort_by=SortOrder.DATE_DESC, limit=limit)
    
    def search_by_category(self, category: FileCategory, limit: int = 50) -> List[SearchResult]:
        """Sucht nach Kategorie."""
        return self.search("", categories=[category], limit=limit)
    
    def search_duplicates(self) -> Dict[str, List[SearchResult]]:
        """Findet Duplikate."""
        duplicates = self._index.find_duplicates()
        
        result = {}
        for hash_val, metadatas in duplicates.items():
            result[hash_val] = [
                SearchResult(metadata=m, score=1.0, match_fields=['hash'])
                for m in metadatas
            ]
        
        return result
