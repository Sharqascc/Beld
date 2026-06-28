from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math


@dataclass
class RoomRect:
    name: str
    room_type: str
    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.w / 2.0, self.y + self.h / 2.0)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


@dataclass
class AdjacencyRule:
    room_type_a: str
    room_type_b: str
    weight: float = 1.0
    desired: bool = True


@dataclass
class LayoutMetrics:
    total_area: float
    overlap_area: float
    adjacency_score: float
    compactness_score: float
    circulation_score: float
    overall_score: float


@dataclass
class SolverResult:
    rooms: List[RoomRect]
    metrics: LayoutMetrics
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "SolverResult",
            f"- rooms: {len(self.rooms)}",
            f"- total_area: {self.metrics.total_area:.2f}",
            f"- overlap_area: {self.metrics.overlap_area:.2f}",
            f"- adjacency_score: {self.metrics.adjacency_score:.3f}",
            f"- compactness_score: {self.metrics.compactness_score:.3f}",
            f"- circulation_score: {self.metrics.circulation_score:.3f}",
            f"- overall_score: {self.metrics.overall_score:.3f}",
        ]
        if self.notes:
            lines.append("- notes:")
            lines.extend([f"  - {n}" for n in self.notes])
        return "\n".join(lines)


def _intersection_area(a: RoomRect, b: RoomRect) -> float:
    ax1, ay1, ax2, ay2 = a.bounds
    bx1, by1, bx2, by2 = b.bounds
    dx = min(ax2, bx2) - max(ax1, bx1)
    dy = min(ay2, by2) - max(ay1, by1)
    if dx <= 0 or dy <= 0:
        return 0.0
    return dx * dy


def _touching_edge_length(a: RoomRect, b: RoomRect, tol: float = 1e-9) -> float:
    ax1, ay1, ax2, ay2 = a.bounds
    bx1, by1, bx2, by2 = b.bounds

    vertical_touch = abs(ax2 - bx1) <= tol or abs(bx2 - ax1) <= tol
    horizontal_touch = abs(ay2 - by1) <= tol or abs(by2 - ay1) <= tol

    if vertical_touch:
        overlap = min(ay2, by2) - max(ay1, by1)
        return max(0.0, overlap)

    if horizontal_touch:
        overlap = min(ax2, bx2) - max(ax1, bx1)
        return max(0.0, overlap)

    return 0.0


class LayoutSolver:
    def __init__(self, rules=None, verbose: bool = False):
        self.rules = rules or self.default_rules()
        self.verbose = verbose

    @staticmethod
    def default_rules():
        return [
            AdjacencyRule("kitchen", "dining", 1.0, True),
            AdjacencyRule("living", "dining", 0.8, True),
            AdjacencyRule("bedroom", "bathroom", 0.7, True),
            AdjacencyRule("bathroom", "kitchen", 0.8, False),
        ]

    def evaluate(self, rooms: List[RoomRect]) -> LayoutMetrics:
        total_area = sum(r.area for r in rooms)

        overlap_area = 0.0
        adjacency_score = 0.0
        max_rule_score = sum(abs(r.weight) for r in self.rules) or 1.0

        for i in range(len(rooms)):
            for j in range(i + 1, len(rooms)):
                overlap_area += _intersection_area(rooms[i], rooms[j])

        for rule in self.rules:
            matched = False
            pair_score = 0.0
            for i in range(len(rooms)):
                for j in range(i + 1, len(rooms)):
                    a, b = rooms[i], rooms[j]
                    types = {a.room_type, b.room_type}
                    if {rule.room_type_a, rule.room_type_b} == types:
                        edge = _touching_edge_length(a, b)
                        if rule.desired:
                            pair_score = max(pair_score, 1.0 if edge > 0 else 0.0)
                        else:
                            pair_score = max(pair_score, 1.0 if edge == 0 else 0.0)
                        matched = True
            if not matched and not rule.desired:
                pair_score = 1.0
            adjacency_score += pair_score * abs(rule.weight)

        adjacency_score /= max_rule_score

        min_x = min(r.x for r in rooms)
        min_y = min(r.y for r in rooms)
        max_x = max(r.x + r.w for r in rooms)
        max_y = max(r.y + r.h for r in rooms)
        bbox_area = max((max_x - min_x) * (max_y - min_y), 1e-9)
        compactness_score = min(total_area / bbox_area, 1.0)

        centers = [r.center for r in rooms]
        if len(centers) >= 2:
            avg_dist = sum(
                math.dist(centers[i], centers[j])
                for i in range(len(centers))
                for j in range(i + 1, len(centers))
            ) / (len(centers) * (len(centers) - 1) / 2)
            circulation_score = 1.0 / (1.0 + avg_dist / 10.0)
        else:
            circulation_score = 1.0

        overlap_penalty = min(overlap_area / max(total_area, 1e-9), 1.0)
        overall_score = (
            0.45 * adjacency_score
            + 0.30 * compactness_score
            + 0.25 * circulation_score
            - 0.80 * overlap_penalty
        )

        return LayoutMetrics(
            total_area=total_area,
            overlap_area=overlap_area,
            adjacency_score=adjacency_score,
            compactness_score=compactness_score,
            circulation_score=circulation_score,
            overall_score=overall_score,
        )

    def optimize(self, rooms: List[RoomRect]) -> SolverResult:
        metrics = self.evaluate(rooms)
        notes = []

        if metrics.overlap_area > 0:
            notes.append("Detected room overlap; refine positions before downstream wall generation.")
        if metrics.adjacency_score < 0.5:
            notes.append("Adjacency satisfaction is weak; consider swapping or shifting rooms.")
        if metrics.compactness_score < 0.6:
            notes.append("Layout footprint is loose; clustering rooms may improve compactness.")

        return SolverResult(rooms=rooms, metrics=metrics, notes=notes)
