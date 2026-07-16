from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class DesignIssue:
    code: str
    severity: str
    message: str
    location: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
