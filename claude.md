# Claude.md - 3D Cutting Stock Optimization

Complete engineering documentation for the 2026 "亿星软件杯" Mathematical Modeling Competition Problem A.

## 1. Project Objective

Solve two 3D cutting stock sub-problems using a hybrid optimization framework:
- **Problem 1**: Maximize material utilization (minimize waste volume)
- **Problem 2**: Maximize total profit while ensuring each piece type is produced at least 10 times

## 2. Problem Data

### Materials (3 types, 5 blocks each)

| Material | Length | Width | Height | Volume | Per-Block Volume |
|----------|--------|-------|--------|--------|-----------------|
| L01 | 300 | 200 | 150 | 45,000,000 | 9,000,000 |
| L02 | 250 | 150 | 100 | 18,750,000 | 3,750,000 |
| L03 | 200 | 150 | 80 | 12,000,000 | 2,400,000 |
| **Total** | | | | **75,750,000** | |

### Pieces (7 types)

| Piece | Length | Width | Height | Volume | Profit | Profit Density |
|-------|--------|-------|--------|--------|--------|-----------------|
| J01 | 40 | 40 | 40 | 64,000 | 620 | 0.00969 |
| J02 | 50 | 40 | 40 | 80,000 | 780 | 0.00975 |
| J03 | 60 | 50 | 30 | 90,000 | 880 | 0.00978 |
| J04 | 75 | 60 | 40 | 180,000 | 1,850 | 0.01028 |
| J05 | 80 | 60 | 50 | 240,000 | 2,520 | 0.01050 |
| J06 | 100 | 50 | 20 | 100,000 | 1,000 | 0.01000 |
| J07 | 120 | 20 | 20 | 48,000 | 540 | 0.01125 |

90-degree rotations allowed. All dimensions multiples of 5.

## 3. Mathematical Models

### Problem 1: Minimize Waste

Decision variables: $x_{t,p} \in \mathbb{Z}_{\geq 0}$ = blocks of material $t$ using pattern $p$

$$\min \sum_{t \in T} \sum_{p \in P_t} x_{t,p} \cdot (V_t - v_p)$$

Constraints:
- $\sum_{p \in P_t} x_{t,p} = 5$, $\forall t \in T$ (each material type has exactly 5 blocks)
- $x_{t,p} \geq 0$, integer

### Problem 2: Maximize Profit

$$\max \sum_{t \in T} \sum_{p \in P_t} x_{t,p} \cdot r_p$$

Constraints:
- $\sum_{p \in P_t} x_{t,p} = 5$, $\forall t \in T$
- $\sum_{t \in T} \sum_{p \in P_t} x_{t,p} \cdot c_{p,j} \geq 10$, $\forall j \in J$ (min 10 per piece type)
- $x_{t,p} \geq 0$, integer

## 4. Key Modeling Assumptions

- All dimensions are integers, multiples of 5 (grid_gcd = 5)
- 90-degree axis-aligned rotations only (6 possible orientations for distinct dims)
- Zero cutting kerf/loss
- Pieces must be fully contained within material bounds
- No overlap between any two pieces
- All coordinates are non-negative integers

## 5. Algorithm Framework

### 5.1 Pattern Generation (`pattern_generator.py`)

Three pattern generator types:

**a) Grid Patterns**: Single-piece-type regular grid packing with multiple fill levels (100%, 90%, 75%, 50%). Fast but limited to single piece type.

**b) Legacy Greedy Patterns**: Iterates through piece types sorted by profit density/volume/profit, places each piece at the first available (x,y,z). Multiple sorting strategies for diversity.

**c) Improved Greedy Patterns** (new): Maintains candidate position set `{(0,0,0)}`, iteratively places the best-scored piece, updates candidate positions after each placement. Uses scoring:
```
Score = w_profit * profit_density_norm + w_volume * volume_norm
      + w_contact * contact_norm + w_corner * corner_score
      - w_frag * fragmentation_penalty
```
Configurable via `configs/default.yaml` under `greedy:` section.

**d) Extreme Point Patterns**: Uses extreme-point-based packing heuristic with beam search and random restarts. Scoring:
```
Score = alpha * volume_fill + beta * profit_density
      + gamma * contact_score - eta * fragmentation_penalty
```

