#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extracts UI strings from gui/ for translation catalogs."""

import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent

patterns = [
    re.compile(r'setText\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'setWindowTitle\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'QLabel\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'QPushButton\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'QAction\s*\(\s*["\']([^"\']+)["\']\s*,'),
    re.compile(r'addMenu\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'addTab\s*\([^,]+,\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'addRow\s*\(\s*["\']([^"\']+)["\']\s*,'),
    re.compile(r'QGroupBox\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'QCheckBox\s*\(\s*["\']([^"\']+)["\']\s*\)'),
]

found = set()
for py in (root / 'gui').rglob('*.py'):
    txt = py.read_text(encoding='utf-8', errors='ignore')
    for p in patterns:
        for m in p.findall(txt):
            m_clean = m.strip()
            if m_clean and len(m_clean) > 1 and not m_clean.startswith('%') and not m_clean.startswith('{'):
                found.add(m_clean)

for s in sorted(found):
    print(repr(s))
print(f'Total strings: {len(found)}')
