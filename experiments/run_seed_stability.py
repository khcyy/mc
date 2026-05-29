"""Run seed stability analysis to verify reproducibility - covers both problems."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.data import load_config, create_materials, create_pieces
from src.cutting3d.orientations import generate_all_orientations
from src.cutting3d.pattern_generator import generate_all_patterns
from src.cutting3d.master_solver import solve_master_problem1, solve_master_problem2
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.utils import ensure_dir


def main():
    parser = argparse.ArgumentParser(description="Run seed stability analysis")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    ensure_dir("logs")
    ensure_dir("outputs/results")

    logger = setup_logging("logs", seed=20260528, config_path=str(config_path))

    config = load_config(config_path)
    materials = create_materials(config)
    pieces = create_pieces(config)
    all_orientations = generate_all_orientations(pieces)
    total_vol = sum(m.volume * m.count for m in materials.values())

    seeds = [20260528, 42, 12345, 99999, 77777]
    results = []

    for seed in seeds:
        cfg = dict(config)
        cfg["random_seed"] = seed

        # Problem 1
        start = time.time()
        patterns1 = generate_all_patterns(materials, pieces, all_orientations, cfg)
        p1_sol = solve_master_problem1(materials, pieces, patterns1, cfg)
        p1_runtime = time.time() - start

        results.append({
            "seed": seed,
            "problem_name": "problem1",
            "objective_value": p1_sol.total_waste_volume,
            "material_utilization": p1_sol.material_utilization,
            "total_profit": p1_sol.total_profit,
            "total_waste_volume": p1_sol.total_waste_volume,
            "runtime": p1_runtime,
        })
        logger.info(f"  Seed {seed} P1: util={p1_sol.material_utilization*100:.4f}%, waste={p1_sol.total_waste_volume}, time={p1_runtime:.2f}s")

        # Problem 2
        p2_cfg = dict(cfg)
        p2_cfg["objective"] = "maximize_profit"
        p2_cfg["min_pieces_per_type"] = 10
        start = time.time()
        patterns2 = generate_all_patterns(materials, pieces, all_orientations, p2_cfg)
        p2_sol = solve_master_problem2(materials, pieces, patterns2, p2_cfg)
        p2_runtime = time.time() - start

        results.append({
            "seed": seed,
            "problem_name": "problem2",
            "objective_value": p2_sol.total_profit,
            "material_utilization": p2_sol.material_utilization,
            "total_profit": p2_sol.total_profit,
            "total_waste_volume": p2_sol.total_waste_volume,
            "runtime": p2_runtime,
        })
        logger.info(f"  Seed {seed} P2: profit={p2_sol.total_profit}, util={p2_sol.material_utilization*100:.2f}%, time={p2_runtime:.2f}s")

    # Save CSV
    csv_path = Path("outputs/results/seed_stability_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "seed", "problem_name", "objective_value", "material_utilization",
            "total_profit", "total_waste_volume", "runtime",
        ])
        writer.writeheader()
        writer.writerows(results)
    logger.info(f"Seed stability CSV saved: {csv_path}")

    json_path = Path("outputs/results/seed_stability_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Seed stability JSON saved: {json_path}")


if __name__ == "__main__":
    main()
