#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen - Workspace Export Module
=================================
Erstellt redigierte, datenschutzfreundliche Arbeitsbereich-Snapshots
(dokuzen-workspace-v1.json) für Offline-Archivierung und mobile PWA-Begleiter.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core import __version__ as APP_VERSION

SCHEMA_NAME = "dokuzen-workspace-v1"
SCHEMA_VERSION = 1
APP_NAME = "DokuZen"

_PLATFORM_MAP = {
    "win32": "windows",
    "darwin": "macos",
    "linux": "linux",
}

SAFE_SETTINGS_KEYS = (
    "theme",
    "language",
    "ocr_language",
    "auto_save",
    "auto_save_interval_sec",
    "duplicate_check",
    "default_theme",
    "pdf_dpi",
    "image_quality",
    "default_encoding",
    "clipboard_format",
    "fuzzy_threshold",
)

FORBIDDEN_SETTINGS_KEYS = (
    "last_directory",
    "window_state",
    "window_geometry",
    "tesseract_path",
    "master_password",
    "output_directory",
    "state_file",
    "hotkey",
    "secrets",
    "api_key",
    "token",
)


def _looks_like_absolute_path(value: str) -> bool:
    """Prüft, ob ein String wie ein absoluter lokaler Pfad aussieht."""
    if not isinstance(value, str):
        return False
    if len(value) >= 3 and value[1] == ":" and value[2] in ("\\", "/"):
        return True
    if value.startswith(("\\\\", "//", "/home", "/Users", "/root", "/var", "/tmp", "/etc", "/opt")):
        return True
    return False


def sanitize_settings(settings: Optional[Union[Dict[str, Any], Any]]) -> Dict[str, Any]:
    """Extrahiert ausschließlich sichere Einstellungsschlüssel.

    Entfernt Pfade, Fenstergeometrien, Passwörter und tokens.
    """
    if not settings:
        return {
            "theme": "light",
            "language": "de",
            "ocr_language": "deu+eng",
            "duplicate_check": True,
            "default_theme": "Allgemein",
        }

    raw_dict: Dict[str, Any] = {}
    if hasattr(settings, "get_all") and callable(settings.get_all):
        raw_dict = settings.get_all()
    elif hasattr(settings, "_settings") and isinstance(settings._settings, dict):
        raw_dict = settings._settings
    elif isinstance(settings, dict):
        raw_dict = settings

    sanitized: Dict[str, Any] = {}

    def _extract_flat(d: Dict[str, Any], prefix: str = ""):
        for k, v in d.items():
            full_key = f"{prefix}{k}" if prefix else k
            if isinstance(v, dict) and k not in ("window_state", "credentials"):
                _extract_flat(v, prefix=f"{k}_")
            else:
                for safe_key in SAFE_SETTINGS_KEYS:
                    if k == safe_key or full_key.endswith(f"_{safe_key}"):
                        if not (isinstance(v, str) and _looks_like_absolute_path(v)):
                            sanitized[safe_key] = v

    _extract_flat(raw_dict)

    sanitized.setdefault("theme", "light")
    sanitized.setdefault("language", "de")
    sanitized.setdefault("ocr_language", "deu+eng")
    sanitized.setdefault("duplicate_check", True)
    sanitized.setdefault("default_theme", "Allgemein")

    for forbidden in FORBIDDEN_SETTINGS_KEYS:
        sanitized.pop(forbidden, None)

    return sanitized


