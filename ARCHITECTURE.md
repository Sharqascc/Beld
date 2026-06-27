# Beld — Modular Floor Plan Framework (v53)

## Package layout

```
beld/
├── __init__.py          # version + docstring
├── models/              # data classes only — no logic
│   └── __init__.py      # Room, WallSegment, Door, Window, FloorPlan
├── geometry/            # pure math helpers
│   └── __init__.py      # point_on_segment, interval_free, canonical_wall_key …
├── walls/               # wall graph construction
│   └── __init__.py      # extract_wall_segments, split_walls
├── openings/            # door & window placement strategies
│   └── __init__.py      # OpeningPlacer, place_interior_doors, place_exterior_door …
├── validation/          # read-only post-generation checks
│   └── __init__.py      # validate_openings, attach_warnings
├── rendering/           # SVG output
│   └── __init__.py      # SVGRenderer
└── export/              # serialisation
    └── __init__.py      # export_json, export_svg
pipeline/
└── __init__.py          # FloorPlanPipeline (orchestrator)
```

## Quick start

```python
from shapely.geometry import Polygon
from beld.models import Room
from beld.pipeline import FloorPlanPipeline
from beld.export import export_svg, export_json

rooms = [
    Room("Living", Polygon([(0,0),(5,0),(5,4),(0,4)]), "living", 20.0),
    Room("Kitchen", Polygon([(5,0),(10,0),(10,4),(5,4)]), "kitchen", 20.0),
]

plan = FloorPlanPipeline(
    width_by_room_type={"living": 2.1, "kitchen": 1.8}
).run(rooms)

export_svg(plan, "out.svg")
export_json(plan, "out.json")
```

## Extension points

### Custom opening strategy

```python
from beld.openings import OpeningPlacer

class MyPlacer(OpeningPlacer):
    def place(self, exterior_walls, interior_walls, room_map):
        doors, windows = super().place(exterior_walls, interior_walls, room_map)
        # apply custom rules here
        return doors, windows
```

### Custom pipeline stage

```python
from beld.pipeline import FloorPlanPipeline

class MyPipeline(FloorPlanPipeline):
    def post_validate(self, plan):
        plan = super().post_validate(plan)
        # e.g. log to a database
        return plan
```

### Custom renderer

```python
from beld.rendering import SVGRenderer

class DarkSVGRenderer(SVGRenderer):
    ROOM_FILL = "#1a1a2e"
    ROOM_STROKE = "#e0e0e0"
    EXTERIOR_WALL_COLOUR = "#4fc3f7"
```

### Add a new export format

Add a function to `beld/export/__init__.py`:

```python
def export_dxf(plan: FloorPlan, path) -> None:
    ...  # implement DXF writer
```

## Module responsibilities (single-responsibility summary)

| Module        | What it does                                  | What it does NOT do               |
|---------------|-----------------------------------------------|-----------------------------------|
| `models`      | Define data structures                        | Any computation or I/O            |
| `geometry`    | Pure coordinate math                          | Domain/room concepts              |
| `walls`       | Build wall graph from polygons                | Place doors or windows            |
| `openings`    | Place doors and windows on walls              | Build walls or render             |
| `validation`  | Check plan for conflicts                      | Mutate the plan                   |
| `rendering`   | Convert plan → SVG string                     | Write files                       |
| `export`      | Write files (SVG, JSON, …)                    | Generate content                  |
| `pipeline`    | Wire stages together in order                 | Implement any individual stage    |
