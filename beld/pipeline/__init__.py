"""
beld.pipeline
-------------
High-level orchestrator that wires all modules together.

This is the primary public API for generating a FloorPlan.

Typical usage
-------------
    from beld.pipeline import FloorPlanPipeline
    from beld.models import Room
    from shapely.geometry import Polygon

    rooms = [
        Room("R1", Polygon([(0,0),(5,0),(5,4),(0,4)]), "living", 20.0),
        Room("R2", Polygon([(5,0),(10,0),(10,4),(5,4)]), "kitchen", 20.0),
    ]

    plan = FloorPlanPipeline(
        width_by_room_type={"living": 2.1, "kitchen": 1.8}
    ).run(rooms)

Extension points
----------------
Subclass FloorPlanPipeline and override individual hook methods:

    class MyPipeline(FloorPlanPipeline):
        def post_validate(self, plan):
            # custom post-processing
            return plan
"""

from __future__ import annotations
from typing import Dict, List, Optional

from beld.models import FloorPlan, Room
from beld.openings import OpeningPlacer
from beld.validation import attach_warnings
from beld.walls import extract_wall_segments, split_walls


class FloorPlanPipeline:
    """
    Orchestrates the full floor-plan generation pipeline.

    Stages (in order)
    -----------------
    1. extract_walls   — build WallSegment graph from room polygons
    2. split_walls     — partition into exterior / interior lists
    3. place_openings  — run OpeningPlacer for doors and windows
    4. assemble        — build FloorPlan with metadata
    5. validate        — attach warnings to metadata

    Parameters
    ----------
    door_width : float
        Standard interior door width in metres.
    exterior_door_width : float
        Exterior entry door width in metres.
    width_by_room_type : dict, optional
        Window width overrides keyed by room type string.
    add_exterior_door : bool
        Whether to add one exterior entry door.
    max_windows_per_wall : int
        Maximum windows placed on a single exterior wall.
    validate : bool
        Whether to run validation and attach warnings.
    """

    def __init__(
        self,
        door_width: float = 0.9,
        exterior_door_width: float = 0.9,
        width_by_room_type: Optional[Dict[str, float]] = None,
        add_exterior_door: bool = True,
        max_windows_per_wall: int = 2,
        validate: bool = True,
    ):
        self.door_width = door_width
        self.exterior_door_width = exterior_door_width
        self.width_by_room_type = width_by_room_type or {}
        self.add_exterior_door = add_exterior_door
        self.max_windows_per_wall = max_windows_per_wall
        self.validate = validate

    # ------------------------------------------------------------------
    # Pipeline stages (override in subclasses to customise behaviour)
    # ------------------------------------------------------------------

    def extract_walls(self, rooms: List[Room]):
        return extract_wall_segments(rooms)

    def make_placer(self) -> OpeningPlacer:
        return OpeningPlacer(
            door_width=self.door_width,
            exterior_door_width=self.exterior_door_width,
            width_by_room_type=self.width_by_room_type,
            add_exterior_door=self.add_exterior_door,
            max_windows_per_wall=self.max_windows_per_wall,
        )

    def assemble(self, rooms, walls, exterior_walls, interior_walls, doors, windows) -> FloorPlan:
        return FloorPlan(
            rooms=rooms,
            walls=walls,
            doors=doors,
            windows=windows,
            exterior_walls=exterior_walls,
            interior_walls=interior_walls,
            metadata={
                "total_rooms": len(rooms),
                "total_walls": len(walls),
                "total_doors": len(doors),
                "total_windows": len(windows),
                "exterior_walls": len(exterior_walls),
                "interior_walls": len(interior_walls),
            },
        )

    def post_validate(self, plan: FloorPlan) -> FloorPlan:
        if self.validate:
            attach_warnings(plan)
        return plan

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, rooms: List[Room]) -> FloorPlan:
        """
        Execute the full pipeline and return a populated FloorPlan.

        Parameters
        ----------
        rooms : list of Room
            The spatial layout to process.

        Returns
        -------
        FloorPlan
        """
        if not rooms:
            raise ValueError("FloorPlanPipeline.run() requires at least one Room.")

        # Stage 1 & 2 — walls
        walls = self.extract_walls(rooms)
        exterior_walls, interior_walls = split_walls(walls)

        # Stage 3 — openings
        room_map = {r.id: r for r in rooms}
        placer = self.make_placer()
        doors, windows = placer.place(exterior_walls, interior_walls, room_map)

        # Stage 4 — assemble
        plan = self.assemble(rooms, walls, exterior_walls, interior_walls, doors, windows)

        # Stage 5 — validate
        plan = self.post_validate(plan)

        return plan
