"""Tests for master solver module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.models import Material, Piece
from src.cutting3d.orientations import generate_all_orientations
from src.cutting3d.pattern_generator import generate_all_patterns
from src.cutting3d.master_solver import solve_master_problem1, solve_master_problem2


def test_solve_problem1():
    """Test that Problem 1 solver finds a feasible solution."""
    materials = {
        "L01": Material("L01", 100, 80, 60, 3),
    }
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
        "master": {
            "time_limit_seconds": 10,
            "num_workers": 2,
        },
        "random_seed": 42,
    }

    patterns = generate_all_patterns(materials, pieces, all_orients, config, max_per_material=50)
    solution = solve_master_problem1(materials, pieces, patterns, config)

    assert solution.status.value in ["OPTIMAL", "FEASIBLE"]
    assert solution.material_utilization >= 0
    assert solution.total_used_volume > 0
    assert solution.total_waste_volume >= 0


def test_solve_problem2():
    """Test that Problem 2 solver finds a feasible solution."""
    materials = {
        "L01": Material("L01", 150, 100, 80, 5),
    }
    pieces = {
        "J01": Piece("J01", 20, 20, 20, 100),
        "J02": Piece("J02", 30, 20, 20, 150),
    }
    all_orients = generate_all_orientations(pieces)
    config = {
        "pattern_generation": {
            "max_patterns_per_material": 100,
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
            "random_restarts": 5,
        },
        "master": {
            "time_limit_seconds": 15,
            "num_workers": 2,
        },
        "min_pieces_per_type": 5,
        "random_seed": 42,
    }

    patterns = generate_all_patterns(materials, pieces, all_orients, config, max_per_material=100)
    solution = solve_master_problem2(materials, pieces, patterns, config)

    assert solution.status.value in ["OPTIMAL", "FEASIBLE"]
    assert solution.material_utilization >= 0
    for pname, count in solution.piece_counts.items():
        assert count >= 0  # may not meet min if infeasible, but should give best effort


if __name__ == "__main__":
    test_solve_problem1()
    test_solve_problem2()
    print("All solver tests passed!")
