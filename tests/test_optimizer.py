from beld.optimizer import LayoutOptimizer, RoomRect


def test_layout_optimizer_smoke():
    rooms = [
        RoomRect("Living Room", "living", 0, 0, 5, 4),
        RoomRect("Kitchen", "kitchen", 5, 0, 4, 4),
        RoomRect("Dining Room", "dining", 9, 0, 3.5, 4),
        RoomRect("Bedroom 1", "bedroom", 0, 4, 4.5, 4),
        RoomRect("Bathroom", "bathroom", 5, 4, 3, 3),
    ]

    result = LayoutOptimizer(verbose=False).optimize(rooms)

    assert len(result.solver_result.rooms) == 5
    assert result.solver_result.metrics.total_area > 0
    assert result.solver_result.metrics.overlap_area == 0
    assert isinstance(result.summary(), str)
    assert "SolverResult" in result.summary()
