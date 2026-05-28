"""3D geometry utilities: overlap detection, containment check."""

from __future__ import annotations

from .models import Material, Orientation, PlacedPiece


def is_inside(
    x: int, y: int, z: int,
    dx: int, dy: int, dz: int,
    material: Material,
) -> bool:
    """Check if a piece with origin (x,y,z) and dimensions (dx,dy,dz)
    is fully inside the material."""
    return (
        x >= 0
        and y >= 0
        and z >= 0
        and x + dx <= material.length
        and y + dy <= material.width
        and z + dz <= material.height
    )


def check_overlap_1d(a_min: int, a_max: int, b_min: int, b_max: int) -> bool:
    """Check if two 1D intervals overlap. Intervals are [min, max)."""
    return a_min < b_max and b_min < a_max


def has_overlap(a: PlacedPiece, b: PlacedPiece) -> bool:
    """Check if two placed pieces overlap in 3D."""
    return (
        check_overlap_1d(a.x, a.x + a.dx, b.x, b.x + b.dx)
        and check_overlap_1d(a.y, a.y + a.dy, b.y, b.y + b.dy)
        and check_overlap_1d(a.z, a.z + a.dz, b.z, b.z + b.dz)
    )


def check_all_no_overlap(pieces: list[PlacedPiece]) -> bool:
    """Verify no pair of placed pieces overlap."""
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            if has_overlap(pieces[i], pieces[j]):
                return False
    return True


def check_all_inside(pieces: list[PlacedPiece], material: Material) -> bool:
    """Verify all placed pieces are inside the material."""
    for pp in pieces:
        if not is_inside(pp.x, pp.y, pp.z, pp.dx, pp.dy, pp.dz, material):
            return False
    return True


def validate_pattern(pieces: list[PlacedPiece], material: Material) -> tuple[bool, str]:
    """Validate a pattern: all pieces inside material and no overlaps.

    Returns (is_valid, error_message).
    """
    errors: list[str] = []

    for i, pp in enumerate(pieces):
        if not is_inside(pp.x, pp.y, pp.z, pp.dx, pp.dy, pp.dz, material):
            errors.append(
                f"Piece {i} ({pp.piece_name}) at ({pp.x},{pp.y},{pp.z}) "
                f"size ({pp.dx},{pp.dy},{pp.dz}) exceeds material "
                f"({material.length},{material.width},{material.height})"
            )

    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            if has_overlap(pieces[i], pieces[j]):
                errors.append(
                    f"Overlap between piece {i} ({pieces[i].piece_name}) "
                    f"and piece {j} ({pieces[j].piece_name})"
                )

    if errors:
        return False, "; ".join(errors)
    return True, "OK"


def calculate_contact_score(
    placed: PlacedPiece, existing: list[PlacedPiece]
) -> float:
    """Calculate contact score: how much surface area the new piece shares
    with existing pieces and material boundaries."""
    score = 0.0
    x, y, z = placed.x, placed.y, placed.z
    dx, dy, dz = placed.dx, placed.dy, placed.dz

    # Contact with material boundaries
    if x == 0:
        score += dy * dz
    if y == 0:
        score += dx * dz
    if z == 0:
        score += dx * dy

    # Contact with existing pieces (simplified: face alignment)
    for ep in existing:
        ex, ey, ez = ep.x, ep.y, ep.z
        edx, edy, edz = ep.dx, ep.dy, ep.dz

        # X-face contact
        if (x == ex + edx or x + dx == ex) and _range_overlap(y, y + dy, ey, ey + edy) and _range_overlap(z, z + dz, ez, ez + edz):
            score += min(dy * dz, edy * edz)
        # Y-face contact
        if (y == ey + edy or y + dy == ey) and _range_overlap(x, x + dx, ex, ex + edx) and _range_overlap(z, z + dz, ez, ez + edz):
            score += min(dx * dz, edx * edz)
        # Z-face contact
        if (z == ez + edz or z + dz == ez) and _range_overlap(x, x + dx, ex, ex + edx) and _range_overlap(y, y + dy, ey, ey + edy):
            score += min(dx * dy, edx * edy)

    return score


def _range_overlap(a_min: int, a_max: int, b_min: int, b_max: int) -> bool:
    """Check if two ranges have any overlap (for contact calculation)."""
    return a_min < b_max and b_min < a_max
