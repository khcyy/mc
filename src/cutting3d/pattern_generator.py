"""Candidate pattern generation for 3D cutting stock.

Implements three types of pattern generators:
1. Grid-based single-piece patterns
2. Greedy constructive patterns
3. Extreme-point-based patterns
"""

from __future__ import annotations

import math
import random
from typing import Any

from .models import Material, Orientation, Pattern, Piece, PlacedPiece
from .orientations import generate_orientations
from .geometry import (
    check_all_inside,
    check_all_no_overlap,
    is_inside,
    validate_pattern,
)
from .extreme_point import ExtremePointPacker
from .pattern import compute_pattern_stats


def generate_grid_patterns(
    material: Material,
    piece: Piece,
    orientations: list[Orientation],
    pattern_id_start: int,
    max_patterns: int = 50,
) -> list[Pattern]:
    """Generate patterns by filling a material with a single piece type
    in a regular grid arrangement."""
    patterns: list[Pattern] = []
    pid = pattern_id_start

    for orient in orientations:
        dx, dy, dz = orient.dx, orient.dy, orient.dz
        if dx > material.length or dy > material.width or dz > material.height:
            continue

        # Compute how many fit in each dimension
        nx = material.length // dx
        ny = material.width // dy
        nz = material.height // dz

        total_capacity = nx * ny * nz
        if total_capacity == 0:
            continue

        # Try different fill levels
        fill_levels = [total_capacity]
        # Add some partial fills for diversity
        for ratio in [1.0, 0.9, 0.75, 0.5]:
            partial = max(1, int(total_capacity * ratio))
            if partial not in fill_levels:
                fill_levels.append(partial)

        for num_pieces in fill_levels[:5]:
            placed_pieces: list[PlacedPiece] = []
            count = 0
            for iz in range(min(nz, 20)):
                for iy in range(min(ny, 20)):
                    for ix in range(min(nx, 20)):
                        if count >= num_pieces:
                            break
                        x, y, z = ix * dx, iy * dy, iz * dz
                        if is_inside(x, y, z, dx, dy, dz, material):
                            placed_pieces.append(
                                PlacedPiece(
                                    piece_name=piece.name,
                                    x=x, y=y, z=z,
                                    orientation=orient,
                                )
                            )
                            count += 1
                    if count >= num_pieces:
                        break
                if count >= num_pieces:
                    break

            if placed_pieces:
                pattern = Pattern(
                    pattern_id=pid,
                    material_name=material.name,
                    placed_pieces=placed_pieces,
                )
                patterns.append(pattern)
                pid += 1

            if len(patterns) >= max_patterns:
                break

        if len(patterns) >= max_patterns:
            break

    return patterns


