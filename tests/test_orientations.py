"""Tests for orientations module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.orientations import generate_orientations, generate_all_orientations
from src.cutting3d.models import Piece


def test_generate_orientations_unique():
    piece = Piece("test", 40, 40, 40, 100)
    orients = generate_orientations(piece)
    assert len(orients) == 1  # cube has only 1 unique orientation


def test_generate_orientations_rectangular():
    piece = Piece("test", 50, 40, 30, 100)
    orients = generate_orientations(piece)
    # All 3! = 6 permutations are unique for distinct dimensions
    assert len(orients) == 6


def test_generate_orientations_symmetric():
    piece = Piece("test", 50, 50, 30, 100)
    orients = generate_orientations(piece)
    # Two equal dimensions: fewer unique permutations
    assert len(orients) == 3  # (50,50,30), (50,30,50), (30,50,50)


def test_generate_all_orientations():
    pieces = {
        "J01": Piece("J01", 40, 40, 40, 620),
        "J02": Piece("J02", 50, 40, 40, 780),
    }
    all_orients = generate_all_orientations(pieces)
    assert len(all_orients["J01"]) == 1
    assert len(all_orients["J02"]) == 3  # two dims equal


if __name__ == "__main__":
    test_generate_orientations_unique()
    test_generate_orientations_rectangular()
    test_generate_orientations_symmetric()
    test_generate_all_orientations()
    print("All orientation tests passed!")
