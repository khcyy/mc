"""Enumeration of production vectors for exact pattern covering.

Enumerates all integer vectors (a1,...,a7) of piece counts that fit
within a material's volume constraint, optionally filtered to
non-dominated vectors.
"""

from __future__ import annotations

import itertools
import logging
from typing import Any

from .models import Material, Piece


def enumerate_production_vectors(
    material: Material,
    pieces: dict[str, Piece],
    grid_gcd: int = 5,
    min_used_volume_threshold: float = 0.5,
    only_nondominated: bool = True,
    max_vectors: int = 100000,
    logger: logging.Logger | None = None,
) -> list[dict[str, Any]]:
    """Enumerate feasible production vectors for one material.

    A production vector (a1,...,a7) is feasible if:
        sum(a_j * vol_j) <= material.volume

    Args:
        material: The material to pack into.
        pieces: Piece definitions (name -> Piece).
        grid_gcd: GCD for grid normalization (outputs use original units).
        min_used_volume_threshold: Minimum utilization threshold.
        only_nondominated: If True, keep only non-dominated vectors.
        max_vectors: Maximum number of vectors to enumerate.

    Returns:
        List of dicts with vector info.
    """
    piece_names = sorted(pieces.keys())
    piece_vols = {pn: pieces[pn].volume for pn in piece_names}
    piece_profits = {pn: pieces[pn].profit for pn in piece_names}
    mat_vol = material.volume
    min_vol = int(mat_vol * min_used_volume_threshold)

    # Enumerate using bounded recursion/iteration
    vectors: list[dict[str, Any]] = []
    _enumerate_recursive(
        mat_vol=mat_vol,
        min_vol=min_vol,
        piece_names=piece_names,
        piece_vols=piece_vols,
        piece_profits=piece_profits,
        idx=0,
        current_vec={pn: 0 for pn in piece_names},
        current_vol=0,
        current_profit=0,
        results=vectors,
        max_vectors=max_vectors,
    )

    if logger:
        logger.info(f"  Enumerated {len(vectors)} raw vectors for {material.name}")

    # Sort by used volume descending
    vectors.sort(key=lambda v: -v["used_volume"])

    # Filter nondominated
    if only_nondominated and vectors:
        vectors = _filter_nondominated(vectors, piece_names)
        if logger:
            logger.info(f"  After nondominated filter: {len(vectors)} vectors")

    return vectors


def _enumerate_recursive(
    mat_vol: int,
    min_vol: int,
    piece_names: list[str],
    piece_vols: dict[str, int],
    piece_profits: dict[str, int],
    idx: int,
    current_vec: dict[str, int],
    current_vol: int,
    current_profit: int,
    results: list[dict[str, Any]],
    max_vectors: int,
) -> None:
    """Recursive vector enumeration with pruning."""
    if idx >= len(piece_names):
        if current_vol >= min_vol and current_vol <= mat_vol:
            vec = dict(current_vec)
            vec["used_volume"] = current_vol
            vec["waste_volume"] = mat_vol - current_vol
            vec["utilization"] = current_vol / mat_vol
            vec["total_profit"] = current_profit
            results.append(vec)
        return

    if len(results) >= max_vectors:
        return

    pname = piece_names[idx]
    vol = piece_vols[pname]
    profit = piece_profits[pname]
    max_count = (mat_vol - current_vol) // vol if vol > 0 else 0

    # Only try a reasonable range
    max_count = min(max_count, 100)

    for count in range(max_count + 1):
        new_vol = current_vol + count * vol
        if new_vol > mat_vol:
            break
        current_vec[pname] = count
        _enumerate_recursive(
            mat_vol=mat_vol,
            min_vol=min_vol,
            piece_names=piece_names,
            piece_vols=piece_vols,
            piece_profits=piece_profits,
            idx=idx + 1,
            current_vec=current_vec,
            current_vol=new_vol,
            current_profit=current_profit + count * profit,
            results=results,
            max_vectors=max_vectors,
        )


def _filter_nondominated(
    vectors: list[dict[str, Any]], piece_names: list[str]
) -> list[dict[str, Any]]:
    """Filter vectors to keep only Pareto-non-dominated ones.

    A vector v1 dominates v2 if:
        v1.used_volume >= v2.used_volume AND
        v1.total_profit >= v2.total_profit AND
        for all j: v1[j] >= v2[j]
    with at least one strict inequality.
    """
    kept: list[dict[str, Any]] = []
    for i, vi in enumerate(vectors):
        dominated = False
        for vj in vectors:
            if vi is vj:
                continue
            if _dominates(vj, vi, piece_names):
                dominated = True
                break
        if not dominated:
            kept.append(vi)
    return kept[:50000]  # Cap for memory


def _dominates(
    v1: dict[str, Any], v2: dict[str, Any], piece_names: list[str]
) -> bool:
    """Check if v1 dominates v2."""
    better = False
    if v1["used_volume"] < v2["used_volume"]:
        return False
    if v1["used_volume"] > v2["used_volume"]:
        better = True
    if v1["total_profit"] > v2["total_profit"]:
        better = True
    for pn in piece_names:
        if v1[pn] < v2[pn]:
            return False
        if v1[pn] > v2[pn]:
            better = True
    return better


def enumerate_vectors_for_all_materials(
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Enumerate production vectors for all materials.

    Returns dict[material_name] -> list[vectors].
    """
    ec = config.get("exact_certificate", {})
    grid_gcd = ec.get("grid_gcd", 5)
    min_util = ec.get("min_used_volume_threshold", 0.5)
    nondominated = ec.get("only_nondominated_vectors", True)
    max_vecs = ec.get("max_vectors", 50000)

    results: dict[str, list[dict[str, Any]]] = {}

    for mat_name, material in materials.items():
        if logger:
            logger.info(f"Enumerating vectors for {mat_name}...")
        vectors = enumerate_production_vectors(
            material=material,
            pieces=pieces,
            grid_gcd=grid_gcd,
            min_used_volume_threshold=min_util,
            only_nondominated=nondominated,
            max_vectors=max_vecs,
            logger=logger,
        )
        results[mat_name] = vectors

    return results
