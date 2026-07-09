"""
beld.walls
----------
Extracts WallSegment objects from Room polygons.

Responsibilities
~~~~~~~~~~~~~~~~
* Walk each room's exterior polygon ring
* Deduplicate shared edges (interior walls appear in two rooms)
* Classify each segment as exterior or interior
* Assign room_a / room_b references

Nothing in this module places doors or windows — that lives in beld.openings.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from shapely.geometry import LineString

from beld.models import Room, WallSegment
from beld.geometry import canonical_wall_key, isclose


def extract_wall_segments(rooms: List[Room]) -> List[WallSegment]:
    """
    Build the complete wall graph from a list of rooms.

    Algorithm
    ---------
    1. For each room polygon, iterate its exterior edges.
    2. Use a canonical integer key to detect shared (interior) edges.
    3. Each unique edge becomes exactly one WallSegment, tagged
       with room_a and (optionally) room_b.

    Returns
    -------
    List[WallSegment]
        Sorted by wall_id (deterministic ordering).
    """
    walls: List[WallSegment] = []
    seg_by_key: Dict[Tuple[int, int, int, int], WallSegment] = {}

    for room in rooms:
        poly = room.polygon
        if poly.is_empty or poly.area < 0.01:
            continue

        # coords[:-1] avoids the duplicated closing vertex
        coords = list(poly.exterior.coords[:-1])
        n = len(coords)

        for i in range(n):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]

            # Skip degenerate edges
            if isclose(x1, x2) and isclose(y1, y2):
                continue

            key = canonical_wall_key(x1, y1, x2, y2)

            if key in seg_by_key:
                # Edge already recorded from a neighbouring room → mark interior
                existing = seg_by_key[key]
                if existing.room_b is None:
                    existing.room_b = room.id
                    existing.room_b_type = room.room_type
                    existing.exterior = False
                continue

            # Determine adjacency via Shapely boundary proximity
            room_b: Optional[str] = None
            room_b_type: Optional[str] = None
            edge = LineString([(x1, y1), (x2, y2)])
            edge_len = edge.length

            for other in rooms:
                if other.id == room.id:
                    continue
                # Measure how much of this edge actually runs along the
                # other room's boundary, not just whether it touches it.
                # A corner touch has ~0 overlap length; a true shared
                # wall has overlap length close to the full edge.
                overlap = edge.intersection(other.polygon.boundary.buffer(0.02))
                if edge_len > 0 and overlap.length > 0.5 * edge_len:
                    room_b = other.id
                    room_b_type = other.room_type
                    break

            exterior = room_b is None
            wall_id = f"W{len(walls):04d}"

            seg = WallSegment(
                wall_id=wall_id,
                x1=x1, y1=y1, x2=x2, y2=y2,
                room_a=room.id,
                room_b=room_b,
                room_a_type=room.room_type,
                room_b_type=room_b_type,
                exterior=exterior,
                thickness=0.15,
            )
            seg_by_key[key] = seg
            walls.append(seg)

    walls.sort(key=lambda w: w.wall_id)
    return walls


def split_walls(
    walls: List[WallSegment],
) -> Tuple[List[WallSegment], List[WallSegment]]:
    """Partition walls into (exterior_walls, interior_walls)."""
    exterior = [w for w in walls if w.exterior]
    interior = [w for w in walls if not w.exterior]
    return exterior, interior
