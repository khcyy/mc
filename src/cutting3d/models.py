"""Data models for 3D cutting stock optimization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class Objective(Enum):
    MAXIMIZE_UTILIZATION = "maximize_utilization"
    MAXIMIZE_PROFIT = "maximize_profit"


class SolverStatus(Enum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class Material:
    """Raw material specification."""
    name: str
    length: int
    width: int
    height: int
    count: int

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def dims(self) -> tuple[int, int, int]:
        return (self.length, self.width, self.height)


@dataclass
class Piece:
    """Piece/item specification."""
    name: str
    length: int
    width: int
    height: int
    profit: int

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def profit_density(self) -> float:
        return self.profit / self.volume if self.volume > 0 else 0.0

    @property
    def dims(self) -> tuple[int, int, int]:
        return (self.length, self.width, self.height)


@dataclass
class Orientation:
    """A specific rotation of a piece (dx, dy, dz)."""
    dx: int
    dy: int
    dz: int

    def __hash__(self) -> int:
        return hash((self.dx, self.dy, self.dz))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Orientation):
            return False
        return self.dx == other.dx and self.dy == other.dy and self.dz == other.dz


@dataclass
class PlacedPiece:
    """A piece placed in a pattern with orientation and coordinates."""
    piece_name: str
    x: int
    y: int
    z: int
    orientation: Orientation

    @property
    def dx(self) -> int:
        return self.orientation.dx

    @property
    def dy(self) -> int:
        return self.orientation.dy

    @property
    def dz(self) -> int:
        return self.orientation.dz

    @property
    def volume(self) -> int:
        return self.dx * self.dy * self.dz

    def to_dict(self) -> dict[str, Any]:
        return {
            "piece_name": self.piece_name,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "dx": self.dx,
            "dy": self.dy,
            "dz": self.dz,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlacedPiece:
        return cls(
            piece_name=d["piece_name"],
            x=d["x"],
            y=d["y"],
            z=d["z"],
            orientation=Orientation(d["dx"], d["dy"], d["dz"]),
        )


@dataclass
class Pattern:
    """A cutting pattern: arrangement of pieces in one material block."""
    pattern_id: int
    material_name: str
    placed_pieces: list[PlacedPiece] = field(default_factory=list)

    @property
    def num_pieces(self) -> int:
        return len(self.placed_pieces)

    @property
    def used_volume(self) -> int:
        return sum(p.volume for p in self.placed_pieces)

    @property
    def total_profit(self) -> int:
        return 0  # set externally or computed from piece profits

    def get_piece_counts(self, piece_names: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {name: 0 for name in piece_names}
        for pp in self.placed_pieces:
            counts[pp.piece_name] = counts.get(pp.piece_name, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "material_name": self.material_name,
            "placed_pieces": [pp.to_dict() for pp in self.placed_pieces],
            "num_pieces": self.num_pieces,
            "used_volume": self.used_volume,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Pattern:
        return cls(
            pattern_id=d["pattern_id"],
            material_name=d["material_name"],
            placed_pieces=[PlacedPiece.from_dict(pp) for pp in d["placed_pieces"]],
        )


@dataclass
class MasterSolution:
    """Solution to the master integer programming problem."""
    status: SolverStatus
    objective_value: float
    pattern_usage: dict[int, int]  # pattern_id -> number of times used
    total_profit: float = 0.0
    total_used_volume: int = 0
    total_waste_volume: int = 0
    total_material_volume: int = 0
    material_utilization: float = 0.0
    piece_counts: dict[str, int] = field(default_factory=dict)
    solve_time_seconds: float = 0.0
    upper_bound: float = 0.0
    lower_bound: float = 0.0
    gap: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "objective_value": self.objective_value,
            "pattern_usage": self.pattern_usage,
            "total_profit": self.total_profit,
            "total_used_volume": self.total_used_volume,
            "total_waste_volume": self.total_waste_volume,
            "total_material_volume": self.total_material_volume,
            "material_utilization": self.material_utilization,
            "piece_counts": self.piece_counts,
            "solve_time_seconds": self.solve_time_seconds,
            "upper_bound": self.upper_bound,
            "lower_bound": self.lower_bound,
            "gap": self.gap,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MasterSolution:
        return cls(
            status=SolverStatus(d["status"]),
            objective_value=d["objective_value"],
            pattern_usage={int(k): v for k, v in d["pattern_usage"].items()},
            total_profit=d.get("total_profit", 0.0),
            total_used_volume=d.get("total_used_volume", 0),
            total_waste_volume=d.get("total_waste_volume", 0),
            total_material_volume=d.get("total_material_volume", 0),
            material_utilization=d.get("material_utilization", 0.0),
            piece_counts=d.get("piece_counts", {}),
            solve_time_seconds=d.get("solve_time_seconds", 0.0),
            upper_bound=d.get("upper_bound", 0.0),
            lower_bound=d.get("lower_bound", 0.0),
            gap=d.get("gap", 0.0),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ExperimentResult:
    """Complete experiment result for a problem instance."""
    problem_name: str
    solution: MasterSolution
    patterns: list[Pattern]
    config: dict[str, Any] = field(default_factory=dict)

    def to_json(self, path: str) -> None:
        import json as _json
        data = {
            "problem_name": self.problem_name,
            "solution": self.solution.to_dict(),
            "patterns": [p.to_dict() for p in self.patterns],
        }
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, path: str) -> ExperimentResult:
        import json as _json
        with open(path, "r", encoding="utf-8") as f:
            data = _json.load(f)
        solution = MasterSolution.from_dict(data["solution"])
        patterns = [Pattern.from_dict(p) for p in data["patterns"]]
        return cls(
            problem_name=data["problem_name"],
            solution=solution,
            patterns=patterns,
        )
