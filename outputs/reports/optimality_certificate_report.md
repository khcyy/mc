# Optimality Certificate Report

Generated: 2026-05-29

---

## Terminology

- **Feasible Solution**: Satisfies all constraints.
- **Pattern-Library Optimal**: Best among generated patterns (CP-SAT OPTIMAL = this).
- **Relaxation Upper Bound**: Bound relaxing some constraints (e.g., geometry).
- **Global Optimal Proved**: Proven best among ALL feasible solutions.
- **Not Proved**: Optimality not rigorously established.

---

## Problem 1: NOT globally optimal proved

- **Global Optimal Proved**: 
- **Status**: PATTERN_LIBRARY_OPTIMAL
- **Material Utilization**: 99.0099%
- **Waste**: 750,000
- **Utilization Gap to 100%**: 0.9901%

L01 (100%) and L03 (100%) fully utilized. The 750,000 waste is entirely from L02
(150,000 per block ¡Á 5 blocks). To prove global optimal, we must show no L02 packing
exceeds 3,600,000 used volume per block. L02 infeasibility certificate not completed.

**Empirical evidence**: All heuristic strategies failed to exceed 3,600,000 on L02.
Strong but not a mathematical proof.

---

## Problem 2: NOT globally optimal proved

- **Global Optimal Proved**: 
- **Current Profit**: 745,680
- **Profit Density Relaxation Bound**: 852,187.5
- **Gap**: 106,507.5 (12.50%)

The profit density relaxation bound ignores geometry, discretization, and min-piece
constraints. It is a LOOSE bound. Complete pattern enumeration or branch-and-price
would be needed for a tight optimality proof.

---

## L02 Infeasibility Certificate: NOT_PROVED

- **Status**: NOT_PROVED
- Full vector enumeration + CP-SAT checking not run (computationally expensive)
- Heuristic best: 3,600,000 per block (96.0%)

---

## Recommendations

1. To prove Problem 1: run full L02 vector enumeration + CP-SAT geometric feasibility
2. To tighten Problem 2 bound: implement LP-based pattern relaxation
3. To improve solutions: metaheuristics (BRKGA, simulated annealing)
