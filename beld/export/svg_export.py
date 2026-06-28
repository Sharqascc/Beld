from __future__ import annotations
from pathlib import Path
from typing import Optional, Union

from beld.models import FloorPlan
from beld.rendering import SVGRenderer


def export_svg(
    plan: FloorPlan,
    path: Union[str, Path],
    renderer: Optional[SVGRenderer] = None,
) -> None:
    """Render plan to SVG file. Uses default SVGRenderer if none supplied."""
    r = renderer or SVGRenderer()
    Path(path).write_text(r.render(plan), encoding="utf-8")
