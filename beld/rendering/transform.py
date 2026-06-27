from __future__ import annotations
from typing import Tuple

from beld.models import FloorPlan


class SVGTransformMixin:
# ------------------------------------------------------------------
    # Coordinate transform
    # ------------------------------------------------------------------

    def _setup_transform(self, plan: FloorPlan):
        all_coords = []
        for room in plan.rooms:
            all_coords.extend(list(room.polygon.exterior.coords[:-1]))
        if not all_coords:
            return None

        xs, ys = zip(*all_coords)
        self._min_x, self._max_x = min(xs), max(xs)
        self._min_y, self._max_y = min(ys), max(ys)

        pad_x = (self._max_x - self._min_x) * 0.1 or 1
        pad_y = (self._max_y - self._min_y) * 0.1 or 1
        self._pad_x, self._pad_y = pad_x, pad_y

        s = self.scale
        m = self.margin
        self._svg_w = (self._max_x - self._min_x + 2 * pad_x) * s + 2 * m
        self._svg_h = (self._max_y - self._min_y + 2 * pad_y) * s + 2 * m
        return True

    def _to_svg(self, x: float, y: float) -> Tuple[float, float]:
        s, m = self.scale, self.margin
        sx = m + (x - self._min_x + self._pad_x) * s
        sy = m + (self._max_y - y + self._pad_y) * s
        return sx, sy

    def _pt(self, x: float, y: float) -> str:
        sx, sy = self._to_svg(x, y)
        return f"{sx:.2f},{sy:.2f}"

    
