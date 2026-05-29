"""Visualization module for 3D cutting stock optimization.

Generates publication-quality charts and 3D layout visualizations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.patches import Patch

from .models import (
    ExperimentResult,
    Material,
    Pattern,
    Piece,
    PlacedPiece,
)
from .metrics import compute_solution_metrics
from .utils import ensure_dir


# Try to configure Chinese font
def _setup_chinese_font():
    """Try to set up Chinese font support."""
    try:
        import matplotlib.font_manager as fm
        # Common Chinese fonts on different platforms
        candidates = [
            "SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei",
            "Noto Sans CJK SC", "Source Han Sans SC",
            "Arial Unicode MS", "DejaVu Sans",
        ]
        available = [f.name for f in fm.fontManager.ttflist]
        for font in candidates:
            if font in available:
                plt.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
                break
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass


_setup_chinese_font()

# Global style
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})


def save_figure(fig: plt.Figure, base_path: str | Path, formats: list[str] | None = None) -> list[Path]:
    """Save figure in multiple formats."""
    if formats is None:
        formats = ["png", "pdf"]
    base_path = Path(base_path)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for fmt in formats:
        p = base_path.with_suffix(f".{fmt}")
        fig.savefig(p, dpi=300, bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    return paths


def plot_material_utilization(
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot material utilization by material type."""
    output_dir = ensure_dir(output_dir)
    metrics = compute_solution_metrics(result.solution, materials, pieces, result.patterns)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: Utilization bar chart
    mat_names = list(materials.keys())
    utils = [metrics.get(f"{m}_utilization", 0) * 100 for m in mat_names]
    bars = ax1.bar(mat_names, utils, color=["#2196F3", "#4CAF50", "#FF9800"], edgecolor="white", linewidth=1.2)
    ax1.set_ylabel("Utilization (%)")
    ax1.set_title("Material Utilization by Type")
    ax1.set_ylim(0, 105)
    for bar, val in zip(bars, utils):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{val:.1f}%", ha="center", va="bottom", fontweight="bold")

    # Draw 100% reference line
    ax1.axhline(y=100, color="red", linestyle="--", alpha=0.5, label="100%")
    ax1.legend()

    # Panel 2: Volume breakdown (stacked: used vs waste)
    used_vols = [metrics.get(f"{m}_used_volume", 0) for m in mat_names]
    waste_vols = [metrics.get(f"{m}_waste", 0) for m in mat_names]
    x = np.arange(len(mat_names))
    width = 0.5
    ax2.bar(x, used_vols, width, label="Used Volume", color="#4CAF50", edgecolor="white")
    ax2.bar(x, waste_vols, width, bottom=used_vols, label="Waste Volume", color="#F44336", edgecolor="white")
    ax2.set_xticks(x)
    ax2.set_xticklabels(mat_names)
    ax2.set_ylabel("Volume")
    ax2.set_title("Volume Breakdown: Used vs Waste")
    ax2.legend()

    fig.suptitle(f"{result.problem_name.upper()}: Material Utilization Analysis", fontweight="bold", y=1.01)
    plt.tight_layout()
    return save_figure(fig, output_dir / f"{result.problem_name}_material_utilization")


