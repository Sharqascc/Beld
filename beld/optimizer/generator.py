
from __future__ import annotations
import math
import random
from typing import List, Tuple, Optional

from .solver import RoomRect, SolverResult, LayoutSolver, AdjacencyRule


# Rough width/height aspect ratio per room type, used to turn a target
# area into an initial (w, h). Local search only reorders rooms, it never
# needs to touch these — shape stays fixed, only position changes.
_DEFAULT_ASPECT = {
    "bathroom": 1.0,
    "bath": 1.0,
    "bedroom": 1.15,
    "kitchen": 1.3,
    "dining": 1.3,
    "living": 1.5,
}


def _room_dims(room_type: str, area: float, aspect_by_type=None) -> Tuple[float, float]:
    aspects = aspect_by_type or _DEFAULT_ASPECT
    aspect = aspects.get(room_type, 1.2)
    w = math.sqrt(area * aspect)
    h = area / w
    return w, h


def _shelf_pack(
    ordered_rooms: List[Tuple[str, str, float]],
    target_width: float,
    aspect_by_type=None,
) -> List[RoomRect]:
    """Greedy left-to-right, top-to-bottom shelf packing.

    Guarantees a non-overlapping layout by construction — rooms are placed
    in a row until the row would exceed target_width, then a new row
    starts below the tallest room in the current row.
    """
    rects: List[RoomRect] = []
    x = 0.0
    y = 0.0
    row_height = 0.0

    for name, room_type, area in ordered_rooms:
        w, h = _room_dims(room_type, area, aspect_by_type)
        if x > 0 and x + w > target_width:
            x = 0.0
            y += row_height
            row_height = 0.0
        rects.append(RoomRect(name=name, room_type=room_type, x=x, y=y, w=w, h=h))
        x += w
        row_height = max(row_height, h)

    return rects


def generate_layout(
    room_program: List[Tuple[str, str, float]],
    rules: Optional[List[AdjacencyRule]] = None,
    target_aspect: float = 1.3,
    iterations: int = 300,
    seed: Optional[int] = None,
    aspect_by_type=None,
) -> SolverResult:
    """Search over room orderings, scoring each with LayoutSolver.evaluate,
    and return the best-scoring valid (non-overlapping) layout found.

    room_program: list of (name, room_type, target_area) tuples.
    """
    if not room_program:
        raise ValueError("room_program must contain at least one room")

    solver = LayoutSolver(rules=rules)
    total_area = sum(area for _, _, area in room_program)
    target_width = math.sqrt(total_area * target_aspect)
    rng = random.Random(seed)

    best: Optional[SolverResult] = None
    order = list(room_program)

    for i in range(iterations):
        if i == 0:
            # Deterministic baseline: largest rooms first tends to pack tightly.
            trial_order = sorted(order, key=lambda r: -r[2])
        else:
            trial_order = order[:]
            rng.shuffle(trial_order)

        rects = _shelf_pack(trial_order, target_width, aspect_by_type)
        result = solver.optimize(rects)

        if best is None or result.metrics.overall_score > best.metrics.overall_score:
            best = result

    return best
