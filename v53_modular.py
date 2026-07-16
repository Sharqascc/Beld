"""
v53_modular.py
--------------
Drop-in replacement for v52b_optimizer_corrected.py using the new
modular beld package.

Run
---
    python v53_modular.py

Outputs
-------
    floor_plan_v53.svg
    floor_plan_v53.json
"""

from shapely.geometry import Polygon

from beld.models import Room
from beld.pipeline import FloorPlanPipeline
from beld.rendering import SVGRenderer
from beld.export import export_svg, export_json

def main():
    # ---------------------------------------------------------------
    # 1.  Define rooms
    # ---------------------------------------------------------------
    rooms = [
        Room("Living Room",  Polygon([(0,0),  (5,0),  (5,4),  (0,4)]),  "living",  20.0),
        Room("Kitchen",      Polygon([(5,0),  (10,0), (10,4), (5,4)]),  "kitchen", 20.0),
        Room("Bedroom",      Polygon([(10,0), (15,0), (15,4), (10,4)]), "bedroom", 20.0),
        Room("Bathroom",     Polygon([(12,4), (15,4), (15,7), (12,7)]), "bathroom", 9.0),
        Room("Hallway",      Polygon([(7,0),  (12,0), (12,4), (7,4)]),  "hallway", 20.0),
    ]

    # ---------------------------------------------------------------
    # 2.  Configure and run the pipeline
    # ---------------------------------------------------------------
    plan = FloorPlanPipeline(
        width_by_room_type={"living": 2.1, "kitchen": 1.8, "bedroom": 1.8, "bathroom": 1.0},
        add_exterior_door=True,
        max_windows_per_wall=2,
        validate=True,
    ).run(rooms)

    # ---------------------------------------------------------------
    # 3.  Export
    # ---------------------------------------------------------------
    export_svg(plan, "floor_plan_v53.svg", renderer=SVGRenderer(scale=60, margin=40))
    export_json(plan, "floor_plan_v53.json")

    # ---------------------------------------------------------------
    # 4.  Summary
    # ---------------------------------------------------------------
    print(f"Rooms    : {len(plan.rooms)}")
    print(f"Walls    : {len(plan.walls)}")
    print(f"Doors    : {len(plan.doors)}")
    print(f"Windows  : {len(plan.windows)}")

    issues = plan.metadata.get("design_issues", [])
    if issues:
        print(f"\nStructured issues: {len(issues)}")
        for issue in issues:
            severity = issue.get("severity", "unknown") if isinstance(issue, dict) else getattr(issue, "severity", "unknown")
            code = issue.get("code", "UNKNOWN") if isinstance(issue, dict) else getattr(issue, "code", "UNKNOWN")
            message = issue.get("message", "") if isinstance(issue, dict) else getattr(issue, "message", "")
            print(f"  [{severity}] {code}: {message}")
    else:
        print("\nNo structured validation issues.")

    warnings = plan.metadata.get("warnings", [])
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  ⚠  {w}")
    else:
        print("\nNo validation warnings.")

    print("\nSaved: floor_plan_v53.svg")
    print("Saved: floor_plan_v53.json")


if __name__ == "__main__":
    main()
