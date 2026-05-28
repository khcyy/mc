"""Extreme Point heuristic for 3D packing.

Implements the Extreme Point / Maximal Space concept for constructive
3D packing of rectangular items into a rectangular container.
"""

from __future__ import annotations

import random
from typing import Any

from .models import Material, Orientation, Piece, PlacedPiece
from .geometry import (
    has_overlap,
    is_inside,
    calculate_contact_score,
)


def _compute_fragmentation_penalty(
    placed: list[PlacedPiece], material: Material
) -> float:
    """Estimate fragmentation penalty: how much the remaining space is fragmented.

    Higher penalty = more fragmented = worse.
    Simplified: count number of extreme points as proxy for fragmentation.
    """
    eps = _compute_extreme_points(placed, material)
    return len(eps) * 0.001


class ExtremePointPacker:
    """Extreme Point based 3D packer.

    Places pieces one by one, each time selecting the best position
    from the current set of extreme points based on a scoring function.
    """

    def __init__(
        self,
        material: Material,
        pieces: dict[str, Piece],
        all_orientations: dict[str, list[Orientation]],
        alpha: float = 1.0,
        beta: float = 0.5,
        gamma: float = 0.3,
        eta: float = 0.1,
        beam_width: int = 5,
    ):
        self.material = material
        self.pieces = pieces
        self.all_orientations = all_orientations
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.eta = eta
        self.beam_width = beam_width

        self._piece_list = list(pieces.values())

    def pack(self, seed: int | None = None) -> list[PlacedPiece]:
        """Run the extreme point packing heuristic.

        Args:
            seed: Random seed for reproducibility.

        Returns:
            List of PlacedPiece objects representing the packing.
        """
        rng = random.Random(seed)
        placed: list[PlacedPiece] = []

        # Shuffle piece list for randomness
        piece_order = list(self._piece_list)
        rng.shuffle(piece_order)

        # Iterative placement
        max_iterations = 1000
        for _ in range(max_iterations):
            eps = _compute_extreme_points(placed, self.material)
            if not eps:
                break

            candidates: list[tuple[float, PlacedPiece]] = []

            # Evaluate each extreme point with each piece and orientation
            # Sample to limit computation
            sampled_eps = eps
            if len(eps) > self.beam_width * 3:
                sampled_eps = rng.sample(eps, self.beam_width * 3)

            for ep in sampled_eps:
                ex, ey, ez = ep
                for piece in piece_order:
                    for orient in self.all_orientations[piece.name]:
                        dx, dy, dz = orient.dx, orient.dy, orient.dz
                        if not is_inside(ex, ey, ez, dx, dy, dz, self.material):
                            continue

                        # Check overlap with already placed pieces
                        test = PlacedPiece(
                            piece_name=piece.name,
                            x=ex, y=ey, z=ez,
                            orientation=orient,
                        )
                        if _check_overlap(test, placed):
                            continue

                        # Compute score
                        score = self._score(test, placed)
                        candidates.append((score, test))

            if not candidates:
                break

            # Sort by score descending and add jitter for diversity
            candidates.sort(key=lambda x: -x[0])
            top_k = candidates[: self.beam_width]
            # Select from top-k with probability proportional to score
            if len(top_k) > 1:
                total_score = sum(max(0.01, c[0]) for c in top_k)
                pick = rng.random() * total_score
                cumsum = 0.0
                chosen = top_k[0]
                for c in top_k:
                    cumsum += max(0.01, c[0])
                    if pick <= cumsum:
                        chosen = c
                        break
            else:
                chosen = top_k[0]

            placed.append(chosen[1])

        return placed

    def _score(
        self, piece: PlacedPiece, existing: list[PlacedPiece]
    ) -> float:
        """Score a placement candidate.

        Score = alpha * volume_fill + beta * profit_density
                + gamma * contact_score - eta * fragmentation_penalty
        """
        vol = piece.volume
        p = self.pieces.get(piece.piece_name)
        profit_density = p.profit_density if p else 0.0
        contact = calculate_contact_score(piece, existing)

        # Normalize
        mat_vol = self.material.volume
        vol_norm = vol / mat_vol if mat_vol > 0 else 0.0
        contact_norm = contact / (mat_vol ** (2 / 3) + 1)
        profit_norm = profit_density / 100.0  # scale to similar range

        total_score = (
            self.alpha * vol_norm
            + self.beta * profit_norm
            + self.gamma * contact_norm
        )

        # Add small random perturbation for diversity
        perturbation = random.uniform(0, 0.01)
        return total_score + perturbation

    def pack_multiple(
        self, num_trials: int = 10, base_seed: int = 42
    ) -> list[list[PlacedPiece]]:
        """Run multiple packing trials with different seeds."""
        results: list[list[PlacedPiece]] = []
        for i in range(num_trials):
            placed = self.pack(seed=base_seed + i * 100)
            if placed:
                results.append(placed)
        return results


def _compute_extreme_points(
    placed: list[PlacedPiece], material: Material
) -> list[tuple[int, int, int]]:
    """Compute current extreme points given placed pieces.

    An extreme point is a candidate position where a new piece can be placed.
    It is generated by projecting the faces of placed pieces.
    """
    if not placed:
        return [(0, 0, 0)]

    points: set[tuple[int, int, int]] = set()

    # Origin is always a candidate
    points.add((0, 0, 0))

    for pp in placed:
        # Points at the max extent of each placed piece
        candidates = [
            (pp.x + pp.dx, pp.y, pp.z),
            (pp.x, pp.y + pp.dy, pp.z),
            (pp.x, pp.y, pp.z + pp.dz),
            (pp.x + pp.dx, pp.y + pp.dy, pp.z),
            (pp.x + pp.dx, pp.y, pp.z + pp.dz),
            (pp.x, pp.y + pp.dy, pp.z + pp.dz),
            (pp.x + pp.dx, pp.y + pp.dy, pp.z + pp.dz),
        ]

        for pt in candidates:
            # Check if point is inside material
            if (
                0 <= pt[0] < material.length
                and 0 <= pt[1] < material.width
                and 0 <= pt[2] < material.height
            ):
                points.add(pt)

    # Remove points that are inside any placed piece
    valid_points: list[tuple[int, int, int]] = []
    for pt in points:
        x, y, z = pt
        is_valid = True
        for pp in placed:
            if (
                pp.x <= x < pp.x + pp.dx
                and pp.y <= y < pp.y + pp.dy
                and pp.z <= z < pp.z + pp.dz
            ):
                is_valid = False
                break
        if is_valid:
            valid_points.append(pt)

    # Remove dominated points
    filtered: list[tuple[int, int, int]] = []
    for pt in valid_points:
        dominated = False
        for other in valid_points:
            if pt == other:
                continue
            if (
                other[0] <= pt[0]
                and other[1] <= pt[1]
                and other[2] <= pt[2]
                and (
                    other[0] < pt[0]
                    or other[1] < pt[1]
                    or other[2] < pt[2]
                )
            ):
                dominated = True
                break
        if not dominated:
            filtered.append(pt)

    return filtered


def _check_overlap(
    test: PlacedPiece, existing: list[PlacedPiece]
) -> bool:
    """Check if test piece overlaps with any existing piece."""
    for ep in existing:
        if has_overlap(test, ep):
            return True
    return False
