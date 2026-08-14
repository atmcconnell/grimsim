"""Extensible army-list validation."""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.army_list import ArmyList


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


class ArmyListValidator:
    """Validates army lists with a small, extensible rule set.

    Future checks (max copies, leaders, transports, etc.) can be added as
    methods invoked from ``validate`` without changing call sites.
    """

    def validate(self, army_list: ArmyList) -> ValidationResult:
        issues: list[ValidationIssue] = []
        issues.extend(self._check_detachment_faction(army_list))
        issues.extend(self._check_empty(army_list))
        issues.extend(self._check_points(army_list))
        issues.extend(self._check_selections(army_list))
        return ValidationResult(issues=tuple(issues))

    def _check_detachment_faction(self, army_list: ArmyList) -> list[ValidationIssue]:
        if army_list.detachment.faction_id != army_list.faction.id:
            return [
                ValidationIssue(
                    code="DETACHMENT_FACTION_MISMATCH",
                    message=(
                        f"Detachment '{army_list.detachment.id}' belongs to faction "
                        f"'{army_list.detachment.faction_id}', but list faction is "
                        f"'{army_list.faction.id}'."
                    ),
                )
            ]
        return []

    def _check_empty(self, army_list: ArmyList) -> list[ValidationIssue]:
        if army_list.selection_count == 0:
            return [
                ValidationIssue(
                    code="EMPTY_ARMY_LIST",
                    message="Army list has no unit selections.",
                )
            ]
        return []

    def _check_points(self, army_list: ArmyList) -> list[ValidationIssue]:
        if army_list.total_points > army_list.points_limit:
            return [
                ValidationIssue(
                    code="OVER_POINTS",
                    message=(
                        f"Army list is {army_list.total_points} points, exceeding "
                        f"the limit of {army_list.points_limit} "
                        f"(over by {-army_list.remaining_points})."
                    ),
                )
            ]
        return []

    def _check_selections(self, army_list: ArmyList) -> list[ValidationIssue]:
        # Construction-time checks on UnitSelection already enforce quantity/points/
        # duplicate enhancements. This hook is reserved for list-level rules.
        _ = army_list
        return []


_DEFAULT_VALIDATOR = ArmyListValidator()


def validate_army_list(
    army_list: ArmyList,
    validator: ArmyListValidator | None = None,
) -> ValidationResult:
    """Validate an army list using the default or provided validator."""
    active = validator if validator is not None else _DEFAULT_VALIDATOR
    return active.validate(army_list)
