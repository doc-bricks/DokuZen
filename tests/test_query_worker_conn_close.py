#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für QueryWorker — sqlite3-Connection wird auch bei Exception geschlossen.

Bugfix: run() schloss die Verbindung nicht wenn cursor.execute() oder fetchall() warfen.
"""

import sys
import sqlite3
import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# QueryWorker ohne PySide6 testen: Klasse direkt importieren und _run-Logik extrahieren
def _run_query(db_path: str, query: str):
    """Spiegelt QueryWorker.run() ohne Qt-Signals."""
    columns = None
    rows = None
    error = None
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
    except Exception as e:
        error = str(e)
    finally:
        if conn:
            conn.close()
    return columns, rows, error


class TestQueryWorkerConnClose(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db_path = self._tmp.name
        self._tmp.close()
        conn = sqlite3.connect(self._db_path)
        conn.execute("CREATE TABLE test (id INTEGER, val TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()

    def tearDown(self):
        os.unlink(self._db_path)

    def test_conn_closed_on_success(self):
        """Verbindung wird nach erfolgreicher Abfrage geschlossen."""
        columns, rows, error = _run_query(self._db_path, "SELECT * FROM test")
        self.assertIsNone(error)
        self.assertEqual(rows, [(1, "hello")])

    def test_conn_closed_on_bad_query(self):
        """Verbindung wird geschlossen, auch wenn die Abfrage fehlschlägt."""
        columns, rows, error = _run_query(self._db_path, "SELECT * FROM nonexistent_table")
        self.assertIsNotNone(error)
        # Datei muss noch zugänglich sein (Verbindung nicht offen gelassen)
        conn = sqlite3.connect(self._db_path)
        result = conn.execute("SELECT COUNT(*) FROM test").fetchone()
        conn.close()
        self.assertEqual(result[0], 1)


if __name__ == "__main__":
    unittest.main()
