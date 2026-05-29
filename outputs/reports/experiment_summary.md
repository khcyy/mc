# Experiment Summary - 3D Cutting Stock Optimization

Generated: 2026-05-29 23:28:50
Total runtime: 1382.38s
Random seed: 20260528

## Runtime Breakdown

- **problem1_pattern_generation_duration**: 90.20s
- **problem1_master_solve_duration**: 90.24s
- **problem1_plotting_duration**: 8.23s
- **problem2_pattern_generation_duration**: 87.19s
- **problem2_master_solve_duration**: 87.24s
- **problem2_plotting_duration**: 11.87s
- **excel_writing_time**: 0.11s
- **total_runtime**: 1382.38s

## Output Files

- **problem1_csv**: `outputs/results/problem1_summary.csv`
- **problem1_filled**: `outputs/results/result1_filled.xlsx`
- **problem1_json**: `outputs/results/problem1_solution.json`
- **problem2_csv**: `outputs/results/problem2_summary.csv`
- **problem2_filled**: `outputs/results/result2_filled.xlsx`
- **problem2_json**: `outputs/results/problem2_solution.json`

## Optimality Notes

**IMPORTANT**: CP-SAT solver returning OPTIMAL means the solution is optimal
WITHIN the generated pattern library, NOT necessarily globally optimal.

For rigorous global optimality claims, see `outputs/reports/optimality_certificate_report.md`.

## Figures

| Type | Path |
|------|------|
| Problem 1 | `outputs/figures/problem1/` |
| Problem 2 | `outputs/figures/problem2/` |
| Ablation | `outputs/figures/ablation/` |
| Sensitivity | `outputs/figures/sensitivity/` |
| 3D Layouts | `outputs/figures/3d_layouts/` |

## Excel Files

| File | Description |
|------|-------------|
| `result1.xlsx` | Original template (preserved) |
| `result2.xlsx` | Original template (preserved) |
| `result1_filled.xlsx` | Filled + computed_solution |
| `result2_filled.xlsx` | Filled + computed_solution |
| `excel_validation_report.json` | Cross-validation report |