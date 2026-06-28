from __future__ import annotations
import json
from pathlib import Path
from typing import Union

from beld.models import FloorPlan


def floorplan_to_dict(plan: FloorPlan) -> dict:
    """Convert a FloorPlan into a structured Python dict."""
    return {
        "metadata": plan.metadata,
        "rooms": [
            {
                "id": r.id,
                "type": r.room_type,
                "area": round(r.area, 2),
                "centroid": [round(c, 2) for c in r.centroid],
            }
            for r in plan.rooms
        ],
        "walls": [
            {
                "id": w.wall_id,
                "length": round(w.length, 2),
                "exterior": w.exterior,
                "rooms": [r for r in [w.room_a, w.room_b] if r],
            }
            for w in plan.walls
        ],
        "doors": [
            {
                "wall_id": d.wall_id,
                "center": [round(c, 2) for c in d.center],
                "width": round(d.width, 2),
                "rooms": [r for r in [d.room_a, d.room_b] if r],
                "is_exterior": d.is_exterior,
                "door_type": d.door_type,
            }
            for d in plan.doors
        ],
        "windows": [
            {
                "wall_id": w.wall_id,
                "center": [round(c, 2) for c in w.center],
                "width": round(w.width, 2),
                "room": w.room,
                "room_type": w.room_type,
                "sill_height": w.sill_height,
                "glazing": w.glazing,
            }
            for w in plan.windows
        ],
    }


def export_json(plan: FloorPlan, path: Union[str, Path]) -> None:
    """Serialise plan to a structured JSON file."""
    data = floorplan_to_dict(plan)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
