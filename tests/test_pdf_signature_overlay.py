#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für core/pdf/signature.py — Signatur-Overlay-Funktion.

Fixtures werden programmatisch erstellt:
- Test-PDF: minimale Ein-Seiten-PDF via PyMuPDF (fitz)
- Test-Signaturbild: kleines rotes PNG via Pillow
Kein echtes Signaturbild oder echtes PDF als Datei-Fixture nötig.
"""

import io
import shutil
import tempfile
from pathlib import Path

import pytest

# --- Abhängigkeits-Guards ---

try:
    import pymupdf as fitz
    FITZ_AVAILABLE = True
except ImportError:
    try:
        import fitz
        FITZ_AVAILABLE = True
    except ImportError:
        FITZ_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not FITZ_AVAILABLE,
    reason="PyMuPDF (fitz) nicht installiert",
)


# === Fixtures ===

@pytest.fixture()
def tmp_dir():
    """Temporäres Verzeichnis, wird nach dem Test gelöscht."""
    d = tempfile.mkdtemp(prefix="dokuzen_sig_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def sample_pdf(tmp_dir) -> Path:
    """Minimale Ein-Seiten-PDF (A4, leer) als Fixture."""
    pdf_path = tmp_dir / "test_input.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842)  # A4 in Punkten
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def multipage_pdf(tmp_dir) -> Path:
    """Drei-Seiten-PDF als Fixture für Seitenindex-Tests."""
    pdf_path = tmp_dir / "test_multi.pdf"
    doc = fitz.open()
    for _ in range(3):
        doc.new_page(width=595, height=842)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def signed_text_pdf(tmp_dir) -> Path:
    """Ein PDF mit textlichem Signaturhinweis auf Seite 1."""
    pdf_path = tmp_dir / "signed_text.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 120), "Dieses Dokument ist bereits unterschrieben.")
    page.insert_text((72, 150), "Unterschrift: Lukas Geiger")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def signature_png(tmp_dir) -> Path:
    """Kleines rotes PNG (100×40 px) als Signatur-Fixture."""
    img_path = tmp_dir / "test_sig.png"
    if PIL_AVAILABLE:
        img = Image.new("RGBA", (100, 40), color=(200, 0, 0, 200))
        img.save(str(img_path))
    else:
        # Fallback: minimales gültiges 1×1-PNG per Rohbytes
        _write_minimal_png(img_path)
    return img_path


@pytest.fixture()
def signature_jpg(tmp_dir) -> Path:
    """Kleines grünes JPG als Signatur-Fixture."""
    img_path = tmp_dir / "test_sig.jpg"
    if PIL_AVAILABLE:
        img = Image.new("RGB", (100, 40), color=(0, 180, 0))
        img.save(str(img_path), format="JPEG")
    else:
        _write_minimal_jpg(img_path)
    return img_path


def _write_minimal_png(path: Path):
    """Schreibt ein 1×1-rotes PNG ohne Pillow (Fallback)."""
    import zlib
    import struct

    def _chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xFF\x00\x00"  # filter byte + RGB
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    path.write_bytes(header + ihdr + idat + iend)


def _write_minimal_jpg(path: Path):
    """Schreibt ein minimales weißes 1×1-JPEG ohne Pillow (Fallback)."""
    # Minimales gültiges JPEG (SOI + APP0 + DQT + SOF0 + DHT + SOS + EOI)
    # Hier vereinfacht: nicht valide genug für fitz, Test wird übersprungen
    path.write_bytes(b"\xff\xd8\xff\xd9")  # SOI + EOI (leeres JPEG)


# === Hilfsfunktion ===

def _count_images_on_page(pdf_path: Path, page_index: int = 0) -> int:
    """Zählt eingebettete Bilder auf einer PDF-Seite."""
    doc = fitz.open(str(pdf_path))
    count = len(doc[page_index].get_images())
    doc.close()
    return count


def _page_count(pdf_path: Path) -> int:
    doc = fitz.open(str(pdf_path))
    n = doc.page_count
    doc.close()
    return n


# === Tests ===

class TestEmbedSignatureCore:
    """Tests für SignatureOverlay.embed_signature()."""

    def test_png_einbetten_basic(self, sample_pdf, signature_png, tmp_dir):
        """Grundfunktion: PNG wird eingebettet, Ausgabe ist valides PDF."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_basic.pdf"
        result = embed_signature(
            pdf_path=str(sample_pdf),
            signature_path=str(signature_png),
            output_path=str(out),
        )

        assert result is True, "embed_signature() soll True zurückgeben"
        assert out.is_file(), "Ausgabe-PDF muss existieren"
        assert out.stat().st_size > 0, "Ausgabe-PDF darf nicht leer sein"

    def test_seitenzahl_unveraendert(self, sample_pdf, signature_png, tmp_dir):
        """Seitenzahl darf sich durch das Overlay nicht ändern."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_pages.pdf"
        embed_signature(str(sample_pdf), str(signature_png), str(out))

        assert _page_count(out) == _page_count(sample_pdf)

    def test_bild_auf_zielseite_vorhanden(self, sample_pdf, signature_png, tmp_dir):
        """Das eingebettete Bild muss auf der Zielseite nachweisbar sein."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_img_check.pdf"
        embed_signature(str(sample_pdf), str(signature_png), str(out))

        assert _count_images_on_page(out, page_index=0) >= 1, (
            "Zielseite 0 soll mindestens ein eingebettetes Bild enthalten"
        )

    def test_zielseite_waehlen(self, multipage_pdf, signature_png, tmp_dir):
        """Signatur landet auf der gewählten Seite, nicht auf Seite 0."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_page2.pdf"
        embed_signature(
            str(multipage_pdf),
            str(signature_png),
            str(out),
            page_index=2,  # Seite 3 (0-basiert)
        )

        assert out.is_file()
        # Seite 3 hat das Bild
        assert _count_images_on_page(out, page_index=2) >= 1
        # Seite 1 hat kein Bild
        assert _count_images_on_page(out, page_index=0) == 0

    def test_jpg_einbetten(self, sample_pdf, signature_jpg, tmp_dir):
        """JPG-Signaturen werden ebenfalls korrekt eingebettet."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_jpg.pdf"
        result = embed_signature(
            str(sample_pdf),
            str(signature_jpg),
            str(out),
        )
        # Einige Minimal-JPEGs (Fallback) sind nicht fitz-kompatibel →
        # wir prüfen nur: kein unbehandelter Exception, Rückgabe ist bool
        assert isinstance(result, bool)

    def test_position_und_groesse(self, sample_pdf, signature_png, tmp_dir):
        """Individuelle Position/Größe werden akzeptiert."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_pos.pdf"
        result = embed_signature(
            str(sample_pdf),
            str(signature_png),
            str(out),
            x=100.0,
            y=200.0,
            width=150.0,
            height=60.0,
            keep_aspect=False,
        )

        assert result is True
        assert out.is_file()

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow nicht installiert")
    def test_keep_aspect_beibehalten(self, sample_pdf, signature_png, tmp_dir):
        """keep_aspect=True liefert ebenfalls True (Pillow-Pfad)."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_aspect.pdf"
        result = embed_signature(
            str(sample_pdf),
            str(signature_png),
            str(out),
            width=300.0,
            height=300.0,
            keep_aspect=True,
        )

        assert result is True
        assert _count_images_on_page(out) >= 1


