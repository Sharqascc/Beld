"""
beld.validation
---------------
Post-generation checks that produce human-readable warnings.

Design principle: validation is *read-only* — it never mutates the plan.
Warnings are collected and stored in plan.metadata["warnings"].
"""

from __future__ import annotations
from typing import List

from beld.models import FloorPlan
from beld.geometry import distance


def validate_openings(plan: FloorPlan) -> List[str]:
    """
    Check for common placement conflicts and return a list of warning strings.

    Checks performed
    ----------------
    * Door ↔ window overlap on the same wall
    * Door ↔ door overlap on the same wall
    * Missing exterior door
    * Windows without an associated room
    """
    warnings: List[str] = []

    # Door–window conflicts
    for door in plan.doors:
        for window in plan.windows:
            if door.wall_id == window.wall_id:
                dist = distance(door.center, window.center)
                min_gap = (door.width + window.width) / 2
                if dist < min_gap:
                    warnings.append(
                        f"Door–window conflict on wall {door.wall_id} "
                        f"(gap {dist:.2f} m, need {min_gap:.2f} m)"
                    )

    # Door–door conflicts
    for i, d1 in enumerate(plan.doors):
        for d2 in plan.doors[i + 1:]:
            if d1.wall_id == d2.wall_id:
                dist = distance(d1.center, d2.center)
                min_gap = (d1.width + d2.width) / 2
                if dist < min_gap:
                    warnings.append(
                        f"Door–door conflict on wall {d1.wall_id}"
                    )

    # Exterior accessibility
    if plan.rooms and not any(d.is_exterior for d in plan.doors):
        warnings.append("No exterior door — building may be inaccessible")

    # Orphaned windows
    for win in plan.windows:
        if not win.room:
            warnings.append(f"Window on wall {win.wall_id} has no associated room")

    return warnings


def attach_warnings(plan: FloorPlan) -> FloorPlan:
    """Run validation and store warnings in plan.metadata. Returns the plan."""
    warnings = validate_openings(plan)
    if warnings:
        plan.metadata["warnings"] = warnings
    return plan
