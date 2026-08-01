#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - PDF Security
==============================
Verwaltet PDF-Verschlüsselung und Passwortschutz.
"""

from pathlib import Path
from typing import Optional, Tuple
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
        
        try:
            doc = fitz.open(input_path)
            try:
                was_encrypted = doc.is_encrypted

                if was_encrypted:
                    # Versuche zu authentifizieren
                    if doc.needs_pass:
                        if not doc.authenticate(password):
                            return UnlockResult(False, output_path, True, "Falsches Passwort")
                    else:
                        # Nur Owner-Passwort, kein User-Passwort nötig
                        doc.authenticate(password)

                # Unverschlüsselt speichern
                doc.save(output_path, encryption=fitz.PDF_ENCRYPT_NONE)
            finally:
                doc.close()

            self.logger.info(f"PDF entsperrt: {output_path}")
            return UnlockResult(True, output_path, was_encrypted)

        except Exception as e:
            self.logger.debug(f"PyMuPDF Unlock fehlgeschlagen: {e}")
            return UnlockResult(False, output_path, True, str(e))
    
    def _unlock_pikepdf(self, input_path: str, output_path: str,
                        password: str) -> UnlockResult:
        """Versucht Unlock mit pikepdf."""
        if not PIKEPDF_AVAILABLE:
            return UnlockResult(False, output_path, False, "pikepdf nicht verfügbar")

        pdf = None
        try:
            # pikepdf kann PDFs mit nur Owner-Passwort direkt öffnen
            pdf = pikepdf.open(input_path, password=password or None,
                               allow_overwriting_input=False)

            # Unverschlüsselt speichern
            pdf.save(output_path)

            self.logger.info(f"PDF mit pikepdf entsperrt: {output_path}")
            return UnlockResult(True, output_path, True)

        except pikepdf.PasswordError:
            return UnlockResult(False, output_path, True, "Passwort erforderlich")
        except Exception as e:
            self.logger.debug(f"pikepdf Unlock fehlgeschlagen: {e}")
            return UnlockResult(False, output_path, True, str(e))
        finally:
            if pdf is not None:
                pdf.close()
    
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
        
        try:
            doc = fitz.open(input_path)
            try:
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
                    if Permission.PRINT in permissions:
                        perm |= fitz.PDF_PERM_PRINT
                    if Permission.COPY in permissions:
                        perm |= fitz.PDF_PERM_COPY
                    if Permission.MODIFY in permissions:
                        perm |= fitz.PDF_PERM_MODIFY
                    if Permission.ANNOTATE in permissions:
                        perm |= fitz.PDF_PERM_ANNOTATE

                # Verschlüsselt speichern
                doc.save(
                    output_path,
                    encryption=encrypt_method,
                    user_pw=user_password,
                    owner_pw=owner_password or user_password,
                    permissions=perm
                )
            finally:
                doc.close()

            self.logger.info(f"PDF verschlüsselt: {output_path}")
            return UnlockResult(True, output_path, False)

        except Exception as e:
            self.logger.error(f"Verschlüsselungsfehler: {e}")
            return UnlockResult(False, output_path, False, str(e))
    
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
        try:
            pdf = pikepdf.open(input_path, password=owner_password or None)

            # Ohne Verschlüsselung speichern entfernt auch Einschränkungen
            pdf.save(output_path)

            return UnlockResult(True, output_path, True)

        except Exception as e:
            return UnlockResult(False, output_path, True, str(e))
        finally:
            if pdf is not None:
                pdf.close()


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