def generate_greedy_patterns(
    material: Material,
    pieces: dict[str, Piece],
    all_orientations: dict[str, list[Orientation]],
    pattern_id_start: int,
    max_patterns: int = 100,
    rng: random.Random | None = None,
) -> list[Pattern]:
    """Generate patterns using a greedy constructive approach.
    Sorts pieces by profit density and fills the material sequentially."""
    if rng is None:
        rng = random.Random(42)

    patterns: list[Pattern] = []
    pid = pattern_id_start

    # Create piece list sorted by various criteria
    piece_list = list(pieces.values())

    # Multiple sorting strategies for diversity
    strategies = [
        ("profit_density_desc", lambda p: -p.profit_density),
        ("volume_desc", lambda p: -p.volume),
        ("profit_desc", lambda p: -p.profit),
        ("volume_asc", lambda p: p.volume),
    ]

    for strategy_name, sort_key in strategies:
        sorted_pieces = sorted(piece_list, key=sort_key)

        for start_piece in sorted_pieces[:3]:  # Try different starting pieces
            placed_pieces: list[PlacedPiece] = []
            # Track occupied space using a simple grid
            occupied = _OccupancyGrid(material, grid_size=5)

            # Try placing pieces greedily
            for piece in sorted_pieces:
                orients = all_orientations[piece.name]
                best_placement = None
                best_score = -float("inf")

                for orient in orients:
                    dx, dy, dz = orient.dx, orient.dy, orient.dz
                    # Find first available position
                    for z in range(0, material.height - dz + 1, 5):
                        for y in range(0, material.width - dy + 1, 5):
                            for x in range(0, material.length - dx + 1, 5):
                                if not is_inside(x, y, z, dx, dy, dz, material):
                                    continue
                                # Check overlap with placed pieces
                                test_piece = PlacedPiece(
                                    piece_name=piece.name,
                                    x=x, y=y, z=z,
                                    orientation=orient,
                                )
                                if not _check_overlap_with_list(test_piece, placed_pieces):
                                    # Simple score: prefer lower coordinates
                                    score = -(x + y + z)
                                    if score > best_score:
                                        best_score = score
                                        best_placement = (x, y, z, orient)

                if best_placement is not None:
                    x, y, z, orient = best_placement
                    placed_pieces.append(
                        PlacedPiece(
                            piece_name=piece.name,
                            x=x, y=y, z=z,
                            orientation=orient,
                        )
                    )

            if len(placed_pieces) >= 2:  # At least 2 pieces to be useful
                # Validate
                is_valid, _ = validate_pattern(placed_pieces, material)
                if is_valid:
                    pattern = Pattern(
                        pattern_id=pid,
                        material_name=material.name,
                        placed_pieces=placed_pieces,
                    )
                    patterns.append(pattern)
                    pid += 1

            if len(patterns) >= max_patterns:
                break

        if len(patterns) >= max_patterns:
            break

    return patterns


