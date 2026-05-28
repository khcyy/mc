"""Logging configuration and utilities."""

from __future__ import annotations

import logging
import sys
import platform
from datetime import datetime
from pathlib import Path

import numpy as np


def setup_logging(
    log_dir: str | Path,
    seed: int,
    config_path: str | None = None,
) -> logging.Logger:
    """Set up logging to file and console.

    Creates a timestamped log file in log_dir.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"run_{timestamp}.log"

    logger = logging.getLogger("cutting3d")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 60)
    logger.info("3D Cutting Stock Optimization - Experimental Log")
    logger.info("=" * 60)
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Random seed: {seed}")
    if config_path:
        logger.info(f"Config path: {config_path}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    return logger


def log_versions(logger: logging.Logger) -> None:
    """Log versions of key dependencies."""
    try:
        import ortools
        logger.info(f"OR-Tools version: {ortools.__version__}")
    except ImportError:
        logger.warning("OR-Tools not installed")
    try:
        import numpy as np
        logger.info(f"NumPy version: {np.__version__}")
    except ImportError:
        logger.warning("NumPy not installed")
    try:
        import pandas as pd
        logger.info(f"Pandas version: {pd.__version__}")
    except ImportError:
        logger.warning("Pandas not installed")
    try:
        import matplotlib
        logger.info(f"Matplotlib version: {matplotlib.__version__}")
    except ImportError:
        logger.warning("Matplotlib not installed")
    try:
        import openpyxl
        logger.info(f"openpyxl version: {openpyxl.__version__}")
    except ImportError:
        logger.warning("openpyxl not installed")
    try:
        import yaml
        logger.info(f"PyYAML version: {yaml.__version__}")
    except ImportError:
        logger.warning("PyYAML not installed")
