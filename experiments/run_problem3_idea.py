"""Problem 3: Order Selection Idea - Undergraduate Team.

Provides order analysis: inventory deduction, remaining material production
capacity estimation (theoretical and effective), net profit calculation,
and order recommendation logic with risk-aware switch condition.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Problem 3 Data (from docs/question.md) ──────────────────────────

REMAINING_MATERIALS = {
    "L01": 2,  # 300x200x150, volume 9,000,000 each
    "L02": 2,  # 250x150x100, volume 3,750,000 each
    "L03": 1,  # 200x150x80,  volume 2,400,000 each
}

PIECE_STOCK = {
    "J01": 0, "J02": 0, "J03": 20, "J04": 0,
    "J05": 3, "J06": 11, "J07": 19,
}

PIECE_DATA = {
    "J01": {"profit": 620, "length": 40, "width": 40, "height": 40},
    "J02": {"profit": 780, "length": 50, "width": 40, "height": 40},
    "J03": {"profit": 880, "length": 60, "width": 50, "height": 30},
    "J04": {"profit": 1850, "length": 75, "width": 60, "height": 40},
    "J05": {"profit": 2520, "length": 80, "width": 60, "height": 50},
    "J06": {"profit": 1000, "length": 100, "width": 50, "height": 20},
    "J07": {"profit": 540, "length": 120, "width": 20, "height": 20},
}

ORDERS = {
    "H01": {"J03": 24, "J04": 54, "J05": 25, "J06": 80, "J07": 40},
    "H02": {"J01": 48, "J02": 200, "J03": 70, "J05": 11, "J06": 11, "J07": 56},
    "H03": {"J03": 27, "J04": 54, "J05": 27, "J06": 115, "J07": 44},
}

MATERIAL_DATA = {
    "L01": {"length": 300, "width": 200, "height": 150},
    "L02": {"length": 250, "width": 150, "height": 100},
    "L03": {"length": 200, "width": 150, "height": 80},
}

# Conservative effective utilization rate (based on Problem 1/2 empirical results)
EFFECTIVE_UTILIZATION_RATE = 0.95

# Emergency purchase ratio threshold for switching from primary to backup order
SWITCH_PURCHASE_THRESHOLD = 0.20

# Recommendation roles
ROLE_RECOMMENDED = "recommended"
ROLE_BACKUP = "backup"
ROLE_CONSERVATIVE = "conservative"


def piece_volume(piece_name: str) -> int:
    d = PIECE_DATA[piece_name]
    return d["length"] * d["width"] * d["height"]


def material_volume(material_name: str) -> int:
    d = MATERIAL_DATA[material_name]
    return d["length"] * d["width"] * d["height"]


def total_remaining_material_volume() -> int:
    return sum(REMAINING_MATERIALS[m] * material_volume(m) for m in REMAINING_MATERIALS)


def compute_net_demand(order: dict[str, int]) -> dict[str, int]:
    """Net demand after deducting existing stock."""
    net = {}
    for piece, demand in order.items():
        stock = PIECE_STOCK.get(piece, 0)
        net[piece] = max(0, demand - stock)
    return net


def compute_order_metrics(order_name: str, order: dict[str, int]) -> dict:
    """Compute key metrics for an order."""
    net = compute_net_demand(order)

    gross_profit = sum(order[p] * PIECE_DATA[p]["profit"] for p in order)

    net_volume = sum(net[p] * piece_volume(p) for p in net)
    total_demand_volume = sum(order[p] * piece_volume(p) for p in order)

    # Inventory coverage
    stock_covered = sum(
        min(order.get(p, 0), PIECE_STOCK.get(p, 0)) * piece_volume(p)
        for p in order
    )
    inventory_coverage = stock_covered / total_demand_volume if total_demand_volume > 0 else 0

    total_remaining = total_remaining_material_volume()
    effective_remaining = int(total_remaining * EFFECTIVE_UTILIZATION_RATE)

    # Theoretical coverage: using total remaining material volume (ignores geometry loss)
    theoretical_coverage = (total_remaining / net_volume * 100) if net_volume > 0 else float('inf')

    # Effective coverage: using 95% effective volume (accounts for packing loss)
    effective_coverage = (effective_remaining / net_volume * 100) if net_volume > 0 else float('inf')

    # Purchase ratio estimate: based on effective coverage gap
    if effective_coverage >= 100:
        estimated_purchase_ratio = 0.10  # ~10% for geometry-specific shortfalls
    else:
        shortage = net_volume - effective_remaining
        estimated_purchase_ratio = min(1.0, (shortage / net_volume) + 0.10)

    estimated_purchase_cost = 0
    for p in net:
        if net[p] > 0:
            purchased = max(0, int(net[p] * estimated_purchase_ratio))
            estimated_purchase_cost += purchased * PIECE_DATA[p]["profit"] * 2

    net_profit = gross_profit - estimated_purchase_cost
    best_case_net = gross_profit
    worst_case_purchase_cost = sum(net[p] * PIECE_DATA[p]["profit"] * 2 for p in net)

    return {
        "order_name": order_name,
        "gross_profit": gross_profit,
        "net_demand": net,
        "inventory_coverage_pct": round(inventory_coverage * 100, 2),
        "net_volume": net_volume,
        "remaining_material_capacity": total_remaining,
        "effective_remaining_capacity": effective_remaining,
        "theoretical_coverage_pct": round(theoretical_coverage, 1),
        "effective_coverage_pct": round(effective_coverage, 1),
        "estimated_purchase_ratio_pct": round(estimated_purchase_ratio * 100, 1),
        "estimated_purchase_cost": estimated_purchase_cost,
        "estimated_net_profit": net_profit,
        "best_case_net_profit": best_case_net,
        "worst_case_purchase_cost": worst_case_purchase_cost,
        "purchase_below_threshold": estimated_purchase_ratio < SWITCH_PURCHASE_THRESHOLD,
    }


def assign_roles(metrics: list[dict]) -> dict[str, str]:
    """Assign recommendation roles: recommended, backup, conservative."""
    # Sort by estimated net profit descending
    sorted_metrics = sorted(metrics, key=lambda m: m["estimated_net_profit"], reverse=True)
    roles = {}
    if len(sorted_metrics) >= 1:
        roles[sorted_metrics[0]["order_name"]] = ROLE_RECOMMENDED
    if len(sorted_metrics) >= 2:
        # Check if recommended order's purchase ratio is too high
        if not sorted_metrics[0]["purchase_below_threshold"]:
            # If primary has high purchase risk, note backup more prominently
            roles[sorted_metrics[1]["order_name"]] = ROLE_BACKUP
        else:
            roles[sorted_metrics[1]["order_name"]] = ROLE_BACKUP
    if len(sorted_metrics) >= 3:
        roles[sorted_metrics[2]["order_name"]] = ROLE_CONSERVATIVE
    return roles


def main():
    print("=" * 70)
    print("Problem 3: Order Selection Analysis (Revised)")
    print("=" * 70)

    total_vol = total_remaining_material_volume()
    effective_vol = int(total_vol * EFFECTIVE_UTILIZATION_RATE)
    print(f"\nRemaining Materials: {REMAINING_MATERIALS}")
    print(f"Total Remaining Volume: {total_vol:,}")
    print(f"Effective Remaining Volume (95%): {effective_vol:,}")
    print(f"\nPiece Stock: {PIECE_STOCK}")

    all_metrics = []
    for order_name in ["H01", "H02", "H03"]:
        order = ORDERS[order_name]
        m = compute_order_metrics(order_name, order)
        all_metrics.append(m)
        print(f"\n{'─' * 50}")
        print(f"Order {order_name}: {order}")
        print(f"  Net Demand: {m['net_demand']}")
        print(f"  Gross Profit: {m['gross_profit']:,}")
        print(f"  Inventory Coverage: {m['inventory_coverage_pct']:.1f}%")
        print(f"  Net Volume Needed: {m['net_volume']:,}")
        print(f"  Theoretical Coverage: {m['theoretical_coverage_pct']:.1f}%")
        print(f"  Effective Coverage (95%): {m['effective_coverage_pct']:.1f}%")
        print(f"  Est. Purchase Ratio: {m['estimated_purchase_ratio_pct']:.1f}%")
        print(f"  Est. Purchase Cost: {m['estimated_purchase_cost']:,}")
        print(f"  Est. Net Profit: {m['estimated_net_profit']:,}")
        print(f"  Best Case Net Profit: {m['best_case_net_profit']:,}")
        print(f"  Worst Case Purchase Cost: {m['worst_case_purchase_cost']:,}")
        print(f"  Purchase Below Threshold: {m['purchase_below_threshold']}")

    roles = assign_roles(all_metrics)
    for m in all_metrics:
        m["recommendation_role"] = roles.get(m["order_name"], "unknown")

    recommended = [m for m in all_metrics if m["recommendation_role"] == ROLE_RECOMMENDED]
    backup = [m for m in all_metrics if m["recommendation_role"] == ROLE_BACKUP]
    conservative = [m for m in all_metrics if m["recommendation_role"] == ROLE_CONSERVATIVE]

    print(f"\n{'=' * 50}")
    print("Recommendation:")
    if recommended:
        rec = recommended[0]
        print(f"  RECOMMENDED: {rec['order_name']}")
        print(f"    Gross Profit: {rec['gross_profit']:,}")
        print(f"    Est. Net Profit: {rec['estimated_net_profit']:,}")
        print(f"    Theoretical Coverage: {rec['theoretical_coverage_pct']:.1f}%")
        print(f"    Effective Coverage (95%): {rec['effective_coverage_pct']:.1f}%")
    if backup:
        bak = backup[0]
        print(f"  BACKUP: {bak['order_name']}")
        print(f"    Gross Profit: {bak['gross_profit']:,}")
        print(f"    Est. Net Profit: {bak['estimated_net_profit']:,}")
    if conservative:
        con = conservative[0]
        print(f"  CONSERVATIVE: {con['order_name']}")
    print(f"\n  Switch condition: If {rec['order_name']} emergency purchase ratio exceeds "
          f"{int(SWITCH_PURCHASE_THRESHOLD*100)}%, switch to {bak['order_name']}.")

    # ── Save results ──
    ensure_dir("outputs/results")

    # CSV
    import csv
    csv_path = "outputs/results/problem3_order_scores.csv"
    fieldnames = [
        "order_name", "gross_profit", "inventory_coverage_pct",
        "net_volume", "theoretical_coverage_pct", "effective_coverage_pct",
        "estimated_purchase_ratio_pct", "estimated_purchase_cost",
        "estimated_net_profit", "best_case_net_profit",
        "worst_case_purchase_cost", "recommendation_role",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for m in all_metrics:
            writer.writerow({k: m.get(k) for k in fieldnames})
    print(f"\nSaved: {csv_path}")

    # JSON
    json_path = "outputs/results/problem3_order_recommendation.json"
    rec_order = recommended[0] if recommended else None
    bak_order = backup[0] if backup else None
    con_order = conservative[0] if conservative else None

    recommendation = {
        "remaining_materials": REMAINING_MATERIALS,
        "remaining_total_volume": total_vol,
        "remaining_effective_volume": effective_vol,
        "effective_utilization_rate": EFFECTIVE_UTILIZATION_RATE,
        "piece_stock": PIECE_STOCK,
        "orders": {name: ORDERS[name] for name in ORDERS},
        "recommended_order": rec_order["order_name"] if rec_order else None,
        "backup_order": bak_order["order_name"] if bak_order else None,
        "conservative_order": con_order["order_name"] if con_order else None,
        "switch_condition": (
            f"If {rec_order['order_name']} emergency purchase ratio exceeds "
            f"{int(SWITCH_PURCHASE_THRESHOLD*100)}%, switch to {bak_order['order_name']}."
        ) if rec_order and bak_order else "N/A",
        "coverage_metrics": {
            m["order_name"]: {
                "theoretical_coverage_pct": m["theoretical_coverage_pct"],
                "effective_coverage_pct": m["effective_coverage_pct"],
            }
            for m in all_metrics
        },
        "analysis": all_metrics,
        "reasoning": (
            f"Order {rec_order['order_name']} achieves the highest estimated net profit "
            f"({rec_order['estimated_net_profit']:,}) among all candidates. "
            f"Theoretical volume coverage is {rec_order['theoretical_coverage_pct']:.1f}%, "
            f"conservative effective coverage (at {int(EFFECTIVE_UTILIZATION_RATE*100)}% utilization) "
            f"is {rec_order['effective_coverage_pct']:.1f}%. "
            f"Order {bak_order['order_name']} serves as the backup: it has lower gross profit "
            f"({bak_order['estimated_net_profit']:,}) but more flexible geometry "
            f"(smaller workpieces J01/J02/J07) and J06 is fully covered by stock. "
            f"If {rec_order['order_name']} emergency purchase ratio exceeds "
            f"{int(SWITCH_PURCHASE_THRESHOLD*100)}%, switch to {bak_order['order_name']}."
        ) if rec_order and bak_order else "N/A",
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(recommendation, f, indent=2, ensure_ascii=False)
    print(f"Saved: {json_path}")

    print("\nDone.")


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
