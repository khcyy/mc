"""Tests for pattern generator module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.models import Material, Piece
from src.cutting3d.orientations import generate_orientations, generate_all_orientations
from src.cutting3d.pattern_generator import (
    generate_grid_patterns,
    generate_greedy_patterns,
    generate_all_patterns,
)
from src.cutting3d.geometry import validate_pattern


def test_generate_grid_patterns():
    material = Material("test", 100, 80, 60, 1)
    piece = Piece("J01", 20, 20, 20, 100)
    orients = generate_orientations(piece)

    patterns = generate_grid_patterns(material, piece, orients, 0, max_patterns=20)
    assert len(patterns) > 0
    for p in patterns:
        assert p.material_name == "test"
        is_valid, msg = validate_pattern(p.placed_pieces, material)
        assert is_valid, f"Pattern {p.pattern_id}: {msg}"


def test_generate_greedy_patterns():
    material = Material("test", 100, 80, 60, 1)
    pieces = {
        "J01": Piece("J01", 20, 20, 20, 100),
        "J02": Piece("J02", 30, 20, 20, 150),
    }
    all_orients = generate_all_orientations(pieces)

    patterns = generate_greedy_patterns(
        material, pieces, all_orients, 0, max_patterns=10
    )
    # May be empty for small materials, but typically generates something
    for p in patterns:
        is_valid, msg = validate_pattern(p.placed_pieces, material)
        assert is_valid, f"Pattern {p.pattern_id}: {msg}"


def test_generate_all_patterns():
    materials = {"L01": Material("L01", 100, 80, 60, 1)}
    pieces = {
        "J01": Piece("J01", 20, 20, 20, 100),
        "J02": Piece("J02", 30, 20, 20, 150),
    }
    all_orients = generate_all_orientations(pieces)
    config = {
        "pattern_generation": {
            "max_patterns_per_material": 50,
            "grid_patterns": True,
            "greedy_patterns": True,
            "extreme_point_patterns": True,
        },
        "extreme_point": {
            "beam_width": 3,
            "alpha": 1.0,
            "beta": 0.5,
            "gamma": 0.3,
            "eta": 0.1,
            "random_restarts": 3,
        },
        "random_seed": 42,
    }

    patterns = generate_all_patterns(materials, pieces, all_orients, config, max_per_material=50)
    assert "L01" in patterns
    assert len(patterns["L01"]) > 0


if __name__ == "__main__":
    test_generate_grid_patterns()
    test_generate_greedy_patterns()
    test_generate_all_patterns()
    print("All pattern generator tests passed!")
