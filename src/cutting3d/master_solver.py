"""Master Problem Solver using OR-Tools CP-SAT.

Builds an integer programming model to select the best combination of
patterns for each material type, solving the master problem.
"""

from __future__ import annotations

import time
from typing import Any

from ortools.sat.python import cp_model

from .models import (
    MasterSolution,
    Material,
    Pattern,
    Piece,
    SolverStatus,
)


def solve_master_problem1(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    all_patterns: dict[str, list[Pattern]],
    config: dict[str, Any],
) -> MasterSolution:
    """Solve master problem for Problem 1: maximize material utilization.

    Equivalent to minimizing total waste volume.

    Variables:
        x_{t,p} = number of material type t blocks using pattern p

    Objective:
        minimize sum_{t,p} x_{t,p} * waste_volume(p)

    Constraints:
        For each material type t: sum_p x_{t,p} = material_count_t
        x_{t,p} >= 0, integer
    """
    master_config = config.get("master", {})
    time_limit = master_config.get("time_limit_seconds", 120)
    num_workers = master_config.get("num_workers", 4)

    model = cp_model.CpModel()

    # Create variables
    var_map: dict[tuple[str, int], cp_model.IntVar] = {}
    material_counts: dict[str, int] = {}

    for mat_name, mat_patterns in all_patterns.items():
        material = materials[mat_name]
        material_counts[mat_name] = material.count
        for pattern in mat_patterns:
            var = model.NewIntVar(0, material.count, f"x_{mat_name}_{pattern.pattern_id}")
            var_map[(mat_name, pattern.pattern_id)] = var

    # Constraint: each material's pattern usage sums to count
    for mat_name, count in material_counts.items():
        mat_vars = [
            var_map[(mat_name, p.pattern_id)]
            for p in all_patterns.get(mat_name, [])
            if (mat_name, p.pattern_id) in var_map
        ]
        if mat_vars:
            model.Add(sum(mat_vars) == count)
        else:
            # No patterns available: create dummy variable
            dummy = model.NewIntVar(0, count, f"dummy_{mat_name}")
            model.Add(dummy == count)

    # Objective: minimize total waste volume
    waste_terms: list[tuple[cp_model.IntVar, int]] = []
    for mat_name, mat_patterns in all_patterns.items():
        material = materials[mat_name]
        for pattern in mat_patterns:
            var = var_map[(mat_name, pattern.pattern_id)]
            waste = material.volume - pattern.used_volume
            waste_terms.append((var, waste))

    total_used_volume_terms: list[tuple[cp_model.IntVar, int]] = []
    for mat_name, mat_patterns in all_patterns.items():
        for pattern in mat_patterns:
            var = var_map[(mat_name, pattern.pattern_id)]
            total_used_volume_terms.append((var, pattern.used_volume))

    total_waste = sum(var * waste for var, waste in waste_terms)
    total_used = sum(var * vol for var, vol in total_used_volume_terms)
    model.Minimize(total_waste)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = num_workers

    start_time = time.time()
    status = solver.Solve(model)
    solve_time = time.time() - start_time

    return _extract_solution(
        solver=solver,
        status=status,
        solve_time=solve_time,
        var_map=var_map,
        all_patterns=all_patterns,
        materials=materials,
        pieces=pieces,
        config=config,
    )


def solve_master_problem2(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    all_patterns: dict[str, list[Pattern]],
    config: dict[str, Any],
) -> MasterSolution:
    """Solve master problem for Problem 2: maximize total profit.

    Variables:
        x_{t,p} = number of material type t blocks using pattern p

    Objective:
        maximize sum_{t,p} x_{t,p} * total_profit(p)

    Constraints:
        For each material type t: sum_p x_{t,p} = material_count_t
        For each piece type j: sum_{t,p} x_{t,p} * count_j(p) >= min_pieces
        x_{t,p} >= 0, integer
    """
    master_config = config.get("master", {})
    time_limit = master_config.get("time_limit_seconds", 120)
    num_workers = master_config.get("num_workers", 4)
    min_pieces = config.get("min_pieces_per_type", 10)

    model = cp_model.CpModel()

    # Create variables
    var_map: dict[tuple[str, int], cp_model.IntVar] = {}
    material_counts: dict[str, int] = {}

    for mat_name, mat_patterns in all_patterns.items():
        material = materials[mat_name]
        material_counts[mat_name] = material.count
        for pattern in mat_patterns:
            var = model.NewIntVar(0, material.count, f"x_{mat_name}_{pattern.pattern_id}")
            var_map[(mat_name, pattern.pattern_id)] = var

    # Constraint: each material's pattern usage sums to count
    for mat_name, count in material_counts.items():
        mat_vars = [
            var_map[(mat_name, p.pattern_id)]
            for p in all_patterns.get(mat_name, [])
            if (mat_name, p.pattern_id) in var_map
        ]
        if mat_vars:
            model.Add(sum(mat_vars) == count)
        else:
            dummy = model.NewIntVar(0, count, f"dummy_{mat_name}")
            model.Add(dummy == count)

    # Constraint: minimum pieces per type
    piece_names = sorted(pieces.keys())
    for pname in piece_names:
        piece_terms: list[tuple[cp_model.IntVar, int]] = []
        for mat_name, mat_patterns in all_patterns.items():
            for pattern in mat_patterns:
                var = var_map[(mat_name, pattern.pattern_id)]
                count = pattern.get_piece_counts(piece_names).get(pname, 0)
                if count > 0:
                    piece_terms.append((var, count))
        if piece_terms:
            model.Add(sum(var * c for var, c in piece_terms) >= min_pieces)

    # Objective: maximize total profit
    profit_terms: list[tuple[cp_model.IntVar, int]] = []
    for mat_name, mat_patterns in all_patterns.items():
        for pattern in mat_patterns:
            var = var_map[(mat_name, pattern.pattern_id)]
            profit = sum(
                pieces[pp.piece_name].profit
                for pp in pattern.placed_pieces
                if pp.piece_name in pieces
            )
            if profit > 0:
                profit_terms.append((var, profit))

    total_profit = sum(var * p for var, p in profit_terms)
    model.Maximize(total_profit)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = num_workers

    start_time = time.time()
    status = solver.Solve(model)
    solve_time = time.time() - start_time

    return _extract_solution(
        solver=solver,
        status=status,
        solve_time=solve_time,
        var_map=var_map,
        all_patterns=all_patterns,
        materials=materials,
        pieces=pieces,
        config=config,
    )


