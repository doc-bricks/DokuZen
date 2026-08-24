#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Redaction Detector
====================================
Erkennt sensible Daten für Schwärzung.
"""

import os
import re
import shutil
import tempfile
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from utils.logger import LoggerMixin, get_logger

_logger = get_logger(__name__)

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class SensitiveType(Enum):
    """Typen sensibler Daten."""
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    IBAN = "iban"
    DATE = "date"
    ADDRESS = "address"
    CUSTOM = "custom"


@dataclass
class Match:
    """Ein gefundener Treffer."""
    text: str
    start: int
    end: int
    type: SensitiveType
    confidence: float
    page: int = 0
    rects: Optional[List[Tuple[float, float, float, float]]] = None


class RedactionDetector(LoggerMixin):
    """
    Erkennt sensible Daten in Text.
    
    Features:
    - Regex-basierte Erkennung (Email, Telefon, IBAN, etc.)
    - Blacklist-Wörter (exakt und fuzzy)
    - Whitelist (Ausnahmen)
    - Konfigurierbare Schwellwerte
    """
    
    # Regex-Patterns für deutsche Formate
    PATTERNS = {
        # Bugsweep 28 BUG-5: in der TLD-Zeichenklasse stand ein versehentliches Pipe-Literal -> bereinigt
        # auf reine Buchstaben (A-Za-z); rein additiv/verengend.
        SensitiveType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        # Bugsweep 28 BUG-4 (PII-Leak): fuehrendes \b matcht VOR '+' nach Whitespace nie (non-word ->
        # non-word = keine Boundary) -> '+49'-Nummern wurden nie erkannt/geschwaerzt. (?<!\d) erfasst
        # zusaetzlich '+49' UND lockert die Boundary der 0/0049-Varianten (matcht jetzt auch z.B.
        # "abc0170...") -> mehr Treffer, für Redaction die sichere Richtung (eher mehr schwaerzen).
        SensitiveType.PHONE: r'(?<!\d)(?:\+49|0049|0)[\s\-]?(?:\d[\s\-]?){9,14}\b',
        SensitiveType.IBAN: r'\b[A-Z]{2}\d{2}[\s]?(?:\d{4}[\s]?){4}\d{2}\b',
        SensitiveType.DATE: r'\b\d{1,2}[.\-/]\d{1,2}[.\-/](?:\d{2}|\d{4})\b',
    }
    
    def __init__(self, fuzzy_threshold: int = 80):
        """
        Initialisiert den Detector.
        
        Args:
            fuzzy_threshold: Schwellwert für Fuzzy-Matching (0-100)
        """
        self._blacklist: Set[str] = set()
        self._whitelist: Set[str] = set()
        self._fuzzy_threshold = fuzzy_threshold
        self._compiled_patterns: Dict[SensitiveType, re.Pattern] = {}
        
        # Patterns kompilieren
        for type_, pattern in self.PATTERNS.items():
            self._compiled_patterns[type_] = re.compile(pattern, re.IGNORECASE)
        
        if not RAPIDFUZZ_AVAILABLE:
            self.logger.warning("rapidfuzz nicht installiert - Fuzzy-Matching deaktiviert")
    
    def load_blacklist(self, path: str) -> int:
        """
        Lädt Blacklist aus Datei.
        
        Args:
            path: Pfad zur Textdatei (ein Wort pro Zeile)
            
        Returns:
            Anzahl geladener Wörter
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                words = {line.strip().lower() for line in f if line.strip()}
            self._blacklist.update(words)
            self.logger.info(f"Blacklist geladen: {len(words)} Wörter aus {path}")
            return len(words)
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Blacklist: {e}")
            return 0
    
    def load_whitelist(self, path: str) -> int:
        """Lädt Whitelist aus Datei."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                words = {line.strip().lower() for line in f if line.strip()}
            self._whitelist.update(words)
            self.logger.info(f"Whitelist geladen: {len(words)} Wörter")
            return len(words)
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Whitelist: {e}")
            return 0
    
    def add_to_blacklist(self, words: List[str]):
        """Fügt Wörter zur Blacklist hinzu."""
        self._blacklist.update(w.lower() for w in words)
    
    def add_to_whitelist(self, words: List[str]):
        """Fügt Wörter zur Whitelist hinzu."""
        self._whitelist.update(w.lower() for w in words)
    
    def clear_blacklist(self):
        """Leert die Blacklist."""
        self._blacklist.clear()
    
    def clear_whitelist(self):
        """Leert die Whitelist."""
        self._whitelist.clear()
    
    def detect(self, text: str, page: int = 0,
               use_patterns: bool = True,
               use_blacklist: bool = True,
               use_fuzzy: bool = True,
               char_rects: Optional[List[Optional[Tuple[float, float, float, float]]]] = None) -> List[Match]:
        """
        Erkennt sensible Daten im Text.
        
        Args:
            text: Zu analysierender Text
            page: Seitennummer (für Referenz)
            use_patterns: Regex-Patterns verwenden
            use_blacklist: Blacklist-Wörter suchen
            use_fuzzy: Fuzzy-Matching für Blacklist
            char_rects: Optionale Liste von Bounding-Boxes pro Zeichen (len == len(text))
            
        Returns:
            Liste von Match-Objekten
        """
        matches: List[Match] = []
        
        if use_patterns:
            matches.extend(self._detect_patterns(text, page))
        
        if use_blacklist and self._blacklist:
            if use_fuzzy and RAPIDFUZZ_AVAILABLE:
                matches.extend(self._detect_fuzzy(text, page))
            else:
                matches.extend(self._detect_exact(text, page))
        
        # Whitelist-Filterung
        matches = self._filter_whitelist(matches)
        
        # Duplikate entfernen (basierend auf Position)
        matches = self._deduplicate(matches)
        
        # Falls char_rects übergeben wurden, präzise Rechtecke für jeden Match berechnen
        if char_rects and len(char_rects) == len(text):
            for m in matches:
                if 0 <= m.start < m.end <= len(char_rects):
                    matched_bboxes = [r for r in char_rects[m.start:m.end] if r is not None]
                    m.rects = char_bboxes_to_rects(matched_bboxes)

        return sorted(matches, key=lambda m: (m.page, m.start))
    
    def _detect_patterns(self, text: str, page: int) -> List[Match]:
        """Erkennt Patterns via Regex."""
        matches = []
        
        for type_, pattern in self._compiled_patterns.items():
            for m in pattern.finditer(text):
                matches.append(Match(
                    text=m.group(),
                    start=m.start(),
                    end=m.end(),
                    type=type_,
                    confidence=100.0,
                    page=page
                ))
        
        return matches
    
    def _detect_exact(self, text: str, page: int) -> List[Match]:
        """Sucht exakte Blacklist-Treffer."""
        matches = []
        text_lower = text.lower()
        
        for word in self._blacklist:
            start = 0
            while True:
                pos = text_lower.find(word, start)
                if pos == -1:
                    break
                
                matches.append(Match(
                    text=text[pos:pos+len(word)],
                    start=pos,
                    end=pos + len(word),
                    type=SensitiveType.CUSTOM,
                    confidence=100.0,
                    page=page
                ))
                start = pos + 1
        
        return matches
    
    def _detect_fuzzy(self, text: str, page: int) -> List[Match]:
        """Fuzzy-Matching für Blacklist.

        Hinweis: Fuzzy-Matching kann bei niedrigem Schwellwert falsche Treffer
        liefern. Für sicherheitskritische Anwendungen exaktes Matching bevorzugen
        (use_fuzzy=False in detect()).
        """
        matches = []

        # Text in Woerter mit ihren Positionen aufteilen
        for m in re.finditer(r'\b\w+\b', text):
            word = m.group()
            if len(word) < 3:  # Zu kurze Woerter ignorieren
                continue

            # Bestes Match in Blacklist suchen
            result = process.extractOne(
                word.lower(),
                self._blacklist,
                scorer=fuzz.ratio,
                score_cutoff=self._fuzzy_threshold
            )

            if result:
                match_word, score, _ = result
                # Position direkt aus dem Regex-Match verwenden (korrekt auch
                # bei mehrfach vorkommenden Woertern)
                pos = m.start()
                matches.append(Match(
                    text=text[pos:pos + len(word)],
                    start=pos,
                    end=pos + len(word),
                    type=SensitiveType.CUSTOM,
                    confidence=score,
                    page=page
                ))

        return matches
    
    def _filter_whitelist(self, matches: List[Match]) -> List[Match]:
        """Filtert Whitelist-Einträge heraus."""
        if not self._whitelist:
            return matches
        
        return [
            m for m in matches
            if m.text.lower() not in self._whitelist
        ]
    
    def _deduplicate(self, matches: List[Match]) -> List[Match]:
        """Entfernt überlappende Treffer."""
        # BUGSWEEP-28 KRITISCH USER-REVIEW (NICHT auto-gefixt — Redaction-Reliability, Redesign noetig):
        # Zwei gekoppelte PII-Leak-Risiken, die ein isolierter Fix hier NICHT schliesst:
        #  (1) Tail-Verlust: bei Ueberlappung ersetzt ein kuerzerer, höher-konfidenter Match den
        #      laengeren (z.B. "John Smith"(conf90) -> "John"(conf100)); "Smith" bleibt UNGESCHWAERZT.
        #  (2) Kopplung an RedactionApplier.redact_pdf (~Z.329): der Applier VERWIRFT die hier
        #      berechneten (start,end)-Offsets und sucht per page.search_for(match.text) NEU -> bei
        #      internen Leerzeichen/Umbruechen (IBAN "DE89 3704 ...") liefert search_for [] -> KEINE
        #      Schwaerzung, KEIN Fehler (gibt True zurück) -> sensible Daten bleiben im PDF.
        # Echter Fix = per detektierter Span/Rect schwaerzen statt Text neu zu suchen (Architektur-
        # Änderung, sicherheitskritisch) -> dem User zur Entscheidung vorgelegt, hier bewusst belassen.
        if not matches:
            return matches
        
        # Nach Position sortieren
        sorted_matches = sorted(matches, key=lambda m: (m.page, m.start, -m.end))
        
        result = [sorted_matches[0]]
        for match in sorted_matches[1:]:
            last = result[-1]
            
            # Überlappung prüfen
            if match.page != last.page or match.start >= last.end:
                result.append(match)
            elif match.confidence > last.confidence:
                result[-1] = match
        
        return result


class RedactionApplier(LoggerMixin):
    """Wendet Schwärzungen auf PDFs an."""
    
    def __init__(self):
        # P0-Fix (Review 2026-07-23): Statistik der letzten redact_pdf()-Ausführung.
        # search_for() findet Treffer mit internen Leerzeichen/Zeilenumbruechen
        # (z.B. IBAN "DE89 3704 ...") oft NICHT -> ohne diese Statistik meldete
        # redact_pdf() unveraendert "True", obwohl einzelne Treffer NICHT
        # geschwaerzt wurden (stiller PII-Leak). Aufrufer koennen über
        # last_redaction_stats["missed"] prüfen, ob wirklich alle Treffer
        # geschwaerzt wurden, bevor sie Erfolg melden.
        self.last_redaction_stats: Dict[str, int] = {"total": 0, "redacted": 0, "missed": 0}
        try:
            import fitz
            self._fitz = fitz
            self._available = True
        except ImportError:
            self._available = False
            self.logger.warning("PyMuPDF nicht verfügbar")

    def redact_pdf(self, input_path: str, output_path: str,
                   matches: List[Match],
                   redaction_color: Tuple[int, int, int] = (0, 0, 0)) -> bool:
        """
        Schwaerzt Textstellen in einer PDF.

        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            matches: Zu schwaerzende Stellen
            redaction_color: Farbe (R, G, B)

        Returns:
            True bei Erfolg (Datei wurde geschrieben). Prüft NICHT allein,
            ob wirklich jeder Treffer geschwaerzt wurde - dafuer nach dem
            Aufruf `last_redaction_stats["missed"]` auswerten.
        """
        self.last_redaction_stats = {"total": len(matches), "redacted": 0, "missed": 0}

        if not self._available:
            return False

        doc = None
        temp_file = None
        try:
            doc = self._fitz.open(input_path)

            # Matches nach Seite gruppieren
            by_page: Dict[int, List[Match]] = {}
            for m in matches:
                by_page.setdefault(m.page, []).append(m)

            missed_examples: List[str] = []

            # Pro Seite schwaerzen
            for page_num, page_matches in by_page.items():
                if page_num < 1 or page_num > doc.page_count:
                    continue

                page = doc[page_num - 1]

                for match in page_matches:
                    # Präzise vorberechnete Rects verwenden oder per Textsuche neu lokalisieren
                    rects = match.rects
                    if not rects:
                        rects = page.search_for(match.text)

                    if rects:
                        self.last_redaction_stats["redacted"] += 1
                        for rect in rects:
                            page.add_redact_annot(rect, fill=redaction_color)
                    else:
                        # Treffer wurde NICHT im PDF lokalisiert (z.B. Text mit
                        # internen Leerzeichen/Zeilenumbruch) -> bleibt UNGESCHWAERZT.
                        self.last_redaction_stats["missed"] += 1
                        if len(missed_examples) < 5:
                            missed_examples.append(f"S.{page_num}:{match.text!r}")

                # Redactions anwenden
                page.apply_redactions()

            # Speichern (mit In-Place-Unterstützung)
            src = Path(input_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src == dst:
                with tempfile.NamedTemporaryFile(dir=dst.parent, prefix="dokuzen_redact_", suffix=".tmp", delete=False) as tmp:
                    temp_file = Path(tmp.name)
                doc.save(str(temp_file))
            else:
                doc.save(output_path)

            if self.last_redaction_stats["missed"]:
                self.logger.warning(
                    "PDF geschwaerzt, aber %d von %d Treffern wurden NICHT im "
                    "PDF gefunden und bleiben UNGESCHWAERZT: %s",
                    self.last_redaction_stats["missed"],
                    self.last_redaction_stats["total"],
                    ", ".join(missed_examples),
                )
            self.logger.info(f"PDF geschwaerzt: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Schwaerzungsfehler: {e}")
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return False
        finally:
            if doc is not None:
                doc.close()
            if temp_file and temp_file.exists():
                try:
                    shutil.move(str(temp_file), str(Path(output_path).resolve()))
                except Exception:
                    pass


# === Hilfsfunktionen ===

def char_bboxes_to_rects(char_bboxes: List[Tuple[float, float, float, float]]) -> List[Tuple[float, float, float, float]]:
    """
    Fügt eine Liste von Zeichen-Bounding-Boxes (x0, y0, x1, y1) zu zeilenbasierten
    Rechtecken (min_x0, min_y0, max_x1, max_y1) zusammen.
    """
    if not char_bboxes:
        return []
    lines: List[List[Tuple[float, float, float, float]]] = []
    current_line: List[Tuple[float, float, float, float]] = []
    for bbox in char_bboxes:
        if not bbox:
            continue
        if not current_line:
            current_line.append(bbox)
        else:
            prev = current_line[-1]
            y0_diff = abs(bbox[1] - prev[1])
            y1_diff = abs(bbox[3] - prev[3])
            if y0_diff < 4 and y1_diff < 4:
                current_line.append(bbox)
            else:
                lines.append(current_line)
                current_line = [bbox]
    if current_line:
        lines.append(current_line)

    rects: List[Tuple[float, float, float, float]] = []
    for line in lines:
        x0 = min(b[0] for b in line)
        y0 = min(b[1] for b in line)
        x1 = max(b[2] for b in line)
        y1 = max(b[3] for b in line)
        rects.append((x0, y0, x1, y1))
    return rects


def extract_page_text_and_char_rects(page) -> Tuple[str, List[Optional[Tuple[float, float, float, float]]]]:
    """
    Extrahiert Text und zeichenweise Bounding-Boxes (x0, y0, x1, y1) aus einer
    PyMuPDF-Seite (fitz.Page).
    
    Returns:
        Tuple (text_str, char_rects) mit len(text_str) == len(char_rects).
    """
    try:
        raw = page.get_text("rawdict")
    except Exception:
        return page.get_text(), []

    text_chars: List[str] = []
    char_rects: List[Optional[Tuple[float, float, float, float]]] = []

    for b in raw.get("blocks", []):
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                for c in s["chars"]:
                    ch = c.get("c", "")
                    bbox = c.get("bbox", None)
                    text_chars.append(ch)
                    char_rects.append(bbox)
            text_chars.append("\n")
            char_rects.append(None)

    text_str = "".join(text_chars)
    return text_str, char_rects


def detect_sensitive_data(text: str, blacklist_path: Optional[str] = None) -> List[Match]:
    """Schnelle Erkennung sensibler Daten."""
    detector = RedactionDetector()
    if blacklist_path:
        detector.load_blacklist(blacklist_path)
    return detector.detect(text)


def redact_pdf(input_path: str, output_path: str,
               blacklist_path: Optional[str] = None) -> bool:
    """Schwaerzt sensible Daten in einer PDF."""
    # Text extrahieren
    doc = None
    try:
        import fitz
        doc = fitz.open(input_path)

        detector = RedactionDetector()
        if blacklist_path:
            detector.load_blacklist(blacklist_path)

        all_matches = []
        for i, page in enumerate(doc):
            text, char_rects = extract_page_text_and_char_rects(page)
            matches = detector.detect(text, page=i + 1, char_rects=char_rects)
            all_matches.extend(matches)

    except Exception as e:
        _logger.error(f"Schwärzungs-Fehler in redact_pdf: {e}")
        return False
    finally:
        if doc is not None:
            doc.close()

    if all_matches:
        applier = RedactionApplier()
        return applier.redact_pdf(input_path, output_path, all_matches)

    src = Path(input_path).resolve()
    dst = Path(output_path).resolve()
    if src != dst:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        except Exception as e:
            _logger.error(f"Kopier-Fehler in redact_pdf: {e}")
            return False

    return True