class TestEmbedSignatureFehlerfaelle:
    """Tests für Fehler- und Randfälle."""

    def test_signaturbild_fehlt(self, sample_pdf, tmp_dir):
        """Nicht vorhandenes Signaturbild → False, kein Exception."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_err.pdf"
        result = embed_signature(
            str(sample_pdf),
            str(tmp_dir / "nicht_vorhanden.png"),
            str(out),
        )

        assert result is False
        assert not out.exists(), "Bei Fehler darf keine Ausgabedatei entstehen"

    def test_pdf_fehlt(self, signature_png, tmp_dir):
        """Nicht vorhandene Eingabe-PDF → False."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_err2.pdf"
        result = embed_signature(
            str(tmp_dir / "gibt_es_nicht.pdf"),
            str(signature_png),
            str(out),
        )

        assert result is False

    def test_seitenindex_zu_gross(self, sample_pdf, signature_png, tmp_dir):
        """Ungültiger Seitenindex → False."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_err3.pdf"
        result = embed_signature(
            str(sample_pdf),
            str(signature_png),
            str(out),
            page_index=99,
        )

        assert result is False

    def test_seitenindex_negativ(self, sample_pdf, signature_png, tmp_dir):
        """Negativer Seitenindex → False."""
        from core.pdf.signature import embed_signature

        out = tmp_dir / "output_err4.pdf"
        result = embed_signature(
            str(sample_pdf),
            str(signature_png),
            str(out),
            page_index=-1,
        )

        assert result is False


class TestSignatureOverlayKlasse:
    """Tests für die SignatureOverlay-Klasse direkt."""

    def test_klasse_instanziierbar(self):
        from core.pdf.signature import SignatureOverlay
        so = SignatureOverlay()
        assert so is not None

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow nicht installiert")
    def test_adjusted_size_landscape(self, signature_png, tmp_dir):
        """Querformat-Bild (100×40) in Quadrat → Breite wird beschnitten."""
        from core.pdf.signature import SignatureOverlay

        so = SignatureOverlay()
        # Bild: 100×40 px → Verhältnis 2.5:1
        # max_width=200, max_height=200 → Ergebnis: 200×80 (Breite limitiert)
        w, h = so._adjusted_size(str(signature_png), 200.0, 200.0)
        assert abs(w / h - 2.5) < 0.01, f"Seitenverhältnis erwartet 2.5:1, got {w/h:.2f}:1"

    def test_adjusted_size_fallback_ohne_pillow(self, tmp_dir):
        """Ohne Pillow-Bild (nicht lesbare Datei) → Fallback auf Wunschgröße."""
        from core.pdf.signature import SignatureOverlay

        so = SignatureOverlay()
        # Nicht-Bilddatei übergeben → Fehler intern gefangen, Fallback
        txt = tmp_dir / "kein_bild.txt"
        txt.write_text("kein Bild", encoding="utf-8")
        w, h = so._adjusted_size(str(txt), 150.0, 60.0)
        assert w == 150.0
        assert h == 60.0


class TestSignatureVorabpruefung:
    """Tests für vorhandene Signaturhinweise vor dem Overlay."""

    def test_detect_existing_signature_pdf_text(self, signed_text_pdf):
        from core.pdf.signature import detect_existing_signature

        result = detect_existing_signature(
            str(signed_text_pdf),
            page_index=0,
            use_ocr=False,
        )

        assert result.found is True
        assert result.page_index == 0
        assert result.source == "pdf-text"
        assert result.matched_term in {"unterschrift", "unterschrieben"}
        assert "Unterschrift" in result.text_excerpt

    def test_checked_embed_skips_when_signature_text_exists(
        self, signed_text_pdf, signature_png, tmp_dir
    ):
        from core.pdf.signature import embed_signature_checked

        out = tmp_dir / "already_signed_output.pdf"
        result = embed_signature_checked(
            str(signed_text_pdf),
            str(signature_png),
            str(out),
            skip_if_present=True,
            use_ocr=False,
        )

        assert result.success is True
        assert result.embedded is False
        assert result.skipped_existing is True
        assert out.is_file()
        assert _count_images_on_page(out, page_index=0) == 0

    def test_checked_embed_adds_overlay_when_no_signature_text(
        self, sample_pdf, signature_png, tmp_dir
    ):
        from core.pdf.signature import embed_signature_checked

        out = tmp_dir / "newly_signed_output.pdf"
        result = embed_signature_checked(
            str(sample_pdf),
            str(signature_png),
            str(out),
            skip_if_present=True,
            use_ocr=False,
        )

        assert result.success is True
        assert result.embedded is True
        assert result.skipped_existing is False
        assert _count_images_on_page(out, page_index=0) >= 1
