"""
beld.rendering
--------------
SVG renderer for FloorPlan objects.
"""

from __future__ import annotations

from collections import defaultdict

from beld.models import FloorPlan
from beld.geometry import point_to_t
from .transform import SVGTransformMixin
from .svg_elements import SVGElementMixin


class SVGRenderer(SVGTransformMixin, SVGElementMixin):
    EXTERIOR_WALL_COLOUR = "#1a237e"
    INTERIOR_WALL_COLOUR = "#333333"
    ROOM_FILL = "#f5f5f5"
    ROOM_STROKE = "#444444"
    DOOR_COLOUR = "#1b5e20"
    DOOR_ARC_COLOUR = "#43a047"
    EXT_DOOR_COLOUR = "#c62828"
    WINDOW_FILL = "#4fc3f7"
    WINDOW_STROKE = "#0277bd"
    LABEL_COLOUR = "#444444"

    def __init__(self, scale: float = 60, margin: float = 40):
        self.scale = scale
        self.margin = margin

    def _opening_intervals_by_wall(self, plan: FloorPlan):
        gaps = defaultdict(list)

        for door in plan.doors:
            wall = next((w for w in plan.walls if w.wall_id == door.wall_id), None)
            if wall and wall.length > 0:
                ct = point_to_t(wall, door.center)
                ht = (door.width / 2) / wall.length
                gaps[wall.wall_id].append((max(0.0, ct - ht), min(1.0, ct + ht)))

        for win in plan.windows:
            wall = next((w for w in plan.walls if w.wall_id == win.wall_id), None)
            if wall and wall.length > 0:
                ct = point_to_t(wall, win.center)
                ht = (win.width / 2) / wall.length
                gaps[wall.wall_id].append((max(0.0, ct - ht), min(1.0, ct + ht)))

        merged = {}
        for wall_id, intervals in gaps.items():
            intervals = sorted(intervals)
            out = []
            for a, b in intervals:
                if not out or a > out[-1][1] + 1e-6:
                    out.append([a, b])
                else:
                    out[-1][1] = max(out[-1][1], b)
            merged[wall_id] = [(a, b) for a, b in out]
        return merged

    def render(self, plan: FloorPlan) -> str:
        if not self._setup_transform(plan):
            return "<svg></svg>"

        self._wall_gaps = self._opening_intervals_by_wall(plan)

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self._svg_w:.2f}" height="{self._svg_h:.2f}">',
            self._render_style(),
        ]

        for room in plan.rooms:
            lines.append(self._render_room(room))
        for wall in plan.walls:
            lines.append(self._render_wall(wall))
        for win in plan.windows:
            lines.append(self._render_window(win))
        for door in plan.doors:
            lines.append(self._render_door(door))

        lines.append("</svg>")
        return "".join(lines)
