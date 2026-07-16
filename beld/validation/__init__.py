from __future__ import annotations

from typing import List, Any

from beld.models import FloorPlan

from .issues import DesignIssue
from .report import ValidationReport
from .rules import validate_plan


def _wall_id(obj):
    return getattr(obj, "wall_id", getattr(obj, "wallid", None))


def _is_exterior(obj) -> bool:
    return bool(getattr(obj, "is_exterior", getattr(obj, "isexterior", False)))


def _room_id(obj):
    return getattr(
        obj,
        "room_id",
        getattr(
            obj,
            "id",
            getattr(obj, "roomid", None),
        ),
    )


def _room_name(obj) -> str:
    return str(
        getattr(
            obj,
            "name",
            getattr(
                obj,
                "room_id",
                getattr(
                    obj,
                    "id",
                    getattr(obj, "roomid", "unknown"),
                ),
            ),
        )
    )


def _wall_line(w):
    line = getattr(w, "line", getattr(w, "geometry", None))
    if line is not None:
        return line

    x1 = getattr(w, "x1", None)
    y1 = getattr(w, "y1", None)
    x2 = getattr(w, "x2", None)
    y2 = getattr(w, "y2", None)
    if None not in (x1, y1, x2, y2):
        from shapely.geometry import LineString
        return LineString([(x1, y1), (x2, y2)])

    return None


def _wall_room_refs(w):
    vals = [
        getattr(w, "room_a", None),
        getattr(w, "room_b", None),
        getattr(w, "rooma", None),
        getattr(w, "roomb", None),
        getattr(w, "room1", None),
        getattr(w, "room2", None),
    ]
    out = []
    for v in vals:
        if v is not None:
            out.append(v)
    return out


def _wall_matches_room(w, room) -> bool:
    rid = _room_id(room)
    for ref in _wall_room_refs(w):
        if ref is room:
            return True
        if ref == rid:
            return True
        if _room_id(ref) == rid:
            return True
    return False


def validate_openings(plan: FloorPlan) -> List[str]:
    warnings: List[str] = []
    seen_exterior = False

    for d in getattr(plan, "doors", []):
        if _is_exterior(d):
            seen_exterior = True
            break

    if not seen_exterior:
        warnings.append("No exterior door found.")

    return warnings


def validate_wall_coverage(plan: FloorPlan, tol: float = 1e-6) -> List[str]:
    warnings: List[str] = []

    rooms = getattr(plan, "rooms", []) or []
    walls = getattr(plan, "walls", []) or []

    for room in rooms:
        polygon = getattr(room, "polygon", None)
        if polygon is None:
            continue

        boundary = getattr(polygon, "boundary", None)
        if boundary is None:
            continue

        room_wall_geoms = []
        for w in walls:
            if _wall_matches_room(w, room):
                line = _wall_line(w)
                if line is not None:
                    room_wall_geoms.append(line)

        if not room_wall_geoms:
            warnings.append(
                f"Wall coverage gap for room {_room_name(room)}: no wall segments found"
            )
            continue

        covered = sum(line.length for line in room_wall_geoms)
        perimeter = boundary.length

        if perimeter - covered > tol:
            warnings.append(
                f"Wall coverage gap for room {_room_name(room)}: "
                f"missing {perimeter - covered:.6f} units"
            )

    return warnings


def attach_warnings(plan: FloorPlan) -> FloorPlan:
    warnings: List[str] = []
    warnings.extend(validate_openings(plan))
    warnings.extend(validate_wall_coverage(plan))
    if warnings:
        if getattr(plan, "metadata", None) is None:
            plan.metadata = {}
        plan.metadata["warnings"] = warnings
    return plan


attachwarnings = attach_warnings
validateopenings = validate_openings
validatewallcoverage = validate_wall_coverage

__all__ = [
    "DesignIssue",
    "ValidationReport",
    "validate_plan",
    "validate_openings",
    "validate_wall_coverage",
    "attach_warnings",
    "attachwarnings",
    "validateopenings",
    "validatewallcoverage",
]
