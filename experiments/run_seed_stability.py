"""Run seed stability analysis to verify reproducibility."""

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
from src.cutting3d.master_solver import solve_master_problem1
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

    seeds = [20260528, 42, 12345, 99999, 77777]

    results = []
    for seed in seeds:
        cfg = dict(config)
        cfg["random_seed"] = seed

        start = time.time()
        patterns = generate_all_patterns(materials, pieces, all_orientations, cfg)
        solution = solve_master_problem1(materials, pieces, patterns, cfg)
        runtime = time.time() - start

        total_vol = sum(m.volume * m.count for m in materials.values())

        results.append({
            "seed": seed,
            "problem_name": "problem1",
            "objective_value": solution.total_waste_volume,
            "material_utilization": solution.material_utilization,
            "total_profit": solution.total_profit,
            "total_waste_volume": solution.total_waste_volume,
            "runtime": runtime,
        })

        logger.info(f"  Seed {seed}: util={solution.material_utilization*100:.4f}%, waste={solution.total_waste_volume}, time={runtime:.2f}s")

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

    # Also save JSON
    json_path = Path("outputs/results/seed_stability_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Seed stability JSON saved: {json_path}")


if __name__ == "__main__":
    main()