def plot_waste_volume(
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot waste volume breakdown."""
    output_dir = ensure_dir(output_dir)
    metrics = compute_solution_metrics(result.solution, materials, pieces, result.patterns)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    mat_names = list(materials.keys())
    waste_vols = [metrics.get(f"{m}_waste", 0) for m in mat_names]
    total_vols = [materials[m].volume * materials[m].count for m in mat_names]
    waste_pcts = [w / t * 100 if t > 0 else 0 for w, t in zip(waste_vols, total_vols)]

    # Panel 1: Waste volume bars
    bars = ax1.bar(mat_names, waste_vols, color="#F44336", edgecolor="white", linewidth=1.2)
    ax1.set_ylabel("Waste Volume")
    ax1.set_title("Waste Volume by Material Type")
    for bar, val in zip(bars, waste_vols):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(waste_vols) * 0.02,
                 f"{val:,}", ha="center", va="bottom", fontweight="bold")

    # Panel 2: Waste percentage
    bars2 = ax2.bar(mat_names, waste_pcts, color="#FF7043", edgecolor="white", linewidth=1.2)
    ax2.set_ylabel("Waste (%)")
    ax2.set_title("Waste Percentage by Material Type")
    for bar, val in zip(bars2, waste_pcts):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{val:.1f}%", ha="center", va="bottom", fontweight="bold")

    fig.suptitle(f"{result.problem_name.upper()}: Waste Volume Analysis", fontweight="bold", y=1.01)
    plt.tight_layout()
    return save_figure(fig, output_dir / f"{result.problem_name}_waste_volume")


def plot_piece_counts(
    result: ExperimentResult,
    pieces: dict[str, Piece],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot piece production counts."""
    output_dir = ensure_dir(output_dir)

    fig, ax = plt.subplots(figsize=(12, 5))
    piece_names = sorted(result.solution.piece_counts.keys())
    counts = [result.solution.piece_counts.get(n, 0) for n in piece_names]
    colors = plt.cm.Set2(np.linspace(0, 1, len(piece_names)))

    bars = ax.bar(piece_names, counts, color=colors, edgecolor="white", linewidth=1.2)
    ax.set_xlabel("Piece Type")
    ax.set_ylabel("Quantity Produced")
    ax.set_title(f"{result.problem_name.upper()}: Piece Production Quantities")

    for bar, val in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(1, max(counts) * 0.02),
                str(val), ha="center", va="bottom", fontweight="bold")

    plt.tight_layout()
    return save_figure(fig, output_dir / f"{result.problem_name}_piece_counts")


