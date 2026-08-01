#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DokuZen Pro - Spawner Plugins Module"""
from .clipboard_monitor import ClipboardMonitor, ClipboardSaver, ClipboardContent
from .tray_plugin import TrayPlugin, SpawnerService
from .registry import RegistryManager, DokuZenRegistry, ContextMenuItem, ContextMenuTarget

__all__ = [
    "ClipboardMonitor",
    "ClipboardSaver",
    "ClipboardContent",
    "TrayPlugin",
    "SpawnerService",
    "RegistryManager",
    "DokuZenRegistry",
    "ContextMenuItem",
    "ContextMenuTarget"
]
