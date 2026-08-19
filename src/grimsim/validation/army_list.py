"""Extensible army-list validation."""

from __future__ import annotations

from grimsim.data.points import PointsCatalog
from grimsim.models.army_list import ArmyList
from grimsim.validation.result import ValidationIssue, ValidationResult
from grimsim.validation.rules import RosterConstraints, ValidationRule, default_rules

__all__ = [
    "ArmyListValidator",
    "RosterConstraints",
    "ValidationIssue",
    "ValidationResult",
    "validate_army_list",
]


class ArmyListValidator:
    """Validates army lists with a small, composable rule set.

    Pass ``catalog`` and/or ``constraints`` for version-aware points and
    data-driven construction limits. Custom ``rules`` replace the defaults.
    """

    def __init__(
        self,
        rules: tuple[ValidationRule, ...] | None = None,
        *,
        catalog: PointsCatalog | None = None,
        constraints: RosterConstraints | None = None,
    ) -> None:
        self._catalog = catalog
        self._constraints = constraints
        self._rules = (
            rules
            if rules is not None
            else default_rules(catalog=catalog, constraints=constraints)
        )

    def validate(self, army_list: ArmyList) -> ValidationResult:
        issues: list[ValidationIssue] = []
        for rule in self._rules:
            issues.extend(rule.check(army_list))
        return ValidationResult(issues=tuple(issues))


_DEFAULT_VALIDATOR = ArmyListValidator()


def validate_army_list(
    army_list: ArmyList,
    validator: ArmyListValidator | None = None,
    *,
    catalog: PointsCatalog | None = None,
    constraints: RosterConstraints | None = None,
) -> ValidationResult:
    """Validate an army list using the default or provided validator."""
    if validator is not None:
        return validator.validate(army_list)
    if catalog is not None or constraints is not None:
        return ArmyListValidator(catalog=catalog, constraints=constraints).validate(
            army_list
        )
    return _DEFAULT_VALIDATOR.validate(army_list)
