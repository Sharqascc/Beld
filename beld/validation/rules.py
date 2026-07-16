from .issues import DesignIssue
from .report import ValidationReport

def validate_plan(plan) -> ValidationReport:
    report = ValidationReport()
    rooms = getattr(plan, "rooms", []) or []

    if not rooms:
        report.add(DesignIssue(
            code="NO_ROOMS",
            severity="error",
            message="Plan contains no rooms.",
            location="plan",
            metrics={}
        ))
        return report

    for room in rooms:
        name = getattr(room, "name", "unknown")
        polygon = getattr(room, "polygon", None)
        area = getattr(polygon, "area", None)

        if area is not None and area <= 0:
            report.add(DesignIssue(
                code="NON_POSITIVE_ROOM_AREA",
                severity="error",
                message=f"Room '{name}' has non-positive area.",
                location=name,
                metrics={"area": area}
            ))

    return report
