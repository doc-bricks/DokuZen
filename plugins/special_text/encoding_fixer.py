#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Encoding Fixer
================================
Erkennt und korrigiert Zeichencodierungsprobleme.
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

from utils.logger import LoggerMixin

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False


class CommonEncoding(Enum):
    """Häufige Zeichencodierungen."""
    UTF8 = "utf-8"
    UTF8_BOM = "utf-8-sig"
    UTF16 = "utf-16"
    LATIN1 = "latin-1"
    CP1252 = "cp1252"
    ASCII = "ascii"
    ISO8859_15 = "iso-8859-15"


@dataclass
class EncodingResult:
    """Ergebnis einer Encoding-Erkennung."""
    detected_encoding: str
    confidence: float
    language: Optional[str] = None
    
    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.8


@dataclass
class ConversionResult:
    """Ergebnis einer Encoding-Konvertierung."""
    success: bool
    source_encoding: str
    target_encoding: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    chars_fixed: int = 0


class EncodingFixer(LoggerMixin):
    """
    Erkennt und repariert Encoding-Probleme.
    
    Features:
    - Automatische Encoding-Erkennung
    - Konvertierung zwischen Encodings
    - Batch-Verarbeitung
    - Problematische Zeichen erkennen
    """
    
    # Bekannte problematische Zeichen-Mappings (CP1252 → UTF-8)
    PROBLEM_CHARS = {
        b'\x80': '€',
        b'\x85': '…',
        b'\x91': ''',
        b'\x92': ''',
        b'\x93': '"',
        b'\x94': '"',
        b'\x96': '–',
        b'\x97': '—',
        b'\xa0': ' ',  # Non-breaking space
        b'\xc4': 'Ä',
        b'\xd6': 'Ö',
        b'\xdc': 'Ü',
        b'\xdf': 'ß',
        b'\xe4': 'ä',
        b'\xf6': 'ö',
        b'\xfc': 'ü',
    }
    
    def __init__(self):
        if not CHARDET_AVAILABLE:
            self.logger.warning("chardet nicht installiert - eingeschränkte Erkennung")
    
    def detect_encoding(self, filepath: str) -> Optional[EncodingResult]:
        """
        Erkennt das Encoding einer Datei.
        
        Args:
            filepath: Pfad zur Datei
            
        Returns:
            EncodingResult oder None
        """
        path = Path(filepath)
        
        if not path.exists():
            self.logger.error(f"Datei nicht gefunden: {filepath}")
            return None
        
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read()
        except Exception as e:
            self.logger.error(f"Lesefehler: {e}")
            return None
        
        return self.detect_encoding_bytes(raw_data)
    
    def detect_encoding_bytes(self, data: bytes) -> EncodingResult:
        """Erkennt das Encoding von Bytes."""
        # BOM-Prüfung
        if data.startswith(b'\xef\xbb\xbf'):
            return EncodingResult("utf-8-sig", 1.0)
        elif data.startswith(b'\xff\xfe'):
            return EncodingResult("utf-16-le", 1.0)
        elif data.startswith(b'\xfe\xff'):
            return EncodingResult("utf-16-be", 1.0)
        
        # chardet verwenden
        if CHARDET_AVAILABLE:
            result = chardet.detect(data)
            return EncodingResult(
                detected_encoding=result.get('encoding', 'utf-8') or 'utf-8',
                confidence=result.get('confidence', 0.0) or 0.0,
                language=result.get('language')
            )
        
        # Fallback: Heuristik
        return self._heuristic_detect(data)
    
    def _heuristic_detect(self, data: bytes) -> EncodingResult:
        """Einfache heuristische Erkennung."""
        # Versuche UTF-8
        try:
            data.decode('utf-8')
            return EncodingResult('utf-8', 0.9)
        except UnicodeDecodeError:
            pass
        
        # Versuche Latin-1 (akzeptiert alles)
        try:
            decoded = data.decode('latin-1')
            # Prüfe auf typische deutsche Umlaute
            if any(c in decoded for c in 'äöüÄÖÜß'):
                return EncodingResult('latin-1', 0.7)
        except (UnicodeDecodeError, LookupError):
            pass
        
        # Fallback
        return EncodingResult('latin-1', 0.5)
    
    def convert_file(self, filepath: str, 
                     target_encoding: str = "utf-8",
                     output_path: str = None,
                     source_encoding: str = None) -> ConversionResult:
        """
        Konvertiert eine Datei in ein anderes Encoding.
        
        Args:
            filepath: Quelldatei
            target_encoding: Ziel-Encoding
            output_path: Ausgabepfad (optional, überschreibt Original)
            source_encoding: Quell-Encoding (optional, wird erkannt)
            
        Returns:
            ConversionResult
        """
        path = Path(filepath)
        
        if not path.exists():
            return ConversionResult(
                success=False,
                source_encoding="",
                target_encoding=target_encoding,
                error="Datei nicht gefunden"
            )
        
        # Encoding erkennen
        if not source_encoding:
            detection = self.detect_encoding(filepath)
            if detection:
                source_encoding = detection.detected_encoding
            else:
                source_encoding = "utf-8"
        
        # Datei lesen
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read()
        except Exception as e:
            return ConversionResult(
                success=False,
                source_encoding=source_encoding,
                target_encoding=target_encoding,
                error=str(e)
            )
        
        # Dekodieren
        # BUGSWEEP-31 REVIEW-NOTIZ (NICHT auto-gefixt — Fach-/User-Entscheidung): errors='replace'
        # ersetzt nicht dekodierbare Bytes durch U+FFFD; wird das Ergebnis (atomar) zurueckgeschrieben,
        # ist der ersetzte Inhalt dauerhaft verloren. Es gibt KEINE Confidence-Schwelle vor dem
        # Schreiben. Robuster waere: bei niedriger chardet-Confidence ODER >0 Replacement-Zeichen NICHT
        # ueberschreiben, sondern warnen/abbrechen. Ändert das Reparatur-Verhalten -> bewusst belassen.
        # (Auch: chars_fixed unten zaehlt die ERZEUGTEN U+FFFD = verlorene Zeichen, nicht "gefixte".)
        try:
            text = raw_data.decode(source_encoding, errors='replace')
        except Exception as e:
            return ConversionResult(
                success=False,
                source_encoding=source_encoding,
                target_encoding=target_encoding,
                error=f"Dekodierungsfehler: {e}"
            )
        
        # Problematische Zeichen zählen
        chars_fixed = text.count('\ufffd')  # Replacement character
        
        # Enkodieren
        try:
            encoded_data = text.encode(target_encoding)
        except Exception as e:
            return ConversionResult(
                success=False,
                source_encoding=source_encoding,
                target_encoding=target_encoding,
                error=f"Enkodierungsfehler: {e}"
            )
        
        # Speichern
        # BUGSWEEP-31 (FATAL): ohne output_path wird die ORIGINALDATEI in-place ueberschrieben;
        # ein Crash/OneDrive-Lock mitten im write zerstoert sie unwiederbringlich. Atomar via
        # tmp + os.replace -> entweder vollstaendig neu geschrieben oder Original unveraendert.
        out_path = output_path or filepath
        try:
            tmp_path = f"{out_path}.tmp"
            with open(tmp_path, 'wb') as f:
                f.write(encoded_data)
            os.replace(tmp_path, out_path)
        except Exception as e:
            return ConversionResult(
                success=False,
                source_encoding=source_encoding,
                target_encoding=target_encoding,
                error=f"Schreibfehler: {e}"
            )
        
        self.logger.info(f"Konvertiert: {source_encoding} → {target_encoding}")
        
        return ConversionResult(
            success=True,
            source_encoding=source_encoding,
            target_encoding=target_encoding,
            output_path=out_path,
            chars_fixed=chars_fixed
        )
    
    def fix_mojibake(self, text: str) -> Tuple[str, int]:
        """
        Repariert Mojibake (falsch dekodierter Text).
        
        Häufig: UTF-8 wurde als Latin-1 interpretiert.
        
        Args:
            text: Beschädigter Text
            
        Returns:
            (reparierter Text, Anzahl Korrekturen)
        """
        fixes = 0
        
        # Typische Mojibake-Muster (UTF-8 als Latin-1 gelesen)
        patterns = {
            'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü',
            'Ã„': 'Ä', 'Ã–': 'Ö', 'Ãœ': 'Ü',
            'ÃŸ': 'ß',
            'â€"': '–', 'â€"': '—',
            'â€œ': '"', 'â€': '"',
            'â€˜': ''', 'â€™': ''',
            'â€¦': '…',
            'â‚¬': '€',
            'Ã©': 'é', 'Ã¨': 'è',
            'Ã ': 'à', 'Ã¡': 'á',
        }
        
        fixed_text = text
        # BUGSWEEP-31: laengste Muster zuerst ersetzen. Sonst greift der Präfix 'â€' (->'"') vor
        # 'â€˜'/'â€™'/'â€¦'/'â€"' und zerstoert diese (z.B. 'â€˜Hallo' -> '"˜Hallo' statt 'Hallo).
        for wrong, right in sorted(patterns.items(), key=lambda kv: len(kv[0]), reverse=True):
            if wrong in fixed_text:
                count = fixed_text.count(wrong)
                fixed_text = fixed_text.replace(wrong, right)
                fixes += count
        
        return fixed_text, fixes
    
    def analyze_file(self, filepath: str) -> Dict:
        """
        Analysiert eine Datei auf Encoding-Probleme.
        
        Returns:
            Dict mit Analyse-Ergebnissen
        """
        path = Path(filepath)
        
        result = {
            'filepath': str(path),
            'filename': path.name,
            'size_bytes': 0,
            'encoding': None,
            'confidence': 0.0,
            'has_bom': False,
            'problem_chars': 0,
            'non_ascii_chars': 0,
            'suggestions': []
        }
        
        if not path.exists():
            result['error'] = "Datei nicht gefunden"
            return result
        
        result['size_bytes'] = path.stat().st_size
        
        with open(filepath, 'rb') as f:
            raw_data = f.read()
        
        # BOM prüfen
        result['has_bom'] = (
            raw_data.startswith(b'\xef\xbb\xbf') or
            raw_data.startswith(b'\xff\xfe') or
            raw_data.startswith(b'\xfe\xff')
        )
        
        # Encoding erkennen
        detection = self.detect_encoding_bytes(raw_data)
        result['encoding'] = detection.detected_encoding
        result['confidence'] = detection.confidence
        
        # Dekodieren und analysieren
        try:
            text = raw_data.decode(detection.detected_encoding, errors='replace')
            
            # Non-ASCII zählen
            result['non_ascii_chars'] = sum(1 for c in text if ord(c) > 127)
            
            # Replacement-Zeichen zählen
            result['problem_chars'] = text.count('\ufffd')
            
        except Exception as e:
            result['error'] = str(e)
        
        # Empfehlungen
        if result['problem_chars'] > 0:
            result['suggestions'].append("Datei enthält nicht dekodierbare Zeichen")
        
        if not result['has_bom'] and detection.detected_encoding.lower() == 'utf-8':
            result['suggestions'].append("UTF-8 ohne BOM erkannt - für Windows evtl. BOM hinzufügen")
        
        if detection.confidence < 0.8:
            result['suggestions'].append(f"Encoding-Erkennung unsicher ({detection.confidence:.0%})")
        
        return result
    
    def batch_convert(self, filepaths: List[str],
                      target_encoding: str = "utf-8",
                      output_dir: str = None) -> List[ConversionResult]:
        """
        Konvertiert mehrere Dateien.
        
        Args:
            filepaths: Liste von Dateipfaden
            target_encoding: Ziel-Encoding
            output_dir: Ausgabeverzeichnis (optional)
            
        Returns:
            Liste von ConversionResults
        """
        results = []
        
        output_path_base = Path(output_dir) if output_dir else None
        if output_path_base:
            output_path_base.mkdir(parents=True, exist_ok=True)
        
        for filepath in filepaths:
            if output_path_base:
                output_path = str(output_path_base / Path(filepath).name)
            else:
                output_path = None
            
            result = self.convert_file(filepath, target_encoding, output_path)
            results.append(result)
        
        success_count = sum(1 for r in results if r.success)
        self.logger.info(f"Batch-Konvertierung: {success_count}/{len(results)} erfolgreich")
        
        return results


# === Hilfsfunktionen ===

def detect_file_encoding(filepath: str) -> Optional[str]:
    """Schnelle Encoding-Erkennung."""
    fixer = EncodingFixer()
    result = fixer.detect_encoding(filepath)
    return result.detected_encoding if result else None


def convert_to_utf8(filepath: str, output_path: str = None) -> bool:
    """Konvertiert eine Datei zu UTF-8."""
    fixer = EncodingFixer()
    result = fixer.convert_file(filepath, "utf-8", output_path)
    return result.success
