
# Optimality Certificate Report

Generated: 2026-05-29

---

## Terminology

- **Feasible Solution**: A solution satisfying all constraints.
- **Pattern-Library Optimal**: Best among generated patterns. CP-SAT OPTIMAL status refers to this.
- **Relaxation Upper Bound**: A bound relaxing some constraints for theoretical upper limit.
- **Global Optimal Proved**: Proven best among ALL feasible solutions.
- **Not Proved**: Optimality not rigorously established.

---

## Problem 1: NOT globally optimal proved

- **Global Optimal Proved**: 
- **Status**: PATTERN_LIBRARY_OPTIMAL
- **Material Utilization**: 99.0099%
- **Utilization Gap to 100%**: 0.9901%

### Why not proved?
L01 (100%) and L03 (100%) are fully utilized. The 750,000 waste comes entirely from L02 (150,000/block × 5 blocks). To prove global optimality, we must show L02 cannot exceed 3,600,000 per block. L02 infeasibility certificate did not complete within computational budget.

**Strong empirical evidence**: All heuristic strategies (grid, improved greedy, extreme point with 10+ restarts) failed to find > 3,600,000. This is strong but not a mathematical proof.

---

## Problem 2: NOT globally optimal proved

- **Global Optimal Proved**: 
- **Current Profit**: 742,400
- **Profit Density Relaxation Bound**: 852,187.5
- **Gap**: 109,787.5 (12.88%)

### Why not proved?
The profit density relaxation bound is LOOSE (ignores geometry, discretization, min-piece constraints). A tight bound requires complete pattern enumeration or branch-and-price, both computationally intractable.

---

## L02 Infeasibility Certificate: NOT_PROVED

- **Status**: NOT_PROVED
- Full vector enumeration did not complete
- Current best from heuristics: 3,600,000 (96.0%)
- All strategies failed to find > 3,600,000

---

## Recommendations

1. To prove Problem 1: complete L02 infeasibility with more compute time
2. To tighten Problem 2 bound: LP-based pattern relaxation
3. To improve solutions: metaheuristics (BRKGA, simulated annealing)
