"""Independent tests for composable army-list validation rules."""

from __future__ import annotations

from datetime import date

from grimsim.data.points import PointsCatalog, PointsEntry
from grimsim.examples import melee_attacker
from grimsim.models.army_list import ArmyList
from grimsim.models.detachment import Detachment
from grimsim.models.enhancement import Enhancement
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection
from grimsim.validation import RosterConstraints, validate_army_list
from grimsim.validation.rules import (
    AllowedSizesRule,
    EnhancementUniquenessRule,
    MaxCopiesRule,
    MissingPointsRule,
    UniqueUnitsRule,
)


def _ruleset() -> Ruleset:
    return Ruleset(
        id="v",
        edition="10th",
        rules_version="0.3.0",
        points_version="x",
        effective_date=date(2025, 1, 1),
    )


def _list(*selections: UnitSelection, limit: int = 2000) -> ArmyList:
    return ArmyList(
        name="T",
        faction=Faction(id="crimson_hosts", name="Crimson Hosts"),
        detachment=Detachment(id="blood_tide", name="Blood Tide", faction_id="crimson_hosts"),
        ruleset=_ruleset(),
        selections=selections,
        points_limit=limit,
    )


def test_allowed_sizes_independent() -> None:
    army = _list(UnitSelection(unit=melee_attacker(), points=180, model_count=7))
    constraints = RosterConstraints(allowed_sizes=(("example-berserkers", (5, 10)),))
    issues = AllowedSizesRule(constraints).check(army)
    assert any(i.code == "INVALID_UNIT_SIZE" for i in issues)


def test_max_copies_independent() -> None:
    army = _list(UnitSelection(unit=melee_attacker(), quantity=3, points=180))
    constraints = RosterConstraints(max_copies=(("example-berserkers", 2),))
    issues = MaxCopiesRule(constraints).check(army)
    assert any(i.code == "MAX_COPIES" for i in issues)


def test_unique_units_independent() -> None:
    army = _list(UnitSelection(unit=melee_attacker(), quantity=2, points=180))
    constraints = RosterConstraints(unique_unit_ids=("example-berserkers",))
    issues = UniqueUnitsRule(constraints).check(army)
    assert any(i.code == "UNIQUE_UNIT" for i in issues)


def test_enhancement_uniqueness_independent() -> None:
    blade = Enhancement(id="blade", name="Blade", points=10)
    unit = melee_attacker()
    army = _list(
        UnitSelection(unit=unit, points=180, enhancements=(blade,)),
        UnitSelection(unit=unit, points=180, enhancements=(blade,)),
    )
    issues = EnhancementUniquenessRule().check(army)
    assert any(i.code == "DUPLICATE_ENHANCEMENT" for i in issues)


def test_missing_points_independent() -> None:
    catalog = PointsCatalog(entries=())
    army = _list(UnitSelection(unit=melee_attacker(), points=180))
    issues = MissingPointsRule(catalog).check(army)
    assert any(i.code == "MISSING_POINTS" for i in issues)


def test_catalog_over_points() -> None:
    catalog = PointsCatalog(
        entries=(PointsEntry("example-berserkers", "v", 10, 500),)
    )
    army = _list(UnitSelection(unit=melee_attacker(), quantity=1), limit=200)
    result = validate_army_list(army, catalog=catalog)
    assert not result.is_valid
    assert any(i.code == "OVER_POINTS" for i in result.errors)


def test_armylist_points_cost_uses_catalog() -> None:
    catalog = PointsCatalog(
        entries=(PointsEntry("example-berserkers", "v", 10, 175),)
    )
    army = _list(UnitSelection(unit=melee_attacker(), quantity=2, points=0))
    assert army.points_cost(catalog) == 350
    assert army.remaining_catalog_points(catalog) == 1650