def _extract_solution(
    solver: cp_model.CpSolver,
    status: Any,
    solve_time: float,
    var_map: dict[tuple[str, int], cp_model.IntVar],
    all_patterns: dict[str, list[Pattern]],
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    config: dict[str, Any],
) -> MasterSolution:
    """Extract solution from CP-SAT solver."""
    # Map status
    status_map = {
        cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        cp_model.FEASIBLE: SolverStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
        cp_model.UNKNOWN: SolverStatus.UNKNOWN,
    }
    solver_status = status_map.get(status, SolverStatus.UNKNOWN)

    # Extract pattern usage
    pattern_usage: dict[int, int] = {}
    total_used_volume = 0
    total_material_volume = 0
    total_profit = 0
    piece_counts: dict[str, int] = {name: 0 for name in pieces}

    for mat_name, mat_patterns in all_patterns.items():
        material = materials[mat_name]
        for pattern in mat_patterns:
            var = var_map.get((mat_name, pattern.pattern_id))
            if var is not None:
                val = solver.Value(var)
                if val > 0:
                    pattern_usage[pattern.pattern_id] = val
                    total_used_volume += val * pattern.used_volume
                    total_material_volume += val * material.volume
                    pat_profit = sum(
                        pieces[pp.piece_name].profit
                        for pp in pattern.placed_pieces
                        if pp.piece_name in pieces
                    )
                    total_profit += val * pat_profit
                    for pname, count in pattern.get_piece_counts(list(pieces.keys())).items():
                        piece_counts[pname] += val * count

    total_waste = total_material_volume - total_used_volume
    utilization = (
        total_used_volume / total_material_volume
        if total_material_volume > 0
        else 0.0
    )

    # Objective value
    objective_value = solver.ObjectiveValue()

    # Compute semantically correct bounds
    problem_type = config.get("objective", "maximize_utilization")
    ub, lb, gap = _compute_correct_bounds(
        problem_type=problem_type,
        objective_value=objective_value,
        total_material_volume=total_material_volume,
        total_waste=total_waste,
        utilization=utilization,
        total_profit=total_profit,
        solver=solver,
        materials=materials,
        pieces=pieces,
        solver_status=solver_status,
    )

    return MasterSolution(
        status=solver_status,
        objective_value=objective_value,
        pattern_usage=pattern_usage,
        total_profit=total_profit,
        total_used_volume=total_used_volume,
        total_waste_volume=total_waste,
        total_material_volume=total_material_volume,
        material_utilization=utilization,
        piece_counts=piece_counts,
        solve_time_seconds=solve_time,
        upper_bound=ub,
        lower_bound=lb,
        gap=gap,
    )


def _compute_correct_bounds(
    problem_type: str,
    objective_value: float,
    total_material_volume: int,
    total_waste: int,
    utilization: float,
    total_profit: float,
    solver: cp_model.CpSolver,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    solver_status: Any,
) -> tuple[float, float, float]:
    """Compute semantically correct upper bound, lower bound, and gap.

    Problem 1 (minimize waste):
        upper_bound on utilization = 1.0 (100%)
        lower_bound on utilization = current_utilization
        gap = (1.0 - utilization) / 1.0 = 1.0 - utilization

        OR in waste terms:
        waste_lower_bound = 0
        current_waste = total_waste
        waste_gap_to_zero = total_waste

    Problem 2 (maximize profit):
        upper_bound = profit_density_relaxation (LOOSE, not tight)
        lower_bound = current_total_profit
        gap = (upper_bound - lower_bound) / upper_bound
    """
    if problem_type == "maximize_utilization":
        # Utilization viewpoint (semantically clearer):
        # upper_bound = 1.0 (100% utilization = theoretical best)
        # lower_bound = current_utilization (feasible solution)
        upper_bound = 1.0
        lower_bound = utilization
        gap = 1.0 - utilization  # distance from 100%

        # Note: we store upper_bound on utilization, NOT waste
        # The objective_value from the solver is the minimized waste,
        # but for gap reporting we use utilization
        return upper_bound, lower_bound, gap

    else:
        # Problem 2: maximize profit
        total_volume = sum(m.volume * m.count for m in materials.values())
        max_density = max(p.profit_density for p in pieces.values())
        upper_bound = total_volume * max_density  # loose volume-relaxation bound
        lower_bound = total_profit  # feasible solution value
        gap = (upper_bound - lower_bound) / upper_bound if upper_bound > 0 else 0.0
        return upper_bound, lower_bound, gap


# Legacy function kept for backward compatibility
def _compute_upper_bound(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    all_patterns: dict[str, list[Pattern]],
    config: dict[str, Any],
) -> float:
    """Compute theoretical upper bound. DEPRECATED - use _compute_correct_bounds."""
    total_volume = sum(m.volume * m.count for m in materials.values())
    problem_type = config.get("objective", "maximize_utilization")
    if problem_type == "maximize_utilization":
        return 1.0  # utilization upper bound
    else:
        max_density = max(p.profit_density for p in pieces.values())
        return total_volume * max_density
