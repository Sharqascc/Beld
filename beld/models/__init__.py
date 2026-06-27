"""
beld.models
-----------
Pure data classes for the floor-plan domain.
No geometry logic here — only structured state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from shapely.geometry import Polygon


# ---------------------------------------------------------------------------
# Core spatial primitives
# ---------------------------------------------------------------------------

@dataclass
class Room:
    """A named polygon with a semantic room type and pre-computed area."""
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
    """A single wall edge shared (interior) or owned (exterior) by rooms."""
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
        import math
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def angle(self) -> float:
        import math
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))

    @property
    def midpoint(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def point_at_t(self, t: float) -> Tuple[float, float]:
        """Interpolate position along the wall (0 = start, 1 = end)."""
        return (
            self.x1 + (self.x2 - self.x1) * t,
            self.y1 + (self.y2 - self.y1) * t,
        )


# ---------------------------------------------------------------------------
# Opening types
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Top-level plan container
# ---------------------------------------------------------------------------

@dataclass
class FloorPlan:
    rooms: List[Room]
    walls: List[WallSegment]
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    exterior_walls: List[WallSegment] = field(default_factory=list)
    interior_walls: List[WallSegment] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
