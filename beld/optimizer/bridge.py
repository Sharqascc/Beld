
from __future__ import annotations
from typing import List

from shapely.geometry import Polygon

from beld.models import Room
from .solver import RoomRect


def rects_to_rooms(rects: List[RoomRect]) -> List[Room]:
    """Convert a solved/generated RoomRect layout into Room polygons that
    the rest of the pipeline (walls, openings, export, render) understands.
    """
    rooms: List[Room] = []
    for r in rects:
        poly = Polygon(
            [
                (r.x, r.y),
                (r.x + r.w, r.y),
                (r.x + r.w, r.y + r.h),
                (r.x, r.y + r.h),
            ]
        )
        rooms.append(Room(id=r.name, polygon=poly, room_type=r.room_type, area=poly.area))
    return rooms


def generate_floor_plan(room_program, width_by_room_type, rules=None, iterations=300, seed=None):
    """End-to-end convenience: room program -> generated layout -> full FloorPlan.

    room_program: list of (name, room_type, target_area) tuples.
    width_by_room_type: passed straight through to FloorPlanPipeline.
    Returns (plan, solver_result) so callers can inspect layout quality/notes.
    """
    from .generator import generate_layout
    from beld.pipeline import FloorPlanPipeline

    solver_result = generate_layout(
        room_program, rules=rules, iterations=iterations, seed=seed
    )
    rooms = rects_to_rooms(solver_result.rooms)
    plan = FloorPlanPipeline(width_by_room_type=width_by_room_type).run(rooms)
    return plan, solver_result
