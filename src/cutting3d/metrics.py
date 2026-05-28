"""Metrics and evaluation functions for 3D cutting optimization."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from .models import Material, Pattern, Piece, MasterSolution


def compute_solution_metrics(
    solution: MasterSolution,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    patterns: list[Pattern],
) -> dict[str, Any]:
    """Compute comprehensive metrics for a solution."""
    total_mat_volume = sum(m.volume * m.count for m in materials.values())

    metrics: dict[str, Any] = {
        "status": solution.status.value,
        "objective_value": solution.objective_value,
        "total_profit": solution.total_profit,
        "total_used_volume": solution.total_used_volume,
        "total_waste_volume": solution.total_waste_volume,
        "total_material_volume": total_mat_volume,
        "material_utilization": solution.material_utilization,
        "material_utilization_pct": solution.material_utilization * 100,
        "waste_percentage": (solution.total_waste_volume / total_mat_volume * 100) if total_mat_volume > 0 else 0.0,
        "solve_time_seconds": solution.solve_time_seconds,
        "upper_bound": solution.upper_bound,
        "lower_bound": solution.lower_bound,
        "gap": solution.gap,
        "num_patterns_used": len(solution.pattern_usage),
        "total_patterns_generated": len(patterns),
    }

    # Per-material breakdown
    pattern_map = {p.pattern_id: p for p in patterns}
    for mat_name, material in materials.items():
        mat_used_vol = 0
        mat_waste = 0
        mat_patterns = 0
        for pid, count in solution.pattern_usage.items():
            if pid in pattern_map and pattern_map[pid].material_name == mat_name:
                mat_used_vol += count * pattern_map[pid].used_volume
                mat_patterns += count
        mat_vol = material.volume * material.count
        mat_waste = mat_vol - mat_used_vol
        metrics[f"{mat_name}_used_volume"] = mat_used_vol
        metrics[f"{mat_name}_waste"] = mat_waste
        metrics[f"{mat_name}_utilization"] = mat_used_vol / mat_vol if mat_vol > 0 else 0.0
        metrics[f"{mat_name}_blocks_used"] = mat_patterns

    # Per-piece breakdown
    for pname, count in solution.piece_counts.items():
        metrics[f"count_{pname}"] = count
        if pname in pieces:
            metrics[f"profit_{pname}"] = count * pieces[pname].profit
            metrics[f"volume_{pname}"] = count * pieces[pname].volume

    return metrics


def save_metrics_csv(metrics: dict[str, Any], path: str | Path) -> None:
    """Save metrics to CSV file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([metrics])
    df.to_csv(path, index=False, encoding="utf-8")


def print_summary(
    problem_name: str,
    solution: MasterSolution,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    logger=None,
) -> None:
    """Print a formatted summary of the solution."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  {problem_name} - Solution Summary")
    lines.append("=" * 60)
    lines.append(f"  Status:            {solution.status.value}")
    lines.append(f"  Objective Value:   {solution.objective_value:.2f}")
    lines.append(f"  Solve Time:        {solution.solve_time_seconds:.2f}s")
    lines.append(f"  Total Profit:      {solution.total_profit:.2f}")
    lines.append(f"  Material Used Vol: {solution.total_used_volume}")
    lines.append(f"  Waste Volume:      {solution.total_waste_volume}")
    lines.append(f"  Utilization:       {solution.material_utilization * 100:.2f}%")
    lines.append(f"  Gap:               {solution.gap * 100:.2f}%")
    lines.append("-" * 60)
    lines.append("  Piece Counts:")
    for name in sorted(solution.piece_counts.keys()):
        count = solution.piece_counts[name]
        profit = pieces[name].profit * count if name in pieces else 0
        lines.append(f"    {name}: {count} (profit: {profit})")
    lines.append("-" * 60)
    lines.append("  Per-Material Utilization:")
    for mat_name, material in materials.items():
        lines.append(f"    {mat_name}: {material.count} blocks of {material.volume:,} each")
    lines.append("=" * 60)

    summary = "\n".join(lines)
    if logger:
        logger.info("\n" + summary)
    else:
        print(summary)