def generate_improved_greedy_patterns(
    material: Material,
    pieces: dict[str, Piece],
    all_orientations: dict[str, list[Orientation]],
    pattern_id_start: int,
    config: dict[str, Any],
    max_patterns: int = 100,
    rng: random.Random | None = None,
) -> list[Pattern]:
    """Improved greedy constructive packing using candidate position tracking.

    Maintains a set of candidate (x,y,z) positions, iteratively places the
    best-scored piece, and updates candidate positions after each placement.

    Score = score_profit_density * profit_density_norm
          + score_volume_fill * volume_norm
          + score_contact * contact_norm
          + score_low_corner * (1 - (x+y+z)/max_extent)
          - score_fragmentation * fragment_norm
    """
    if rng is None:
        rng = random.Random(42)

    gc = config.get("greedy", {})
    max_steps = gc.get("max_steps", 1000)
    w_profit = gc.get("score_profit_density", 0.5)
    w_volume = gc.get("score_volume_fill", 1.0)
    w_contact = gc.get("score_contact", 0.3)
    w_corner = gc.get("score_low_corner", 0.2)
    w_frag = gc.get("score_fragmentation_penalty", 0.1)

    patterns: list[Pattern] = []
    pid = pattern_id_start

    # Multiple strategies for diversity
    piece_list = sorted(pieces.values(), key=lambda p: -p.profit_density)
    mat_vol = material.volume
    max_extent = material.length + material.width + material.height + 1

    # Generate patterns with different starting piece type priorities
    for strategy_offset in range(5):
        if len(patterns) >= max_patterns:
            break

        placed: list[PlacedPiece] = []
        candidates: list[tuple[int, int, int]] = [(0, 0, 0)]

        piece_order = list(piece_list)
        # Rotate priorities for diversity
        for _ in range(strategy_offset):
            piece_order = piece_order[1:] + piece_order[:1]
        if strategy_offset > 0:
            rng.shuffle(piece_order)

        for _step in range(max_steps):
            if not candidates:
                break

            best_candidate: tuple[float, PlacedPiece] | None = None
            tries = 0
            candidate_sample = candidates
            if len(candidates) > 50:
                candidate_sample = rng.sample(candidates, 50)

            for ep in candidate_sample:
                ex, ey, ez = ep
                for piece in piece_order:
                    for orient in all_orientations[piece.name]:
                        dx, dy, dz = orient.dx, orient.dy, orient.dz
                        if not is_inside(ex, ey, ez, dx, dy, dz, material):
                            continue
                        test = PlacedPiece(
                            piece_name=piece.name,
                            x=ex, y=ey, z=ez,
                            orientation=orient,
                        )
                        if _check_overlap_with_list(test, placed):
                            continue
                        tries += 1

                        # Score
                        vol_norm = test.volume / mat_vol
                        p = pieces.get(piece.name)
                        profit_norm = p.profit_density / 0.02 if p else 0.0
                        contact = _compute_contact_score(test, placed, material)
                        contact_norm = contact / (mat_vol ** (2 / 3) + 1)
                        corner_score = 1.0 - (ex + ey + ez) / max_extent
                        frag_penalty = len(candidates) * 0.0005

                        score = (
                            w_profit * profit_norm
                            + w_volume * vol_norm
                            + w_contact * contact_norm
                            + w_corner * corner_score
                            - w_frag * frag_penalty
                        )

                        if best_candidate is None or score > best_candidate[0]:
                            best_candidate = (score, test)

            if best_candidate is None:
                break

            chosen = best_candidate[1]
            placed.append(chosen)

            # Update candidate positions
            new_candidates: set[tuple[int, int, int]] = set()
            for pp in placed:
                new_candidates.add((pp.x + pp.dx, pp.y, pp.z))
                new_candidates.add((pp.x, pp.y + pp.dy, pp.z))
                new_candidates.add((pp.x, pp.y, pp.z + pp.dz))

            # Filter valid candidates
            filtered: list[tuple[int, int, int]] = []
            for pt in new_candidates:
                x, y, z = pt
                if x >= material.length or y >= material.width or z >= material.height:
                    continue
                inside_piece = False
                for pp in placed:
                    if (pp.x <= x < pp.x + pp.dx and pp.y <= y < pp.y + pp.dy
                            and pp.z <= z < pp.z + pp.dz):
                        inside_piece = True
                        break
                if not inside_piece:
                    # Remove dominated
                    dominated = False
                    for other in new_candidates:
                        if pt == other:
                            continue
                        ox, oy, oz = other
                        if ox <= x and oy <= y and oz <= z and (ox < x or oy < y or oz < z):
                            dominated = True
                            break
                    if not dominated:
                        filtered.append(pt)

            candidates = filtered

        if len(placed) >= 2:
            is_valid, _ = validate_pattern(placed, material)
            if is_valid:
                pattern = Pattern(
                    pattern_id=pid,
                    material_name=material.name,
                    placed_pieces=placed,
                )
                patterns.append(pattern)
                pid += 1

    return patterns


def _compute_contact_score(
    placed: PlacedPiece, existing: list[PlacedPiece], material: Material
) -> float:
    """Compute how much surface area the new piece shares with existing pieces and boundaries."""
    from .geometry import calculate_contact_score as ccs
    return ccs(placed, existing)


def generate_extreme_point_patterns(
    material: Material,
    pieces: dict[str, Piece],
    all_orientations: dict[str, list[Orientation]],
    pattern_id_start: int,
    config: dict[str, Any],
    max_patterns: int = 100,
    rng: random.Random | None = None,
) -> list[Pattern]:
    """Generate patterns using the Extreme Point heuristic."""
    if rng is None:
        rng = random.Random(42)

    ep_config = config.get("extreme_point", {})
    beam_width = ep_config.get("beam_width", 5)
    alpha = ep_config.get("alpha", 1.0)
    beta = ep_config.get("beta", 0.5)
    gamma = ep_config.get("gamma", 0.3)
    eta = ep_config.get("eta", 0.1)
    num_restarts = ep_config.get("random_restarts", 10)

    patterns: list[Pattern] = []
    pid = pattern_id_start

    packer = ExtremePointPacker(
        material=material,
        pieces=pieces,
        all_orientations=all_orientations,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        eta=eta,
        beam_width=beam_width,
    )

    for restart in range(min(num_restarts, 30)):
        seed = rng.randint(0, 2**31 - 1)
        placed = packer.pack(seed=seed)

        if len(placed) >= 2:
            is_valid, _ = validate_pattern(placed, material)
            if is_valid:
                pattern = Pattern(
                    pattern_id=pid,
                    material_name=material.name,
                    placed_pieces=placed,
                )
                patterns.append(pattern)
                pid += 1

        if len(patterns) >= max_patterns:
            break

    return patterns


