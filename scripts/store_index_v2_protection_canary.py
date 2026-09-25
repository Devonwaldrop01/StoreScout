#!/usr/bin/env python3
"""Dedicated frozen ten-domain scope. No fallback to ordinary expansion."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from index_v2.cli import main
main(['run-canary'])
