"""Upper bound and gap analysis for the cutting stock problems.

Terminology:
  - Problem 1 (minimize waste / maximize utilization):
    * waste_lower_bound = 0 (theoretical minimum, cannot go below zero)
    * utilization_upper_bound = 1.0 (100% utilization, theoretical max)
    * current_waste = actual waste volume
    * waste_gap_to_zero = current_waste - 0
    * utilization_gap_to_full = 1.0 - current_utilization

  - Problem 2 (maximize profit):
    * profit_density_relaxation_upper_bound = total_volume * max_profit_density
      NOTE: This bound ignores geometry, min-piece constraints, and discretization.
      It is a loose reference bound, NOT a tight optimality certificate.
    * lp_relaxation_upper_bound = CP-SAT LP relaxation bound (if available)
    * current_profit = feasible solution profit
    * relaxation_gap = upper_bound - current_profit
"""

from __future__ import annotations

import logging
from typing import Any

from .models import Material, Pattern, Piece, MasterSolution


def compute_problem1_bounds(
    materials: dict[str, Material],
    current_waste: int,
    current_utilization: float,
    total_used_volume: int,
) -> dict[str, Any]:
    """Compute semantically correct bounds for Problem 1.

    Problem 1 minimizes waste volume, equivalent to maximizing utilization.

    Returns dict with clear field names and explanations.
    """
    total_volume = sum(m.volume * m.count for m in materials.values())

    return {
        "total_material_volume": total_volume,
        "total_used_volume": total_used_volume,
        "total_waste_volume": current_waste,
        "material_utilization": current_utilization,
        # For waste minimization:
        "waste_lower_bound": 0,  # theoretical minimum waste
        "current_waste": current_waste,
        "waste_gap_to_zero": current_waste - 0,
        "waste_gap_ratio_to_total_volume": current_waste / total_volume if total_volume > 0 else 0.0,
        # For utilization maximization:
        "utilization_upper_bound": 1.0,  # theoretical max utilization
        "current_utilization": current_utilization,
        "utilization_gap_to_full": 1.0 - current_utilization,
        # Semantic note
        "bound_note": (
            "Problem 1 minimizes waste. waste_lower_bound=0 is the theoretical minimum. "
            "utilization_upper_bound=1.0 is 100% utilization. "
            "The gap is the distance from the theoretical bound."
        ),
    }


def compute_problem2_bounds(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    current_profit: float,
    solver_best_bound: float | None = None,
) -> dict[str, Any]:
    """Compute semantically correct bounds for Problem 2.

    Problem 2 maximizes total profit with min-piece constraints.

    The profit_density_relaxation_upper_bound is a LOOSE bound that ignores
    geometry, min-piece constraints, and discretization. It should NOT be
    used as a tight optimality certificate.

    Returns dict with clear field names and explanations.
    """
    total_volume = sum(m.volume * m.count for m in materials.values())
    max_density = max(p.profit_density for p in pieces.values())
    profit_density_bound = total_volume * max_density

    result: dict[str, Any] = {
        "current_profit": current_profit,
        "profit_density_relaxation_upper_bound": profit_density_bound,
        "relaxation_gap": profit_density_bound - current_profit,
        "relaxation_gap_ratio": (
            (profit_density_bound - current_profit) / profit_density_bound
            if profit_density_bound > 0
            else 0.0
        ),
        "bound_note": (
            "profit_density_relaxation_upper_bound ignores geometry, "
            "min-piece constraints, and discretization. It is a LOOSE reference "
            "bound, NOT a tight optimality certificate. A tight bound requires "
            "complete pattern enumeration or branch-and-price."
        ),
    }

    if solver_best_bound is not None:
        result["solver_best_bound"] = solver_best_bound
        result["solver_gap"] = (
            (solver_best_bound - current_profit) / solver_best_bound
            if solver_best_bound > 0
            else 0.0
        )

    return result


def compute_gap(lower_bound: float, upper_bound: float) -> float:
    """Compute relative gap between lower and upper bounds.

    gap = |upper_bound - lower_bound| / |upper_bound|
    """
    if abs(upper_bound) < 1e-12:
        return 0.0
    return abs(upper_bound - lower_bound) / abs(upper_bound)


def analyze_bounds(
    solution: MasterSolution,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Comprehensive bound analysis for a solution.

    Returns dict with analysis results. Uses semantically correct field names
    depending on the problem type.
    """
    total_volume = sum(m.volume * m.count for m in materials.values())
    problem_type = config.get("objective", "maximize_utilization")

    if problem_type == "maximize_utilization":
        analysis = compute_problem1_bounds(
            materials=materials,
            current_waste=solution.total_waste_volume,
            current_utilization=solution.material_utilization,
            total_used_volume=solution.total_used_volume,
        )
    else:
        analysis = compute_problem2_bounds(
            materials=materials,
            pieces=pieces,
            current_profit=solution.total_profit,
        )

    # Add problem-agnostic fields
    analysis["problem_type"] = problem_type
    analysis["solution_status"] = solution.status.value
    analysis["solution_objective_value"] = solution.objective_value

    if logger:
        logger.info("Bound Analysis:")
        for k, v in analysis.items():
            if isinstance(v, str) and len(v) > 80:
                logger.info(f"  {k}: {v[:80]}...")
            else:
                logger.info(f"  {k}: {v}")

    return analysis
