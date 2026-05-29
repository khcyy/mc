"""Run all experiments: Problem 1, Problem 2, ablation, sensitivity, L02 search,
exact certificate, Excel filling. Supports command-line flags for selective execution.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.data import load_config, create_materials, create_pieces
from src.cutting3d.experiment import ExperimentRunner
from src.cutting3d.visualization import generate_all_plots
from src.cutting3d.excel_writer import (
    fill_result_xlsx, save_template_mapping, make_backup,
    generate_validation_report,
)
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.metrics import print_summary
from src.cutting3d.utils import ensure_dir
from src.cutting3d.models import ExperimentResult


def main():
    parser = argparse.ArgumentParser(description="Run all experiments")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--skip-problem1", action="store_true")
    parser.add_argument("--skip-problem2", action="store_true")
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--skip-sensitivity", action="store_true")
    parser.add_argument("--skip-l02-search", action="store_true")
    parser.add_argument("--skip-fill-excel", action="store_true")
    parser.add_argument("--skip-certificate", action="store_true")
    parser.add_argument("--with-exact-certificate", action="store_true")
    parser.add_argument("--only-plots", action="store_true")
    parser.add_argument("--only-fill-excel", action="store_true")
    parser.add_argument("--output-dir", type=str, default="outputs")
    args = parser.parse_args()

    ensure_dir("logs")
    for d in ["results", "figures/problem1", "figures/problem2", "figures/ablation",
              "figures/sensitivity", "figures/3d_layouts", "reports"]:
        ensure_dir(f"outputs/{d}")

    logger = setup_logging("logs", seed=20260528)
    log_versions(logger)

    total_start = time.time()
    all_outputs: dict[str, str] = {}
    timing_summary: dict[str, float] = {}

    # ---- Problem 1 ----
    if not args.skip_problem1 and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 1: Problem 1 - Maximize Material Utilization")
        logger.info("=" * 60)
        try:
            runner = ExperimentRunner("configs/problem1.yaml", logger=logger)
            result1 = runner.run_problem1()

            runner.save_results(result1, "outputs/results")
            p1_timing = runner.timing
            timing_summary["problem1_pattern_generation_duration"] = p1_timing.get("pattern_generation_time", 0)
            timing_summary["problem1_master_solve_duration"] = p1_timing.get("master_solve_time", 0)
            all_outputs["problem1_json"] = "outputs/results/problem1_solution.json"
            all_outputs["problem1_csv"] = "outputs/results/problem1_summary.csv"

            plot_start = time.time()
            plot_paths = generate_all_plots(
                result1, runner.materials, runner.pieces,
                "outputs/figures/problem1", result1.patterns, logger=logger,
            )
            timing_summary["problem1_plotting_duration"] = time.time() - plot_start
            all_outputs["problem1_plots"] = str(plot_paths)
            logger.info("Problem 1 completed.")
        except Exception as e:
            logger.error(f"Problem 1 failed: {e}", exc_info=True)

    # ---- Problem 2 ----
    if not args.skip_problem2 and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2: Problem 2 - Maximize Total Profit")
        logger.info("=" * 60)
        try:
            runner = ExperimentRunner("configs/problem2.yaml", logger=logger)
            result2 = runner.run_problem2()

            runner.save_results(result2, "outputs/results")
            p2_timing = runner.timing
            timing_summary["problem2_pattern_generation_duration"] = p2_timing.get("pattern_generation_time", 0)
            timing_summary["problem2_master_solve_duration"] = p2_timing.get("master_solve_time", 0)
            all_outputs["problem2_json"] = "outputs/results/problem2_solution.json"
            all_outputs["problem2_csv"] = "outputs/results/problem2_summary.csv"

            plot_start = time.time()
            plot_paths = generate_all_plots(
                result2, runner.materials, runner.pieces,
                "outputs/figures/problem2", result2.patterns, logger=logger,
            )
            timing_summary["problem2_plotting_duration"] = time.time() - plot_start
            all_outputs["problem2_plots"] = str(plot_paths)
            logger.info("Problem 2 completed.")
        except Exception as e:
            logger.error(f"Problem 2 failed: {e}", exc_info=True)

    # ---- Ablation ----
    if not args.skip_ablation and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 3: Ablation Study")
        logger.info("=" * 60)
        try:
            subprocess.run(
                [sys.executable, "-m", "experiments.run_ablation", "--config", "configs/default.yaml"],
                cwd=Path(__file__).resolve().parent.parent, check=False,
            )
        except Exception as e:
            logger.error(f"Ablation failed: {e}")

    # ---- Sensitivity ----
    if not args.skip_sensitivity and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 4: Sensitivity Analysis")
        logger.info("=" * 60)
        try:
            subprocess.run(
                [sys.executable, "-m", "experiments.run_sensitivity", "--config", "configs/default.yaml"],
                cwd=Path(__file__).resolve().parent.parent, check=False,
            )
        except Exception as e:
            logger.error(f"Sensitivity failed: {e}")

    # ---- L02 Search ----
    if not args.skip_l02_search and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 5: L02 Specialized Search")
        logger.info("=" * 60)
        try:
            subprocess.run(
                [sys.executable, "-m", "experiments.run_l02_search", "--config", "configs/default.yaml"],
                cwd=Path(__file__).resolve().parent.parent, check=False,
            )
        except Exception as e:
            logger.error(f"L02 search failed: {e}")

    # ---- Exact Certificate ----
    if args.with_exact_certificate and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 6: Exact Optimality Certificate")
        logger.info("=" * 60)
        try:
            subprocess.run(
                [sys.executable, "-m", "experiments.run_exact_certificate",
                 "--config", "configs/default.yaml", "--fast"],
                cwd=Path(__file__).resolve().parent.parent, check=False,
            )
        except Exception as e:
            logger.error(f"Exact certificate failed: {e}")

    # ---- Excel Filling ----
    if not args.skip_fill_excel or args.only_fill_excel:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE: Excel Template Filling & Validation")
        logger.info("=" * 60)
        try:
            _fill_and_validate_excel(logger, all_outputs, timing_summary)
        except Exception as e:
            logger.error(f"Excel filling failed: {e}", exc_info=True)

    # ---- Reports ----
    timing_summary["total_runtime"] = time.time() - total_start
    _generate_experiment_report(logger, all_outputs, timing_summary)

    # ---- Final Summary ----
    _print_final_summary(logger, all_outputs, timing_summary)


def _fill_and_validate_excel(logger, all_outputs, timing):
    """Fill, backup, map, and validate Excel files."""
    materials = create_materials(load_config("configs/default.yaml"))
    pieces = create_pieces(load_config("configs/default.yaml"))

    combined_validation: dict[str, Any] = {}

    for prob_name, template, filled_name in [
        ("problem1", "outputs/results/result1.xlsx", "result1_filled.xlsx"),
        ("problem2", "outputs/results/result2.xlsx", "result2_filled.xlsx"),
    ]:
        result_path = Path(f"outputs/results/{prob_name}_solution.json")
        if not result_path.exists():
            logger.warning(f"{result_path} not found, skipping Excel fill for {prob_name}")
            continue

        result = ExperimentResult.from_json(str(result_path))

        # 1. Backup
        make_backup(template, "outputs/results/backups")

        # 2. Template mapping
        map_name = f"template_mapping_{filled_name.replace('.xlsx', '.json')}"
        save_template_mapping(template, f"outputs/results/{map_name}", logger)

        # 3. Fill Excel
        excel_start = time.time()
        filled_path = f"outputs/results/{filled_name}"
        success, report = fill_result_xlsx(
            template, filled_path, result, materials, pieces, logger, timing=timing,
        )
        timing["excel_writing_time"] = time.time() - excel_start
        logger.info(f"{filled_name}: success={success}, data_cells={report['grey_cells_found']}, filled={report['grey_cells_filled']}")

        # 4. Validate individually
        key = "result1" if "problem1" in prob_name else "result2"
        val_report = generate_validation_report(
            filled_path, result, materials, pieces,
            f"outputs/results/excel_validation_{key}.json", logger,
        )
        combined_validation[key] = val_report
        all_outputs[f"{prob_name}_filled"] = filled_path

    # Combined validation report
    with open("outputs/results/excel_validation_report.json", "w", encoding="utf-8") as f:
        json.dump(combined_validation, f, indent=2, ensure_ascii=False)
    logger.info("Combined excel_validation_report.json saved")

    # Combined template mapping
    _save_combined_mapping(logger)


def _save_combined_mapping(logger):
    """Save combined template_mapping.json."""
    combined = {}
    for name in ["template_mapping_result1_filled.json", "template_mapping_result2_filled.json"]:
        path = Path(f"outputs/results/{name}")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                key = "result1" if "result1" in name else "result2"
                combined[key] = json.load(f)
    with open("outputs/results/template_mapping.json", "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    logger.info("Combined template_mapping.json saved")


def _generate_experiment_report(logger, all_outputs, timing):
    """Generate experiment_summary.md."""
    report_path = Path("outputs/reports/experiment_summary.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Experiment Summary - 3D Cutting Stock Optimization",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total runtime: {timing.get('total_runtime', 0):.2f}s",
        f"Random seed: 20260528",
        "",
        "## Runtime Breakdown",
        "",
    ]
    for key, val in timing.items():
        lines.append(f"- **{key}**: {val:.2f}s")
    lines += ["", "## Output Files", ""]
    for key, path in sorted(all_outputs.items()):
        if isinstance(path, str) and len(path) < 200:
            lines.append(f"- **{key}**: `{path}`")

    lines += [
        "",
        "## Optimality Notes",
        "",
        "**IMPORTANT**: CP-SAT solver returning OPTIMAL means the solution is optimal",
        "WITHIN the generated pattern library, NOT necessarily globally optimal.",
        "",
        "For rigorous global optimality claims, see `outputs/reports/optimality_certificate_report.md`.",
        "",
        "## Figures",
        "",
        "| Type | Path |",
        "|------|------|",
        "| Problem 1 | `outputs/figures/problem1/` |",
        "| Problem 2 | `outputs/figures/problem2/` |",
        "| Ablation | `outputs/figures/ablation/` |",
        "| Sensitivity | `outputs/figures/sensitivity/` |",
        "| 3D Layouts | `outputs/figures/3d_layouts/` |",
        "",
        "## Excel Files",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| `result1.xlsx` | Original template (preserved) |",
        "| `result2.xlsx` | Original template (preserved) |",
        "| `result1_filled.xlsx` | Filled + computed_solution |",
        "| `result2_filled.xlsx` | Filled + computed_solution |",
        "| `excel_validation_report.json` | Cross-validation report |",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Experiment report: {report_path}")


def _print_final_summary(logger, all_outputs, timing):
    """Print final summary to terminal."""
    summary = f"""
======================================================================
  3D Cutting Stock Optimization - COMPLETED
======================================================================
  Total Runtime: {timing.get('total_runtime', 0):.2f}s
  P1 Pattern Gen:  {timing.get('problem1_pattern_generation_duration', 0):.2f}s
  P1 Master Solve: {timing.get('problem1_master_solve_duration', 0):.2f}s
  P2 Pattern Gen:  {timing.get('problem2_pattern_generation_duration', 0):.2f}s
  P2 Master Solve: {timing.get('problem2_master_solve_duration', 0):.2f}s

Output directories:
  Results:  outputs/results/
  Figures:  outputs/figures/
  Logs:     logs/
  Reports:  outputs/reports/

Excel files:
  result1_filled.xlsx  (with computed_solution sheet)
  result2_filled.xlsx  (with computed_solution sheet)

======================================================================
"""
    logger.info(summary)
    print(summary)


if __name__ == "__main__":
    main()
