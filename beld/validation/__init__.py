from __future__ import annotations

from typing import List

from beld.models import FloorPlan
from beld.geometry import distance


def _wall_id(obj):
    return getattr(obj, "wall_id", getattr(obj, "wallid", None))


def _is_exterior_door(obj) -> bool:
    return getattr(obj, "is_exterior", getattr(obj, "isexterior", False))


def validate_openings(plan: FloorPlan) -> List[str]:
    warnings: List[str] = []

    for door in plan.doors:
        for window in plan.windows:
            if _wall_id(door) != _wall_id(window):
                continue
            dist = distance(door.center, window.center)
            min_gap = (door.width + window.width) / 2
            if dist < min_gap:
                warnings.append(
                    f"Door-window conflict on wall {_wall_id(door)} "
                    f"(gap {dist:.2f} m, need {min_gap:.2f} m)"
                )

    for i, d1 in enumerate(plan.doors):
        for d2 in plan.doors[i + 1:]:
            if _wall_id(d1) != _wall_id(d2):
                continue
            dist = distance(d1.center, d2.center)
            min_gap = (d1.width + d2.width) / 2
            if dist < min_gap:
                warnings.append(
                    f"Door-door conflict on wall {_wall_id(d1)} "
                    f"(gap {dist:.2f} m, need {min_gap:.2f} m)"
                )

    if plan.rooms and not any(_is_exterior_door(d) for d in plan.doors):
        warnings.append("No exterior door found; building may be inaccessible")

    for win in plan.windows:
        if not win.room:
            warnings.append(f"Window on wall {_wall_id(win)} has no associated room")

    return warnings


def attach_warnings(plan: FloorPlan) -> FloorPlan:
    warnings = []
    warnings.extend(validate_openings(plan))
    if warnings:
        plan.metadata["warnings"] = warnings
    return plan


attachwarnings = attach_warnings
validateopenings = validate_openings