### 5.2 Extreme Point Packing (`extreme_point.py`)

- Maintains candidate extreme points from placed pieces
- Deduplicates and removes dominated/infeasible points
- Beam search: keeps top `beam_width` candidates
- Multiple random restarts for exploration
- All parameters in config

### 5.3 Master Integer Programming (`master_solver.py`)

OR-Tools CP-SAT for pattern selection:
- Variables: $x_{t,p}$ = count of pattern p used for material t
- Problem 1: minimize total waste
- Problem 2: maximize total profit with min-piece constraints

### 5.4 CP-SAT Validation (`cpsat_validator.py`)

Validates pattern geometry: containment + non-overlap checks.
Returns solver status: OPTIMAL / FEASIBLE / INFEASIBLE / UNKNOWN.

## 6. Why OPTIMAL Only Means Pattern-Library Optimal

**CRITICAL**: When the CP-SAT solver returns `OPTIMAL`, this means the integer programming solution is optimal **within the generated pattern library**, NOT necessarily globally optimal for the 3D cutting problem.

A pattern library is a finite set of pre-generated cutting patterns. The master problem selects the best combination from this finite set. If the pattern library does not contain every possible feasible pattern, the solution may not be globally optimal.

To claim global optimality, one must either:
1. Prove the pattern library is complete (all feasible patterns enumerated), OR
2. Prove via geometric certification that no better pattern exists, OR
3. Close the gap between feasible solution and a tight relaxation bound.

## 7. Bound and Gap Metrics

### Problem 1 (Minimize Waste)
- **waste_lower_bound** = 0 (cannot have negative waste)
- **utilization_upper_bound** = 1.0 (100% utilization)
- **waste_gap_to_zero** = current_waste - 0
- **waste_gap_ratio** = current_waste / total_material_volume
- **utilization_gap_to_full** = 1.0 - current_utilization

### Problem 2 (Maximize Profit)
- **profit_density_relaxation_upper_bound** = total_volume * max_profit_density
  - This is a LOOSE bound: ignores geometry, discretization, and min-piece constraints
  - Should NOT be interpreted as a tight optimality certificate
- **relaxation_gap** = upper_bound - current_profit
- **relaxation_gap_ratio** = gap / upper_bound

## 8. L02 Specialized Search

Module: `experiments/run_l02_search.py`

Verifies whether L02 utilization can exceed the current baseline of 3,600,000 per block (96% of 3,750,000).

Search strategies:
1. Grid patterns with multiple offsets
2. Improved greedy with multiple random seeds (20 trials)
3. Intensive extreme point with beam_width=10, 20 restarts (15 trials)
4. Alternative weight configurations for EP

Outputs: `l02_best_patterns.csv`, `l02_search_report.json`

## 9. Optimality Certificate Module

### 9.1 Exact Enumeration (`exact_enumeration.py`)
Enumerates production vectors (a1,...,a7) satisfying volume constraints for each material. Supports non-dominated filtering and configurable pruning.

### 9.2 Exact Geometry CP-SAT (`exact_geometry_cp.py`)
CP-SAT model for checking geometric feasibility of a production vector. Uses discrete coordinate variables, orientation selection, and non-overlap constraints.

### 9.3 Certificate Generator (`certificate.py`)
- **L02 Infeasibility Certificate**: Enumerates vectors above baseline, checks CP-SAT feasibility
- **Problem 1 Global Optimal Certificate**: Combines L01/L03 100% proof with L02 infeasibility
- **Problem 2 Optimality Certificate**: Always `global_optimal_proved=false` unless complete pattern enumeration

### 9.4 Certificate Statuses
- `PROVED_OPTIMAL`: All vectors above baseline are INFEASIBLE, no unknowns
- `NOT_PROVED`: Feasible or unknown vectors exist above baseline
- `PATTERN_LIBRARY_OPTIMAL`: Best within generated patterns, not globally proven

## 10. Ablation Study

Configurations compared:
1. `only_grid_patterns`: Single-piece grid patterns only
2. `legacy_greedy_without_extreme_points`: Grid + legacy greedy
3. `improved_greedy_without_extreme_points`: Grid + improved greedy
4. `extreme_points_without_random_restart`: Full but 1 EP restart
5. `full_hybrid_solver`: All three with multiple restarts

