from __future__ import annotations
import math

from beld.models import Door, Room, WallSegment, Window


class SVGElementMixin:
# ------------------------------------------------------------------
    # Element renderers
    # ------------------------------------------------------------------

    def _render_style(self) -> str:
        return (
            "<style>"
            f".room{{fill:{self.ROOM_FILL};stroke:{self.ROOM_STROKE};stroke-width:2;}}"
            ".label{font-family:Arial,sans-serif;font-size:12px;text-anchor:middle;"
            f"fill:{self.LABEL_COLOUR};}}"
            ".label-sub{font-size:10px;}"
            f".door{{stroke:{self.DOOR_COLOUR};stroke-width:2;fill:none;}}"
            f".door-arc{{stroke:{self.DOOR_ARC_COLOUR};stroke-width:1.5;fill:none;"
            "stroke-dasharray:4,3;}}"
            f".ext-door{{stroke:{self.EXT_DOOR_COLOUR};stroke-width:2.5;fill:none;}}"
            f".window{{fill:{self.WINDOW_FILL};fill-opacity:0.7;"
            f"stroke:{self.WINDOW_STROKE};stroke-width:2;}}"
            "</style>"
        )

    def _render_room(self, room: Room) -> str:
        pts = " ".join(
            self._pt(x, y) for x, y in room.polygon.exterior.coords[:-1]
        )
        c = room.polygon.centroid
        cx, cy = self._to_svg(c.x, c.y)
        lines = [
            f'<polygon class="room" points="{pts}"/>',
            f'<text class="label" x="{cx:.2f}" y="{cy:.2f}" dy="-4">',
            f'<tspan>{room.id}</tspan>',
            f'<tspan class="label-sub" x="{cx:.2f}" dy="14">({room.room_type})</tspan>',
            "</text>",
        ]
        return "\n".join(lines)

    def _render_wall(self, wall: WallSegment) -> str:
        x1, y1 = self._to_svg(wall.x1, wall.y1)
        x2, y2 = self._to_svg(wall.x2, wall.y2)
        colour = self.EXTERIOR_WALL_COLOUR if wall.exterior else self.INTERIOR_WALL_COLOUR
        sw = 3.5 if wall.exterior else 2.5
        return (
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{colour}" stroke-width="{sw}" stroke-linecap="butt"/>'
        )

    def _render_window(self, win: Window) -> str:
        cx, cy = self._to_svg(win.center[0], win.center[1])
        half = (win.width * self.scale) / 2
        a = math.radians(win.wall_angle)
        cos_a, sin_a = math.cos(a), math.sin(a)

        corners = [(-half, -4), (half, -4), (half, 4), (-half, 4)]
        pts = " ".join(
            f"{cx + dx*cos_a - dy*sin_a:.2f},{cy + dx*sin_a + dy*cos_a:.2f}"
            for dx, dy in corners
        )

        # Cross-hair lines
        lx1 = cx - half * cos_a
        ly1 = cy - half * sin_a
        lx2 = cx + half * cos_a
        ly2 = cy + half * sin_a
        tx1 = cx + 4 * sin_a
        ty1 = cy - 4 * cos_a
        tx2 = cx - 4 * sin_a
        ty2 = cy + 4 * cos_a

        return (
            f'<polygon class="window" points="{pts}"/>'
            f'<line x1="{lx1:.2f}" y1="{ly1:.2f}" x2="{lx2:.2f}" y2="{ly2:.2f}" '
            'stroke="white" stroke-width="1.5"/>'
            f'<line x1="{tx1:.2f}" y1="{ty1:.2f}" x2="{tx2:.2f}" y2="{ty2:.2f}" '
            'stroke="white" stroke-width="1.5"/>'
        )

    def _render_door(self, door: Door) -> str:
        if door.hinge_point is None:
            return ""

        hx, hy = self._to_svg(*door.hinge_point)
        wall_a = math.radians(door.wall_angle)
        leaf_a = wall_a + math.pi / 2
        leaf_len = door.swing_radius * self.scale

        ex = hx + leaf_len * math.cos(leaf_a)
        ey = hy - leaf_len * math.sin(leaf_a)

        cls = "ext-door" if door.is_exterior else "door"
        arc_pts = " ".join(
            f"{hx + leaf_len * math.cos(wall_a + (math.pi/2)*(i/18)):.2f},"
            f"{hy - leaf_len * math.sin(wall_a + (math.pi/2)*(i/18)):.2f}"
            for i in range(19)
        )

        return (
            f'<line class="{cls}" x1="{hx:.2f}" y1="{hy:.2f}" '
            f'x2="{ex:.2f}" y2="{ey:.2f}"/>'
            f'<polyline class="door-arc" points="{arc_pts}"/>'
        )

    
