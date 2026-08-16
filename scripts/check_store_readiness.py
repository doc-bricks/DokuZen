#!/usr/bin/env python3
"""Wrapper script for DokuZen Windows Store readiness check."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.check_store_readiness import main

if __name__ == "__main__":
    sys.exit(main())
