"""
beld.openings
-------------
Door and window placement strategies.

Sub-modules
~~~~~~~~~~~
* priority   — room-type priority table used by door placement
* doors      — interior and exterior door placement
* windows    — exterior window placement
* placer     — high-level orchestrator that combines the above

Public API
~~~~~~~~~~
    from beld.openings import OpeningPlacer
    doors, windows = OpeningPlacer().place(walls, room_map)
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple

from beld.models import Door, Room, WallSegment, Window
from beld.geometry import (
    OccupiedList,
    interval_free,
    mark_interval,
    point_on_segment,
    point_to_t,
)


# ===========================================================================
# Priority table
# ===========================================================================

_ROOM_PRIORITY: Dict[str, int] = {
    "kitchen": 10, "living": 9, "dining": 8, "entrance": 8,
    "bedroom": 7, "bathroom": 6, "office": 6, "study": 6,
    "hallway": 5, "utility": 4, "mudroom": 4, "laundry": 4,
    "closet": 3, "storage": 3, "pantry": 3,
}


def room_priority(room_type: str) -> int:
    return _ROOM_PRIORITY.get(room_type.lower(), 5)


# ===========================================================================
# Interior door placement
# ===========================================================================

def _try_place_door(
    seg: WallSegment,
    width: float = 0.9,
    end_clearance: float = 0.35,
    min_wall_length: float = 1.5,
) -> Optional[Door]:
    """
    Attempt to place a single interior door on seg.

    Tries centre first, then ⅓ and ⅔ positions.
    Returns None if the wall is too short or every position fails clearance.
    """
    if seg.exterior or not seg.room_a or not seg.room_b:
        return None
    if seg.length < max(width + 2 * end_clearance, min_wall_length):
        return None

    clear_t = end_clearance / seg.length
    half_t = (width / 2) / seg.length

    for center_t in (0.5, 0.33, 0.67):
        if center_t - half_t < clear_t or center_t + half_t > 1 - clear_t:
            continue

        cx, cy = point_on_segment(seg, center_t)
        hx, hy = point_on_segment(seg, center_t - half_t)

        return Door(
            wall_id=seg.wall_id,
            center=(cx, cy),
            width=width,
            room_a=seg.room_a,
            room_b=seg.room_b,
            wall_angle=seg.angle,
            swing_side="right",
            swing_radius=width,
            hinge_point=(hx, hy),
            open_angle_deg=90.0,
            door_type="interior_swing",
            is_exterior=False,
        )

    return None


def place_interior_doors(
    walls: List[WallSegment],
    room_map: Dict[str, Room],
    door_width: float = 0.9,
) -> Tuple[List[Door], OccupiedList]:
    """
    Place one door per unique room-pair connection, prioritised by room type.

    Returns (doors, occupied) so callers can pass occupied downstream.
    """
    occupied: OccupiedList = []
    doors: List[Door] = []
    seen_connections: set = set()

    # Group interior walls by the room-pair they connect
    connections: Dict[Tuple[str, str], List[WallSegment]] = {}
    for seg in walls:
        if not seg.exterior and seg.room_a and seg.room_b:
            key = tuple(sorted((seg.room_a, seg.room_b)))  # type: ignore[arg-type]
            connections.setdefault(key, []).append(seg)  # type: ignore[arg-type]

    # Sort connections: highest combined room priority first
    ranked = sorted(
        connections.items(),
        key=lambda kv: max(
            room_priority(room_map[kv[0][0]].room_type),
            room_priority(room_map[kv[0][1]].room_type),
        ),
        reverse=True,
    )

    for (room_a, room_b), segs in ranked:
        if (room_a, room_b) in seen_connections or (room_b, room_a) in seen_connections:
            continue

        # Use the longest shared wall segment
        best = max(segs, key=lambda s: s.length)
        door = _try_place_door(best, width=door_width)

        if door:
            ct = point_to_t(best, door.center)
            ht = (door.width / 2) / best.length
            if interval_free(occupied, best.wall_id, ct - ht, ct + ht):
                doors.append(door)
                mark_interval(occupied, best.wall_id, ct - ht, ct + ht, "door")
                seen_connections.add((room_a, room_b))

    return doors, occupied


# ===========================================================================
# Exterior door placement
# ===========================================================================

def place_exterior_door(
    exterior_walls: List[WallSegment],
    occupied: OccupiedList,
    width: float = 0.9,
    min_wall_length: float = 2.0,
) -> Optional[Door]:
    """
    Place a single exterior entry door on the longest suitable exterior wall.
    """
    candidates = [w for w in exterior_walls if w.length >= min_wall_length]
    if not candidates:
        return None

    seg = max(candidates, key=lambda w: w.length)
    cx, cy = seg.midpoint
    half_t = (width / 2) / seg.length
    hx, hy = point_on_segment(seg, 0.5 - half_t)

    door = Door(
        wall_id=seg.wall_id,
        center=(cx, cy),
        width=width,
        room_a=seg.room_a,
        room_b=None,
        wall_angle=seg.angle,
        swing_side="right",
        swing_radius=width,
        hinge_point=(hx, hy),
        open_angle_deg=90.0,
        door_type="exterior_swing",
        is_exterior=True,
    )

    # Register in occupied so windows don't overlap
    ct = point_to_t(seg, (cx, cy))
    mark_interval(occupied, seg.wall_id, ct - half_t, ct + half_t, "exterior_door")
    return door


# ===========================================================================
# Window placement
# ===========================================================================

_DEFAULT_WINDOW_WIDTHS: Dict[str, float] = {
    "living": 1.8, "dining": 1.8, "kitchen": 1.5, "bedroom": 1.5,
    "office": 1.5, "study": 1.5, "bathroom": 1.0, "closet": 0.8, "hallway": 1.0,
}


def place_windows_on_wall(
    seg: WallSegment,
    room_type: Optional[str],
    width_by_room_type: Optional[Dict[str, float]] = None,
    end_clearance: float = 0.4,
    max_windows: int = 2,
) -> List[Window]:
    """
    Generate candidate Window objects for a single exterior wall.

    Does NOT check occupancy — the caller handles that via occupied list.
    """
    if not seg.exterior:
        return []

    widths = {**_DEFAULT_WINDOW_WIDTHS, **(width_by_room_type or {})}
    w = widths.get(room_type or "", 1.2)

    usable = seg.length - 2 * end_clearance
    if usable < w:
        return []

    min_spacing = 0.3
    n = min(int((usable + min_spacing) / (w + min_spacing)), max_windows)
    if usable < 2.0:
        n = min(n, 1)
    if n == 0:
        return []

    if n == 1:
        ts = [0.5]
    else:
        span = 1 - 2 * (end_clearance / seg.length)
        ts = [
            end_clearance / seg.length + span / (n + 1) * (i + 1)
            for i in range(n)
        ]

    room = seg.room_a or seg.room_b
    return [
        Window(
            wall_id=seg.wall_id,
            center=point_on_segment(seg, t),
            width=w,
            room=room,
            room_type=room_type,
            sill_height=0.9,
            height=1.2,
            wall_angle=seg.angle,
            window_type="casement",
            glazing="double_pane",
        )
        for t in ts
        if 0 < t < 1
    ]


# ===========================================================================
# High-level placer (orchestrates everything above)
# ===========================================================================

class OpeningPlacer:
    """
    Orchestrates door and window placement for a complete set of walls.

    Parameters
    ----------
    door_width : float
        Standard interior door leaf width in metres (default 0.9 m).
    exterior_door_width : float
        Exterior entry door width in metres (default 0.9 m).
    width_by_room_type : dict, optional
        Override default window widths per room type.
    add_exterior_door : bool
        Whether to add one exterior entry door (default True).
    max_windows_per_wall : int
        Maximum windows per exterior wall (default 2).
    """

    def __init__(
        self,
        door_width: float = 0.9,
        exterior_door_width: float = 0.9,
        width_by_room_type: Optional[Dict[str, float]] = None,
        add_exterior_door: bool = True,
        max_windows_per_wall: int = 2,
    ):
        self.door_width = door_width
        self.exterior_door_width = exterior_door_width
        self.width_by_room_type = width_by_room_type
        self.add_exterior_door = add_exterior_door
        self.max_windows_per_wall = max_windows_per_wall

    def place(
        self,
        exterior_walls: List[WallSegment],
        interior_walls: List[WallSegment],
        room_map: Dict[str, Room],
    ) -> Tuple[List[Door], List[Window]]:
        """
        Place all openings and return (doors, windows).
        """
        # 1. Interior doors
        doors, occupied = place_interior_doors(
            interior_walls, room_map, door_width=self.door_width
        )

        # 2. Exterior entry door
        if self.add_exterior_door:
            ext_door = place_exterior_door(
                exterior_walls, occupied, width=self.exterior_door_width
            )
            if ext_door:
                doors.append(ext_door)

        # 3. Windows (skip walls already occupied by exterior door)
        windows: List[Window] = []
        for seg in exterior_walls:
            room_type = None
            if seg.room_a and seg.room_a in room_map:
                room_type = room_map[seg.room_a].room_type
            elif seg.room_b and seg.room_b in room_map:
                room_type = room_map[seg.room_b].room_type

            for win in place_windows_on_wall(
                seg, room_type, self.width_by_room_type, max_windows=self.max_windows_per_wall
            ):
                ct = point_to_t(seg, win.center)
                ht = (win.width / 2) / seg.length
                if interval_free(occupied, seg.wall_id, ct - ht, ct + ht):
                    windows.append(win)
                    mark_interval(occupied, seg.wall_id, ct - ht, ct + ht, "window")

        return doors, windows
