from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .solver import SolverResult


@dataclass
class AIRefinementResult:
    enabled: bool
    applied: bool
    critique: str = ""
    suggestions: List[str] = field(default_factory=list)


class AIRefiner:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "claude"):
        self.api_key = api_key
        self.model_name = model_name

    def refine(self, solver_result: SolverResult) -> AIRefinementResult:
        suggestions = []

        if solver_result.metrics.overlap_area > 0:
            suggestions.append("Resolve overlapping rectangles before converting layout to walls.")
        if solver_result.metrics.adjacency_score < 0.7:
            suggestions.append("Increase shared edges for kitchen-dining and living-dining relationships.")
        if solver_result.metrics.compactness_score < 0.7:
            suggestions.append("Reduce unused bounding-box area by tightening room clusters.")

        if not self.api_key:
            return AIRefinementResult(
                enabled=False,
                applied=False,
                critique="AI refinement disabled: no API key provided.",
                suggestions=suggestions,
            )

        return AIRefinementResult(
            enabled=True,
            applied=False,
            critique="AI hook enabled, but live remote refinement is intentionally stubbed in this local version.",
            suggestions=suggestions,
        )
