"""Run exact optimality certificate generation.

Generates L02 infeasibility certificate, Problem 1 global optimal certificate,
and Problem 2 optimality certificate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.data import load_config, create_materials, create_pieces
from src.cutting3d.certificate import (
    generate_l02_infeasibility_certificate,
    generate_problem1_certificate,
    generate_problem2_certificate,
    generate_optimality_report,
)
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.utils import ensure_dir


def main():
    parser = argparse.ArgumentParser(description="Run exact optimality certificate")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--fast", action="store_true", help="Fast mode: fewer vector checks")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    ensure_dir("logs")
    ensure_dir("outputs/results")
    ensure_dir("outputs/reports")

    logger = setup_logging("logs", seed=20260528, config_path=str(config_path))
    log_versions(logger)

    config = load_config(config_path)
    materials = create_materials(config)
    pieces = create_pieces(config)

    if args.fast:
        config["exact_certificate"]["cp_sat_time_limit"] = 15
        config["exact_certificate"]["max_vectors"] = 10000

    total_start = time.time()

    # Load current problem 1 solution for context
    p1_path = Path("outputs/results/problem1_solution.json")
    p2_path = Path("outputs/results/problem2_solution.json")

    current_utilization = 0.99
    current_waste = 750000
    current_used_volume = 75000000
    current_profit = 745680

    if p1_path.exists():
        with open(p1_path, "r", encoding="utf-8") as f:
            p1_data = json.load(f)
        sol = p1_data.get("solution", {})
        current_utilization = sol.get("material_utilization", 0.99)
        current_waste = sol.get("total_waste_volume", 750000)
        current_used_volume = sol.get("total_used_volume", 75000000)

    if p2_path.exists():
        with open(p2_path, "r", encoding="utf-8") as f:
            p2_data = json.load(f)
        sol = p2_data.get("solution", {})
        current_profit = sol.get("total_profit", 745680)

    # Step 1: L02 infeasibility certificate
    logger.info("\n" + "=" * 60)
    logger.info("Step 1: L02 Infeasibility Certificate")
    logger.info("=" * 60)

    cert_start = time.time()
    l02_cert = generate_l02_infeasibility_certificate(
        materials=materials,
        pieces=pieces,
        config=config,
        baseline_used_volume=3_600_000,
        output_dir="outputs/results",
        logger=logger,
    )
    l02_time = time.time() - cert_start

    # Step 2: Problem 1 global optimal certificate
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Problem 1 Global Optimal Certificate")
    logger.info("=" * 60)

    p1_cert = generate_problem1_certificate(
        materials=materials,
        pieces=pieces,
        l02_certificate=l02_cert,
        current_utilization=current_utilization,
        current_waste=current_waste,
        current_used_volume=current_used_volume,
        output_dir="outputs/results",
        logger=logger,
    )

    # Step 3: Problem 2 optimality certificate
    logger.info("\n" + "=" * 60)
    logger.info("Step 3: Problem 2 Optimality Certificate")
    logger.info("=" * 60)

    p2_cert = generate_problem2_certificate(
        materials=materials,
        pieces=pieces,
        current_profit=current_profit,
        pattern_library_complete=False,
        output_dir="outputs/results",
        logger=logger,
    )

    # Step 4: Generate report
    logger.info("\n" + "=" * 60)
    logger.info("Step 4: Generating optimality certificate report")
    logger.info("=" * 60)

    generate_optimality_report(
        p1_cert=p1_cert,
        p2_cert=p2_cert,
        l02_cert=l02_cert,
        output_path="outputs/reports/optimality_certificate_report.md",
        logger=logger,
    )

    total_time = time.time() - total_start

    logger.info("\n" + "=" * 60)
    logger.info("Exact Certificate Summary")
    logger.info("=" * 60)
    logger.info(f"  L02 infeasibility: {l02_cert.get('proof_status', 'UNKNOWN')}")
    logger.info(f"  Problem 1 global optimal: {p1_cert.get('global_optimal_proved', False)}")
    logger.info(f"  Problem 2 global optimal: {p2_cert.get('global_optimal_proved', False)}")
    logger.info(f"  L02 time: {l02_time:.2f}s")
    logger.info(f"  Total time: {total_time:.2f}s")

    # Save timing
    cert_timing = {
        "l02_search_time": l02_time,
        "exact_certificate_time": total_time,
    }
    with open("outputs/results/certificate_timing.json", "w", encoding="utf-8") as f:
        json.dump(cert_timing, f, indent=2)


if __name__ == "__main__":
    main()
