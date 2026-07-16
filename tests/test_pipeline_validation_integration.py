from shapely.geometry import Polygon

from beld.models import Room
from beld.pipeline import FloorPlanPipeline


def test_pipeline_attaches_structured_validation_metadata():
    rooms = [
        Room("A", Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]), "living", 16.0),
        Room("B", Polygon([(4, 0), (8, 0), (8, 4), (4, 4)]), "kitchen", 16.0),
    ]

    plan = FloorPlanPipeline(
        width_by_room_type={"living": 2.1, "kitchen": 1.8},
        add_exterior_door=True,
        max_windows_per_wall=2,
        validate=True,
    ).run(rooms)

    assert isinstance(plan.metadata, dict)
    assert "validation_report" in plan.metadata
    assert "design_issues" in plan.metadata
    assert isinstance(plan.metadata["design_issues"], list)
    assert "warnings" in plan.metadata or plan.metadata["design_issues"] == []


def test_pipeline_without_validation_does_not_attach_structured_metadata():
    rooms = [
        Room("A", Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]), "living", 16.0),
        Room("B", Polygon([(4, 0), (8, 0), (8, 4), (4, 4)]), "kitchen", 16.0),
    ]

    plan = FloorPlanPipeline(validate=False).run(rooms)

    assert "validation_report" not in plan.metadata
    assert "design_issues" not in plan.metadata
