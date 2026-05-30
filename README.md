# 3D Cutting Stock Optimization

2026 "亿星软件杯" Mathematical Modeling Competition - Problem A

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run everything
python run_all.py

# Or run individual components
python -m experiments.run_problem1
python -m experiments.run_problem2
python -m experiments.run_ablation
python -m experiments.run_sensitivity
python -m experiments.run_l02_search

# Problem 3 order selection idea (undergraduate)
python experiments/run_problem3_idea.py
```

## Project Structure

See [claude.md](claude.md) for complete engineering documentation.

See `编程建模全流程详解-给我自己.md` for a beginner-friendly walkthrough of the full pipeline (Chinese).

See `论文写作指南-给队友.md` for paper-writing guidance (Chinese).

## Key Results

| Problem | Objective | Result | Notes |
|---------|-----------|--------|-------|
| Problem 1 | Maximize utilization | **99.01%** | L01/L03 = 100%, L02 = 96% |
| Problem 2 | Maximize profit | **748,640** | All pieces >= 10, validated |
| Problem 3 | Order selection | **H03** recommended | H02 backup; switch if purchase > 20% |

### Problem 3 Coverage Metrics

| Order | Gross Profit | Theoretical Cov. | Effective Cov. (95%) | Role |
|-------|-------------|-----------------|---------------------|------|
| H03 | 330,460 | 100.7% | 95.7% | Recommended |
| H02 | 316,320 | 102.3% | 97.2% | Backup |
| H01 | 285,620 | 119.9% | 113.9% | Conservative |

## Output

All results are in `outputs/`:
- `results/` - JSON, CSV, and filled Excel files
- `figures/` - Publication-quality PNG and PDF charts
- `reports/` - experiment_summary.md, optimality_certificate_report.md, problem3_order_selection_idea.md

Logs are in `logs/`.

## File Map for Paper Writing

| What | Where |
|------|-------|
| Problem 1 full solution | `outputs/results/problem1_solution.json` |
| Problem 2 full solution | `outputs/results/problem2_solution.json` |
| Problem 2 validation | `outputs/results/problem2_solution_validation.json` |
| Problem 3 order analysis | `outputs/reports/problem3_order_selection_idea.md` |
| Problem 3 scores CSV | `outputs/results/problem3_order_scores.csv` |
| Problem 3 recommendation JSON | `outputs/results/problem3_order_recommendation.json` |
| Ablation study data | `outputs/results/ablation_results.csv` |
| Sensitivity analysis data | `outputs/results/sensitivity_results.csv` |
| Optimality certificates | `outputs/results/*_certificate.json` |
| Filled Excel templates | `outputs/results/result1_filled.xlsx`, `result2_filled.xlsx` |
| All figures (PNG+PDF) | `outputs/figures/` |