def _check_overlap_with_list(
    test: PlacedPiece, existing: list[PlacedPiece]
) -> bool:
    """Check if test piece overlaps with any in the list."""
    from .geometry import has_overlap
    for ep in existing:
        if has_overlap(test, ep):
            return True
    return False


class _OccupancyGrid:
    """Simple occupancy grid for fast overlap checks during greedy placement."""

    def __init__(self, material: Material, grid_size: int = 5):
        self.material = material
        self.grid_size = grid_size
        self.lx = material.length // grid_size + 1
        self.ly = material.width // grid_size + 1
        self.lz = material.height // grid_size + 1
        self.grid: list[list[list[bool]]] = [
            [[False for _ in range(self.lz)] for _ in range(self.ly)]
            for _ in range(self.lx)
        ]


def generate_all_patterns(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    all_orientations: dict[str, list[Orientation]],
    config: dict[str, Any],
    max_per_material: int = 200,
) -> dict[str, list[Pattern]]:
    """Generate all candidate patterns for all materials.

    Returns dict[material_name] -> list[Pattern].
    """
    pg_config = config.get("pattern_generation", {})
    max_per = pg_config.get("max_patterns_per_material", max_per_material)
    use_grid = pg_config.get("grid_patterns", True)
    use_greedy = pg_config.get("greedy_patterns", True)
    use_ep = pg_config.get("extreme_point_patterns", True)
    seed = config.get("random_seed", 20260528)
    rng = random.Random(seed)

    all_patterns: dict[str, list[Pattern]] = {}
    global_pid = 0

    for mat_name, material in materials.items():
        mat_patterns: list[Pattern] = []

        if use_grid:
            for piece_name, piece in pieces.items():
                orients = all_orientations[piece_name]
                patterns = generate_grid_patterns(
                    material, piece, orients,
                    pattern_id_start=global_pid,
                    max_patterns=max_per // (len(pieces) * 3),
                )
                for p in patterns:
                    p.pattern_id = global_pid
                    global_pid += 1
                mat_patterns.extend(patterns)

        if use_greedy:
            greedy_mode = config.get("greedy", {}).get("mode", "legacy")
            if greedy_mode == "improved":
                patterns = generate_improved_greedy_patterns(
                    material, pieces, all_orientations,
                    pattern_id_start=global_pid,
                    config=config,
                    max_patterns=max_per // 3,
                    rng=rng,
                )
            else:
                patterns = generate_greedy_patterns(
                    material, pieces, all_orientations,
                    pattern_id_start=global_pid,
                    max_patterns=max_per // 3,
                    rng=rng,
                )
            for p in patterns:
                p.pattern_id = global_pid
                global_pid += 1
            mat_patterns.extend(patterns)

        if use_ep:
            patterns = generate_extreme_point_patterns(
                material, pieces, all_orientations,
                pattern_id_start=global_pid,
                config=config,
                max_patterns=max_per // 3,
                rng=rng,
            )
            for p in patterns:
                p.pattern_id = global_pid
                global_pid += 1
            mat_patterns.extend(patterns)

        # Deduplicate: keep patterns with unique piece count vectors
        seen_vectors: set[tuple[int, ...]] = set()
        unique_patterns: list[Pattern] = []
        piece_names = sorted(pieces.keys())
        for p in mat_patterns:
            vec = tuple(p.get_piece_counts(piece_names).get(n, 0) for n in piece_names)
            if vec not in seen_vectors and sum(vec) > 0:
                seen_vectors.add(vec)
                unique_patterns.append(p)

        # Sort by utilization
        unique_patterns.sort(
            key=lambda p: p.used_volume / material.volume if material.volume > 0 else 0,
            reverse=True,
        )
        all_patterns[mat_name] = unique_patterns[:max_per]

    return all_patterns
