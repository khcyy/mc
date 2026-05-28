"""Enumerate all non-redundant orientations for 3D pieces."""

from __future__ import annotations

import itertools

from .models import Orientation, Piece


def generate_orientations(piece: Piece) -> list[Orientation]:
    """Generate all unique orientations for a piece (90-degree rotations).

    Returns all distinct (dx, dy, dz) permutations of (length, width, height).
    """
    dims = (piece.length, piece.width, piece.height)
    seen: set[tuple[int, int, int]] = set()
    orientations: list[Orientation] = []

    for perm in itertools.permutations(dims):
        if perm not in seen:
            seen.add(perm)
            orientations.append(Orientation(dx=perm[0], dy=perm[1], dz=perm[2]))

    return orientations


def generate_all_orientations(pieces: dict[str, Piece]) -> dict[str, list[Orientation]]:
    """Generate orientations for all pieces."""
    return {name: generate_orientations(piece) for name, piece in pieces.items()}
