#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - File Index (Knowledge Engine)
=================================================
Hash-basierte Datei-Identifikation und Metadaten-Index.
"""

import sqlite3
import hashlib
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class FileCategory(Enum):
    """Dateikategorien."""
    DOCUMENT = "document"      # PDF, DOCX, ODT
    TEXT = "text"              # TXT, MD, LOG
    CODE = "code"              # PY, JS, HTML, CSS
    IMAGE = "image"            # PNG, JPG, GIF
    DATABASE = "database"      # DB, SQLITE
    ARCHIVE = "archive"        # ZIP, RAR, 7Z
    OTHER = "other"


@dataclass
class FileMetadata:
    """Metadaten einer Datei."""
    path: str
    name: str
    extension: str
    size_bytes: int
    hash_sha256: str
    category: FileCategory
    mime_type: str
    created_at: datetime
    modified_at: datetime
    indexed_at: datetime
    
    # PDF-spezifisch
    pdf_pages: Optional[int] = None
    pdf_has_text: Optional[bool] = None
    pdf_is_encrypted: Optional[bool] = None
    pdf_title: Optional[str] = None
    pdf_author: Optional[str] = None
    
    # Tags & Collections
    tags: List[str] = field(default_factory=list)
    collection_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary."""
        return {
            'path': self.path,
            'name': self.name,
            'extension': self.extension,
            'size_bytes': self.size_bytes,
            'hash_sha256': self.hash_sha256,
            'category': self.category.value,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'indexed_at': self.indexed_at.isoformat(),
            'pdf_pages': self.pdf_pages,
            'pdf_has_text': self.pdf_has_text,
            'pdf_is_encrypted': self.pdf_is_encrypted,
            'pdf_title': self.pdf_title,
            'pdf_author': self.pdf_author,
            'tags': self.tags,
            'collection_id': self.collection_id,
        }