def sanitize_document(doc: Any) -> Dict[str, Any]:
    """Sanitisiert einen Dokumenteneintrag.

    Entfernt absolute Systempfade und gibt nur Dateiname und Erweiterung weiter.
    """
    if isinstance(doc, dict):
        raw_path = str(doc.get("path") or "")
        tags = list(doc.get("tags") or [])
        is_read = bool(doc.get("is_read", False))
        read_date = doc.get("read_date")
        added = doc.get("added")
        notes = str(doc.get("notes") or "").strip()
        custom_name = str(doc.get("name") or "")
    else:
        raw_path = getattr(doc, "path", "")
        tags = list(getattr(doc, "tags", []))
        is_read = bool(getattr(doc, "is_read", False))
        read_date = getattr(doc, "read_date", None)
        if hasattr(read_date, "isoformat"):
            read_date = read_date.isoformat()
        added = getattr(doc, "added", None)
        if hasattr(added, "isoformat"):
            added = added.isoformat()
        notes = str(getattr(doc, "notes", "") or "").strip()
        custom_name = getattr(doc, "name", "")

    p = Path(raw_path) if raw_path else None
    filename = custom_name if (custom_name and not _looks_like_absolute_path(custom_name)) else (p.name if p else "unnamed")
    ext = p.suffix.lower() if p else ""
    if not ext and "." in filename:
        ext = f".{filename.rsplit('.', 1)[-1].lower()}"

    size_bytes = 0
    if hasattr(doc, "size"):
        try:
            size_bytes = int(doc.size)
        except Exception:
            size_bytes = 0
    elif isinstance(doc, dict) and "size" in doc:
        try:
            size_bytes = int(doc["size"])
        except Exception:
            size_bytes = 0

    return {
        "filename": filename,
        "extension": ext,
        "is_read": is_read,
        "read_date": str(read_date) if read_date else None,
        "tags": [str(t).strip() for t in tags if str(t).strip()],
        "notes": notes,
        "size_bytes": size_bytes,
        "added": str(added) if added else None,
    }


