"""Validation result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding."""

    code: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __post_init__(self) -> None:
        if self.severity not in {"error", "warning"}:
            raise ValueError(f"severity must be 'error' or 'warning', got {self.severity}")


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate outcome of validating an army list."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """True when there are no error-severity issues."""
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")
