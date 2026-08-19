"""Composable army-list validation rules.

Rules take metadata/configuration. None of them branch on faction or unit names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from grimsim.data.points import PointsCatalog
from grimsim.models.army_list import ArmyList
from grimsim.validation.result import ValidationIssue


class ValidationRule(Protocol):
    def check(self, army_list: ArmyList) -> list[ValidationIssue]: ...


@dataclass(frozen=True)
class RosterConstraints:
    """Data-driven construction limits. Keys are unit identities, not names."""

    max_copies: tuple[tuple[str, int], ...] = ()
    allowed_sizes: tuple[tuple[str, tuple[int, ...]], ...] = ()
    unique_unit_ids: tuple[str, ...] = ()
    unique_enhancements: bool = False

    def max_copies_map(self) -> dict[str, int]:
        return dict(self.max_copies)

    def allowed_sizes_map(self) -> dict[str, tuple[int, ...]]:
        return dict(self.allowed_sizes)


@dataclass(frozen=True)
class DetachmentFactionRule:
    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
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


@dataclass(frozen=True)
class EmptyListRule:
    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        if army_list.selection_count == 0:
            return [
                ValidationIssue(
                    code="EMPTY_ARMY_LIST",
                    message="Army list has no unit selections.",
                )
            ]
        return []


@dataclass(frozen=True)
class PointsLimitRule:
    catalog: PointsCatalog | None = None

    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        if self.catalog is None:
            total = army_list.total_points
            if total > army_list.points_limit:
                return [_over_points_issue(total, army_list.points_limit)]
            return []

        total = 0
        for selection in army_list.selections:
            unit_cost = self.catalog.try_cost_for(
                selection.unit, army_list.ruleset, selection.size
            )
            if unit_cost is None:
                continue
            total += unit_cost * selection.quantity + sum(
                e.points for e in selection.enhancements
            )
        if total > army_list.points_limit:
            return [_over_points_issue(total, army_list.points_limit)]
        return []


def _over_points_issue(total: int, limit: int) -> ValidationIssue:
    over = total - limit
    return ValidationIssue(
        code="OVER_POINTS",
        message=(
            f"Army list is {total} points, exceeding the limit of {limit} (over by {over})."
        ),
    )


@dataclass(frozen=True)
class MissingPointsRule:
    catalog: PointsCatalog

    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for selection in army_list.selections:
            cost = self.catalog.try_cost_for(
                selection.unit, army_list.ruleset, selection.size
            )
            if cost is None:
                issues.append(
                    ValidationIssue(
                        code="MISSING_POINTS",
                        message=(
                            f"No points for unit '{selection.unit.identity}' "
                            f"size {selection.size} under ruleset "
                            f"'{army_list.ruleset.slug}'."
                        ),
                    )
                )
        return issues


@dataclass(frozen=True)
class AllowedSizesRule:
    constraints: RosterConstraints

    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        allowed = self.constraints.allowed_sizes_map()
        if not allowed:
            return []
        issues: list[ValidationIssue] = []
        for selection in army_list.selections:
            sizes = allowed.get(selection.unit.identity)
            if sizes is None:
                continue
            if selection.size not in sizes:
                issues.append(
                    ValidationIssue(
                        code="INVALID_UNIT_SIZE",
                        message=(
                            f"Unit '{selection.unit.identity}' size {selection.size} "
                            f"is not in allowed sizes {sizes}."
                        ),
                    )
                )
        return issues


@dataclass(frozen=True)
class MaxCopiesRule:
    constraints: RosterConstraints

    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        limits = self.constraints.max_copies_map()
        if not limits:
            return []
        counts: dict[str, int] = {}
        for selection in army_list.selections:
            ident = selection.unit.identity
            counts[ident] = counts.get(ident, 0) + selection.quantity
        issues: list[ValidationIssue] = []
        for ident, count in counts.items():
            limit = limits.get(ident)
            if limit is not None and count > limit:
                issues.append(
                    ValidationIssue(
                        code="MAX_COPIES",
                        message=(
                            f"Unit '{ident}' appears {count} times; maximum is {limit}."
                        ),
                    )
                )
        return issues


@dataclass(frozen=True)
class UniqueUnitsRule:
    constraints: RosterConstraints

    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        unique = set(self.constraints.unique_unit_ids)
        if not unique:
            return []
        counts: dict[str, int] = {}
        for selection in army_list.selections:
            ident = selection.unit.identity
            if ident in unique:
                counts[ident] = counts.get(ident, 0) + selection.quantity
        issues: list[ValidationIssue] = []
        for ident, count in counts.items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        code="UNIQUE_UNIT",
                        message=f"Unit '{ident}' is unique but appears {count} times.",
                    )
                )
        return issues


@dataclass(frozen=True)
class EnhancementUniquenessRule:
    """Reject the same enhancement id appearing on more than one selection."""

    def check(self, army_list: ArmyList) -> list[ValidationIssue]:
        seen: dict[str, int] = {}
        for selection in army_list.selections:
            for enhancement in selection.enhancements:
                seen[enhancement.id] = seen.get(enhancement.id, 0) + 1
        issues: list[ValidationIssue] = []
        for eid, count in seen.items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        code="DUPLICATE_ENHANCEMENT",
                        message=f"Enhancement '{eid}' is attached {count} times.",
                    )
                )
        return issues


def default_rules(
    *,
    catalog: PointsCatalog | None = None,
    constraints: RosterConstraints | None = None,
) -> tuple[ValidationRule, ...]:
    rules: list[ValidationRule] = [
        DetachmentFactionRule(),
        EmptyListRule(),
        PointsLimitRule(catalog=catalog),
    ]
    if catalog is not None:
        rules.append(MissingPointsRule(catalog=catalog))
    if constraints is not None:
        rules.append(AllowedSizesRule(constraints=constraints))
        rules.append(MaxCopiesRule(constraints=constraints))
        rules.append(UniqueUnitsRule(constraints=constraints))
        if constraints.unique_enhancements:
            rules.append(EnhancementUniquenessRule())
    return tuple(rules)
