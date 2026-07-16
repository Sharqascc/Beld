from shapely.geometry import Polygon
from beld.validation import validate_plan

class DummyRoom:
    def __init__(self, name, polygon):
        self.name = name
        self.polygon = polygon

class DummyPlan:
    def __init__(self, rooms):
        self.rooms = rooms

def test_validate_plan_accepts_simple_valid_plan():
    plan = DummyPlan([
        DummyRoom("bedroom", Polygon([(0,0),(4,0),(4,3),(0,3)]))
    ])
    report = validate_plan(plan)
    assert report.is_valid()
    assert report.issues == []

def test_validate_plan_flags_empty_plan():
    plan = DummyPlan([])
    report = validate_plan(plan)
    assert not report.is_valid()
    assert any(i.code == "NO_ROOMS" for i in report.issues)

def test_validate_plan_flags_non_positive_area():
    plan = DummyPlan([
        DummyRoom("bad_room", Polygon([(0,0),(1,0),(2,0),(0,0)]))
    ])
    report = validate_plan(plan)
    assert not report.is_valid()
    assert any(i.code == "NON_POSITIVE_ROOM_AREA" for i in report.issues)
