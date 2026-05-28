"""Data loading and management module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Material, Piece


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load YAML configuration file."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Handle extends
    if "extends" in config:
        base_path = config_path.parent / config["extends"]
        base_config = load_config(base_path)
        merged = _deep_merge(base_config, config)
        merged.pop("extends", None)
        return merged

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def create_materials(config: dict[str, Any]) -> dict[str, Material]:
    """Create Material objects from configuration."""
    materials = {}
    for name, spec in config["materials"].items():
        materials[name] = Material(
            name=name,
            length=spec["length"],
            width=spec["width"],
            height=spec["height"],
            count=spec["count"],
        )
    return materials


def create_pieces(config: dict[str, Any]) -> dict[str, Piece]:
    """Create Piece objects from configuration."""
    pieces = {}
    for name, spec in config["pieces"].items():
        pieces[name] = Piece(
            name=name,
            length=spec["length"],
            width=spec["width"],
            height=spec["height"],
            profit=spec["profit"],
        )
    return pieces


def get_default_materials() -> dict[str, Material]:
    """Return default materials as specified in the problem."""
    return {
        "L01": Material("L01", 300, 200, 150, 5),
        "L02": Material("L02", 250, 150, 100, 5),
        "L03": Material("L03", 200, 150, 80, 5),
    }


def get_default_pieces() -> dict[str, Piece]:
    """Return default pieces as specified in the problem."""
    return {
        "J01": Piece("J01", 40, 40, 40, 620),
        "J02": Piece("J02", 50, 40, 40, 780),
        "J03": Piece("J03", 60, 50, 30, 880),
        "J04": Piece("J04", 75, 60, 40, 1850),
        "J05": Piece("J05", 80, 60, 50, 2520),
        "J06": Piece("J06", 100, 50, 20, 1000),
        "J07": Piece("J07", 120, 20, 20, 540),
    }
