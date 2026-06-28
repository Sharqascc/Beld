import math
import pytest

from beld.geometry import (
    point_on_segment,
    point_to_t,
    distance,
    isclose,
    interval_free,
    mark_interval,
    canonical_wall_key,
)
from beld.models import WallSegment


def make_seg():
    return WallSegment(
        wall_id="w1",
        room_a="A",
        room_b=None,
        x1=0.0,
        y1=0.0,
        x2=10.0,
        y2=0.0,
        orientation="horizontal",
        is_exterior=True,
    )


def test_point_on_segment_midpoint():
    seg = make_seg()
    assert point_on_segment(seg, 0.5) == (5.0, 0.0)


@pytest.mark.parametrize(
    "pt, expected_t",
    [
        ((0.0, 0.0), 0.0),
        ((5.0, 0.0), 0.5),
        ((10.0, 0.0), 1.0),
    ],
)
def test_point_to_t_basic(pt, expected_t):
    seg = make_seg()
    assert point_to_t(seg, pt) == pytest.approx(expected_t)


def test_point_to_t_zero_length_segment():
    seg = WallSegment(
        wall_id="w0",
        room_a="A",
        room_b=None,
        x1=1.0,
        y1=1.0,
        x2=1.0,
        y2=1.0,
        orientation="point",
        is_exterior=False,
    )
    assert point_to_t(seg, (5.0, 5.0)) == 0.0


def test_distance():
    assert distance((0.0, 0.0), (3.0, 4.0)) == 5.0


def test_isclose_default_tolerance():
    assert isclose(1.000, 1.009)
    assert not isclose(1.000, 1.020)


def test_mark_interval_clamps_to_unit_range():
    occupied = []
    mark_interval(occupied, "w1", -0.2, 1.3, "door")
    assert occupied == [("w1", 0.0, 1.0, "door")]


def test_interval_free_detects_overlap_same_wall():
    occupied = [("w1", 0.20, 0.40, "door")]
    assert not interval_free(occupied, "w1", 0.30, 0.50)


def test_interval_free_allows_different_wall():
    occupied = [("w1", 0.20, 0.40, "door")]
    assert interval_free(occupied, "w2", 0.30, 0.50)


def test_interval_free_respects_margin():
    occupied = [("w1", 0.20, 0.40, "door")]
    assert not interval_free(occupied, "w1", 0.41, 0.50, margin=0.02)
    assert interval_free(occupied, "w1", 0.43, 0.50, margin=0.02)


def test_canonical_wall_key_is_order_independent():
    a = canonical_wall_key(0.0, 0.0, 1.0, 1.0)
    b = canonical_wall_key(1.0, 1.0, 0.0, 0.0)
    assert a == b


def test_canonical_wall_key_rounds_to_grid():
    key = canonical_wall_key(0.001, 0.001, 1.004, 1.004, grid=100)
    assert key == (0, 0, 100, 100)