def enumerate_forms(forms: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """Sanitisiert Formulare für den Export."""
    if not forms:
        return []
    sanitized = []
    for f in forms:
        if isinstance(f, dict):
            name = str(f.get("name") or f.get("title") or "Formular").strip()
            fields = f.get("fields") or f.get("elements") or []
            sanitized.append({
                "name": name,
                "field_count": len(fields),
                "title": str(f.get("title") or name),
                "page_size": f.get("page_size", [210, 297]),
            })
        elif hasattr(f, "to_dict") and callable(f.to_dict):
            d = f.to_dict()
            fields = d.get("fields", [])
            sanitized.append({
                "name": getattr(f, "name", "Formular"),
                "field_count": len(fields),
                "title": getattr(f, "title", getattr(f, "name", "Formular")),
                "page_size": getattr(f, "page_size", (210, 297)),
            })
    return sanitized


def build_workspace_snapshot(
    library: Optional[Any] = None,
    settings: Optional[Union[Dict[str, Any], Any]] = None,
    forms: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Erstellt einen redigierten, datenschutzsicheren Arbeitsbereich-Snapshot.

    Garantien:
    - Keine absoluten Pfade in Dokumenten oder Einstellungen
    - Keine Passwörter oder Anmeldedaten
    - Keine rohen Dateiinhalte eingebettet
    """
    safe_settings = sanitize_settings(settings)
    platform_name = _PLATFORM_MAP.get(sys.platform, sys.platform)

    themes_list: List[Dict[str, Any]] = []
    documents_list: List[Dict[str, Any]] = []

    if library is not None:
        if hasattr(library, "themes") and hasattr(library.themes, "get_all_themes"):
            all_themes_raw = library.themes.get_all_themes()
            for t_item in all_themes_raw:
                if hasattr(t_item, "name"):
                    t_name = t_item.name
                    doc_count = getattr(t_item, "document_count", 0)
                    read_count = getattr(t_item, "read_count", 0)
                else:
                    t_name = str(t_item)
                    t_obj = getattr(library.themes, "get_theme", lambda _: None)(t_name) if hasattr(library.themes, "get_theme") else None
                    doc_count = t_obj.document_count if t_obj else 0
                    read_count = t_obj.read_count if t_obj else 0
                themes_list.append({
                    "name": t_name,
                    "document_count": doc_count,
                    "read_count": read_count,
                })
                docs = library.get_documents(theme=t_name) if hasattr(library, "get_documents") else []
                for d in docs:
                    s_doc = sanitize_document(d)
                    s_doc["theme"] = t_name
                    documents_list.append(s_doc)

        elif hasattr(library, "get_all_themes") and callable(library.get_all_themes):
            all_theme_names = library.get_all_themes()
            for t_name in all_theme_names:
                docs = library.get_documents(t_name) if hasattr(library, "get_documents") else []
                themes_list.append({
                    "name": t_name,
                    "document_count": len(docs),
                    "read_count": sum(1 for d in docs if getattr(d, "is_read", False) or (isinstance(d, dict) and d.get("is_read"))),
                })
                for d in docs:
                    s_doc = sanitize_document(d)
                    s_doc["theme"] = t_name
                    documents_list.append(s_doc)

        elif isinstance(library, dict) and "themes" in library:
            for t_name, t_data in library["themes"].items():
                docs = t_data.get("documents", []) if isinstance(t_data, dict) else []
                themes_list.append({
                    "name": t_name,
                    "document_count": len(docs),
                    "read_count": sum(1 for d in docs if d.get("is_read")),
                })
                for d in docs:
                    s_doc = sanitize_document(d)
                    s_doc["theme"] = t_name
                    documents_list.append(s_doc)

    if not themes_list:
        themes_list.append({
            "name": safe_settings.get("default_theme", "Allgemein"),
            "document_count": len(documents_list),
            "read_count": 0,
        })

    sanitized_forms = enumerate_forms(forms)

    snapshot: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "export_app": APP_NAME,
        "app_version": APP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_platform": platform_name,
        "redaction": {
            "raw_documents_embedded": False,
            "absolute_paths_included": False,
            "secrets_included": False,
        },
        "settings": safe_settings,
        "themes": themes_list,
        "documents": documents_list,
        "forms": sanitized_forms,
        "companion_hints": {
            "recommended_mode": "read_only",
            "can_import_settings": False,
            "can_preview_forms": True,
            "can_show_job_summary": True,
            "can_filter_by_theme": True,
        },
        "totals": {
            "theme_count": len(themes_list),
            "document_count": len(documents_list),
            "form_count": len(sanitized_forms),
            "read_document_count": sum(1 for d in documents_list if d.get("is_read")),
        },
    }

    return snapshot


def validate_workspace_snapshot(data: Any) -> bool:
    """Prüft, ob ein Dictionary dem Schema dokuzen-workspace-v1 entspricht."""
    if not isinstance(data, dict):
        return False
    if data.get("schema") not in (SCHEMA_NAME, "textbrain-workspace-v1"):
        return False
    if data.get("schema_version") != 1:
        return False
    if "redaction" not in data or not isinstance(data["redaction"], dict):
        return False
    if data["redaction"].get("absolute_paths_included") is not False:
        return False

    for doc in data.get("documents", []):
        if not isinstance(doc, dict):
            return False
        fn = doc.get("filename", "")
        if _looks_like_absolute_path(fn):
            return False

    for k, v in data.get("settings", {}).items():
        if k in FORBIDDEN_SETTINGS_KEYS:
            return False
        if isinstance(v, str) and _looks_like_absolute_path(v):
            return False

    return True


def export_workspace_to_file(
    filepath: Union[str, Path],
    library: Optional[Any] = None,
    settings: Optional[Union[Dict[str, Any], Any]] = None,
    forms: Optional[List[Any]] = None,
) -> Path:
    """Schreibt den Workspace-Snapshot atomar als JSON-Datei."""
    target_path = Path(filepath).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot = build_workspace_snapshot(library=library, settings=settings, forms=forms)

    if not validate_workspace_snapshot(snapshot):
        raise ValueError("Erstellter Workspace-Snapshot ist ungültig oder enthält verbotene Pfade")

    temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp.{os.getpid()}")
    try:
        content = json.dumps(snapshot, ensure_ascii=False, indent=2)
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(target_path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise

    return target_path
