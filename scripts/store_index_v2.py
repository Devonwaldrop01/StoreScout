#!/usr/bin/env python3
"""Render Docker Command: ./scripts/store_index_v2.py (no shell wrapper)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from index_v2.cli import main
main(['run'])
