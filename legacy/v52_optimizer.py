"""
v52_optimizer.py - Floor plan generator with openings (doors & windows)
Ready-to-run Colab version with basic collision-aware placement and SVG export
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
import math
from shapely.geometry import Polygon
import numpy as np

@dataclass
class Room:
    id: str
    polygon: Polygon
    room_type: str
    area: float

@dataclass
class WallSegment:
    wall_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    room_a: Optional[str] = None
    room_b: Optional[str] = None
    exterior: bool = False
    thickness: float = 0.15

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))

@dataclass
class Door:
    wall_id: str
    center: Tuple[float, float]
    width: float
    room_a: Optional[str]
    room_b: Optional[str]
    wall_angle: float
    swing_side: str = "right"
    swing_radius: float = 0.9
    hinge_point: Optional[Tuple[float, float]] = None
    open_angle_deg: float = 90.0

@dataclass
class Window:
    wall_id: str
    center: Tuple[float, float]
    width: float
    room: Optional[str]
    sill_height: float = 0.9
    height: float = 1.2
    kind: str = "window"

@dataclass
class FloorPlan:
    rooms: List[Room]
    walls: List[WallSegment]
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    exterior_walls: List[WallSegment] = field(default_factory=list)
    interior_walls: List[WallSegment] = field(default_factory=list)

def point_on_segment(seg: WallSegment, t: float) -> Tuple[float, float]:
    return (
        seg.x1 + (seg.x2 - seg.x1) * t,
        seg.y1 + (seg.y2 - seg.y1) * t,
    )

def point_to_t(seg: WallSegment, pt: Tuple[float, float]) -> float:
    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    denom = dx * dx + dy * dy
    if denom == 0:
        return 0.0
    return ((pt[0] - seg.x1) * dx + (pt[1] - seg.y1) * dy) / denom

def interval_free(occupied, wall_id, t0, t1):
    for owid, a, b, _kind in occupied:
        if owid != wall_id:
            continue
        if not (t1 <= a or t0 >= b):
            return False
    return True

def mark_interval(occupied, wall_id, t0, t1, kind):
    occupied.append((wall_id, max(0.0, t0), min(1.0, t1), kind))

def place_door(seg: WallSegment, width: float = 0.9, end_clearance: float = 0.35):
    if seg.exterior or not seg.room_a or not seg.room_b:
        return None
    if seg.length < width + 2 * end_clearance:
        return None

    center_t = 0.5
    cx, cy = point_on_segment(seg, center_t)

    half_t = (width / 2) / seg.length
    clear_t = end_clearance / seg.length
    if center_t - half_t < clear_t or center_t + half_t > 1 - clear_t:
        return None

    dx = seg.x2 - seg.x1
    dy = seg.y2 - seg.y1
    seg_len = seg.length
    ux, uy = dx / seg_len, dy / seg_len

    hinge_t = center_t - half_t
    hx, hy = point_on_segment(seg, hinge_t)

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
    )

def place_windows(seg: WallSegment, room: Optional[str], width_by_room: Optional[dict] = None,
                  end_clearance: float = 0.4):
    if not seg.exterior:
        return []

    default_width = 1.2
    w = width_by_room.get(room, default_width) if width_by_room else default_width
    usable = seg.length - 2 * end_clearance
    if usable < w:
        return []

    n = 2 if usable >= (2 * w + 0.6) else 1
    ts = [0.5] if n == 1 else [1/3, 2/3]

    out = []
    for t in ts:
        cx, cy = point_on_segment(seg, t)
        out.append(Window(seg.wall_id, (cx, cy), w, room))
    return out

def extract_wall_segments(rooms: List[Room]) -> List[WallSegment]:
    walls = []
    edge_to_rooms = {}
    wall_id_counter = 0

    for room in rooms:
        coords = list(room.polygon.exterior.coords)
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]

            if (x1, y1) > (x2, y2):
                x1, y1, x2, y2 = x2, y2, x1, y1

            key = (round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3))
            edge_to_rooms.setdefault(key, []).append(room.id)

    for (x1, y1, x2, y2), room_ids in edge_to_rooms.items():
        walls.append(
            WallSegment(
                wall_id=f"W{wall_id_counter:04d}",
                x1=x1, y1=y1, x2=x2, y2=y2,
                room_a=room_ids[0] if len(room_ids) >= 1 else None,
                room_b=room_ids[1] if len(room_ids) >= 2 else None,
                exterior=(len(room_ids) == 1),
            )
        )
        wall_id_counter += 1

    return walls

def generate_openings(walls: List[WallSegment], width_by_room: Optional[dict] = None):
    doors = []
    windows = []
    occupied = []
    seen_connections = set()

    for seg in sorted(walls, key=lambda w: w.length, reverse=True):
        if not seg.exterior and seg.room_a and seg.room_b:
            key = tuple(sorted((seg.room_a, seg.room_b)))
            if key not in seen_connections:
                d = place_door(seg)
                if d:
                    center_t = point_to_t(seg, d.center)
                    half_t = (d.width / 2) / seg.length
                    if interval_free(occupied, seg.wall_id, center_t - half_t, center_t + half_t):
                        doors.append(d)
                        mark_interval(occupied, seg.wall_id, center_t - half_t, center_t + half_t, "door")
                        seen_connections.add(key)

        if seg.exterior:
            room = seg.room_a or seg.room_b
            for w in place_windows(seg, room, width_by_room=width_by_room):
                center_t = point_to_t(seg, w.center)
                half_t = (w.width / 2) / seg.length
                if interval_free(occupied, seg.wall_id, center_t - half_t, center_t + half_t):
                    windows.append(w)
                    mark_interval(occupied, seg.wall_id, center_t - half_t, center_t + half_t, "window")

    return doors, windows

def generate_floor_plan_with_openings(rooms: List[Room], width_by_room: Optional[dict] = None) -> FloorPlan:
    walls = extract_wall_segments(rooms)
    exterior_walls = [w for w in walls if w.exterior]
    interior_walls = [w for w in walls if not w.exterior]
    doors, windows = generate_openings(walls, width_by_room=width_by_room)
    return FloorPlan(
        rooms=rooms,
        walls=walls,
        doors=doors,
        windows=windows,
        exterior_walls=exterior_walls,
        interior_walls=interior_walls,
    )

def render_floor_plan_svg(plan: FloorPlan, scale: float = 60, margin: float = 40) -> str:
    all_coords = []
    for room in plan.rooms:
        all_coords.extend(list(room.polygon.exterior.coords))
    if not all_coords:
        return "<svg></svg>"

    xs, ys = zip(*all_coords)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = (max_x - min_x) * scale + 2 * margin
    height = (max_y - min_y) * scale + 2 * margin

    def to_svg(x, y):
        return margin + (x - min_x) * scale, margin + (max_y - y) * scale

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<style>',
        '.room{fill:#f5f5f5;stroke:#444;stroke-width:2;}',
        '.label{font-family:Arial,sans-serif;font-size:12px;fill:#444;}',
        '.door{stroke:#1b5e20;stroke-width:2;fill:none;}',
        '.door-arc{stroke:#43a047;stroke-width:1.5;fill:none;stroke-dasharray:4,3;}',
        '.window{fill:#4fc3f7;stroke:#0277bd;stroke-width:2;}',
        '</style>'
    ]

    for room in plan.rooms:
        pts = " ".join(f"{to_svg(x,y)[0]},{to_svg(x,y)[1]}" for x, y in room.polygon.exterior.coords)
        svg.append(f'<polygon class="room" points="{pts}"/>')
        c = room.polygon.centroid
        cx, cy = to_svg(c.x, c.y)
        svg.append(f'<text class="label" x="{cx}" y="{cy}" text-anchor="middle">{room.id}</text>')

    for d in plan.doors:
        if d.hinge_point is None:
            continue
        hx, hy = to_svg(*d.hinge_point)
        wall_angle = math.radians(d.wall_angle)
        leaf_angle = wall_angle + math.pi/2
        leaf_len = d.swing_radius * scale
        ex = hx + leaf_len * math.cos(leaf_angle)
        ey = hy - leaf_len * math.sin(leaf_angle)
        svg.append(f'<line class="door" x1="{hx}" y1="{hy}" x2="{ex}" y2="{ey}"/>')

        arc_pts = []
        steps = 18
        for i in range(steps + 1):
            a = wall_angle + (math.pi/2) * (i / steps)
            ax = hx + leaf_len * math.cos(a)
            ay = hy - leaf_len * math.sin(a)
            arc_pts.append(f"{ax},{ay}")
        svg.append(f'<polyline class="door-arc" points="{" ".join(arc_pts)}"/>')

    for w in plan.windows:
        cx, cy = to_svg(*w.center)
        half = (w.width * scale) / 2
        svg.append(f'<rect class="window" x="{cx-half}" y="{cy-5}" width="{2*half}" height="10" rx="2"/>')
        svg.append(f'<line x1="{cx-half+4}" y1="{cy}" x2="{cx+half-4}" y2="{cy}" stroke="white" stroke-width="1"/>')
        svg.append(f'<line x1="{cx}" y1="{cy-4}" x2="{cx}" y2="{cy+4}" stroke="white" stroke-width="1"/>')

    svg.append("</svg>")
    return "\n".join(svg)

if __name__ == "__main__":
    room1 = Room(
        id="Living",
        polygon=Polygon([(0,0), (5,0), (5,4), (0,4)]),
        room_type="living",
        area=20.0
    )
    room2 = Room(
        id="Kitchen",
        polygon=Polygon([(5,0), (10,0), (10,4), (5,4)]),
        room_type="kitchen",
        area=20.0
    )

    width_by_room = {
        "Living": 1.8,
        "Kitchen": 1.2,
    }

    plan = generate_floor_plan_with_openings([room1, room2], width_by_room=width_by_room)
    print(f"Rooms: {len(plan.rooms)}")
    print(f"Walls: {len(plan.walls)}")
    print(f"Doors: {len(plan.doors)}")
    print(f"Windows: {len(plan.windows)}")

    svg = render_floor_plan_svg(plan)
    with open("floor_plan_v52.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Saved floor_plan_v52.svg")
