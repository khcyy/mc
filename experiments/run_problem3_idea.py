"""Problem 3: Order Selection Idea - Undergraduate Team.

Provides order analysis: inventory deduction, remaining material production
capacity estimation, net profit calculation, and order recommendation logic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Problem 3 Data (from docs/question.md) ──────────────────────────

# Remaining raw materials
REMAINING_MATERIALS = {
    "L01": 2,  # 300x200x150, volume 9,000,000 each
    "L02": 2,  # 250x150x100, volume 3,750,000 each
    "L03": 1,  # 200x150x80,  volume 2,400,000 each
}

# Remaining workpiece stock
PIECE_STOCK = {
    "J01": 0, "J02": 0, "J03": 20, "J04": 0,
    "J05": 3, "J06": 11, "J07": 19,
}

# Workpiece profits and volumes
PIECE_DATA = {
    "J01": {"profit": 620, "length": 40, "width": 40, "height": 40},
    "J02": {"profit": 780, "length": 50, "width": 40, "height": 40},
    "J03": {"profit": 880, "length": 60, "width": 50, "height": 30},
    "J04": {"profit": 1850, "length": 75, "width": 60, "height": 40},
    "J05": {"profit": 2520, "length": 80, "width": 60, "height": 50},
    "J06": {"profit": 1000, "length": 100, "width": 50, "height": 20},
    "J07": {"profit": 540, "length": 120, "width": 20, "height": 20},
}

# Orders
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

    # Inventory coverage: how much of the order is already available
    stock_covered = sum(
        min(order.get(p, 0), PIECE_STOCK.get(p, 0)) * piece_volume(p)
        for p in order
    )
    inventory_coverage = stock_covered / total_demand_volume if total_demand_volume > 0 else 0

    # Remaining material capacity
    remaining_capacity = total_remaining_material_volume()

    # Production coverage estimate: can remaining materials cover net demand?
    production_coverage = min(1.0, remaining_capacity / net_volume) if net_volume > 0 else 1.0

    # Estimated emergency purchase needed (worst case: all net demand)
    # In practice, some can be produced from remaining materials
    # We estimate: if net_volume <= remaining_capacity, purchase ratio is low
    # Otherwise, purchase_ratio = (net_volume - remaining_capacity) / net_volume
    if net_volume <= remaining_capacity:
        estimated_purchase_ratio = 0.1  # Assume ~10% of net demand needs purchase due to geometry limits
    else:
        estimated_purchase_ratio = (net_volume - remaining_capacity) / net_volume + 0.1

    # Emergency purchase cost = 2 × profit of purchased items
    # Estimate: purchase_ratio × net items × profit
    estimated_purchase_cost = 0
    for p in net:
        if net[p] > 0:
            purchased = int(net[p] * estimated_purchase_ratio)
            estimated_purchase_cost += purchased * PIECE_DATA[p]["profit"] * 2

    # Net profit estimate
    net_profit = gross_profit - estimated_purchase_cost

    # Calculate actual purchase cost if we assume geometric feasibility
    # Simplification: assume we produce all we can, purchase what cannot fit
    purchasable_from_production = sum(net[p] * PIECE_DATA[p]["profit"] for p in net)
    worst_case_purchase_cost = purchasable_from_production * 2  # if nothing can be produced
    best_case_net = gross_profit  # if everything can be produced

    return {
        "order_name": order_name,
        "gross_profit": gross_profit,
        "net_demand": net,
        "inventory_coverage_pct": round(inventory_coverage * 100, 2),
        "net_volume": net_volume,
        "remaining_material_capacity": remaining_capacity,
        "production_coverage_pct": round(production_coverage * 100, 2),
        "estimated_purchase_ratio_pct": round(estimated_purchase_ratio * 100, 2),
        "estimated_purchase_cost": estimated_purchase_cost,
        "estimated_net_profit": net_profit,
        "best_case_net_profit": best_case_net,
        "worst_case_purchase_cost": worst_case_purchase_cost,
    }


def rank_orders(metrics: list[dict]) -> list[dict]:
    """Rank orders by estimated net profit (primary) and inventory coverage (secondary)."""
    return sorted(metrics, key=lambda m: (m["estimated_net_profit"], m["inventory_coverage_pct"]), reverse=True)


def main():
    print("=" * 70)
    print("Problem 3: Order Selection Analysis")
    print("=" * 70)

    total_vol = total_remaining_material_volume()
    print(f"\nRemaining Materials: {REMAINING_MATERIALS}")
    print(f"Total Remaining Volume: {total_vol:,}")
    print(f"\nPiece Stock: {PIECE_STOCK}")

    all_metrics = []
    for order_name, order in ORDERS.items():
        m = compute_order_metrics(order_name, order)
        all_metrics.append(m)
        print(f"\n{'─' * 50}")
        print(f"Order {order_name}: {order}")
        print(f"  Net Demand: {m['net_demand']}")
        print(f"  Gross Profit: {m['gross_profit']:,}")
        print(f"  Inventory Coverage: {m['inventory_coverage_pct']:.1f}%")
        print(f"  Net Volume Needed: {m['net_volume']:,}")
        print(f"  Production Coverage: {m['production_coverage_pct']:.1f}%")
        print(f"  Est. Purchase Ratio: {m['estimated_purchase_ratio_pct']:.1f}%")
        print(f"  Est. Purchase Cost: {m['estimated_purchase_cost']:,}")
        print(f"  Est. Net Profit: {m['estimated_net_profit']:,}")
        print(f"  Best Case Net Profit: {m['best_case_net_profit']:,}")
        print(f"  Worst Case Purchase Cost: {m['worst_case_purchase_cost']:,}")

    ranked = rank_orders(all_metrics)
    print(f"\n{'=' * 50}")
    print("Recommended Order Priority:")
    for i, m in enumerate(ranked):
        print(f"  {i+1}. {m['order_name']}: Est. Net Profit={m['estimated_net_profit']:,}, "
              f"Inventory Coverage={m['inventory_coverage_pct']:.1f}%")

    # Save results
    ensure_dir("outputs/results")

    # CSV
    import csv
    csv_path = "outputs/results/problem3_order_scores.csv"
    fieldnames = [
        "order_name", "gross_profit", "inventory_coverage_pct",
        "net_volume", "production_coverage_pct", "estimated_purchase_ratio_pct",
        "estimated_purchase_cost", "estimated_net_profit",
        "best_case_net_profit", "worst_case_purchase_cost",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in all_metrics:
            writer.writerow({k: m[k] for k in fieldnames})
    print(f"\nSaved: {csv_path}")

    # JSON
    json_path = "outputs/results/problem3_order_recommendation.json"
    recommendation = {
        "remaining_materials": REMAINING_MATERIALS,
        "remaining_total_volume": total_vol,
        "piece_stock": PIECE_STOCK,
        "orders": {name: ORDERS[name] for name in ORDERS},
        "analysis": all_metrics,
        "recommended_order": ranked[0]["order_name"] if ranked else None,
        "recommendation_reason": (
            f"Order {ranked[0]['order_name']} achieves the highest estimated net profit "
            f"({ranked[0]['estimated_net_profit']:,}) with inventory coverage of "
            f"{ranked[0]['inventory_coverage_pct']:.1f}%. "
            f"Production capacity ({total_vol:,} remaining volume) is sufficient to cover "
            f"most of the net demand ({ranked[0]['net_volume']:,}), minimizing emergency purchase cost."
        ) if ranked else "No orders to recommend.",
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(recommendation, f, indent=2, ensure_ascii=False)
    print(f"Saved: {json_path}")

    print("\nDone.")


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