def plot_profit_contribution(
    result: ExperimentResult,
    pieces: dict[str, Piece],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot profit contribution by piece type."""
    output_dir = ensure_dir(output_dir)

    fig, ax = plt.subplots(figsize=(10, 6))
    piece_names = sorted(result.solution.piece_counts.keys())
    profits = []
    for n in piece_names:
        count = result.solution.piece_counts.get(n, 0)
        if n in pieces:
            profits.append(count * pieces[n].profit)
        else:
            profits.append(0)

    colors = plt.cm.Set2(np.linspace(0, 1, len(piece_names)))
    wedges, texts, autotexts = ax.pie(
        profits, labels=piece_names, autopct="%1.1f%%",
        colors=colors, startangle=90,
        textprops={"fontsize": 10},
    )
    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_fontsize(9)

    ax.set_title(f"{result.problem_name.upper()}: Profit Contribution by Piece Type", fontweight="bold")
    return save_figure(fig, output_dir / f"{result.problem_name}_profit_contribution")


def plot_total_profit(
    result: ExperimentResult,
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot total profit bar."""
    output_dir = ensure_dir(output_dir)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(["Total Profit"], [result.solution.total_profit], color="#2E7D32", width=0.4, edgecolor="white")
    ax.set_ylabel("Profit")
    ax.set_title(f"{result.problem_name.upper()}: Total Profit")
    ax.text(0, result.solution.total_profit + max(100, result.solution.total_profit * 0.02),
            f"{result.solution.total_profit:,.0f}", ha="center", fontweight="bold", fontsize=14)
    plt.tight_layout()
    return save_figure(fig, output_dir / f"{result.problem_name}_total_profit")


def plot_pattern_usage(
    result: ExperimentResult,
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot pattern usage frequency."""
    output_dir = ensure_dir(output_dir)

    fig, ax = plt.subplots(figsize=(12, 5))
    if result.solution.pattern_usage:
        pids = list(result.solution.pattern_usage.keys())[:30]  # top 30
        counts = [result.solution.pattern_usage[pid] for pid in pids]
        labels = [f"P{p}" for p in pids]
        colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(pids)))
        ax.bar(labels, counts, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xlabel("Pattern ID")
        ax.set_ylabel("Times Used")
        ax.set_title(f"{result.problem_name.upper()}: Pattern Usage")
        plt.xticks(rotation=45, ha="right", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No patterns used", ha="center", va="center", transform=ax.transAxes)

    plt.tight_layout()
    return save_figure(fig, output_dir / f"{result.problem_name}_pattern_usage")


def plot_bound_gap(
    result: ExperimentResult,
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot gap between solution and theoretical bounds."""
    output_dir = ensure_dir(output_dir)

    fig, ax = plt.subplots(figsize=(10, 5))
    s = result.solution

    problem_type = result.config.get("objective", "maximize_utilization")
    if problem_type == "maximize_utilization":
        # Show utilization vs 100% theoretical upper bound
        labels = [f"Current Utilization\n({s.material_utilization*100:.2f}%)",
                  "Theoretical Upper Bound\n(100%)"]
        values = [s.material_utilization * 100, 100.0]
        colors = ["#2196F3", "#4CAF50"]
        ax.set_ylabel("Utilization (%)")
        ax.set_title(
            f"{result.problem_name.upper()}: Utilization vs Theoretical Bound\n"
            f"Utilization Gap to 100% = {(1.0 - s.material_utilization) * 100:.4f}%",
            fontweight="bold",
        )
    else:
        labels = ["Current Profit", "Profit Density\nRelaxation Bound"]
        values = [s.total_profit, s.upper_bound]
        colors = ["#2196F3", "#FFC107"]
        ax.set_ylabel("Profit")
        ax.set_title(
            f"{result.problem_name.upper()}: Profit vs Relaxation Bound\n"
            f"Relaxation Gap = {s.gap*100:.2f}% (LOOSE bound, not tight)",
            fontweight="bold",
        )

    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=1.2, width=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                f"{val:,.1f}", ha="center", va="bottom", fontweight="bold")

    plt.tight_layout()
    return save_figure(fig, output_dir / f"{result.problem_name}_bound_gap")


def plot_ablation_comparison(
    results: dict[str, dict[str, Any]],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot ablation study comparison."""
    output_dir = ensure_dir(output_dir)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    methods = list(results.keys())

    # Utilization
    ax = axes[0, 0]
    utils = [results[m].get("utilization", 0) * 100 for m in methods]
    ax.bar(methods, utils, color=plt.cm.Set2(np.linspace(0, 1, len(methods))), edgecolor="white")
    ax.set_title("Material Utilization (%)")
    ax.set_ylabel("%")
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")

    # Waste
    ax = axes[0, 1]
    wastes = [results[m].get("waste", 0) for m in methods]
    ax.bar(methods, wastes, color=plt.cm.Set3(np.linspace(0, 1, len(methods))), edgecolor="white")
    ax.set_title("Total Waste Volume")
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")

    # Total Profit
    ax = axes[1, 0]
    profits = [results[m].get("profit", 0) for m in methods]
    ax.bar(methods, profits, color=plt.cm.Set1(np.linspace(0, 1, len(methods))), edgecolor="white")
    ax.set_title("Total Profit")
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")

    # Runtime
    ax = axes[1, 1]
    times = [results[m].get("runtime", 0) for m in methods]
    ax.bar(methods, times, color=plt.cm.Pastel1(np.linspace(0, 1, len(methods))), edgecolor="white")
    ax.set_title("Runtime (seconds)")
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")

    fig.suptitle("Ablation Study Comparison", fontweight="bold", fontsize=16)
    plt.tight_layout()
    return save_figure(fig, output_dir / "ablation_comparison")


def plot_sensitivity_patterns(
    results: dict[int, dict[str, Any]],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot sensitivity analysis for pattern count."""
    output_dir = ensure_dir(output_dir)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    pattern_counts = sorted(results.keys())

    # Utilization vs patterns
    ax = axes[0]
    utils = [results[k].get("utilization", 0) * 100 for k in pattern_counts]
    ax.plot(pattern_counts, utils, "o-", color="#2196F3", linewidth=2, markersize=8)
    ax.set_xlabel("Max Patterns per Material")
    ax.set_ylabel("Utilization (%)")
    ax.set_title("Utilization vs Pattern Count")
    ax.grid(True, alpha=0.3)

    # Profit vs patterns
    ax = axes[1]
    profits = [results[k].get("profit", 0) for k in pattern_counts]
    ax.plot(pattern_counts, profits, "s-", color="#4CAF50", linewidth=2, markersize=8)
    ax.set_xlabel("Max Patterns per Material")
    ax.set_ylabel("Total Profit")
    ax.set_title("Profit vs Pattern Count")
    ax.grid(True, alpha=0.3)

    # Runtime vs patterns
    ax = axes[2]
    times = [results[k].get("runtime", 0) for k in pattern_counts]
    ax.plot(pattern_counts, times, "D-", color="#FF9800", linewidth=2, markersize=8)
    ax.set_xlabel("Max Patterns per Material")
    ax.set_ylabel("Runtime (s)")
    ax.set_title("Runtime vs Pattern Count")
    ax.grid(True, alpha=0.3)

    fig.suptitle("Sensitivity Analysis: Pattern Count", fontweight="bold")
    plt.tight_layout()
    return save_figure(fig, output_dir / "sensitivity_patterns")


def plot_sensitivity_weights(
    results: list[dict[str, Any]],
    param_names: list[str],
    output_dir: str | Path,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Plot sensitivity analysis for scoring weights."""
    output_dir = ensure_dir(output_dir)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    values = [r.get("utilization", 0) * 100 for r in results]

    # Utilization
    ax = axes[0]
    ax.bar(range(len(results)), values, color=plt.cm.viridis(np.linspace(0, 1, len(results))))
    ax.set_xticks(range(len(results)))
    ax.set_xticklabels(param_names, rotation=15)
    ax.set_ylabel("Utilization (%)")
    ax.set_title("Utilization Sensitivity")

    # Profit
    ax = axes[1]
    profits = [r.get("profit", 0) for r in results]
    ax.bar(range(len(results)), profits, color=plt.cm.plasma(np.linspace(0, 1, len(results))))
    ax.set_xticks(range(len(results)))
    ax.set_xticklabels(param_names, rotation=15)
    ax.set_ylabel("Total Profit")
    ax.set_title("Profit Sensitivity")

    # Runtime
    ax = axes[2]
    times = [r.get("runtime", 0) for r in results]
    ax.bar(range(len(results)), times, color=plt.cm.magma(np.linspace(0, 1, len(results))))
    ax.set_xticks(range(len(results)))
    ax.set_xticklabels(param_names, rotation=15)
    ax.set_ylabel("Runtime (s)")
    ax.set_title("Runtime Sensitivity")

    fig.suptitle("Sensitivity Analysis: Scoring Weights", fontweight="bold")
    plt.tight_layout()
    return save_figure(fig, output_dir / "sensitivity_weights")


def plot_3d_layout(
    pattern: Pattern,
    material: Material,
    pieces: dict[str, Piece],
    output_dir: str | Path,
    title: str | None = None,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Generate 3D visualization of a single pattern layout."""
    output_dir = ensure_dir(output_dir)

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")

    # Define colors for different piece types
    piece_colors = plt.cm.Set2(np.linspace(0, 1, max(1, len(pieces))))
    color_map = {name: piece_colors[i % len(piece_colors)] for i, name in enumerate(sorted(pieces.keys()))}

    # Draw material outline
    L, W, H = material.length, material.width, material.height
    _draw_box(ax, 0, 0, 0, L, W, H, color="gray", alpha=0.1, linewidth=1, linestyle="--")

    # Draw each placed piece
    for i, pp in enumerate(pattern.placed_pieces):
        color = color_map.get(pp.piece_name, "blue")
        _draw_box(
            ax, pp.x, pp.y, pp.z, pp.dx, pp.dy, pp.dz,
            color=color, alpha=0.7, linewidth=0.8,
            label=pp.piece_name if i == 0 or pp.piece_name not in [
                pp2.piece_name for pp2 in pattern.placed_pieces[:i]
            ] else "",
        )

    # Add piece type labels (only once per type)
    legend_elements = []
    seen_piece_types: set[str] = set()
    for pp in pattern.placed_pieces:
        if pp.piece_name not in seen_piece_types:
            seen_piece_types.add(pp.piece_name)
            legend_elements.append(
                Patch(facecolor=color_map[pp.piece_name], label=pp.piece_name)
            )

    ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

    ax.set_xlabel("Length (X)")
    ax.set_ylabel("Width (Y)")
    ax.set_zlabel("Height (Z)")
    ax.set_xlim(0, L)
    ax.set_ylim(0, W)
    ax.set_zlim(0, H)

    if title:
        ax.set_title(title, fontweight="bold")
    else:
        ax.set_title(
            f"3D Layout: Pattern {pattern.pattern_id} on {material.name} "
            f"({pattern.num_pieces} pieces, {pattern.used_volume / material.volume * 100:.1f}% util)",
            fontweight="bold",
        )

    # Set equal aspect ratio approximately
    max_range = max(L, W, H)
    ax.set_box_aspect((L / max_range, W / max_range, H / max_range))

    fname = f"3d_layout_pattern_{pattern.pattern_id}_{material.name}"
    return save_figure(fig, output_dir / fname)


def _draw_box(
    ax: plt.Axes,
    x: int, y: int, z: int,
    dx: int, dy: int, dz: int,
    color: Any = "blue",
    alpha: float = 0.5,
    linewidth: float = 1.0,
    linestyle: str = "-",
    label: str = "",
):
    """Draw a 3D box from (x,y,z) to (x+dx, y+dy, z+dz)."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    vertices = np.array([
        [x, y, z],
        [x + dx, y, z],
        [x + dx, y + dy, z],
        [x, y + dy, z],
        [x, y, z + dz],
        [x + dx, y, z + dz],
        [x + dx, y + dy, z + dz],
        [x, y + dy, z + dz],
    ])

    faces = [
        [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
        [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
        [vertices[0], vertices[1], vertices[5], vertices[4]],  # front
        [vertices[2], vertices[3], vertices[7], vertices[6]],  # back
        [vertices[1], vertices[2], vertices[6], vertices[5]],  # right
        [vertices[0], vertices[3], vertices[7], vertices[4]],  # left
    ]

    # Draw faces with transparency
    poly = Poly3DCollection(faces, alpha=alpha, facecolor=color, edgecolor="black",
                            linewidth=linewidth, linestyle=linestyle)
    if label:
        poly.set_label(label)
    ax.add_collection3d(poly)


def generate_all_plots(
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    output_dir: str | Path,
    patterns: list[Pattern] | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, list[Path]]:
    """Generate all required plots for a single experiment result."""
    output_dir = ensure_dir(output_dir)

    if logger:
        logger.info(f"Generating plots for {result.problem_name}...")

    all_paths: dict[str, list[Path]] = {}

    plot_funcs = [
        ("material_utilization", plot_material_utilization),
        ("waste_volume", plot_waste_volume),
        ("piece_counts", plot_piece_counts),
        ("profit_contribution", plot_profit_contribution),
        ("total_profit", plot_total_profit),
        ("pattern_usage", plot_pattern_usage),
        ("bound_gap", plot_bound_gap),
    ]

    for name, func in plot_funcs:
        try:
            kwargs = {"result": result, "materials": materials, "pieces": pieces, "output_dir": output_dir, "logger": logger}
            # Adjust kwargs based on function
            if name == "total_profit":
                kwargs = {"result": result, "output_dir": output_dir, "logger": logger}
            elif name in ("piece_counts", "profit_contribution"):
                kwargs = {"result": result, "pieces": pieces, "output_dir": output_dir, "logger": logger}
            elif name == "pattern_usage":
                kwargs = {"result": result, "output_dir": output_dir, "logger": logger}
            elif name == "bound_gap":
                kwargs = {"result": result, "output_dir": output_dir, "logger": logger}

            paths = func(**kwargs)
            all_paths[name] = paths
            if logger:
                logger.info(f"  {name}: {len(paths)} file(s)")
        except Exception as e:
            if logger:
                logger.error(f"  Failed to generate {name}: {e}")

    # Generate 3D layout plots for selected patterns
    if patterns:
        layout_dir = output_dir.parent / "3d_layouts" / result.problem_name
        pattern_map = {p.pattern_id: p for p in patterns}
        used_patterns = [
            pattern_map[pid] for pid in result.solution.pattern_usage
            if pid in pattern_map
        ]
        # Plot up to 10 representative patterns
        for pat in used_patterns[:10]:
            try:
                mat = materials.get(pat.material_name)
                if mat:
                    paths = plot_3d_layout(
                        pat, mat, pieces,
                        output_dir=layout_dir,
                        title=f"Pattern {pat.pattern_id} ({pat.material_name}) - "
                              f"{pat.num_pieces} pieces, "
                              f"{pat.used_volume / mat.volume * 100:.1f}% util",
                        logger=logger,
                    )
                    all_paths[f"3d_layout_p{pat.pattern_id}"] = paths
            except Exception as e:
                if logger:
                    logger.error(f"  Failed 3D layout for pattern {pat.pattern_id}: {e}")

    return all_paths
