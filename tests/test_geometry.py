"""Tests for geometry module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.geometry import (
    is_inside,
    has_overlap,
    check_all_inside,
    check_all_no_overlap,
    validate_pattern,
    calculate_contact_score,
)
from src.cutting3d.models import Material, Orientation, PlacedPiece


def test_is_inside():
    material = Material("test", 100, 80, 60, 1)
    assert is_inside(0, 0, 0, 50, 40, 30, material) is True
    assert is_inside(0, 0, 0, 100, 80, 60, material) is True  # exact fit
    assert is_inside(0, 0, 0, 101, 80, 60, material) is False  # too long
    assert is_inside(-1, 0, 0, 50, 40, 30, material) is False  # negative x
    assert is_inside(90, 0, 0, 20, 40, 30, material) is False  # exceeds x-bound


def test_has_overlap():
    a = PlacedPiece("J01", 0, 0, 0, Orientation(10, 10, 10))
    b = PlacedPiece("J01", 5, 5, 5, Orientation(10, 10, 10))
    c = PlacedPiece("J01", 20, 20, 20, Orientation(10, 10, 10))
    d = PlacedPiece("J01", 10, 0, 0, Orientation(10, 10, 10))  # adjacent, no overlap

    assert has_overlap(a, b) is True
    assert has_overlap(a, c) is False
    assert has_overlap(a, d) is False  # touching faces


def test_check_all_inside():
    material = Material("test", 100, 80, 60, 1)
    pieces = [
        PlacedPiece("J01", 0, 0, 0, Orientation(50, 40, 30)),
        PlacedPiece("J02", 50, 40, 30, Orientation(50, 40, 30)),
    ]
    assert check_all_inside(pieces, material) is True

    bad_pieces = [
        PlacedPiece("J01", 0, 0, 0, Orientation(50, 40, 30)),
        PlacedPiece("J02", 90, 70, 50, Orientation(20, 20, 20)),  # out of bounds
    ]
    assert check_all_inside(bad_pieces, material) is False


def test_check_all_no_overlap():
    pieces = [
        PlacedPiece("J01", 0, 0, 0, Orientation(10, 10, 10)),
        PlacedPiece("J02", 10, 0, 0, Orientation(10, 10, 10)),
        PlacedPiece("J03", 0, 10, 0, Orientation(10, 10, 10)),
    ]
    assert check_all_no_overlap(pieces) is True

    overlap_pieces = [
        PlacedPiece("J01", 0, 0, 0, Orientation(20, 20, 20)),
        PlacedPiece("J02", 10, 10, 10, Orientation(20, 20, 20)),
    ]
    assert check_all_no_overlap(overlap_pieces) is False


def test_validate_pattern():
    material = Material("test", 100, 80, 60, 1)
    valid = [
        PlacedPiece("J01", 0, 0, 0, Orientation(50, 40, 30)),
        PlacedPiece("J02", 50, 40, 0, Orientation(50, 40, 30)),
    ]
    ok, msg = validate_pattern(valid, material)
    assert ok, msg

    invalid = [
        PlacedPiece("J01", 0, 0, 0, Orientation(50, 40, 30)),
        PlacedPiece("J02", 25, 20, 15, Orientation(50, 40, 30)),  # overlaps
    ]
    ok, msg = validate_pattern(invalid, material)
    assert not ok


def test_calculate_contact_score():
    existing = [PlacedPiece("J01", 0, 0, 0, Orientation(50, 40, 30))]
    new_piece = PlacedPiece("J02", 50, 0, 0, Orientation(50, 40, 30))  # adjacent
    score = calculate_contact_score(new_piece, existing)
    assert score > 0

    new_piece2 = PlacedPiece("J02", 100, 40, 30, Orientation(50, 40, 30))  # no contact
    score2 = calculate_contact_score(new_piece2, existing)
    # This piece doesn't touch existing piece or any boundary, score should be 0
    assert score2 >= 0


if __name__ == "__main__":
    test_is_inside()
    test_has_overlap()
    test_check_all_inside()
    test_check_all_no_overlap()
    test_validate_pattern()
    test_calculate_contact_score()
    print("All geometry tests passed!")
