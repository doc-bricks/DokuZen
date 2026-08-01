#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für CompileWorker — Subprozess wird auch bei Exception bereinigt.

Bugfix: run() schloss weder process.stdout noch terminierte process,
        wenn während der Ausgabezeilen-Iteration eine Ausnahme auftrat.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_compile(command, work_dir, emit_output=None, emit_finished=None):
    """Spiegelt CompileWorker.run() ohne Qt-Signals."""
    import subprocess

    process = None
    output_lines = []
    finished_args = None
    error = None

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=work_dir,
            text=True,
            bufsize=1,
        )
        for line in iter(process.stdout.readline, ''):
            line = line.rstrip()
            output_lines.append(line)
            if emit_output:
                emit_output(line)
        process.wait()
        if process.returncode == 0:
            finished_args = (True, "Kompilierung erfolgreich!")
        else:
            finished_args = (False, f"Fehler (Code {process.returncode})")
    except Exception as e:
        finished_args = (False, str(e))
        error = str(e)
    finally:
        if process is not None:
            if process.stdout:
                process.stdout.close()
            if process.poll() is None:
                process.terminate()
                process.wait()

    return output_lines, finished_args, error


class TestCompileWorkerProcessCleanup(unittest.TestCase):

    def test_stdout_closed_after_successful_run(self):
        """stdout wird nach erfolgreichem Lauf geschlossen."""
        import subprocess

        mock_proc = MagicMock()
        mock_proc.stdout.readline.side_effect = ['line1\n', '']
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0

        with patch('subprocess.Popen', return_value=mock_proc):
            lines, result, err = _run_compile(['echo', 'test'], '.')

        mock_proc.stdout.close.assert_called_once()
        self.assertIsNone(err)
        self.assertTrue(result[0])

    def test_stdout_closed_and_process_terminated_on_exception(self):
        """stdout wird geschlossen und Prozess terminiert, wenn emit eine Ausnahme wirft."""
        import subprocess

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = 'line\n'
        mock_proc.poll.return_value = None  # Prozess noch aktiv

        def bad_emit(line):
            raise RuntimeError("Qt-Thread weg")

        with patch('subprocess.Popen', return_value=mock_proc):
            lines, result, err = _run_compile(['echo', 'test'], '.', emit_output=bad_emit)

        mock_proc.stdout.close.assert_called_once()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called()
        self.assertIsNotNone(err)

    def test_no_terminate_if_process_already_finished(self):
        """Kein terminate() wenn der Prozess schon beendet ist."""
        import subprocess

        mock_proc = MagicMock()
        mock_proc.stdout.readline.side_effect = ['', RuntimeError("pipe broken")]
        mock_proc.poll.return_value = 0  # bereits beendet

        with patch('subprocess.Popen', return_value=mock_proc):
            _run_compile(['echo', 'test'], '.')

        mock_proc.terminate.assert_not_called()
        mock_proc.stdout.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
