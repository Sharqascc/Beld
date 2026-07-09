from shapely.geometry import Polygon

from beld.models import Room, FloorPlan, WallSegment
from beld.validation import validate_wall_coverage
from beld.walls import extract_wall_segments


def test_wall_extraction_splits_multi_neighbor_edge():
    rooms = [
        Room("A", Polygon([(0,0), (6,0), (6,4), (0,4)]), "living", 24.0),
        Room("B", Polygon([(6,0), (8,0), (8,2), (6,2)]), "kitchen", 4.0),
        Room("C", Polygon([(6,2), (8,2), (8,4), (6,4)]), "bedroom", 4.0),
    ]
    walls = extract_wall_segments(rooms)

    shared = [w for w in walls if (not w.exterior) and getattr(w, "room_a", getattr(w, "rooma", None)) == "A"]
    assert len(shared) == 2
    assert sorted(getattr(w, "room_b", getattr(w, "roomb", None)) for w in shared) == ["B", "C"]


def test_wall_coverage_passes_for_extracted_walls():
    rooms = [
        Room("A", Polygon([(0,0), (4,0), (4,4), (0,4)]), "living", 16.0),
        Room("B", Polygon([(4,0), (8,0), (8,4), (4,4)]), "kitchen", 16.0),
    ]
    walls = extract_wall_segments(rooms)
    plan = FloorPlan(
        rooms=rooms,
        walls=walls,
        doors=[],
        windows=[],
        exterior_walls=[w for w in walls if w.exterior],
        interior_walls=[w for w in walls if not w.exterior],
        metadata={},
    )
    warnings = validate_wall_coverage(plan)
    assert warnings == []


def test_wall_coverage_flags_missing_segment():
    rooms = [
        Room("A", Polygon([(0,0), (4,0), (4,4), (0,4)]), "living", 16.0),
    ]
    walls = [
        WallSegment(wall_id="W1", x1=0, y1=0, x2=4, y2=0, room_a="A", exterior=True),
        WallSegment(wall_id="W2", x1=4, y1=0, x2=4, y2=4, room_a="A", exterior=True),
        WallSegment(wall_id="W3", x1=4, y1=4, x2=0, y2=4, room_a="A", exterior=True),
    ]
    plan = FloorPlan(
        rooms=rooms,
        walls=walls,
        doors=[],
        windows=[],
        exterior_walls=walls,
        interior_walls=[],
        metadata={},
    )
    warnings = validate_wall_coverage(plan)
    assert any("Wall coverage gap" in w for w in warnings)
