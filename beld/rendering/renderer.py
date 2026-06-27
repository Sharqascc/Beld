"""
beld.rendering
--------------
SVG renderer for FloorPlan objects.

Usage
-----
    from beld.rendering import SVGRenderer
    svg_str = SVGRenderer(scale=60, margin=40).render(plan)
"""

from __future__ import annotations

from beld.models import FloorPlan
from .transform import SVGTransformMixin
from .svg_elements import SVGElementMixin


class SVGRenderer(SVGTransformMixin, SVGElementMixin):
    """
    Converts a FloorPlan into an SVG string.

    Parameters
    ----------
    scale : float
        Pixels per metre (default 60).
    margin : float
        Pixel padding around the drawing (default 40).
    """

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

# ------------------------------------------------------------------
    # Public render method
    # ------------------------------------------------------------------

    def render(self, plan: FloorPlan) -> str:
        if not self._setup_transform(plan):
            return "<svg></svg>"

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self._svg_w:.2f}" height="{self._svg_h:.2f}">',
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
        return "\n".join(lines)