class FileIndex(LoggerMixin):
    """
    Hash-basierter Datei-Index mit SQLite-Backend.
    
    Features:
    - SHA256-Hash für eindeutige Identifikation
    - Automatische Kategorisierung
    - PDF-Metadaten-Extraktion
    - Duplikat-Erkennung
    - Versionsverfolgung
    """
    
    # Dateityp-Mappings
    CATEGORY_MAP = {
        # Documents
        '.pdf': FileCategory.DOCUMENT,
        '.docx': FileCategory.DOCUMENT,
        '.doc': FileCategory.DOCUMENT,
        '.odt': FileCategory.DOCUMENT,
        '.rtf': FileCategory.DOCUMENT,
        '.epub': FileCategory.DOCUMENT,
        
        # Text
        '.txt': FileCategory.TEXT,
        '.md': FileCategory.TEXT,
        '.log': FileCategory.TEXT,
        '.csv': FileCategory.TEXT,
        '.json': FileCategory.TEXT,
        '.xml': FileCategory.TEXT,
        '.yaml': FileCategory.TEXT,
        '.yml': FileCategory.TEXT,
        
        # Code
        '.py': FileCategory.CODE,
        '.js': FileCategory.CODE,
        '.ts': FileCategory.CODE,
        '.html': FileCategory.CODE,
        '.css': FileCategory.CODE,
        '.java': FileCategory.CODE,
        '.cpp': FileCategory.CODE,
        '.c': FileCategory.CODE,
        '.h': FileCategory.CODE,
        '.cs': FileCategory.CODE,
        '.go': FileCategory.CODE,
        '.rs': FileCategory.CODE,
        '.sql': FileCategory.CODE,
        '.sh': FileCategory.CODE,
        '.bat': FileCategory.CODE,
        '.ps1': FileCategory.CODE,
        
        # Images
        '.png': FileCategory.IMAGE,
        '.jpg': FileCategory.IMAGE,
        '.jpeg': FileCategory.IMAGE,
        '.gif': FileCategory.IMAGE,
        '.bmp': FileCategory.IMAGE,
        '.webp': FileCategory.IMAGE,
        '.svg': FileCategory.IMAGE,
        '.ico': FileCategory.IMAGE,
        
        # Database
        '.db': FileCategory.DATABASE,
        '.sqlite': FileCategory.DATABASE,
        '.sqlite3': FileCategory.DATABASE,
        
        # Archive
        '.zip': FileCategory.ARCHIVE,
        '.rar': FileCategory.ARCHIVE,
        '.7z': FileCategory.ARCHIVE,
        '.tar': FileCategory.ARCHIVE,
        '.gz': FileCategory.ARCHIVE,
    }
    
    MIME_MAP = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.py': 'text/x-python',
        '.zip': 'application/zip',
    }
    
    def __init__(self, db_path: str = None):
        """
        Initialisiert den FileIndex.
        
        Args:
            db_path: Pfad zur SQLite-Datenbank (None = :memory:)
        """
        self._db_path = db_path or ":memory:"
        self._conn: Optional[sqlite3.Connection] = None
        # BUGSWEEP-30 (KRITISCH, sqlite-Threading): Der KnowledgeWatcher ruft index_file() aus
        # einem Daemon-Thread ("FileWatcher-Processor"), die SearchEngine liest _conn aus dem
        # GUI-Thread. Eine sqlite3-Connection ist standardmaessig an ihren Erzeuger-Thread
        # gebunden (check_same_thread=True) -> jeder Watcher-Index-Aufruf warf ProgrammingError,
        # vom bare-except in index_file verschluckt -> Auto-Indizierung lief STILL nie. Fix:
        # check_same_thread=False (Bindung loesen) + RLock (Serialisierung; ohne Lock waere die
        # gleichzeitige Nutzung einer Connection aus zwei Threads ein Race statt eines Fehlers).
        # RLock ist reentrant -> verschachtelte Aufrufe (find_duplicates->get_by_hash,
        # index_file->_save_version, get_file->_row_to_metadata) sind unproblematisch.
        # SHUTDOWN-REIHENFOLGE: Watcher.stop() MUSS vor FileIndex.close() laufen, sonst greift
        # ein noch laufender Watcher-Zugriff auf _conn=None zu.
        self._lock = threading.RLock()
        self._init_database()

    def _init_database(self):
        """Initialisiert die Datenbank."""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        # Tabellen erstellen
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                extension TEXT,
                size_bytes INTEGER,
                hash_sha256 TEXT,
                category TEXT,
                mime_type TEXT,
                created_at TEXT,
                modified_at TEXT,
                indexed_at TEXT,
                pdf_pages INTEGER,
                pdf_has_text INTEGER,
                pdf_is_encrypted INTEGER,
                pdf_title TEXT,
                pdf_author TEXT,
                collection_id INTEGER,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            );
            
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (file_id, tag_id),
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                hash_sha256 TEXT,
                size_bytes INTEGER,
                modified_at TEXT,
                version_number INTEGER,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash_sha256);
            CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
            CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
            CREATE INDEX IF NOT EXISTS idx_versions_file ON versions(file_id);
        """)
        self._conn.commit()
    
    def calculate_hash(self, file_path: str, chunk_size: int = 65536) -> str:
        """Berechnet SHA256-Hash einer Datei."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Hash-Fehler für {file_path}: {e}")
            return ""
    
    def _get_category(self, extension: str) -> FileCategory:
        """Bestimmt die Kategorie anhand der Dateiendung."""
        return self.CATEGORY_MAP.get(extension.lower(), FileCategory.OTHER)
    
    def _get_mime(self, extension: str) -> str:
        """Bestimmt den MIME-Typ anhand der Dateiendung."""
        return self.MIME_MAP.get(extension.lower(), 'application/octet-stream')
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrahiert PDF-spezifische Metadaten."""
        metadata = {
            'pdf_pages': None,
            'pdf_has_text': None,
            'pdf_is_encrypted': None,
            'pdf_title': None,
            'pdf_author': None,
        }
        
        if not PYMUPDF_AVAILABLE:
            return metadata
        
        doc = None
        try:
            doc = fitz.open(file_path)
            metadata['pdf_pages'] = len(doc)
            metadata['pdf_is_encrypted'] = doc.is_encrypted

            # Prüfen ob Text vorhanden
            has_text = False
            for page in doc:
                if page.get_text().strip():
                    has_text = True
                    break
            metadata['pdf_has_text'] = has_text

            # Metadaten extrahieren
            pdf_meta = doc.metadata
            if pdf_meta:
                metadata['pdf_title'] = pdf_meta.get('title', '')
                metadata['pdf_author'] = pdf_meta.get('author', '')

        except Exception as e:
            self.logger.warning(f"PDF-Metadaten-Fehler: {e}")
        finally:
            if doc is not None:
                doc.close()
        
        return metadata
    
    def index_file(self, file_path: str, force_reindex: bool = False) -> Optional[FileMetadata]:
        """
        Indiziert eine einzelne Datei.
        
        Args:
            file_path: Pfad zur Datei
            force_reindex: Erzwingt Neuindizierung
            
        Returns:
            FileMetadata oder None bei Fehler
        """
        path = Path(file_path)
        if not path.exists():
            self.logger.warning(f"Datei nicht gefunden: {file_path}")
            return None
        
        try:
            # BUGSWEEP-30: gesamter DB-Block unter RLock (Watcher-Thread vs. GUI-Thread).
            with self._lock:
                stat = path.stat()
                extension = path.suffix.lower()
                now = datetime.now()

                # Prüfen ob bereits indiziert
                existing = self._conn.execute(
                    # Bugsweep 28 BUG-01 (KRITISCH): size_bytes ergaenzt — _save_version() liest unten
                    # existing['size_bytes']; ohne die Spalte warf sqlite3.Row IndexError bei JEDEM
                    # Re-Index einer bekannten Datei -> vom bare-except verschluckt -> Dateiaenderungen
                    # wurden NIE in den Index uebernommen (Versionierung lief nie).
                    "SELECT id, hash_sha256, modified_at, size_bytes FROM files WHERE path = ?",
                    (str(path),)
                ).fetchone()

                if existing and not force_reindex:
                    # Prüfen ob Datei geändert wurde
                    db_mtime = existing['modified_at']
                    file_mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    if db_mtime == file_mtime:
                        self.logger.debug(f"Datei unverändert: {file_path}")
                        return self.get_file(str(path))

                # Hash berechnen
                file_hash = self.calculate_hash(str(path))

                # BUGSWEEP-30 (MITTEL): calculate_hash liefert bei IO-Fehler "" (leerer String).
                # Ungeprueft gespeichert wuerde idx_files_hash mit Leerwerten gefuellt und
                # find_duplicates/get_by_hash gruppierten ALLE Lese-Fehlschlaege als "Duplikate".
                # -> ohne berechenbaren Hash nicht indizieren.
                if not file_hash:
                    self.logger.warning(f"Kein Hash berechenbar, ueberspringe: {file_path}")
                    return None

                # Metadaten sammeln
                metadata = FileMetadata(
                    path=str(path),
                    name=path.name,
                    extension=extension,
                    size_bytes=stat.st_size,
                    hash_sha256=file_hash,
                    category=self._get_category(extension),
                    mime_type=self._get_mime(extension),
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    indexed_at=now,
                )

                # PDF-Metadaten
                if extension == '.pdf':
                    pdf_meta = self._extract_pdf_metadata(str(path))
                    metadata.pdf_pages = pdf_meta['pdf_pages']
                    metadata.pdf_has_text = pdf_meta['pdf_has_text']
                    metadata.pdf_is_encrypted = pdf_meta['pdf_is_encrypted']
                    metadata.pdf_title = pdf_meta['pdf_title']
                    metadata.pdf_author = pdf_meta['pdf_author']

                # In Datenbank speichern
                if existing:
                    # Version speichern (alte Größe aus DB, nicht neue aus stat)
                    self._save_version(existing['id'], existing['hash_sha256'], existing['size_bytes'])

                    # Update
                    self._conn.execute("""
                        UPDATE files SET
                            name = ?, extension = ?, size_bytes = ?, hash_sha256 = ?,
                            category = ?, mime_type = ?, modified_at = ?, indexed_at = ?,
                            pdf_pages = ?, pdf_has_text = ?, pdf_is_encrypted = ?,
                            pdf_title = ?, pdf_author = ?
                        WHERE path = ?
                    """, (
                        metadata.name, metadata.extension, metadata.size_bytes,
                        metadata.hash_sha256, metadata.category.value, metadata.mime_type,
                        metadata.modified_at.isoformat(), metadata.indexed_at.isoformat(),
                        metadata.pdf_pages, metadata.pdf_has_text, metadata.pdf_is_encrypted,
                        metadata.pdf_title, metadata.pdf_author, metadata.path
                    ))
                else:
                    # Insert
                    self._conn.execute("""
                        INSERT INTO files (
                            path, name, extension, size_bytes, hash_sha256,
                            category, mime_type, created_at, modified_at, indexed_at,
                            pdf_pages, pdf_has_text, pdf_is_encrypted, pdf_title, pdf_author
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metadata.path, metadata.name, metadata.extension, metadata.size_bytes,
                        metadata.hash_sha256, metadata.category.value, metadata.mime_type,
                        metadata.created_at.isoformat(), metadata.modified_at.isoformat(),
                        metadata.indexed_at.isoformat(), metadata.pdf_pages, metadata.pdf_has_text,
                        metadata.pdf_is_encrypted, metadata.pdf_title, metadata.pdf_author
                    ))

                self._conn.commit()
                self.logger.info(f"Indiziert: {file_path}")
                return metadata

        except Exception as e:
            self.logger.error(f"Index-Fehler für {file_path}: {e}")
            # BUGSWEEP-30 (MITTEL): offene Transaktion nach Teilfehler zuruecksetzen, damit der
            # nächste Aufruf keinen halben Zustand mitcommittet.
            try:
                with self._lock:
                    self._conn.rollback()
            except Exception:
                pass
            return None
    
    def _save_version(self, file_id: int, old_hash: str, old_size: int):
        """Speichert eine Version der Datei."""
        # Versionsnummer ermitteln
        result = self._conn.execute(
            "SELECT MAX(version_number) FROM versions WHERE file_id = ?",
            (file_id,)
        ).fetchone()
        version_num = (result[0] or 0) + 1
        
        self._conn.execute("""
            INSERT INTO versions (file_id, hash_sha256, size_bytes, modified_at, version_number)
            VALUES (?, ?, ?, ?, ?)
        """, (file_id, old_hash, old_size, datetime.now().isoformat(), version_num))
    
    def index_folder(self, folder_path: str, recursive: bool = True,
                     extensions: List[str] = None) -> Tuple[int, int]:
        """
        Indiziert einen Ordner.
        
        Args:
            folder_path: Pfad zum Ordner
            recursive: Unterordner einbeziehen
            extensions: Nur bestimmte Endungen (None = alle)
            
        Returns:
            Tuple (erfolg, fehler)
        """
        folder = Path(folder_path)
        if not folder.exists():
            return 0, 0
        
        success = 0
        failed = 0
        
        pattern = '**/*' if recursive else '*'
        
        for file_path in folder.glob(pattern):
            if not file_path.is_file():
                continue
            
            # Extension-Filter
            if extensions:
                if file_path.suffix.lower() not in extensions:
                    continue
            
            result = self.index_file(str(file_path))
            if result:
                success += 1
            else:
                failed += 1
        
        self.logger.info(f"Ordner indiziert: {folder_path} ({success} OK, {failed} Fehler)")
        return success, failed
    
    def get_file(self, path: str) -> Optional[FileMetadata]:
        """Holt FileMetadata für einen Pfad."""
        with self._lock:  # BUGSWEEP-30: gemeinsamer Lock (Watcher-Thread vs. Leser)
            row = self._conn.execute(
                "SELECT * FROM files WHERE path = ?", (path,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_metadata(row)

    def get_by_hash(self, hash_sha256: str) -> List[FileMetadata]:
        """Findet alle Dateien mit gleichem Hash (Duplikate)."""
        with self._lock:  # BUGSWEEP-30
            rows = self._conn.execute(
                "SELECT * FROM files WHERE hash_sha256 = ?", (hash_sha256,)
            ).fetchall()

            return [self._row_to_metadata(row) for row in rows]

    def find_duplicates(self) -> Dict[str, List[FileMetadata]]:
        """Findet alle Duplikate im Index."""
        with self._lock:  # BUGSWEEP-30 (RLock -> get_by_hash darunter ok)
            rows = self._conn.execute("""
                SELECT hash_sha256 FROM files
                GROUP BY hash_sha256
                HAVING COUNT(*) > 1
            """).fetchall()

            duplicates = {}
            for row in rows:
                hash_val = row['hash_sha256']
                duplicates[hash_val] = self.get_by_hash(hash_val)

            return duplicates
    
    def _row_to_metadata(self, row: sqlite3.Row) -> FileMetadata:
        """Konvertiert DB-Row zu FileMetadata."""
        # BUGSWEEP-30: lädt Tags via _conn -> wird auch von SearchEngine aus dem GUI-Thread
        # OHNE umgebende Sperre aufgerufen; eigener (reentranter) Lock schützt diesen Pfad.
        with self._lock:
            # Tags laden
            tags = self._conn.execute("""
                SELECT t.name FROM tags t
                JOIN file_tags ft ON t.id = ft.tag_id
                WHERE ft.file_id = ?
            """, (row['id'],)).fetchall()
        
        def _safe_iso(val):
            """BUG-U5: korruptes/leeres Datum aus DB → None statt ValueError."""
            if not val:
                return None
            try:
                return datetime.fromisoformat(val)
            except (ValueError, TypeError):
                return None

        return FileMetadata(
            path=row['path'],
            name=row['name'],
            extension=row['extension'],
            size_bytes=row['size_bytes'],
            hash_sha256=row['hash_sha256'],
            category=FileCategory(row['category']),
            mime_type=row['mime_type'],
            created_at=_safe_iso(row['created_at']),
            modified_at=_safe_iso(row['modified_at']),
            indexed_at=_safe_iso(row['indexed_at']),
            pdf_pages=row['pdf_pages'],
            pdf_has_text=bool(row['pdf_has_text']) if row['pdf_has_text'] is not None else None,
            pdf_is_encrypted=bool(row['pdf_is_encrypted']) if row['pdf_is_encrypted'] is not None else None,
            pdf_title=row['pdf_title'],
            pdf_author=row['pdf_author'],
            tags=[t['name'] for t in tags],
            collection_id=row['collection_id'],
        )
    
    def add_tag(self, file_path: str, tag_name: str) -> bool:
        """Fügt einen Tag zu einer Datei hinzu."""
        try:
            with self._lock:  # BUGSWEEP-30
                # Tag erstellen falls nicht vorhanden
                self._conn.execute(
                    "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,)
                )

                tag_id = self._conn.execute(
                    "SELECT id FROM tags WHERE name = ?", (tag_name,)
                ).fetchone()['id']

                file_id = self._conn.execute(
                    "SELECT id FROM files WHERE path = ?", (file_path,)
                ).fetchone()

                if not file_id:
                    return False

                self._conn.execute(
                    "INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)",
                    (file_id['id'], tag_id)
                )
                self._conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Tag-Fehler: {e}")
            return False

    def remove_tag(self, file_path: str, tag_name: str) -> bool:
        """Entfernt einen Tag von einer Datei."""
        try:
            with self._lock:  # BUGSWEEP-30
                self._conn.execute("""
                    DELETE FROM file_tags
                    WHERE file_id = (SELECT id FROM files WHERE path = ?)
                    AND tag_id = (SELECT id FROM tags WHERE name = ?)
                """, (file_path, tag_name))
                self._conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Tag-Entfernen-Fehler: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken über den Index zurück."""
        with self._lock:  # BUGSWEEP-30
            stats = {}

            stats['total_files'] = self._conn.execute(
                "SELECT COUNT(*) FROM files"
            ).fetchone()[0]

            stats['total_size'] = self._conn.execute(
                "SELECT SUM(size_bytes) FROM files"
            ).fetchone()[0] or 0

            # Nach Kategorie
            categories = self._conn.execute("""
                SELECT category, COUNT(*) as count
                FROM files GROUP BY category
            """).fetchall()
            stats['by_category'] = {row['category']: row['count'] for row in categories}

            # Duplikate
            stats['duplicate_groups'] = self._conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT hash_sha256 FROM files
                    GROUP BY hash_sha256 HAVING COUNT(*) > 1
                )
            """).fetchone()[0]

            return stats
    
    def close(self):
        """Schließt die Datenbankverbindung."""
        if self._conn:
            self._conn.close()
            self._conn = None
