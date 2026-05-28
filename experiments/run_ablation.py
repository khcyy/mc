"""Run ablation study to compare different algorithm components."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.experiment import ExperimentRunner
from src.cutting3d.data import load_config, create_materials, create_pieces
from src.cutting3d.orientations import generate_all_orientations
from src.cutting3d.pattern_generator import generate_all_patterns
from src.cutting3d.master_solver import solve_master_problem1
from src.cutting3d.models import ExperimentResult
from src.cutting3d.visualization import plot_ablation_comparison, generate_all_plots
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.metrics import compute_solution_metrics, print_summary
from src.cutting3d.utils import ensure_dir


def run_ablation_experiment(
    config: dict,
    materials,
    pieces,
    all_orientations,
    experiment_type: str,
    logger,
) -> dict:
    """Run a single ablation experiment variant."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Ablation: {experiment_type}")
    logger.info(f"{'='*60}")

    cfg = copy.deepcopy(config)
    pg_config = cfg.get("pattern_generation", {})

    start_time = time.time()

    if experiment_type == "only_grid_patterns":
        pg_config["grid_patterns"] = True
        pg_config["greedy_patterns"] = False
        pg_config["extreme_point_patterns"] = False
    elif experiment_type == "greedy_without_extreme_points":
        pg_config["grid_patterns"] = True
        pg_config["greedy_patterns"] = True
        pg_config["extreme_point_patterns"] = False
    elif experiment_type == "extreme_points_without_random_restart":
        pg_config["grid_patterns"] = True
        pg_config["greedy_patterns"] = True
        pg_config["extreme_point_patterns"] = True
        ep = cfg.get("extreme_point", {})
        ep["random_restarts"] = 1
        cfg["extreme_point"] = ep
    elif experiment_type == "full_hybrid_solver":
        pg_config["grid_patterns"] = True
        pg_config["greedy_patterns"] = True
        pg_config["extreme_point_patterns"] = True

    cfg["pattern_generation"] = pg_config

    patterns = generate_all_patterns(materials, pieces, all_orientations, cfg)
    solution = solve_master_problem1(materials, pieces, patterns, cfg)

    runtime = time.time() - start_time

    total_mat_vol = sum(m.volume * m.count for m in materials.values())

    result = {
        "experiment": experiment_type,
        "utilization": solution.total_used_volume / total_mat_vol if total_mat_vol > 0 else 0.0,
        "waste": solution.total_waste_volume,
        "profit": solution.total_profit,
        "runtime": runtime,
        "num_patterns": sum(len(v) for v in patterns.values()),
        "status": solution.status.value,
        "gap": solution.gap,
        "solve_time": solution.solve_time_seconds,
    }

    logger.info(f"  Utilization: {result['utilization']*100:.2f}%")
    logger.info(f"  Waste: {result['waste']}")
    logger.info(f"  Profit: {result['profit']}")
    logger.info(f"  Runtime: {runtime:.2f}s")

    return result


def main():
    parser = argparse.ArgumentParser(description="Run ablation study")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    ensure_dir("logs")
    ensure_dir("outputs/figures/ablation")

    logger = setup_logging("logs", seed=20260528, config_path=str(config_path))
    log_versions(logger)

    config = load_config(config_path)
    materials = create_materials(config)
    pieces = create_pieces(config)
    all_orientations = generate_all_orientations(pieces)

    experiments = [
        "only_grid_patterns",
        "greedy_without_extreme_points",
        "extreme_points_without_random_restart",
        "full_hybrid_solver",
    ]

    results = {}
    for exp_name in experiments:
        try:
            results[exp_name] = run_ablation_experiment(
                config, materials, pieces, all_orientations, exp_name, logger
            )
        except Exception as e:
            logger.error(f"Ablation {exp_name} failed: {e}", exc_info=True)
            results[exp_name] = {
                "experiment": exp_name,
                "utilization": 0,
                "waste": 0,
                "profit": 0,
                "runtime": 0,
                "num_patterns": 0,
                "status": "FAILED",
                "error": str(e),
            }

    # Save results
    output_path = Path("outputs/results/ablation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Ablation results saved to: {output_path}")

    # Generate plot
    try:
        plot_ablation_comparison(results, "outputs/figures/ablation", logger)
        logger.info("Ablation plot generated.")
    except Exception as e:
        logger.error(f"Failed to generate ablation plot: {e}")

    logger.info("Ablation study completed.")


if __name__ == "__main__":
    main()
