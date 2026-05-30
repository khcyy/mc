# Experiment Summary - 3D Cutting Stock Optimization

Generated: 2026-05-30
Total runtime: ~1382s (full pipeline)
Random seed: 20260528 (P1), 9999 (P2 — optimized)

## Runtime Breakdown

- **problem1_pattern_generation_duration**: ~90s
- **problem1_master_solve_duration**: <1s
- **problem1_plotting_duration**: ~8s
- **problem2_pattern_generation_duration**: ~115s
- **problem2_master_solve_duration**: <1s
- **problem2_plotting_duration**: ~12s
- **excel_writing_time**: <1s
- **total_runtime**: ~1380s

## Final Results Summary

### Problem 1: Maximize Utilization
- **Status**: OPTIMAL (pattern-library)
- **Material Utilization**: 99.01%
- **Total Waste**: 750,000
- **Total Profit**: 733,000
- **Piece Counts**: J02=150, J03=700
- **L01**: 100% utilized | **L02**: 96% utilized | **L03**: 100% utilized

### Problem 2: Maximize Profit (Formal Result — v2 Improved)
- **Status**: OPTIMAL (pattern-library)
- **Total Profit**: **748,640** (improved from 745,680, +2,960 / +0.40%)
- **Material Utilization**: 96.15%
- **Total Waste**: 2,918,000
- **Piece Counts**: J01=30, J02=30, J03=100, J04=12, J05=14, J06=370, J07=354
- **All pieces >= 10**: YES
- **Config**: balanced weights (alpha=0.5, beta=0.5, gamma=0.2, eta=0.1), beam_width=10, random_restarts=20, seed=9999
- **Previous best**: 745,680 (default weights), 746,440 (sensitivity config_3)

### Problem 3: Order Selection Idea (Undergraduate)
- **Report**: `outputs/reports/problem3_order_selection_idea.md`
- **Script**: `experiments/run_problem3_idea.py`
- **Recommendation**: H03 (net profit ~279,720), backup H02 (~268,120)

## Output Files

- **problem1_csv**: `outputs/results/problem1_summary.csv`
- **problem1_filled**: `outputs/results/result1_filled.xlsx`
- **problem1_json**: `outputs/results/problem1_solution.json`
- **problem2_csv**: `outputs/results/problem2_summary.csv`
- **problem2_filled**: `outputs/results/result2_filled.xlsx`
- **problem2_json**: `outputs/results/problem2_solution.json`
- **problem3_scores**: `outputs/results/problem3_order_scores.csv`
- **problem3_recommendation**: `outputs/results/problem3_order_recommendation.json`
- **problem3_report**: `outputs/reports/problem3_order_selection_idea.md`

## Excel Validation
- result1: metrics_match_json=true, no errors, no warnings
- result2: metrics_match_json=true, no errors, no warnings

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
| `excel_validation_report.json` | Cross-validation report (both files pass) |
