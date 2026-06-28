from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from .solver import RoomRect, SolverResult, LayoutSolver
from .ai_refiner import AIRefiner, AIRefinementResult


@dataclass
class OptimizationResult:
    solver_result: SolverResult
    ai_result: AIRefinementResult

    def summary(self) -> str:
        base = self.solver_result.summary()
        lines = [
            base,
            "",
            "AIRefinement",
            f"- enabled: {self.ai_result.enabled}",
            f"- applied: {self.ai_result.applied}",
            f"- critique: {self.ai_result.critique}",
        ]
        if self.ai_result.suggestions:
            lines.append("- suggestions:")
            lines.extend([f"  - {s}" for s in self.ai_result.suggestions])
        return "\n".join(lines)


class LayoutOptimizer:
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        self.solver = LayoutSolver(verbose=verbose)
        self.refiner = AIRefiner(api_key=api_key)
        self.verbose = verbose

    def optimize(self, rooms: List[RoomRect]) -> OptimizationResult:
        solver_result = self.solver.optimize(rooms)
        ai_result = self.refiner.refine(solver_result)
        return OptimizationResult(solver_result=solver_result, ai_result=ai_result)
