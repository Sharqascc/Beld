"""
beld.export
-----------
Serialisers for FloorPlan objects.

Currently supported
~~~~~~~~~~~~~~~~~~~
* JSON  — export_json(plan, path)
* SVG   — export_svg(plan, path, renderer=None)

Add new formats here (DXF, GeoJSON, IFC, …) without touching other modules.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Union

from beld.models import FloorPlan
from beld.rendering import SVGRenderer


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def export_json(plan: FloorPlan, path: Union[str, Path]) -> None:
    """Serialise plan to a structured JSON file."""
    data = {
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
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

def export_svg(
    plan: FloorPlan,
    path: Union[str, Path],
    renderer: Optional[SVGRenderer] = None,
) -> None:
    """Render plan to SVG file. Uses default SVGRenderer if none supplied."""
    r = renderer or SVGRenderer()
    Path(path).write_text(r.render(plan), encoding="utf-8")
