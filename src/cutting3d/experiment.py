"""Experiment orchestration module.

Coordinates the full pipeline: data loading, pattern generation,
solving, validation, visualization, and output.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from .data import create_materials, create_pieces, load_config
from .models import (
    ExperimentResult,
    MasterSolution,
    Material,
    Pattern,
    Piece,
    SolverStatus,
)
from .orientations import generate_all_orientations
from .pattern_generator import generate_all_patterns
from .master_solver import solve_master_problem1, solve_master_problem2
from .cpsat_validator import validate_pattern_cpsat
from .geometry import validate_pattern
from .metrics import compute_solution_metrics, print_summary, save_metrics_csv
from .bounds import analyze_bounds
from .utils import ensure_dir, set_seed


class ExperimentRunner:
    """Runs a full cutting optimization experiment."""

    def __init__(
        self,
        config_path: str | Path,
        logger: logging.Logger | None = None,
    ):
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.logger = logger or logging.getLogger("cutting3d")

        # Set seed for reproducibility
        seed = self.config.get("random_seed", 20260528)
        set_seed(seed)

        # Create data
        self.materials = create_materials(self.config)
        self.pieces = create_pieces(self.config)

        # Generate orientations
        self.all_orientations = generate_all_orientations(self.pieces)

        self.logger.info(f"Loaded {len(self.materials)} materials, {len(self.pieces)} pieces")
        for name, m in self.materials.items():
            self.logger.info(f"  {name}: {m.length}x{m.width}x{m.height}, count={m.count}, volume={m.volume}")
        for name, p in self.pieces.items():
            self.logger.info(f"  {name}: {p.length}x{p.width}x{p.height}, profit={p.profit}")
            self.logger.info(f"    orientations: {len(self.all_orientations[name])}")
            self.logger.info(f"    profit density: {p.profit_density:.4f}")

        # Patterns will be generated on demand
        self._all_patterns: dict[str, list[Pattern]] | None = None

        # Timing tracking
        self.timing: dict[str, float] = {}

    @property
    def all_patterns(self) -> dict[str, list[Pattern]]:
        if self._all_patterns is None:
            self.logger.info("Generating candidate patterns...")
            start = time.time()
            self._all_patterns = generate_all_patterns(
                self.materials, self.pieces, self.all_orientations, self.config
            )
            self.timing["pattern_generation_time"] = time.time() - start
            total = sum(len(v) for v in self._all_patterns.values())
            self.logger.info(
                f"Generated {total} patterns across {len(self._all_patterns)} materials "
                f"in {self.timing['pattern_generation_time']:.2f}s"
            )
            for mat_name, patterns in self._all_patterns.items():
                utils = [
                    p.used_volume / self.materials[mat_name].volume
                    for p in patterns
                ]
                avg_util = sum(utils) / len(utils) if utils else 0
                max_util = max(utils) if utils else 0
                self.logger.info(
                    f"  {mat_name}: {len(patterns)} patterns, "
                    f"avg util={avg_util:.3f}, max util={max_util:.3f}"
                )
        return self._all_patterns

    def run_problem1(self) -> ExperimentResult:
        """Run Problem 1: Maximize material utilization."""
        self.logger.info("=" * 60)
        self.logger.info("Running Problem 1: Maximize Material Utilization")
        self.logger.info("=" * 60)

        solve_start = time.time()
        solution = solve_master_problem1(
            materials=self.materials,
            pieces=self.pieces,
            all_patterns=self.all_patterns,
            config=self.config,
        )
        self.timing["master_solve_time"] = time.time() - solve_start

        all_pattern_flat: list[Pattern] = []
        for patterns in self.all_patterns.values():
            all_pattern_flat.extend(patterns)

        self._log_solution("Problem 1", solution)
        self._validate_solution(solution, all_pattern_flat)

        result = ExperimentResult(
            problem_name="problem1",
            solution=solution,
            patterns=all_pattern_flat,
            config=self.config,
        )
        # Store timing in metadata
        result.solution.metadata["timing"] = dict(self.timing)
        return result

    def run_problem2(self) -> ExperimentResult:
        """Run Problem 2: Maximize total profit with minimum piece constraints."""
        self.logger.info("=" * 60)
        self.logger.info("Running Problem 2: Maximize Total Profit")
        self.logger.info("=" * 60)

        solve_start = time.time()
        solution = solve_master_problem2(
            materials=self.materials,
            pieces=self.pieces,
            all_patterns=self.all_patterns,
            config=self.config,
        )
        self.timing["master_solve_time"] = time.time() - solve_start

        all_pattern_flat: list[Pattern] = []
        for patterns in self.all_patterns.values():
            all_pattern_flat.extend(patterns)

        self._log_solution("Problem 2", solution)
        self._validate_solution(solution, all_pattern_flat)

        result = ExperimentResult(
            problem_name="problem2",
            solution=solution,
            patterns=all_pattern_flat,
            config=self.config,
        )
        result.solution.metadata["timing"] = dict(self.timing)
        return result

    def _log_solution(self, name: str, solution: MasterSolution) -> None:
        """Log solution details."""
        print_summary(name, solution, self.materials, self.pieces, self.logger)

    def _validate_solution(
        self, solution: MasterSolution, all_patterns: list[Pattern]
    ) -> None:
        """Validate the solution's geometry constraints."""
        pattern_map = {p.pattern_id: p for p in all_patterns}

        self.logger.info("Validating solution geometry...")
        all_valid = True
        for pid, count in solution.pattern_usage.items():
            if pid not in pattern_map:
                self.logger.warning(f"Pattern {pid} not found in pattern map")
                continue
            pattern = pattern_map[pid]
            material = self.materials.get(pattern.material_name)
            if material is None:
                self.logger.warning(f"Material {pattern.material_name} not found")
                continue
            is_valid, msg = validate_pattern(pattern.placed_pieces, material)
            if not is_valid:
                self.logger.error(f"Pattern {pid} validation FAILED: {msg}")
                all_valid = False

        if all_valid:
            self.logger.info("All patterns passed geometry validation.")
        else:
            self.logger.error("Some patterns FAILED geometry validation!")

    def save_results(
        self,
        result: ExperimentResult,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        """Save experiment results to files."""
        output_dir = ensure_dir(output_dir)

        files: dict[str, Path] = {}

        # Save JSON solution
        json_path = output_dir / f"{result.problem_name}_solution.json"
        result.to_json(str(json_path))
        files["json"] = json_path
        self.logger.info(f"Solution saved to: {json_path}")

        # Save CSV summary
        metrics = compute_solution_metrics(
            result.solution, self.materials, self.pieces, result.patterns
        )
        csv_path = output_dir / f"{result.problem_name}_summary.csv"
        save_metrics_csv(metrics, csv_path)
        files["csv"] = csv_path
        self.logger.info(f"Summary saved to: {csv_path}")

        # Bound analysis
        bound_analysis = analyze_bounds(
            result.solution, self.materials, self.pieces, result.config, self.logger
        )
        bound_path = output_dir / f"{result.problem_name}_bounds.json"
        with open(bound_path, "w", encoding="utf-8") as f:
            json.dump(bound_analysis, f, indent=2)
        files["bounds"] = bound_path

        return files
