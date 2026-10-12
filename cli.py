#!/usr/bin/env python3
"""HIVEMIND CLI Convenience Entry Point.

Usage:
    python cli.py --help
    python cli.py run --days 365 --speed normal
    python cli.py inspect run <run_id>
    python cli.py branch <run_id> --tick 180 --subsidy 0.35
    python cli.py compare <run_id_a> <run_id_b>
    python cli.py replay <run_id>
    python cli.py export <run_id>
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.cli.main import app

if __name__ == "__main__":
    app()
