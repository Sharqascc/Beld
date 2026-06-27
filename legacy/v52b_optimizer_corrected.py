"""
v52b_optimizer_corrected.py - Enhanced floor plan with robust opening placement
Patch version with tolerance-based deduplication, exterior doors, and smart windows
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
import math
from shapely.geometry import Polygon, LineString
import numpy as np
import json

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Room:
    id: str
    polygon: Polygon
    room_type: str
    area: float
    
    @property
    def centroid(self) -> Tuple[float, float]:
        c = self.polygon.centroid
        return (c.x, c.y)

@dataclass
class WallSegment:
    wall_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    room_a: Optional[str] = None
    room_b: Optional[str] = None
    room_a_type: Optional[str] = None
    room_b_type: Optional[str] = None
    exterior: bool = False
    thickness: float = 0.15

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))
    
    @property
    def midpoint(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    def point_at_distance(self, distance: float) -> Tuple[float, float]:
        """Get point at given distance from start."""
        t = distance / self.length if self.length > 0 else 0
        return (
            self.x1 + (self.x2 - self.x1) * t,
            self.y1 + (self.y2 - self.y1) * t,
        )

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
    door_type: str = "interior_swing"
    is_exterior: bool = False
    fire_rating: Optional[float] = None

@dataclass
class Window:
    wall_id: str
    center: Tuple[float, float]
    width: float
    room: Optional[str]
    room_type: Optional[str] = None
    sill_height: float = 0.9
    height: float = 1.2
    wall_angle: float = 0.0
    window_type: str = "casement"
    glazing: str = "double_pane"

@dataclass
class FloorPlan:
    rooms: List[Room]
    walls: List[WallSegment]
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    exterior_walls: List[WallSegment] = field(default_factory=list)
    interior_walls: List[WallSegment] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

# ============================================================================
# GEOMETRY HELPERS
# ============================================================================

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

def interval_free(occupied: List, wall_id: str, t0: float, t1: float, margin: float = 0.02) -> bool:
    """Check if interval [t0, t1] is free with margin."""
    for owid, a, b, _kind in occupied:
        if owid != wall_id:
            continue
        if not (t1 + margin <= a or t0 - margin >= b):
            return False
    return True

def mark_interval(occupied: List, wall_id: str, t0: float, t1: float, kind: str):
    occupied.append((wall_id, max(0.0, t0), min(1.0, t1), kind))

def distance_between_points(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

# ============================================================================
# WALL EXTRACTION WITH TOLERANCE-BASED DEDUPLICATION (CORRECTED LOOP)
# ============================================================================

def extract_wall_segments(rooms: List[Room]) -> List[WallSegment]:
    WALLS: List[WallSegment] = []
    SEG_BY_KEY: Dict[Tuple[int, int, int, int], WallSegment] = {}
    
    def match_key(x1: float, y1: float, x2: float, y2: float) -> Tuple[int, int, int, int]:
        GRID = 100  # 100 → 1 cm if coordinates in meters
        i1 = int(round(x1 * GRID))
        j1 = int(round(y1 * GRID))
        i2 = int(round(x2 * GRID))
        j2 = int(round(y2 * GRID))
        if (i1, j1) <= (i2, j2):
            return (i1, j1, i2, j2)
        else:
            return (i2, j2, i1, j1)
    
    def isclose(a: float, b: float, tol: float = 0.01) -> bool:
        return math.isclose(a, b, abs_tol=tol)
    
    for room in rooms:
        poly = room.polygon
        if poly.is_empty or poly.area < 0.01:
            continue
        
        coords = list(poly.exterior.coords[:-1])  # FIX: Use coords[:-1] to avoid closing point
        n = len(coords)
        
        for i in range(n):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]
            
            if isclose(x1, x2) and isclose(y1, y2):
                continue
            
            room_b = None
            room_b_type = None
            edge = LineString([(x1, y1), (x2, y2)])
            
            for other in rooms:
                if other.id == room.id:
                    continue
                if other.polygon.boundary.distance(edge) < 0.01:
                    room_b = other.id
                    room_b_type = other.room_type
                    break
            
            key = match_key(x1, y1, x2, y2)
            
            if key in SEG_BY_KEY:
                continue
            
            exterior = room_b is None
            wall_id = f"W{len(WALLS):04d}"
            
            seg = WallSegment(
                wall_id=wall_id,
                x1=x1, y1=y1, x2=x2, y2=y2,
                room_a=room.id,
                room_b=room_b,
                room_a_type=room.room_type,
                room_b_type=room_b_type,
                exterior=exterior,
                thickness=0.15
            )
            SEG_BY_KEY[key] = seg
            WALLS.append(seg)
    
    WALLS.sort(key=lambda w: w.wall_id)
    return WALLS

# ============================================================================
# ROOM PRIORITY SYSTEM
# ============================================================================

def get_room_priority(room_type: str) -> int:
    priorities = {
        "kitchen": 10, "living": 9, "dining": 8, "entrance": 8,
        "bedroom": 7, "bathroom": 6, "hallway": 5, "closet": 3,
        "storage": 3, "utility": 4, "office": 6, "study": 6,
        "family": 8, "mudroom": 4, "laundry": 4, "pantry": 3,
    }
    return priorities.get(room_type.lower(), 5)

# ============================================================================
# DOOR PLACEMENT
# ============================================================================

def place_door_enhanced(seg: WallSegment, 
                        width: float = 0.9, 
                        end_clearance: float = 0.35,
                        min_wall_length: float = 1.5) -> Optional[Door]:
    if seg.exterior or not seg.room_a or not seg.room_b:
        return None
    
    if seg.length < max(width + 2 * end_clearance, min_wall_length):
        return None

    positions = [0.5, 0.33, 0.67]
    
    for center_t in positions:
        cx, cy = point_on_segment(seg, center_t)
        half_t = (width / 2) / seg.length
        clear_t = end_clearance / seg.length
        
        if center_t - half_t < clear_t or center_t + half_t > 1 - clear_t:
            continue
        
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

def place_door_with_priority(walls: List[WallSegment], 
                           room_map: Dict[str, Room]) -> List[Door]:
    doors = []
    occupied = []
    seen_connections = set()
    
    connections = {}
    for seg in walls:
        if not seg.exterior and seg.room_a and seg.room_b:
            key = tuple(sorted((seg.room_a, seg.room_b)))
            connections.setdefault(key, []).append(seg)
    
    sorted_connections = []
    for (room_a, room_b), segs in connections.items():
        max_priority = max(get_room_priority(room_map[room_a].room_type),
                          get_room_priority(room_map[room_b].room_type))
        sorted_connections.append((max_priority, room_a, room_b, segs))
    
    sorted_connections.sort(key=lambda x: x[0], reverse=True)
    
    for _, room_a, room_b, segs in sorted_connections:
        if (room_a, room_b) in seen_connections or (room_b, room_a) in seen_connections:
            continue
        
        best_seg = max(segs, key=lambda s: s.length)
        d = place_door_enhanced(best_seg)
        
        if d:
            center_t = point_to_t(best_seg, d.center)
            half_t = (d.width / 2) / best_seg.length
            
            if interval_free(occupied, best_seg.wall_id, center_t - half_t, center_t + half_t):
                doors.append(d)
                mark_interval(occupied, best_seg.wall_id, center_t - half_t, center_t + half_t, "door")
                seen_connections.add((room_a, room_b))
    
    return doors

# ============================================================================
# EXTERIOR DOOR PLACEMENT
# ============================================================================

def place_exterior_entry_door(walls: List[WallSegment]) -> Optional[Door]:
    exterior = [w for w in walls if w.exterior and w.length >= 2.0]
    if not exterior:
        return None
    
    best = max(exterior, key=lambda w: w.length)
    cx, cy = best.midpoint
    half_t = (0.9 / 2) / best.length
    hx, hy = point_on_segment(best, 0.5 - half_t)
    
    return Door(
        wall_id=best.wall_id,
        center=(cx, cy),
        width=0.9,
        room_a=best.room_a,
        room_b=None,
        wall_angle=best.angle,
        swing_side="right",
        swing_radius=0.9,
        hinge_point=(hx, hy),
        open_angle_deg=90.0,
        door_type="exterior_swing",
        is_exterior=True,
    )

# ============================================================================
# WINDOW PLACEMENT
# ============================================================================

def place_windows_enhanced(seg: WallSegment, 
                           room_type: Optional[str],
                           width_by_room_type: Optional[Dict[str, float]] = None,
                           end_clearance: float = 0.4,
                           max_windows: int = 2) -> List[Window]:
    if not seg.exterior:
        return []
    
    default_widths = {
        "living": 1.8, "dining": 1.8, "kitchen": 1.5, "bedroom": 1.5,
        "office": 1.5, "study": 1.5, "bathroom": 1.0, "closet": 0.8, "hallway": 1.0
    }
    
    if width_by_room_type:
        w = width_by_room_type.get(room_type, default_widths.get(room_type, 1.2))
    else:
        w = default_widths.get(room_type, 1.2)
    
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
        positions = [0.5]
    else:
        positions = [
            end_clearance / seg.length + ((1 - 2 * (end_clearance / seg.length)) / (n + 1)) * (i + 1)
            for i in range(n)
        ]
    
    room = seg.room_a or seg.room_b
    return [
        Window(seg.wall_id, point_on_segment(seg, t), w, room, room_type, 0.9, 1.2, seg.angle, "casement")
        for t in positions if 0 < t < 1
    ]

# ============================================================================
# VALIDATION
# ============================================================================

def validate_openings(plan: FloorPlan) -> List[str]:
    warnings = []
    
    for door in plan.doors:
        for window in plan.windows:
            if door.wall_id == window.wall_id:
                dist = distance_between_points(door.center, window.center)
                if dist < (door.width + window.width) / 2:
                    warnings.append(f"Door-window conflict on wall {door.wall_id} (distance: {dist:.2f}m)")
    
    for i, door1 in enumerate(plan.doors):
        for door2 in plan.doors[i+1:]:
            if door1.wall_id == door2.wall_id:
                dist = distance_between_points(door1.center, door2.center)
                if dist < (door1.width + door2.width) / 2:
                    warnings.append(f"Door-door conflict on wall {door1.wall_id}")
    
    ext_doors = [d for d in plan.doors if d.is_exterior]
    if not ext_doors and plan.rooms:
        warnings.append("No exterior doors found - building may be inaccessible")
    
    for window in plan.windows:
        if not window.room:
            warnings.append(f"Window on wall {window.wall_id} has no associated room")
    
    return warnings

# ============================================================================
# MAIN GENERATOR
# ============================================================================

def generate_floor_plan_with_openings_enhanced(
    rooms: List[Room],
    width_by_room_type: Optional[Dict[str, float]] = None,
    validate: bool = True
) -> FloorPlan:
    if not rooms:
        raise ValueError("No rooms provided")
    
    walls = extract_wall_segments(rooms)
    exterior_walls = [w for w in walls if w.exterior]
    interior_walls = [w for w in walls if not w.exterior]
    room_map = {r.id: r for r in rooms}
    
    doors = place_door_with_priority(interior_walls, room_map)
    
    occupied = []
    ext_door = place_exterior_entry_door(exterior_walls)
    
    if ext_door:
        doors.append(ext_door)
        for seg in exterior_walls:
            if seg.wall_id == ext_door.wall_id:
                center_t = point_to_t(seg, ext_door.center)
                half_t = (ext_door.width / 2) / seg.length
                mark_interval(occupied, ext_door.wall_id, center_t - half_t, center_t + half_t, "exterior_door")
                break
    
    windows = []
    for seg in exterior_walls:
        room_type = room_map[seg.room_a].room_type if seg.room_a and seg.room_a in room_map else (
            room_map[seg.room_b].room_type if seg.room_b and seg.room_b in room_map else None
        )
        
        for win in place_windows_enhanced(seg, room_type, width_by_room_type):
            center_t = point_to_t(seg, win.center)
            half_t = (win.width / 2) / seg.length
            
            if interval_free(occupied, seg.wall_id, center_t - half_t, center_t + half_t):
                windows.append(win)
                mark_interval(occupied, seg.wall_id, center_t - half_t, center_t + half_t, "window")
    
    plan = FloorPlan(
        rooms, walls, doors, windows,
        exterior_walls, interior_walls,
        {
            "total_rooms": len(rooms),
            "total_walls": len(walls),
            "total_doors": len(doors),
            "total_windows": len(windows),
            "exterior_walls": len(exterior_walls),
            "interior_walls": len(interior_walls),
        }
    )
    
    if validate:
        warnings = validate_openings(plan)
        if warnings:
            plan.metadata["warnings"] = warnings
    
    return plan

# ============================================================================
# SVG RENDERING
# ============================================================================

def render_floor_plan_svg(plan: FloorPlan, scale: float = 60, margin: float = 40) -> str:
    all_coords = []
    for room in plan.rooms:
        all_coords.extend(list(room.polygon.exterior.coords[:-1]))
    
    if not all_coords:
        return "<svg></svg>"
    
    xs, ys = zip(*all_coords)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    pad_x = (max_x - min_x) * 0.1 or 1
    pad_y = (max_y - min_y) * 0.1 or 1
    
    svg_w = (max_x - min_x + 2 * pad_x) * scale + 2 * margin
    svg_h = (max_y - min_y + 2 * pad_y) * scale + 2 * margin

    def to_svg(x, y):
        return margin + (x - min_x + pad_x) * scale, margin + (max_y - y + pad_y) * scale

    def svg_pt(x, y):
        sx, sy = to_svg(x, y)
        return f"{sx},{sy}"

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}">',
        '<style>',
        '.room{fill:#f5f5f5;stroke:#444;stroke-width:2;}',
        '.wall{stroke:#333;stroke-width:3;stroke-linecap:butt;}',
        '.label{font-family:Arial,sans-serif;font-size:12px;fill:#444;text-anchor:middle;}',
        '.label-first{font-size:12px;}',
        '.label-second{font-size:10px;}',
        '.door{stroke:#1b5e20;stroke-width:2;fill:none;}',
        '.door-arc{stroke:#43a047;stroke-width:1.5;fill:none;stroke-dasharray:4,3;}',
        '.window{stroke:#0277bd;stroke-width:2;fill:#4fc3f7;fill-opacity:0.7;}',
        '.exterior-door{stroke:#c62828;stroke-width:2.5;fill:none;}',
        '</style>'
    ]
    
    for room in plan.rooms:
        pts = " ".join(svg_pt(x, y) for x, y in room.polygon.exterior.coords[:-1])
        svg.append(f'<polygon class="room" points="{pts}"/>')
        
        c = room.polygon.centroid
        cx, cy = to_svg(c.x, c.y)
        svg.append(f'<text class="label" x="{cx}" y="{cy}" dy="-4"><tspan class="label-first">{room.id}</tspan><tspan class="label-second" x="{cx}" dy="12">({room.room_type})</tspan></text>')
    
    for wall in plan.walls:
        x1, y1 = to_svg(wall.x1, wall.y1)
        x2, y2 = to_svg(wall.x2, wall.y2)
        stroke = "#1a237e" if wall.exterior else "#333"
        sw = 3.5 if wall.exterior else 2.5
        svg.append(f'<line class="wall" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"/>')
    
    for win in plan.windows:
        cx, cy = to_svg(win.center[0], win.center[1])
        half = (win.width * scale) / 2
        angle_rad = math.radians(win.wall_angle)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        
        corners = [(-half, -4), (half, -4), (half, 4), (-half, 4)]
        rotated = []
        for dx, dy in corners:
            rx = cx + dx * cos_a - dy * sin_a
            ry = cy + dx * sin_a + dy * cos_a
            rotated.append(f"{rx},{ry}")
        
        svg.append(f'<polygon class="window" points="{" ".join(rotated)}"/>')
        
        x1, y1 = cx - half * cos_a, cy - half * sin_a
        x2, y2 = cx + half * cos_a, cy + half * sin_a
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="white" stroke-width="1.5"/>')
        
        x1, y1 = cx + 4 * sin_a, cy - 4 * cos_a
        x2, y2 = cx - 4 * sin_a, cy + 4 * cos_a
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="white" stroke-width="1.5"/>')
    
    for d in plan.doors:
        if d.hinge_point is None:
            continue
        
        hx, hy = to_svg(d.hinge_point[0], d.hinge_point[1])
        wall_angle = math.radians(d.wall_angle)
        leaf_angle = wall_angle + math.pi / 2
        leaf_len = d.swing_radius * scale
        
        ex = hx + leaf_len * math.cos(leaf_angle)
        ey = hy - leaf_len * math.sin(leaf_angle)
        
        cls = "exterior-door" if d.is_exterior else "door"
        svg.append(f'<line class="{cls}" x1="{hx}" y1="{hy}" x2="{ex}" y2="{ey}"/>')
        
        pts = []
        for i in range(19):
            a = wall_angle + (math.pi / 2) * (i / 18)
            ax = hx + leaf_len * math.cos(a)
            ay = hy - leaf_len * math.sin(a)
            pts.append(f"{ax},{ay}")
        
        svg.append(f'<polyline class="door-arc" points="{" ".join(pts)}"/>')
    
    svg.append("</svg>")
    return "
".join(svg)

# ============================================================================
# JSON EXPORT
# ============================================================================

def export_to_json(plan: FloorPlan, filename: str):
    data = {
        "metadata": plan.metadata,
        "rooms": [
            {
                "id": r.id,
                "type": r.room_type,
                "area": round(r.area, 2),
                "centroid": [round(c, 2) for c in r.centroid]
            } for r in plan.rooms
        ],
        "walls": [
            {
                "id": w.wall_id,
                "length": round(w.length, 2),
                "exterior": w.exterior,
                "rooms": [r for r in [w.room_a, w.room_b] if r]
            } for w in plan.walls
        ],
        "doors": [
            {
                "wall_id": d.wall_id,
                "center": [round(c, 2) for c in d.center],
                "width": round(d.width, 2),
                "rooms": [d.room_a, d.room_b],
                "is_exterior": d.is_exterior,
                "door_type": d.door_type
            } for d in plan.doors
        ],
        "windows": [
            {
                "wall_id": w.wall_id,
                "center": [round(c, 2) for c in w.center],
                "width": round(w.width, 2),
                "room": w.room,
                "room_type": w.room_type
            } for w in plan.windows
        ],
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    rooms = [
        Room("Living Room", Polygon([(0, 0), (5, 0), (5, 4), (0, 4)]), "living", 20.0),
        Room("Kitchen", Polygon([(5, 0), (10, 0), (10, 4), (5, 4)]), "kitchen", 20.0),
        Room("Bedroom", Polygon([(10, 0), (15, 0), (15, 4), (10, 4)]), "bedroom", 20.0),
        Room("Bathroom", Polygon([(12, 4), (15, 4), (15, 7), (12, 7)]), "bathroom", 9.0),
        Room("Hallway", Polygon([(7, 0), (12, 0), (12, 4), (7, 4)]), "hallway", 20.0),
    ]
    
    width_by_room_type = {"living": 2.1, "kitchen": 1.8, "bedroom": 1.8, "bathroom": 1.0}
    plan = generate_floor_plan_with_openings_enhanced(rooms, width_by_room_type)
    
    with open("floor_plan_v52b.svg", "w", encoding="utf-8") as f:
        f.write(render_floor_plan_svg(plan))
    
    export_to_json(plan, "floor_plan_v52b.json")
    
    print(f"Rooms: {len(plan.rooms)}")
    print(f"Walls: {len(plan.walls)}")
    print(f"Doors: {len(plan.doors)}")
    print(f"Windows: {len(plan.windows)}")
    print("Saved floor_plan_v52b.svg")
    print("Saved floor_plan_v52b.json")
