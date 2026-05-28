"""Run Problem 2: Maximize total profit with minimum piece constraints."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cutting3d.experiment import ExperimentRunner
from src.cutting3d.visualization import generate_all_plots
from src.cutting3d.logging_utils import setup_logging, log_versions
from src.cutting3d.utils import ensure_dir
from src.cutting3d.metrics import print_summary


def main():
    parser = argparse.ArgumentParser(description="Run Problem 2")
    parser.add_argument(
        "--config", type=str, default="configs/problem2.yaml",
        help="Path to configuration file",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    ensure_dir("logs")
    ensure_dir("outputs/results")
    ensure_dir("outputs/figures/problem2")

    logger = setup_logging("logs", seed=20260528, config_path=str(config_path))
    log_versions(logger)

    try:
        runner = ExperimentRunner(config_path, logger=logger)
        result = runner.run_problem2()

        runner.save_results(result, "outputs/results")

        generate_all_plots(
            result,
            runner.materials,
            runner.pieces,
            "outputs/figures/problem2",
            result.patterns,
            logger=logger,
        )

        print_summary("Problem 2", result.solution, runner.materials, runner.pieces, logger)

        logger.info("Problem 2 completed successfully.")

    except Exception as e:
        logger.error(f"Problem 2 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
