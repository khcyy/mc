#!/usr/bin/env python3
"""One-click runner for the complete 3D Cutting Stock Optimization pipeline.

Usage:
    python run_all.py
    python run_all.py --skip-ablation --skip-sensitivity
    python run_all.py --only-plots
    python run_all.py --only-fill-excel
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_all_experiments import main

if __name__ == "__main__":
    main()
