from dataclasses import dataclass, field
from .issues import DesignIssue

@dataclass
class ValidationReport:
    issues: list[DesignIssue] = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.severity == "warning"]

    def add(self, issue: DesignIssue):
        self.issues.append(issue)

    def is_valid(self) -> bool:
        return not self.errors
