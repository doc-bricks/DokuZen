#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für ClipboardMonitor — Thread-Safety beim Callback-Management.

Bugfix: add_callback/remove_callback waren nicht durch Lock geschützt.
        _on_new_content iterierte self._callbacks ohne Lock-Snapshot —
        concurrent remove_callback() konnte RuntimeError auslösen.
"""

import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestClipboardMonitorThreadSafety(unittest.TestCase):

    def _make_monitor(self):
        import plugins.spawner.clipboard_monitor as cm_mod
        monitor = cm_mod.ClipboardMonitor.__new__(cm_mod.ClipboardMonitor)
        import logging
        monitor._logger = logging.getLogger("test")
        monitor._check_interval = 0.5
        monitor._history_size = 50
        monitor._running = False
        monitor._thread = None
        monitor._last_content = ""
        monitor._history = []
        monitor._callbacks = []
        import threading as _th
        monitor._lock = _th.Lock()
        return monitor

    def test_add_callback_is_protected_by_lock(self):
        """add_callback() muss mit Lock geschützt sein."""
        import plugins.spawner.clipboard_monitor as cm_mod
        monitor = self._make_monitor()

        cb1 = MagicMock()
        cb2 = MagicMock()

        # Simulates concurrent adds from different threads
        errors = []
        def add_many():
            for _ in range(100):
                try:
                    monitor.add_callback(cb1)
                    monitor.remove_callback(cb1)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=add_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread-Safety-Fehler: {errors}")

    def test_on_new_content_uses_snapshot(self):
        """_on_new_content() iteriert einen Snapshot der Callbacks."""
        import plugins.spawner.clipboard_monitor as cm_mod
        monitor = self._make_monitor()

        called = []

        def cb(content):
            called.append(content)

        monitor._callbacks.append(cb)

        content = cm_mod.ClipboardContent(
            content_type=cm_mod.ClipboardContentType.TEXT,
            text="test"
        )
        monitor._on_new_content("test")

        # The callback was called
        self.assertEqual(len(called), 1)

    def test_remove_callback_during_on_new_content_no_error(self):
        """remove_callback() während on_new_content() darf keinen RuntimeError auslösen."""
        import plugins.spawner.clipboard_monitor as cm_mod
        monitor = self._make_monitor()

        errors = []

        def self_removing_cb(content):
            # Callback removes itself during iteration — previously caused RuntimeError
            try:
                monitor.remove_callback(self_removing_cb)
            except RuntimeError as e:
                errors.append(e)

        monitor.add_callback(self_removing_cb)
        monitor._on_new_content("hello")

        self.assertEqual(errors, [], f"RuntimeError bei self-removing callback: {errors}")
        # Callback should be removed now
        with monitor._lock:
            self.assertNotIn(self_removing_cb, monitor._callbacks)


if __name__ == "__main__":
    unittest.main()
