"""Upper bound and gap analysis for the cutting stock problems."""

from __future__ import annotations

import logging
from typing import Any

from .models import Material, Pattern, Piece, MasterSolution


def compute_volume_relaxation_bound_problem1(
    materials: dict[str, Material],
) -> float:
    """For Problem 1: the theoretical minimum waste is 0 (100% utilization).
    Returns the lower bound on waste (which is 0).
    """
    total_volume = sum(m.volume * m.count for m in materials.values())
    return float(total_volume)  # upper bound on used volume


def compute_profit_relaxation_bound_problem2(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
) -> float:
    """For Problem 2: volume relaxation upper bound on profit.

    Assumes we can fill all material volume with the highest profit-density piece.
    """
    total_volume = sum(m.volume * m.count for m in materials.values())
    max_density = max(p.profit_density for p in pieces.values())
    return total_volume * max_density


def compute_gap(
    lower_bound: float,
    upper_bound: float,
) -> float:
    """Compute relative gap between lower and upper bounds."""
    if upper_bound == 0:
        return 0.0
    return abs(upper_bound - lower_bound) / abs(upper_bound)


def analyze_bounds(
    solution: MasterSolution,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Comprehensive bound analysis.

    Returns dict with bound analysis results.
    """
    total_volume = sum(m.volume * m.count for m in materials.values())

    analysis: dict[str, Any] = {
        "total_material_volume": total_volume,
        "solution_used_volume": solution.total_used_volume,
        "solution_waste_volume": solution.total_waste_volume,
        "waste_percentage": (
            solution.total_waste_volume / total_volume * 100
            if total_volume > 0
            else 0.0
        ),
        "utilization_percentage": solution.material_utilization * 100,
    }

    problem_type = config.get("objective", "maximize_utilization")
    if problem_type == "maximize_utilization":
        analysis["upper_bound_waste"] = 0.0
        analysis["lower_bound_waste"] = solution.total_waste_volume
        analysis["gap_waste"] = compute_gap(0.0, float(solution.total_waste_volume)) if solution.total_waste_volume > 0 else 0.0
    else:
        profit_bound = compute_profit_relaxation_bound_problem2(materials, pieces)
        analysis["upper_bound_profit"] = profit_bound
        analysis["lower_bound_profit"] = solution.total_profit
        analysis["gap_profit"] = compute_gap(solution.total_profit, profit_bound)

    if logger:
        logger.info("Bound Analysis:")
        for k, v in analysis.items():
            logger.info(f"  {k}: {v}")

    return analysis
