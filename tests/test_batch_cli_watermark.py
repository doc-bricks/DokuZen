#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für die Headless-Batch-CLI mit Wasserzeichen-Aktion in DokuZen.

Validiert:
1. batch_watermark Funktion direkt mit Parametern.
2. execute_headless_cli mit --watermark und Argumenten.
3. Strukturierte JSON-Rückgabe via --json.
4. Korrekte Exit-Codes (0 bei Erfolg, 1/2 bei Fehlern).
"""

import json
from pathlib import Path
import pytest
import fitz

from core.batch_cli import batch_watermark, execute_headless_cli
from main import parse_cli_args


@pytest.fixture
def test_pdf(tmp_path) -> Path:
    """Erstellt ein Test-PDF mit 2 Seiten."""
    pdf_path = tmp_path / "cli_test.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_batch_watermark_direct(test_pdf, tmp_path):
    """Testet batch_watermark direkt."""
    out_pdf = tmp_path / "cli_watermarked.pdf"
    res = batch_watermark(
        input_file=test_pdf,
        output_file=out_pdf,
        text="CLI_WATERMARK",
        opacity=0.3,
        angle=45.0,
        pages="all",
        color="red",
        layer="foreground",
    )

    assert res.success is True
    assert res.action == "watermark"
    assert res.details["pages_watermarked"] == 2
    assert res.details["total_pages"] == 2
    assert res.details["layer"] == "foreground"

    doc = fitz.open(str(out_pdf))
    assert "CLI_WATERMARK" in doc[0].get_text()
    doc.close()


def test_execute_headless_cli_watermark(test_pdf, tmp_path, capsys):
    """Testet execute_headless_cli mit --watermark und Ausgabepfad."""
    out_pdf = tmp_path / "cli_out.pdf"
    args = parse_cli_args([
        "--headless",
        "--watermark", str(test_pdf),
        "-o", str(out_pdf),
        "--watermark-text", "GEHEIM",
        "--watermark-color", "blue",
        "--watermark-pages", "1",
    ])

    exit_code = execute_headless_cli(args)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "WATERMARK" in captured.out

    doc = fitz.open(str(out_pdf))
    assert "GEHEIM" in doc[0].get_text()
    assert "GEHEIM" not in doc[1].get_text()
    doc.close()


def test_execute_headless_cli_watermark_json(test_pdf, tmp_path, capsys):
    """Testet execute_headless_cli mit --json Option."""
    out_pdf = tmp_path / "cli_json_out.pdf"
    args = parse_cli_args([
        "--headless",
        "--watermark", str(test_pdf),
        "-o", str(out_pdf),
        "--watermark-text", "JSON_STAMP",
        "--json",
    ])

    exit_code = execute_headless_cli(args)
    assert exit_code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["success"] is True
    assert data["action"] == "watermark"
    assert data["details"]["pages_watermarked"] == 2


def test_execute_headless_cli_watermark_missing_output(test_pdf, capsys):
    """Prüft, ob fehlende Ausgabedatei mit Exit-Code 2 abgewiesen wird."""
    args = parse_cli_args([
        "--headless",
        "--watermark", str(test_pdf),
        "--json",
    ])

    exit_code = execute_headless_cli(args)
    assert exit_code == 2

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["success"] is False
    assert "Ausgabedatei" in data["error"]
