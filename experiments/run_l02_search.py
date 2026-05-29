"""L02 Specialized Search - verify and improve L02 material utilization.

Searches for patterns exceeding the current baseline of 3,600,000
used volume per L02 block (96% utilization of 3,750,000).
"""

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
from src.cutting3d.pattern_generator import (
    generate_grid_patterns,
    generate_greedy_patterns,
    generate_improved_greedy_patterns,
    generate_extreme_point_patterns,
)
from src.cutting3d.geometry import validate_pattern
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.utils import ensure_dir


def main():
    parser = argparse.ArgumentParser(description="Run L02 specialized search")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    ensure_dir("logs")
    ensure_dir("outputs/results")

    logger = setup_logging("logs", seed=20260528, config_path=str(config_path))
    log_versions(logger)

    config = load_config(config_path)
    materials = create_materials(config)
    pieces = create_pieces(config)
    all_orientations = generate_all_orientations(pieces)

    l02 = materials["L02"]
    baseline_used = 3_600_000
    baseline_util = baseline_used / l02.volume

    logger.info("=" * 60)
    logger.info("L02 Specialized Search")
    logger.info(f"  L02 volume: {l02.volume:,}")
    logger.info(f"  Baseline used: {baseline_used:,} ({baseline_util*100:.1f}%)")
    logger.info("=" * 60)

    all_patterns: list[dict[str, Any]] = []
    pid = 0
    start_time = time.time()

    # Strategy 1: Grid patterns with higher resolution
    logger.info("Strategy 1: Grid patterns...")
    for pname, piece in pieces.items():
        orients = all_orientations[pname]
        for _ in range(3):  # multiple random offsets
            patterns = generate_grid_patterns(l02, piece, orients, pid, max_patterns=10)
            for p in patterns:
                p.pattern_id = pid
                pid += 1
                is_valid, _ = validate_pattern(p.placed_pieces, l02)
                if is_valid:
                    all_patterns.append(_pattern_to_record(p, l02, pieces, "grid"))
            pid += len(patterns)

    # Strategy 2: Improved greedy with multiple seeds
    logger.info("Strategy 2: Improved greedy patterns...")
    for seed_offset in range(20):
        cfg = dict(config)
        cfg["greedy"] = dict(config.get("greedy", {}))
        cfg["greedy"]["mode"] = "improved"
        cfg["random_seed"] = config.get("random_seed", 20260528) + seed_offset * 1000

        patterns = generate_improved_greedy_patterns(
            l02, pieces, all_orientations, pid, cfg, max_patterns=30
        )
        for p in patterns:
            p.pattern_id = pid
            pid += 1
            is_valid, _ = validate_pattern(p.placed_pieces, l02)
            if is_valid:
                all_patterns.append(_pattern_to_record(p, l02, pieces, "improved_greedy"))
        pid += len(patterns)

    # Strategy 3: Extreme point with intensive settings
    logger.info("Strategy 3: Extreme point patterns (intensive)...")
    for seed_offset in range(15):
        ep_cfg = dict(config)
        ep_cfg["extreme_point"] = {
            "alpha": 1.0, "beta": 0.5, "gamma": 0.3, "eta": 0.1,
            "beam_width": 10, "random_restarts": 20,
        }

        patterns = generate_extreme_point_patterns(
            l02, pieces, all_orientations, pid, ep_cfg, max_patterns=20
        )
        for p in patterns:
            p.pattern_id = pid
            pid += 1
            is_valid, _ = validate_pattern(p.placed_pieces, l02)
            if is_valid:
                all_patterns.append(_pattern_to_record(p, l02, pieces, "extreme_point"))
        pid += len(patterns)

    # Strategy 4: Different weight combinations for EP
    logger.info("Strategy 4: EP with alternative weights...")
    weight_configs = [
        {"alpha": 1.5, "beta": 0.3, "gamma": 0.5, "eta": 0.05},
        {"alpha": 0.8, "beta": 0.8, "gamma": 0.2, "eta": 0.1},
        {"alpha": 1.2, "beta": 0.4, "gamma": 0.6, "eta": 0.05},
    ]
    for wc in weight_configs:
        ep_cfg = dict(config)
        ep_cfg["extreme_point"] = {**wc, "beam_width": 8, "random_restarts": 15}
        for seed_offset in range(5):
            patterns = generate_extreme_point_patterns(
                l02, pieces, all_orientations, pid, ep_cfg, max_patterns=10
            )
            for p in patterns:
                p.pattern_id = pid
                pid += 1
                is_valid, _ = validate_pattern(p.placed_pieces, l02)
                if is_valid:
                    all_patterns.append(_pattern_to_record(p, l02, pieces, "ep_alt_weights"))
            pid += len(patterns)

    elapsed = time.time() - start_time

    # Deduplicate by used volume + piece counts
    seen: set[tuple] = set()
    unique_patterns: list[dict[str, Any]] = []
    for rec in all_patterns:
        key = (rec["used_volume"], tuple(rec[f"count_{pn}"] for pn in sorted(pieces.keys())))
        if key not in seen:
            seen.add(key)
            unique_patterns.append(rec)

    # Sort by utilization descending
    unique_patterns.sort(key=lambda r: -r["utilization"])
    unique_patterns = unique_patterns[:200]

    # Annotate ranks
    for i, rec in enumerate(unique_patterns):
        rec["rank"] = i + 1

    # Find best
    best = unique_patterns[0] if unique_patterns else {"used_volume": 0, "utilization": 0.0}
    found_better = best["used_volume"] > baseline_used

    # Save CSV
    csv_path = Path("outputs/results/l02_best_patterns.csv")
    if unique_patterns:
        fieldnames = [
            "rank", "pattern_id", "used_volume", "waste_volume", "utilization",
            "total_profit", "count_J01", "count_J02", "count_J03", "count_J04",
            "count_J05", "count_J06", "count_J07", "num_pieces", "source_method", "is_valid",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_patterns)

    # Save report
    report = {
        "best_used_volume": best["used_volume"],
        "best_waste_volume": l02.volume - best["used_volume"],
        "best_utilization": best["utilization"],
        "found_better_than_current": found_better,
        "current_baseline_used_volume": baseline_used,
        "current_baseline_utilization": baseline_util,
        "num_patterns_checked": len(all_patterns),
        "num_valid_patterns": len(unique_patterns),
        "search_configs": {"strategies": ["grid", "improved_greedy", "extreme_point_intensive", "ep_alt_weights"]},
        "runtime_seconds": elapsed,
    }

    report_path = Path("outputs/results/l02_search_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"L02 search complete in {elapsed:.2f}s")
    logger.info(f"  Best: {best['used_volume']:,} ({best['utilization']*100:.2f}%)")
    logger.info(f"  Found better than baseline: {found_better}")
    logger.info(f"  CSV: {csv_path}")
    logger.info(f"  Report: {report_path}")


def _pattern_to_record(pattern, material, pieces, source):
    """Convert pattern to dict record."""
    pc = pattern.get_piece_counts(sorted(pieces.keys()))
    return {
        "pattern_id": pattern.pattern_id,
        "used_volume": pattern.used_volume,
        "waste_volume": material.volume - pattern.used_volume,
        "utilization": pattern.used_volume / material.volume,
        "total_profit": sum(pieces[pp.piece_name].profit for pp in pattern.placed_pieces if pp.piece_name in pieces),
        "count_J01": pc.get("J01", 0), "count_J02": pc.get("J02", 0),
        "count_J03": pc.get("J03", 0), "count_J04": pc.get("J04", 0),
        "count_J05": pc.get("J05", 0), "count_J06": pc.get("J06", 0),
        "count_J07": pc.get("J07", 0),
        "num_pieces": pattern.num_pieces,
        "source_method": source,
        "is_valid": True,
        "rank": 0,
    }


if __name__ == "__main__":
    main()
