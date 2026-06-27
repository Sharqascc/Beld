"""
beld.geometry
-------------
Pure geometry helpers — no domain knowledge, no side-effects.
All functions operate on raw numbers or WallSegment objects.
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional

from beld.models import WallSegment


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def point_on_segment(seg: WallSegment, t: float) -> Tuple[float, float]:
    """Return the 2-D point at parametric position t ∈ [0, 1] along seg."""
    return (
        seg.x1 + (seg.x2 - seg.x1) * t,
        seg.y1 + (seg.y2 - seg.y1) * t,
    )


def point_to_t(seg: WallSegment, pt: Tuple[float, float]) -> float:
    """Project pt onto seg and return the parametric position t."""
    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    denom = dx * dx + dy * dy
    if denom == 0:
        return 0.0
    return ((pt[0] - seg.x1) * dx + (pt[1] - seg.y1) * dy) / denom


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def isclose(a: float, b: float, tol: float = 0.01) -> bool:
    return math.isclose(a, b, abs_tol=tol)


# ---------------------------------------------------------------------------
# Interval occupancy  (wall-space collision detection)
# ---------------------------------------------------------------------------

# Each entry: (wall_id, t_start, t_end, kind_str)
OccupiedList = List[Tuple[str, float, float, str]]


def interval_free(
    occupied: OccupiedList,
    wall_id: str,
    t0: float,
    t1: float,
    margin: float = 0.02,
) -> bool:
    """Return True if [t0, t1] on wall_id is free (no overlap with margin)."""
    for owid, a, b, _ in occupied:
        if owid != wall_id:
            continue
        if not (t1 + margin <= a or t0 - margin >= b):
            return False
    return True


def mark_interval(
    occupied: OccupiedList,
    wall_id: str,
    t0: float,
    t1: float,
    kind: str,
) -> None:
    """Record [t0, t1] on wall_id as occupied by kind."""
    occupied.append((wall_id, max(0.0, t0), min(1.0, t1), kind))


# ---------------------------------------------------------------------------
# Wall-key helpers (for deduplication)
# ---------------------------------------------------------------------------

def canonical_wall_key(
    x1: float, y1: float, x2: float, y2: float, grid: int = 100
) -> Tuple[int, int, int, int]:
    """Return a canonical (sorted) integer key for a wall segment."""
    i1, j1 = int(round(x1 * grid)), int(round(y1 * grid))
    i2, j2 = int(round(x2 * grid)), int(round(y2 * grid))
    if (i1, j1) <= (i2, j2):
        return (i1, j1, i2, j2)
    return (i2, j2, i1, j1)
