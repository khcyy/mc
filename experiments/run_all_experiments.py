"""Run all experiments: Problem 1, Problem 2, ablation, sensitivity, Excel filling.
Supports command-line flags for selective execution.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.data import load_config, create_materials, create_pieces
from src.cutting3d.experiment import ExperimentRunner
from src.cutting3d.visualization import generate_all_plots
from src.cutting3d.excel_writer import fill_result_xlsx, save_template_mapping
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.metrics import print_summary
from src.cutting3d.utils import ensure_dir

from experiments.run_ablation import main as run_ablation_main_func
from experiments.run_sensitivity import main as run_sensitivity_main_func


def main():
    parser = argparse.ArgumentParser(description="Run all experiments")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--skip-problem1", action="store_true")
    parser.add_argument("--skip-problem2", action="store_true")
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--skip-sensitivity", action="store_true")
    parser.add_argument("--skip-fill-excel", action="store_true")
    parser.add_argument("--only-plots", action="store_true")
    parser.add_argument("--only-fill-excel", action="store_true")
    parser.add_argument("--output-dir", type=str, default="outputs")
    args = parser.parse_args()

    # Setup directories
    ensure_dir("logs")
    ensure_dir("outputs/results")
    ensure_dir("outputs/figures/problem1")
    ensure_dir("outputs/figures/problem2")
    ensure_dir("outputs/figures/ablation")
    ensure_dir("outputs/figures/sensitivity")
    ensure_dir("outputs/figures/3d_layouts")
    ensure_dir("outputs/reports")

    logger = setup_logging("logs", seed=20260528)
    log_versions(logger)

    total_start = time.time()
    all_outputs: dict[str, str] = {}

    # ---- Problem 1 ----
    if not args.skip_problem1 and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 1: Problem 1 - Maximize Material Utilization")
        logger.info("=" * 60)
        try:
            config = load_config("configs/problem1.yaml")
            runner = ExperimentRunner("configs/problem1.yaml", logger=logger)
            result1 = runner.run_problem1()

            runner.save_results(result1, "outputs/results")
            all_outputs["problem1_json"] = "outputs/results/problem1_solution.json"
            all_outputs["problem1_csv"] = "outputs/results/problem1_summary.csv"

            # Generate plots
            plot_paths = generate_all_plots(
                result1, runner.materials, runner.pieces,
                "outputs/figures/problem1", result1.patterns, logger=logger,
            )
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
            config = load_config("configs/problem2.yaml")
            runner = ExperimentRunner("configs/problem2.yaml", logger=logger)
            result2 = runner.run_problem2()

            runner.save_results(result2, "outputs/results")
            all_outputs["problem2_json"] = "outputs/results/problem2_solution.json"
            all_outputs["problem2_csv"] = "outputs/results/problem2_summary.csv"

            plot_paths = generate_all_plots(
                result2, runner.materials, runner.pieces,
                "outputs/figures/problem2", result2.patterns, logger=logger,
            )
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
            import subprocess
            subprocess.run(
                [sys.executable, "-m", "experiments.run_ablation", "--config", "configs/default.yaml"],
                cwd=Path(__file__).resolve().parent.parent,
                check=False,
            )
        except Exception as e:
            logger.error(f"Ablation failed: {e}")

    # ---- Sensitivity ----
    if not args.skip_sensitivity and not args.only_fill_excel and not args.only_plots:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 4: Sensitivity Analysis")
        logger.info("=" * 60)
        try:
            import subprocess
            subprocess.run(
                [sys.executable, "-m", "experiments.run_sensitivity", "--config", "configs/default.yaml"],
                cwd=Path(__file__).resolve().parent.parent,
                check=False,
            )
        except Exception as e:
            logger.error(f"Sensitivity failed: {e}")

    # ---- Excel Filling ----
    if not args.skip_fill_excel or args.only_fill_excel:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 5: Excel Template Filling")
        logger.info("=" * 60)
        try:
            _fill_excel_files(logger, all_outputs)
        except Exception as e:
            logger.error(f"Excel filling failed: {e}", exc_info=True)

    # ---- Generate report ----
    _generate_experiment_report(logger, all_outputs, time.time() - total_start)

    # ---- Final summary ----
    _print_final_summary(logger, all_outputs)


def _fill_excel_files(logger, all_outputs):
    """Fill result1.xlsx and result2.xlsx."""
    from src.cutting3d.models import ExperimentResult

    # Analyze templates
    logger.info("Analyzing template structure...")
    save_template_mapping(
        "outputs/results/result1.xlsx",
        "outputs/results/template_mapping.json",
        logger,
    )
    save_template_mapping(
        "outputs/results/result2.xlsx",
        "outputs/results/template_mapping.json",
        logger,
    )

    # Try to load saved results
    result1_path = Path("outputs/results/problem1_solution.json")
    result2_path = Path("outputs/results/problem2_solution.json")

    materials = create_materials(load_config("configs/default.yaml"))
    pieces = create_pieces(load_config("configs/default.yaml"))

    if result1_path.exists():
        result1 = ExperimentResult.from_json(str(result1_path))
        logger.info("Filling result1.xlsx...")
        success, report = fill_result_xlsx(
            "outputs/results/result1.xlsx",
            "outputs/results/result1_filled.xlsx",
            result1, materials, pieces, logger,
        )
        all_outputs["result1_filled"] = "outputs/results/result1_filled.xlsx"
        logger.info(f"Result1 fill: {'SUCCESS' if success else 'FAILED'}")
        logger.info(f"  Grey cells found: {report.get('grey_cells_found', 0)}")
        logger.info(f"  Grey cells filled: {report.get('grey_cells_filled', 0)}")
    else:
        logger.warning("problem1_solution.json not found, skipping result1 fill.")

    if result2_path.exists():
        result2 = ExperimentResult.from_json(str(result2_path))
        logger.info("Filling result2.xlsx...")
        success, report = fill_result_xlsx(
            "outputs/results/result2.xlsx",
            "outputs/results/result2_filled.xlsx",
            result2, materials, pieces, logger,
        )
        all_outputs["result2_filled"] = "outputs/results/result2_filled.xlsx"
        logger.info(f"Result2 fill: {'SUCCESS' if success else 'FAILED'}")
        logger.info(f"  Grey cells found: {report.get('grey_cells_found', 0)}")
        logger.info(f"  Grey cells filled: {report.get('grey_cells_filled', 0)}")
    else:
        logger.warning("problem2_solution.json not found, skipping result2 fill.")


def _generate_experiment_report(logger, all_outputs, total_time):
    """Generate experiment summary markdown report."""
    report_path = Path("outputs/reports/experiment_summary.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Experiment Summary - 3D Cutting Stock Optimization",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total runtime: {total_time:.2f}s",
        "",
        "## Output Files",
        "",
    ]

    for key, path in sorted(all_outputs.items()):
        lines.append(f"- **{key}**: `{path}`")

    lines += [
        "",
        "## Results",
        "",
        "See individual JSON and CSV files for detailed results.",
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
        "| `result1_filled.xlsx` | Filled version with solution data + computed_solution sheet |",
        "| `result2_filled.xlsx` | Filled version with solution data + computed_solution sheet |",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Experiment report saved to: {report_path}")


def _print_final_summary(logger, all_outputs):
    """Print final summary to terminal."""
    summary = """
╔══════════════════════════════════════════════════════════════╗
║     3D Cutting Stock Optimization - COMPLETED                ║
╚══════════════════════════════════════════════════════════════╝

Output files:
"""
    for key, path in sorted(all_outputs.items()):
        summary += f"  {key}: {path}\n"

    summary += """
Figure directories:
  Problem 1:     outputs/figures/problem1/
  Problem 2:     outputs/figures/problem2/
  Ablation:      outputs/figures/ablation/
  Sensitivity:   outputs/figures/sensitivity/
  3D Layouts:    outputs/figures/3d_layouts/

Excel files:
  result1_filled.xlsx  (with computed_solution sheet)
  result2_filled.xlsx  (with computed_solution sheet)

Logs:         logs/
Reports:      outputs/reports/
"""
    logger.info(summary)
    print(summary)


if __name__ == "__main__":
    main()
