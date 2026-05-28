"""Pattern data structure and management."""

from __future__ import annotations

from .models import Material, Orientation, Pattern, Piece, PlacedPiece


def compute_pattern_stats(
    pattern: Pattern,
    material: Material,
    pieces: dict[str, Piece],
) -> dict:
    """Compute statistics for a pattern."""
    used_vol = pattern.used_volume
    total_vol = material.volume
    waste_vol = total_vol - used_vol
    utilization = used_vol / total_vol if total_vol > 0 else 0.0
    total_profit = sum(
        pieces[pp.piece_name].profit for pp in pattern.placed_pieces
        if pp.piece_name in pieces
    )
    piece_counts = pattern.get_piece_counts(list(pieces.keys()))

    return {
        "pattern_id": pattern.pattern_id,
        "material_name": pattern.material_name,
        "num_pieces": pattern.num_pieces,
        "used_volume": used_vol,
        "total_volume": total_vol,
        "waste_volume": waste_vol,
        "utilization": utilization,
        "total_profit": total_profit,
        "piece_counts": piece_counts,
    }


def pattern_to_vector(
    pattern: Pattern,
    piece_names: list[str],
) -> list[int]:
    """Convert pattern to piece count vector."""
    counts = pattern.get_piece_counts(piece_names)
    return [counts.get(name, 0) for name in piece_names]
