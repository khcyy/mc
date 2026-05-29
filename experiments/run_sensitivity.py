"""Run sensitivity analysis on key algorithm parameters."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.data import load_config, create_materials, create_pieces
from src.cutting3d.orientations import generate_all_orientations
from src.cutting3d.pattern_generator import generate_all_patterns
from src.cutting3d.master_solver import solve_master_problem1
from src.cutting3d.visualization import plot_sensitivity_patterns, plot_sensitivity_weights
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.utils import ensure_dir


def run_pattern_count_sensitivity(
    config: dict,
    materials,
    pieces,
    all_orientations,
    logger,
) -> dict:
    """Sensitivity analysis on max patterns per material."""
    logger.info("\n" + "=" * 60)
    logger.info("Sensitivity: Pattern Count")
    logger.info("=" * 60)

    pattern_counts = [20, 50, 100, 150, 200]
    results = {}

    for max_pat in pattern_counts:
        cfg = copy.deepcopy(config)
        cfg["pattern_generation"]["max_patterns_per_material"] = max_pat

        start = time.time()
        patterns = generate_all_patterns(materials, pieces, all_orientations, cfg)
        solution = solve_master_problem1(materials, pieces, patterns, cfg)
        runtime = time.time() - start

        total_mat_vol = sum(m.volume * m.count for m in materials.values())

        results[max_pat] = {
            "utilization": solution.total_used_volume / total_mat_vol if total_mat_vol > 0 else 0.0,
            "waste": solution.total_waste_volume,
            "profit": solution.total_profit,
            "runtime": runtime,
            "num_patterns": sum(len(v) for v in patterns.values()),
            "status": solution.status.value,
        }

        logger.info(f"  Max patterns {max_pat}: util={results[max_pat]['utilization']*100:.2f}%, "
                     f"profit={results[max_pat]['profit']}, runtime={runtime:.2f}s")

    return results


def run_weight_sensitivity(
    config: dict,
    materials,
    pieces,
    all_orientations,
    logger,
) -> tuple[list[dict], list[str]]:
    """Sensitivity analysis on scoring weights."""
    logger.info("\n" + "=" * 60)
    logger.info("Sensitivity: Scoring Weights")
    logger.info("=" * 60)

    weight_configs = [
        {"name": "default", "alpha": 1.0, "beta": 0.5, "gamma": 0.3, "eta": 0.1},
        {"name": "volume_only", "alpha": 1.0, "beta": 0.0, "gamma": 0.0, "eta": 0.0},
        {"name": "profit_only", "alpha": 0.0, "beta": 1.0, "gamma": 0.0, "eta": 0.0},
        {"name": "balanced", "alpha": 0.5, "beta": 0.5, "gamma": 0.2, "eta": 0.05},
        {"name": "contact_heavy", "alpha": 0.3, "beta": 0.3, "gamma": 0.8, "eta": 0.05},
    ]

    results = []
    names = []

    for wc in weight_configs:
        cfg = copy.deepcopy(config)
        cfg["extreme_point"]["alpha"] = wc["alpha"]
        cfg["extreme_point"]["beta"] = wc["beta"]
        cfg["extreme_point"]["gamma"] = wc["gamma"]
        cfg["extreme_point"]["eta"] = wc["eta"]

        start = time.time()
        patterns = generate_all_patterns(materials, pieces, all_orientations, cfg)
        solution = solve_master_problem1(materials, pieces, patterns, cfg)
        runtime = time.time() - start

        total_mat_vol = sum(m.volume * m.count for m in materials.values())

        r = {
            "name": wc["name"],
            "utilization": solution.total_used_volume / total_mat_vol if total_mat_vol > 0 else 0.0,
            "waste": solution.total_waste_volume,
            "profit": solution.total_profit,
            "runtime": runtime,
            "status": solution.status.value,
        }
        results.append(r)
        names.append(wc["name"])

        logger.info(f"  {wc['name']}: util={r['utilization']*100:.2f}%, "
                     f"profit={r['profit']}, runtime={runtime:.2f}s")

    return results, names


def main():
    parser = argparse.ArgumentParser(description="Run sensitivity analysis")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    ensure_dir("logs")
    ensure_dir("outputs/figures/sensitivity")
    ensure_dir("outputs/results")

    logger = setup_logging("logs", seed=20260528, config_path=str(config_path))
    log_versions(logger)

    config = load_config(config_path)
    materials = create_materials(config)
    pieces = create_pieces(config)
    all_orientations = generate_all_orientations(pieces)

    # Pattern count sensitivity
    try:
        pattern_results = run_pattern_count_sensitivity(
            config, materials, pieces, all_orientations, logger
        )
        with open("outputs/results/sensitivity_patterns.json", "w", encoding="utf-8") as f:
            json.dump(pattern_results, f, indent=2, ensure_ascii=False)

        plot_sensitivity_patterns(pattern_results, "outputs/figures/sensitivity", logger)
    except Exception as e:
        logger.error(f"Pattern sensitivity failed: {e}", exc_info=True)

    # Weight sensitivity
    try:
        weight_results, weight_names = run_weight_sensitivity(
            config, materials, pieces, all_orientations, logger
        )
        with open("outputs/results/sensitivity_weights.json", "w", encoding="utf-8") as f:
            json.dump(weight_results, f, indent=2, ensure_ascii=False)

        plot_sensitivity_weights(weight_results, weight_names, "outputs/figures/sensitivity", logger)
    except Exception as e:
        logger.error(f"Weight sensitivity failed: {e}", exc_info=True)

    # Save combined CSV
    _save_sensitivity_csv(pattern_results, weight_results, weight_names, logger)

    logger.info("Sensitivity analysis completed.")


def _save_sensitivity_csv(pattern_results, weight_results, weight_names, logger) -> None:
    """Save combined sensitivity results to CSV."""
    import csv
    csv_path = Path("outputs/results/sensitivity_results.csv")
    fieldnames = [
        "parameter_name", "parameter_value", "problem_name",
        "objective_value", "total_profit", "material_utilization",
        "total_waste_volume", "runtime", "total_patterns_generated",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for max_pat, r in pattern_results.items():
            writer.writerow({
                "parameter_name": "max_patterns_per_material",
                "parameter_value": max_pat,
                "problem_name": "problem1",
                "objective_value": r.get("waste", 0),
                "total_profit": r.get("profit", 0),
                "material_utilization": r.get("utilization", 0),
                "total_waste_volume": r.get("waste", 0),
                "runtime": r.get("runtime", 0),
                "total_patterns_generated": r.get("num_patterns", 0),
            })
        for i, r in enumerate(weight_results):
            writer.writerow({
                "parameter_name": "scoring_weights",
                "parameter_value": weight_names[i] if i < len(weight_names) else f"config_{i}",
                "problem_name": "problem1",
                "objective_value": r.get("waste", 0),
                "total_profit": r.get("profit", 0),
                "material_utilization": r.get("utilization", 0),
                "total_waste_volume": r.get("waste", 0),
                "runtime": r.get("runtime", 0),
                "total_patterns_generated": 0,
            })
    logger.info(f"Sensitivity CSV saved: {csv_path}")


if __name__ == "__main__":
    main()
