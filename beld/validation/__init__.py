from __future__ import annotations

from typing import List

from shapely.geometry import LineString
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


def validate_wall_coverage(plan: FloorPlan, tol: float = 0.02) -> List[str]:
    warnings: List[str] = []

    wall_lines = [
        LineString([(w.x1, w.y1), (w.x2, w.y2)])
        for w in plan.walls
    ]

    for room in plan.rooms:
        coords = list(room.polygon.exterior.coords)
        for i in range(len(coords) - 1):
            edge = LineString([coords[i], coords[i + 1]])
            uncovered = edge
            for wl in wall_lines:
                if uncovered.is_empty:
                    break
                if uncovered.buffer(tol, cap_style=2).intersects(wl):
                    uncovered = uncovered.difference(wl.buffer(tol, cap_style=2))

            if not uncovered.is_empty and getattr(uncovered, "length", 0.0) > tol:
                room_name = getattr(room, "room_id", getattr(room, "id", "unknown"))
                warnings.append(
                    f"Wall coverage gap for room {room_name} "
                    f"on edge {tuple(coords[i])}->{tuple(coords[i + 1])}"
                )

    return warnings


def attach_warnings(plan: FloorPlan) -> FloorPlan:
    warnings = []
    warnings.extend(validate_openings(plan))
    warnings.extend(validate_wall_coverage(plan))
    if warnings:
        plan.metadata["warnings"] = warnings
    return plan


attachwarnings = attach_warnings
validateopenings = validate_openings
validatewallcoverage = validate_wall_coverage