Outputs: `ablation_results.json`, `ablation_results.csv`, comparison chart

## 11. Sensitivity Analysis

Parameters analyzed:
- Pattern count: 20, 50, 100, 150, 200
- Scoring weights: default, volume_only, profit_only, balanced, contact_heavy

Outputs: `sensitivity_patterns.json`, `sensitivity_weights.json`, `sensitivity_results.csv`, charts

## 12. Project Structure

```
project_root/
├── claude.md                     # This file
├── README.md                     # Quick start
├── requirements.txt              # Dependencies
├── run_all.py                    # One-click runner
├── configs/                      # YAML configuration
├── src/cutting3d/                # Core library (17 modules)
├── experiments/                  # Experiment scripts (7 scripts)
├── tests/                        # Unit tests (5 files)
├── outputs/
│   ├── results/                  # JSON, CSV, Excel results
│   ├── figures/                  # Charts (problem1, problem2, ablation, sensitivity, 3d_layouts)
│   ├── reports/                  # experiment_summary.md, optimality_certificate_report.md
│   └── tables/
└── logs/                         # Timestamped run logs
```

## 13. Running Commands

```bash
# Install
pip install -r requirements.txt

# Full pipeline
python run_all.py

# With exact certificate (slower)
python run_all.py --with-exact-certificate

# Individual components
python -m experiments.run_problem1
python -m experiments.run_problem2
python -m experiments.run_ablation
python -m experiments.run_sensitivity
python -m experiments.run_l02_search
python -m experiments.run_exact_certificate
python -m experiments.run_seed_stability

# Skip phases
python run_all.py --skip-ablation --skip-sensitivity
python run_all.py --only-plots
python run_all.py --only-fill-excel

# Tests
python -m pytest tests/ -v
```

## 14. Output Files

### Results
- `problem1_solution.json` / `problem2_solution.json`: Full solutions
- `problem1_summary.csv` / `problem2_summary.csv`: Flat summaries
- `ablation_results.json` / `ablation_results.csv`: Ablation comparison
- `sensitivity_results.csv`: Sensitivity data
- `seed_stability_results.csv`: Seed stability data

### L02 Search
- `l02_best_patterns.csv`: Top L02 patterns from search
- `l02_search_report.json`: Search summary

### Optimality Certificates
- `l02_infeasibility_certificate.json`: L2 infeasibility proof data
- `problem1_global_optimal_certificate.json`: Problem 1 optimality claim
- `problem2_optimality_certificate.json`: Problem 2 optimality status

### Excel Files
- `result1_filled.xlsx` / `result2_filled.xlsx`: Filled templates with `computed_solution` sheet
- `template_mapping.json`: Combined grey cell mapping for both templates
- `excel_validation_report.json`: Cross-validation report

### Figures (PNG + PDF, 300 DPI)
- `outputs/figures/problem1/`: 7 chart types x 2 formats
- `outputs/figures/problem2/`: 7 chart types x 2 formats
- `outputs/figures/ablation/`: Ablation comparison
- `outputs/figures/sensitivity/`: Sensitivity charts
- `outputs/figures/3d_layouts/`: 3D packing visualizations

### Reports
- `experiment_summary.md`: Full experiment summary with results
- `optimality_certificate_report.md`: Detailed optimality explanation

## 15. Excel Filling and Validation Logic

Procedure:
1. **Backup**: Original templates backed up to `outputs/results/backups/` with timestamp
2. **Mapping**: Grey cells identified and mapped to `template_mapping_result{1,2}_filled.json`
3. **Filling**: Grey cells filled by analyzing adjacent labels and column headers
4. **Computed Solution Sheet**: Always added with full results (status, metrics, piece counts, material breakdown, pattern usage, timing)
5. **Validation**: Filled file read back, metrics compared against JSON, report saved to `excel_validation_report.json`
6. **Combined Mapping**: `template_mapping.json` contains both result1 and result2 data

### Manual Verification
If grey cells cannot be auto-matched:
- Check the `computed_solution` sheet for ALL solution data
- Check `excel_validation_report.json` for fill status
- Check logs for per-sheet grey cell counts
- Skipped cells are reported in warnings

## 16. Random Seed and Reproducibility

