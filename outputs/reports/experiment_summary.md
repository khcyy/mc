# Experiment Summary - 3D Cutting Stock Optimization

Generated: 2026-05-29 11:38:05
Total runtime: 219.16s
Random seed: 20260528

## Runtime Breakdown

- **pattern_generation_time**: 1.87s
- **master_solve_time**: 1.99s
- **plotting_time_problem1**: 13.38s
- **plotting_time_problem2**: 22.28s
- **excel_writing_time**: 0.20s
- **total_runtime**: 219.16s

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