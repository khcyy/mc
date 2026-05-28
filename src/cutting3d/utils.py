"""Utility functions."""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

import numpy as np


def set_seed(seed: int) -> None:
    """Set random seed for reproducibility across all libraries."""
    random.seed(seed)
    np.random.seed(seed)


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def normalize_dims(dims: tuple[int, ...], gcd: int = 5) -> tuple[int, ...]:
    """Normalize dimensions by dividing by gcd."""
    return tuple(d // gcd for d in dims)


def denormalize_dims(dims: tuple[int, ...], gcd: int = 5) -> tuple[int, ...]:
    """Convert normalized dimensions back to original."""
    return tuple(d * gcd for d in dims)


def compute_volume_utilization(
    used_volume: int, total_volume: int
) -> float:
    """Compute material utilization rate."""
    if total_volume == 0:
        return 0.0
    return used_volume / total_volume


def compute_waste_volume(used_volume: int, total_volume: int) -> int:
    """Compute waste volume."""
    return total_volume - used_volume


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"