- Default seed: `20260528`
- Controlled via `configs/default.yaml` → `random_seed`
- All random processes are seeded
- Seed stability verified via `experiments/run_seed_stability.py`

## 17. FAQ

**Q: Why does the solver say OPTIMAL but the gap is non-zero?**
A: OPTIMAL means optimal within the candidate pattern library. The gap to the theoretical bound is non-zero because the pattern library may not be complete, and the theoretical bound (profit density relaxation) is loose.

**Q: Is Problem 1 globally optimal?**
A: Only if the L02 infeasibility certificate proves `PROVED_OPTIMAL`. Check `problem1_global_optimal_certificate.json`.

**Q: Why is the profit density relaxation bound loose?**
A: It assumes we can fill all volume with the highest-profit-density piece, ignoring: (a) geometric constraints preventing perfect packing, (b) discrete piece sizes, (c) minimum piece count requirements, (d) the fact that we must use integer patterns.

**Q: How to interpret gap values?**
A: For Problem 1, `utilization_gap_to_full` shows how far from 100%. For Problem 2, `relaxation_gap_ratio` is a loose upper estimate — the true optimality gap is likely smaller.

## 18. Problem 3: Order Selection (Undergraduate)

### 18.1 Problem Context

Production cycle end: remaining materials (L01×2, L02×2, L03×1) and workpiece stock (J03=20, J05=3, J06=11, J07=19). Three candidate orders (H01, H02, H03) available. Must choose one order to fulfill. Emergency purchase allowed at 2× profit cost for shortfall.

**Undergraduate requirement**: Solution idea + analysis only (no full solve required).

### 18.2 Decision Model

Core logic: inventory deduction → net demand → remaining material production → emergency purchase → net profit comparison.

$$d_{hj}^{\text{net}} = \max(0, d_{hj} - s_j)$$

Order selection: $\sum_h y_h = 1$ (three-choose-one).

Objective: $\max$ OrderRevenue $-$ EmergencyPurchaseCost

Emergency purchase cost: $C_{\text{buy}} = \sum_j 2 r_j q_j^{\text{buy}}$

### 18.3 Dual Coverage Metrics

Two independent coverage ratios are used to avoid over-optimistic estimates:

1. **Theoretical coverage**: total_remaining_volume / net_demand_volume (ignores geometry loss)
2. **Effective coverage (95%)**: 0.95 × total_remaining_volume / net_demand_volume (accounts for packing inefficiency)

### 18.4 Order Analysis Summary

| Order | Gross Profit | Net Demand Vol | Theoretical Cov. | Effective Cov. (95%) | Recommendation |
|-------|-------------|----------------|-----------------|---------------------|----------------|
| H01 | 285,620 | 23,268,000 | 119.9% | 113.9% | Conservative |
| H02 | 316,320 | 27,268,000 | 102.3% | 97.2% | Backup |
| **H03** | **330,460** | 27,710,000 | **100.7%** | **95.7%** | **Recommended** |

**Switch condition**: If H03 emergency purchase ratio exceeds 20%, switch to H02.

Note: "good producibility" refers to candidate pattern library observations, NOT proven global optimal production capacity.

### 18.5 Key Files
- Report: `outputs/reports/problem3_order_selection_idea.md` (paper-ready)
- Script: `experiments/run_problem3_idea.py`
- Output: `outputs/results/problem3_order_scores.csv`, `outputs/results/problem3_order_recommendation.json`

## 19. Problem 2 Optimization (v2 — Final)

Problem 2 improved from 745,680 to **748,640** (+2,960 / +0.40%) via:
- Balanced weights (alpha=0.5, beta=0.5, gamma=0.2, eta=0.1)
- Expanded exploration (beam_width=10, random_restarts=20)
- Seed optimization (seed=9999)

Config: `configs/problem2.yaml`
Formal result: `outputs/results/problem2_solution.json` (validated: `problem2_solution_validation.json`, all geometry checks passed)

## Implementation Notes

- All dimensions use original units (gcd normalization only for grid search)
- Paths use `pathlib` for cross-platform compatibility
- Type annotations used throughout
- Dataclasses for core data structures
- CP-SAT time limits configurable — solver returns best feasible on timeout
- Output directories auto-created on first write
