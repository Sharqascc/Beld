from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from shapely.geometry import LineString

from beld.models import Room, WallSegment
from beld.geometry import isclose


MIN_WALL_LENGTH = 0.05
OVERLAP_TOL = 0.02



def _room_type(room: Room) -> Optional[str]:
    return getattr(room, "room_type", getattr(room, "roomtype", None))


def _make_wall(
    wall_id: str,
    room: Room,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    roomb: Optional[str] = None,
    roombtype: Optional[str] = None,
) -> WallSegment:
    return WallSegment(
        wall_id=wall_id,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        room_a=room.id,
        room_b=roomb,
        room_a_type=_room_type(room),
        room_b_type=roombtype,
        exterior=roomb is None,
        thickness=0.15,
    )


def _intervals_for_edge_with_other(
    edge: LineString,
    other_boundary,
    vertical: bool,
) -> List[Tuple[float, float]]:
    overlap = edge.intersection(other_boundary.buffer(OVERLAP_TOL))
    geoms = getattr(overlap, "geoms", [overlap])
    intervals: List[Tuple[float, float]] = []

    for geom in geoms:
        if geom.is_empty:
            continue
        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            if len(coords) < 2:
                continue
            a = coords[0][1] if vertical else coords[0][0]
            b = coords[-1][1] if vertical else coords[-1][0]
            lo, hi = sorted((a, b))
            if hi - lo >= MIN_WALL_LENGTH:
                intervals.append((lo, hi))
        elif geom.geom_type == "MultiLineString":
            for part in geom.geoms:
                coords = list(part.coords)
                if len(coords) < 2:
                    continue
                a = coords[0][1] if vertical else coords[0][0]
                b = coords[-1][1] if vertical else coords[-1][0]
                lo, hi = sorted((a, b))
                if hi - lo >= MIN_WALL_LENGTH:
                    intervals.append((lo, hi))
    return intervals


def _merge_intervals(intervals: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for lo, hi in intervals[1:]:
        plo, phi = merged[-1]
        if lo <= phi + OVERLAP_TOL:
            merged[-1] = (plo, max(phi, hi))
        else:
            merged.append((lo, hi))
    return merged


def extract_wall_segments(rooms: List[Room]) -> List[WallSegment]:
    walls: List[WallSegment] = []
    wall_index = 0

    for room in rooms:
        poly = room.polygon
        if poly.is_empty or poly.area <= 0.01:
            continue

        coords = list(poly.exterior.coords[:-1])
        n = len(coords)

        for i in range(n):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]

            if isclose(x1, x2) and isclose(y1, y2):
                continue

            vertical = isclose(x1, x2)
            horizontal = isclose(y1, y2)

            if not (vertical or horizontal):
                wall_id = f"W{wall_index:04d}"
                wall_index += 1
                walls.append(_make_wall(wall_id, room, x1, y1, x2, y2))
                continue

            if vertical:
                const = x1
                a0, a1 = sorted((y1, y2))
                edge = LineString([(const, a0), (const, a1)])
            else:
                const = y1
                a0, a1 = sorted((x1, x2))
                edge = LineString([(a0, const), (a1, const)])

            cut_points = {a0, a1}
            ownership: List[Tuple[float, float, str, str]] = []

            for other in rooms:
                if other.id == room.id:
                    continue

                intervals = _intervals_for_edge_with_other(edge, other.polygon.boundary, vertical)
                for lo, hi in _merge_intervals(intervals):
                    lo = max(lo, a0)
                    hi = min(hi, a1)
                    if hi - lo < MIN_WALL_LENGTH:
                        continue
                    cut_points.add(lo)
                    cut_points.add(hi)
                    ownership.append((lo, hi, other.id, _room_type(other)))

            cuts = sorted(cut_points)
            for j in range(len(cuts) - 1):
                lo, hi = cuts[j], cuts[j + 1]
                if hi - lo < MIN_WALL_LENGTH:
                    continue

                mid = 0.5 * (lo + hi)
                owner_id = None
                owner_type = None
                for olo, ohi, oid, otype in ownership:
                    if olo - OVERLAP_TOL <= mid <= ohi + OVERLAP_TOL:
                        owner_id = oid
                        owner_type = otype
                        break

                if vertical:
                    sx1, sy1, sx2, sy2 = const, lo, const, hi
                    if y2 < y1:
                        sx1, sy1, sx2, sy2 = const, hi, const, lo
                else:
                    sx1, sy1, sx2, sy2 = lo, const, hi, const
                    if x2 < x1:
                        sx1, sy1, sx2, sy2 = hi, const, lo, const

                wall_id = f"W{wall_index:04d}"
                wall_index += 1
                walls.append(_make_wall(wall_id, room, sx1, sy1, sx2, sy2, owner_id, owner_type))

    dedup: Dict[Tuple[Tuple[float, float], Tuple[float, float], Tuple[str, ...]], WallSegment] = {}
    for w in walls:
        p1 = (round(w.x1, 6), round(w.y1, 6))
        p2 = (round(w.x2, 6), round(w.y2, 6))
        ep = tuple(sorted((p1, p2)))
        rooms_key = tuple(sorted(r for r in (w.room_a, w.room_b) if r))
        key = (ep[0], ep[1], rooms_key)
        if key in dedup:
            continue
        dedup[key] = w

    out = list(dedup.values())
    out.sort(key=lambda w: (round(min(w.x1, w.x2), 6), round(min(w.y1, w.y2), 6), round(w.length, 6), w.room_a, w.room_b or ""))
    for idx, w in enumerate(out):
        w.wall_id = f"W{idx:04d}"
    return out


def split_walls(walls: List[WallSegment]) -> Tuple[List[WallSegment], List[WallSegment]]:
    exterior = [w for w in walls if w.exterior]
    interior = [w for w in walls if not w.exterior]
    return exterior, interior


splitwalls = split_walls
extractwallsegments = extract_wall_segments
