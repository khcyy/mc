"""CP-SAT-based exact geometry feasibility checker.

For a given production vector and material, creates a CP-SAT model
with coordinate variables, rotation choices, and non-overlap constraints
to check if the vector is geometrically feasible.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ortools.sat.python import cp_model

from .models import Material, Orientation, Piece, PlacedPiece, SolverStatus
from .orientations import generate_all_orientations


def check_vector_feasibility_cpsat(
    material: Material,
    piece_counts: dict[str, int],
    pieces: dict[str, Piece],
    all_orientations: dict[str, list[Orientation]],
    time_limit: float = 60.0,
    grid_gcd: int = 5,
    logger: logging.Logger | None = None,
) -> tuple[bool, SolverStatus, dict[str, Any]]:
    """Check if a production vector is geometrically feasible using CP-SAT.

    Creates a CP-SAT model with:
    - For each piece: x, y, z integer variables (in grid units)
    - For each piece: orientation choice among valid orientations
    - Non-overlap constraints between all pairs
    - Containment constraints within material bounds

    Args:
        material: Material to pack into.
        piece_counts: Dict mapping piece_name -> count.
        pieces: All piece definitions.
        all_orientations: Pre-computed orientations per piece type.
        time_limit: CP-SAT time limit in seconds.
        grid_gcd: Grid unit size for discretization.

    Returns:
        (is_feasible, solver_status, metadata)
    """
    # Discretize dimensions
    ml = material.length // grid_gcd
    mw = material.width // grid_gcd
    mh = material.height // grid_gcd

    # Collect all items to place
    items: list[tuple[str, list[Orientation]]] = []
    for pname, count in piece_counts.items():
        if count <= 0:
            continue
        if pname not in pieces:
            continue
        orients = all_orientations.get(pname, [])
        if not orients:
            continue
        for _ in range(count):
            items.append((pname, orients))

    if not items:
        return True, SolverStatus.OPTIMAL, {"note": "no_items"}

    n = len(items)
    # Limit to avoid very slow solves
    if n > 50:
        if logger:
            logger.warning(f"  Too many pieces ({n}), skipping CP-SAT check")
        return False, SolverStatus.UNKNOWN, {
            "note": f"too_many_pieces_{n}", "piece_count": n
        }

    model = cp_model.CpModel()

    # Variables for each item
    xs: list[cp_model.IntVar] = []
    ys: list[cp_model.IntVar] = []
    zs: list[cp_model.IntVar] = []
    dxs: list[cp_model.IntVar] = []
    dys: list[cp_model.IntVar] = []
    dzs: list[cp_model.IntVar] = []
    orientation_vars: list[list[cp_model.IntVar]] = []

    for i, (pname, orients) in enumerate(items):
        xi = model.NewIntVar(0, ml - 1, f"x_{i}")
        yi = model.NewIntVar(0, mw - 1, f"y_{i}")
        zi = model.NewIntVar(0, mh - 1, f"z_{i}")
        xs.append(xi)
        ys.append(yi)
        zs.append(zi)

        # Orientation selection via boolean indicators
        orient_vars: list[cp_model.IntVar] = []
        dx_vals: list[int] = []
        dy_vals: list[int] = []
        dz_vals: list[int] = []
        for orient in orients:
            b = model.NewBoolVar(f"orient_{i}_{orient.dx}_{orient.dy}_{orient.dz}")
            orient_vars.append(b)
            dx_vals.append(orient.dx // grid_gcd)
            dy_vals.append(orient.dy // grid_gcd)
            dz_vals.append(orient.dz // grid_gcd)
        orientation_vars.append(orient_vars)

        # Exactly one orientation
        model.Add(sum(orient_vars) == 1)

        # dx, dy, dz as linear combinations
        dxi = model.NewIntVar(1, ml, f"dx_{i}")
        dyi = model.NewIntVar(1, mw, f"dy_{i}")
        dzi = model.NewIntVar(1, mh, f"dz_{i}")
        dxs.append(dxi)
        dys.append(dyi)
        dzs.append(dzi)

        model.Add(dxi == sum(b * dv for b, dv in zip(orient_vars, dx_vals)))
        model.Add(dyi == sum(b * dv for b, dv in zip(orient_vars, dy_vals)))
        model.Add(dzi == sum(b * dv for b, dv in zip(orient_vars, dz_vals)))

        # Containment
        model.Add(xi + dxi <= ml)
        model.Add(yi + dyi <= mw)
        model.Add(zi + dzi <= mh)

    # Non-overlap constraints (pairwise, 1D disjunctive)
    for i in range(n):
        for j in range(i + 1, n):
            # At least one axis must be separated
            sep_x = model.NewBoolVar(f"sep_x_{i}_{j}")
            sep_y = model.NewBoolVar(f"sep_y_{i}_{j}")
            sep_z = model.NewBoolVar(f"sep_z_{i}_{j}")
            model.Add(sep_x + sep_y + sep_z >= 1)
            # x-separation: xi + dxi <= xj OR xj + dxj <= xi
            xij = model.NewBoolVar(f"xij_{i}_{j}")
            model.Add(xs[i] + dxs[i] <= xs[j]).OnlyEnforceIf(xij)
            model.Add(xs[j] + dxs[j] <= xs[i]).OnlyEnforceIf(xij.Not())
            model.Add(sep_x == 1).OnlyEnforceIf([xij, xij.Not()][0])  # always true
            # Actually, let's simplify: use interval-based separation
            # xi + dxi <= xj => sep_x
            model.Add(xs[i] + dxs[i] <= xs[j] + ml * (1 - sep_x))
            model.Add(xs[j] + dxs[j] <= xs[i] + ml * (1 - sep_x))

            model.Add(ys[i] + dys[i] <= ys[j] + mw * (1 - sep_y))
            model.Add(ys[j] + dys[j] <= ys[i] + mw * (1 - sep_y))

            model.Add(zs[i] + dzs[i] <= zs[j] + mh * (1 - sep_z))
            model.Add(zs[j] + dzs[j] <= zs[i] + mh * (1 - sep_z))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 4

    start = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - start

    # Map status
    status_map = {
        cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        cp_model.FEASIBLE: SolverStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
        cp_model.UNKNOWN: SolverStatus.UNKNOWN,
    }
    solver_status = status_map.get(status, SolverStatus.UNKNOWN)

    metadata: dict[str, Any] = {
        "num_items": n,
        "material": material.name,
        "solve_time": elapsed,
        "solver_status": solver_status.value,
        "grid_gcd": grid_gcd,
    }

    if solver_status == SolverStatus.OPTIMAL or solver_status == SolverStatus.FEASIBLE:
        placed: list[PlacedPiece] = []
        for i, (pname, _) in enumerate(items):
            x_val = solver.Value(xs[i]) * grid_gcd
            y_val = solver.Value(ys[i]) * grid_gcd
            z_val = solver.Value(zs[i]) * grid_gcd
            dx_val = solver.Value(dxs[i]) * grid_gcd
            dy_val = solver.Value(dys[i]) * grid_gcd
            dz_val = solver.Value(dzs[i]) * grid_gcd
            orient = Orientation(dx_val, dy_val, dz_val)
            placed.append(PlacedPiece(
                piece_name=pname, x=x_val, y=y_val, z=z_val, orientation=orient,
            ))
        metadata["placed_pieces"] = [pp.to_dict() for pp in placed]
        return True, solver_status, metadata
    else:
        return False, solver_status, metadata
