# Experiment Summary - 3D Cutting Stock Optimization

Generated: 2026-05-30
Total runtime: ~1,380s (full pipeline)
Random seed: 20260528 (P1), 9999 (P2 — optimized)

## Runtime Breakdown

- **problem1_pattern_generation_duration**: ~90s
- **problem1_master_solve_duration**: <1s
- **problem1_plotting_duration**: ~8s
- **problem2_pattern_generation_duration**: ~115s
- **problem2_master_solve_duration**: <1s
- **problem2_plotting_duration**: ~12s
- **excel_writing_time**: <1s
- **total_runtime**: ~1,380s

## Final Results Summary

### Problem 1: Maximize Material Utilization
- **Status**: OPTIMAL (pattern-library)
- **Material Utilization**: 99.01%
- **Total Waste**: 750,000
- **Total Profit**: 733,000
- **Piece Counts**: J02=150, J03=700
- **L01**: 100% utilized | **L02**: 96% utilized | **L03**: 100% utilized

### Problem 2: Maximize Profit (v2 — Final)
- **Status**: OPTIMAL (pattern-library)
- **Total Profit**: **748,640** (improved from 745,680, +2,960 / +0.40%)
- **Material Utilization**: 96.15% (72,832,000 / 75,750,000)
- **Total Waste**: 2,918,000
- **Piece Counts**: J01=30, J02=30, J03=100, J04=12, J05=14, J06=370, J07=354
- **All pieces >= 10**: YES
- **Config**: balanced weights (alpha=0.5, beta=0.5, gamma=0.2, eta=0.1), beam_width=10, random_restarts=20, seed=9999
- **Validation**: `problem2_solution_validation.json` — geometry validation PASSED, volume accounting verified
- Previous best: 745,680 (default weights), 746,440 (sensitivity config_3)

### Problem 3: Order Selection Idea (Undergraduate)
- **Report**: `outputs/reports/problem3_order_selection_idea.md` (paper-ready)
- **Script**: `experiments/run_problem3_idea.py`
- **Recommended order**: **H03** (gross profit 330,460, est. net profit 256,440)
- **Backup order**: **H02** (gross profit 316,320, est. net profit 249,960)
- **Conservative**: H01 (gross profit 285,620)
- **H03 theoretical coverage**: 100.7% (total remaining volume / net demand)
- **H03 effective coverage**: 95.7% (95% × total volume / net demand)
- **Switch condition**: If H03 emergency purchase ratio exceeds 20%, switch to H02
- **Outputs**: `problem3_order_scores.csv`, `problem3_order_recommendation.json`

## Output Files

| File | Description |
|------|-------------|
| `outputs/results/problem1_solution.json` | Problem 1 full solution |
| `outputs/results/problem1_summary.csv` | Problem 1 flat summary |
| `outputs/results/problem2_solution.json` | Problem 2 full solution (validated, non-empty) |
| `outputs/results/problem2_summary.csv` | Problem 2 flat summary |
| `outputs/results/problem2_solution_validation.json` | Problem 2 validation (PASSED) |
| `outputs/results/problem3_order_scores.csv` | Problem 3 order scoring |
| `outputs/results/problem3_order_recommendation.json` | Problem 3 recommendation |
| `outputs/results/result1_filled.xlsx` | Filled template 1 |
| `outputs/results/result2_filled.xlsx` | Filled template 2 |
| `outputs/results/excel_validation_report.json` | Cross-validation report |
| `outputs/reports/problem3_order_selection_idea.md` | Problem 3 paper-ready report |

## Excel Validation
- result1: metrics_match_json=true, has_computed_solution=true, no errors, no warnings
- result2: metrics_match_json=true, has_computed_solution=true, no errors, no warnings

## Optimality Notes

**IMPORTANT**: CP-SAT solver returning OPTIMAL means the solution is optimal
WITHIN the generated pattern library, NOT necessarily globally optimal.

- **Problem 1**: L01 (100%) and L03 (100%) fully utilized — provably optimal for those materials. L02 at 96% — empirically best, not rigorously proven.
- **Problem 2**: 748,640 is the best feasible solution found within the candidate pattern library. The profit density relaxation bound (852,187.5) is a LOOSE upper bound that ignores geometry.
- **Problem 3**: Recommendation is based on estimated net profit and coverage analysis — not a full CP-SAT solve. Switch condition (20% purchase ratio) provides a risk-management framework.

For detailed optimality discussion, see `outputs/reports/optimality_certificate_report.md`.

## Figures

| Type | Path |
|------|------|
| Problem 1 | `outputs/figures/problem1/` |
| Problem 2 | `outputs/figures/problem2/` |
| Ablation | `outputs/figures/ablation/` |
| Sensitivity | `outputs/figures/sensitivity/` |
| 3D Layouts | `outputs/figures/3d_layouts/` |
