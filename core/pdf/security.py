#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Security
==============================
Verwaltet PDF-Verschlüsselung und Passwortschutz.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from utils.logger import LoggerMixin

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False


class EncryptionMethod(Enum):
    """Verschlüsselungsmethoden."""
    AES_128 = "AES-128"
    AES_256 = "AES-256"
    RC4_128 = "RC4-128"
    RC4_40 = "RC4-40"


class Permission(Enum):
    """PDF-Berechtigungen."""
    PRINT = "print"
    PRINT_HIGH_QUALITY = "print_highres"
    MODIFY = "modify"
    COPY = "copy"
    ANNOTATE = "annotate"
    FILL_FORMS = "fill_forms"
    EXTRACT = "extract"
    ASSEMBLE = "assemble"


@dataclass
class SecurityInfo:
    """Sicherheitsinformationen einer PDF."""
    is_encrypted: bool
    needs_password: bool
    user_password_set: bool
    owner_password_set: bool
    encryption_method: Optional[str] = None
    permissions: Optional[dict] = None


@dataclass
class UnlockResult:
    """Ergebnis einer Unlock-Operation."""
    success: bool
    output_path: str
    was_encrypted: bool
    error: Optional[str] = None


class PDFSecurity(LoggerMixin):
    """
    Verwaltet PDF-Sicherheit.
    
    Features:
    - PDF entsperren (Passwortschutz entfernen)
    - PDF verschlüsseln
    - Berechtigungen setzen
    - Sicherheitsinfo auslesen
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF nicht installiert!")
        if not PIKEPDF_AVAILABLE:
            self.logger.warning("pikepdf nicht installiert (für erweiterte Unlock-Funktionen)")
    
    def get_security_info(self, path: str) -> Optional[SecurityInfo]:
        """
        Gibt Sicherheitsinformationen einer PDF zurück.
        
        Args:
            path: Pfad zur PDF
            
        Returns:
            SecurityInfo oder None
        """
        if not PYMUPDF_AVAILABLE:
            return None
        
        try:
            doc = fitz.open(path)
            try:
                info = SecurityInfo(
                    is_encrypted=doc.is_encrypted,
                    needs_password=doc.needs_pass if doc.is_encrypted else False,
                    user_password_set=False,
                    owner_password_set=False
                )

                # Verschlüsselungsmethode ermitteln
                if doc.is_encrypted:
                    # PyMuPDF gibt nicht direkt die Methode zurück
                    info.encryption_method = "Unbekannt"
            finally:
                doc.close()
            return info

        except Exception as e:
            self.logger.error(f"Fehler beim Lesen der Sicherheitsinfo: {e}")
            return None
    
    def unlock(self, input_path: str, output_path: str,
               password: str = "") -> UnlockResult:
        """
        Entsperrt eine PDF (entfernt Passwortschutz).
        
        Versucht mehrere Methoden:
        1. Mit Passwort öffnen und unverschlüsselt speichern
        2. pikepdf für PDFs ohne User-Passwort
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            password: Passwort (falls bekannt)
            
        Returns:
            UnlockResult
        """
        if not Path(input_path).exists():
            return UnlockResult(False, output_path, False, "Datei nicht gefunden")
        
        # Methode 1: PyMuPDF
        result = self._unlock_pymupdf(input_path, output_path, password)
        if result.success:
            return result
        
        # Methode 2: pikepdf (für PDFs mit nur Owner-Passwort)
        if PIKEPDF_AVAILABLE:
            result = self._unlock_pikepdf(input_path, output_path, password)
            if result.success:
                return result
        
        return UnlockResult(False, output_path, True, "Konnte PDF nicht entsperren")
    
    def _unlock_pymupdf(self, input_path: str, output_path: str,
                        password: str) -> UnlockResult:
        """Versucht Unlock mit PyMuPDF."""
        if not PYMUPDF_AVAILABLE:
            return UnlockResult(False, output_path, False, "PyMuPDF nicht verfügbar")
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(input_path)
            was_encrypted = doc.is_encrypted

            if was_encrypted:
                # Versuche zu authentifizieren
                if doc.needs_pass:
                    if not doc.authenticate(password):
                        return UnlockResult(False, output_path, True, "Falsches Passwort")
                else:
                    # Nur Owner-Passwort, kein User-Passwort nötig
                    doc.authenticate(password)

            src = Path(input_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)

            if src == dst:
                with tempfile.NamedTemporaryFile(
                    dir=dst.parent,
                    prefix="dokuzen_sec_",
                    suffix=".tmp",
                    delete=False
                ) as tmp:
                    temp_file = Path(tmp.name)
                doc.save(str(temp_file), encryption=fitz.PDF_ENCRYPT_NONE)
            else:
                doc.save(str(dst), encryption=fitz.PDF_ENCRYPT_NONE)

            if doc is not None:
                doc.close()
                doc = None

            if temp_file and temp_file.exists():
                shutil.move(str(temp_file), str(dst))
                temp_file = None

            self.logger.info(f"PDF entsperrt: {output_path}")
            return UnlockResult(True, output_path, was_encrypted)

        except Exception as e:
            self.logger.debug(f"PyMuPDF Unlock fehlgeschlagen: {e}")
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return UnlockResult(False, output_path, True, str(e))
        finally:
            if doc is not None and not getattr(doc, "is_closed", False):
                doc.close()
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
    
    def _unlock_pikepdf(self, input_path: str, output_path: str,
                        password: str) -> UnlockResult:
        """Versucht Unlock mit pikepdf."""
        if not PIKEPDF_AVAILABLE:
            return UnlockResult(False, output_path, False, "pikepdf nicht verfügbar")

        pdf = None
        temp_file = None
        try:
            src = Path(input_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)

            safe_pw = str(password or "")
            # pikepdf kann PDFs mit nur Owner-Passwort direkt öffnen
            pdf = pikepdf.open(input_path, password=safe_pw,
                               allow_overwriting_input=True)

            if src == dst:
                with tempfile.NamedTemporaryFile(
                    dir=dst.parent,
                    prefix="dokuzen_sec_pike_",
                    suffix=".tmp",
                    delete=False
                ) as tmp:
                    temp_file = Path(tmp.name)
                pdf.save(str(temp_file))
            else:
                pdf.save(str(dst))

            if pdf is not None:
                pdf.close()
                pdf = None

            if temp_file and temp_file.exists():
                shutil.move(str(temp_file), str(dst))
                temp_file = None

            self.logger.info(f"PDF mit pikepdf entsperrt: {output_path}")
            return UnlockResult(True, output_path, True)

        except pikepdf.PasswordError:
            return UnlockResult(False, output_path, True, "Passwort erforderlich")
        except Exception as e:
            self.logger.debug(f"pikepdf Unlock fehlgeschlagen: {e}")
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return UnlockResult(False, output_path, True, str(e))
        finally:
            if pdf is not None:
                pdf.close()
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
    
    def encrypt(self, input_path: str, output_path: str,
                user_password: str = "",
                owner_password: str = "",
                method: EncryptionMethod = EncryptionMethod.AES_256,
                permissions: Optional[list] = None) -> UnlockResult:
        """
        Verschlüsselt eine PDF.
        
        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            user_password: Passwort zum Öffnen
            owner_password: Passwort für Berechtigungen
            method: Verschlüsselungsmethode
            permissions: Liste von Permission-Werten
            
        Returns:
            UnlockResult
        """
        if not PYMUPDF_AVAILABLE:
            return UnlockResult(False, output_path, False, "PyMuPDF nicht verfügbar")
        
        if not user_password and not owner_password:
            return UnlockResult(False, output_path, False, "Mindestens ein Passwort erforderlich")
        
        doc = None
        temp_file = None
        try:
            doc = fitz.open(input_path)
            # Wenn bereits verschlüsselt, erst entsperren
            if doc.is_encrypted:
                if not doc.authenticate(""):
                    return UnlockResult(False, output_path, True,
                                       "Originaldatei ist passwortgeschützt")

            # Verschlüsselungsmethode wählen
            encrypt_method = {
                EncryptionMethod.AES_256: fitz.PDF_ENCRYPT_AES_256,
                EncryptionMethod.AES_128: fitz.PDF_ENCRYPT_AES_128,
                EncryptionMethod.RC4_128: fitz.PDF_ENCRYPT_RC4_128,
                EncryptionMethod.RC4_40: fitz.PDF_ENCRYPT_RC4_40
            }.get(method, fitz.PDF_ENCRYPT_AES_256)

            # Berechtigungen
            perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY  # Standard
            if permissions:
                perm = 0
                perm_items = set()
                for p in permissions:
                    if isinstance(p, Permission):
                        perm_items.add(p)
                        perm_items.add(p.value)
                    elif isinstance(p, str):
                        perm_items.add(p.strip().lower())

                if Permission.PRINT in perm_items or "print" in perm_items:
                    perm |= fitz.PDF_PERM_PRINT
                if Permission.COPY in perm_items or "copy" in perm_items:
                    perm |= fitz.PDF_PERM_COPY
                if Permission.MODIFY in perm_items or "modify" in perm_items:
                    perm |= fitz.PDF_PERM_MODIFY
                if Permission.ANNOTATE in perm_items or "annotate" in perm_items:
                    perm |= fitz.PDF_PERM_ANNOTATE
                if Permission.FILL_FORMS in perm_items or "fill_forms" in perm_items:
                    perm |= getattr(fitz, "PDF_PERM_FORM", 256)
                if Permission.EXTRACT in perm_items or "extract" in perm_items:
                    perm |= getattr(fitz, "PDF_PERM_ACCESSIBILITY", 16)
                if Permission.ASSEMBLE in perm_items or "assemble" in perm_items:
                    perm |= getattr(fitz, "PDF_PERM_ASSEMBLE", 1024)
                if Permission.PRINT_HIGH_QUALITY in perm_items or "print_highres" in perm_items:
                    perm |= getattr(fitz, "PDF_PERM_PRINT_HQ", 2048)

            src = Path(input_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)

            if src == dst:
                with tempfile.NamedTemporaryFile(
                    dir=dst.parent,
                    prefix="dokuzen_enc_",
                    suffix=".tmp",
                    delete=False
                ) as tmp:
                    temp_file = Path(tmp.name)
                doc.save(
                    str(temp_file),
                    encryption=encrypt_method,
                    user_pw=user_password,
                    owner_pw=owner_password or user_password,
                    permissions=perm
                )
            else:
                doc.save(
                    str(dst),
                    encryption=encrypt_method,
                    user_pw=user_password,
                    owner_pw=owner_password or user_password,
                    permissions=perm
                )

            if doc is not None:
                doc.close()
                doc = None

            if temp_file and temp_file.exists():
                shutil.move(str(temp_file), str(dst))
                temp_file = None

            self.logger.info(f"PDF verschlüsselt: {output_path}")
            return UnlockResult(True, output_path, False)

        except Exception as e:
            self.logger.error(f"Verschlüsselungsfehler: {e}")
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return UnlockResult(False, output_path, False, str(e))
        finally:
            if doc is not None and not getattr(doc, "is_closed", False):
                doc.close()
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
    
    def remove_restrictions(self, input_path: str, output_path: str,
                           owner_password: str = "") -> UnlockResult:
        """
        Entfernt nur Einschränkungen (nicht das User-Passwort).

        Args:
            input_path: Eingabe-PDF
            output_path: Ausgabe-PDF
            owner_password: Owner-Passwort

        Returns:
            UnlockResult
        """
        if not PIKEPDF_AVAILABLE:
            return UnlockResult(False, output_path, False, "pikepdf erforderlich")

        pdf = None
        temp_file = None
        try:
            src = Path(input_path).resolve()
            dst = Path(output_path).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)

            safe_pw = str(owner_password or "")
            pdf = pikepdf.open(input_path, password=safe_pw, allow_overwriting_input=True)

            if src == dst:
                with tempfile.NamedTemporaryFile(
                    dir=dst.parent,
                    prefix="dokuzen_restr_",
                    suffix=".tmp",
                    delete=False
                ) as tmp:
                    temp_file = Path(tmp.name)
                pdf.save(str(temp_file))
            else:
                pdf.save(str(dst))

            if pdf is not None:
                pdf.close()
                pdf = None

            if temp_file and temp_file.exists():
                shutil.move(str(temp_file), str(dst))
                temp_file = None

            return UnlockResult(True, output_path, True)

        except Exception as e:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            temp_file = None
            return UnlockResult(False, output_path, True, str(e))
        finally:
            if pdf is not None:
                pdf.close()
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass


# === Hilfsfunktionen ===

def unlock_pdf(input_path: str, output_path: str, password: str = "") -> bool:
    """Schnelle Funktion zum Entsperren."""
    security = PDFSecurity()
    result = security.unlock(input_path, output_path, password)
    return result.success


def is_pdf_locked(path: str) -> bool:
    """Prüft ob PDF passwortgeschützt ist."""
    security = PDFSecurity()
    info = security.get_security_info(path)
    return info.needs_password if info else False


def encrypt_pdf(input_path: str, output_path: str, password: str) -> bool:
    """Schnelle Funktion zum Verschlüsseln."""
    security = PDFSecurity()
    result = security.encrypt(input_path, output_path, user_password=password)
    return result.success
