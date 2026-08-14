"""Tests for UnitSelection, Enhancement, ArmyList, validation, and Army."""

from __future__ import annotations

from datetime import date

import pytest

from grimsim.examples import (
    elite_infantry,
    example_army_list,
    light_infantry,
    melee_attacker,
    vehicle,
)
from grimsim.models.army import Army, UnitState
from grimsim.models.army_list import ArmyList
from grimsim.models.detachment import Detachment
from grimsim.models.enhancement import Enhancement
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection
from grimsim.validation import ValidationIssue, ValidationResult, validate_army_list


def _ruleset() -> Ruleset:
    return Ruleset(
        id="test",
        edition="10th",
        rules_version="0.2.0",
        points_version="2025.01",
        effective_date=date(2025, 1, 1),
    )


def _faction() -> Faction:
    return Faction(id="crimson_hosts", name="Crimson Hosts")


def _detachment() -> Detachment:
    return Detachment(id="blood_tide", name="Blood Tide", faction_id="crimson_hosts")


class TestUnitSelection:
    def test_valid_selection_points(self) -> None:
        selection = UnitSelection(
            unit=melee_attacker(),
            quantity=2,
            points=180,
            enhancements=(Enhancement(id="e1", name="Blade", points=25),),
        )
        assert selection.total_points == 180 * 2 + 25

    def test_invalid_quantity(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            UnitSelection(unit=melee_attacker(), quantity=0, points=100)

    def test_invalid_points(self) -> None:
        with pytest.raises(ValueError, match="points"):
            UnitSelection(unit=melee_attacker(), quantity=1, points=-1)

    def test_duplicate_enhancements_rejected(self) -> None:
        enhancement = Enhancement(id="e1", name="Blade", points=10)
        with pytest.raises(ValueError, match="duplicate enhancement"):
            UnitSelection(
                unit=elite_infantry(),
                points=200,
                enhancements=(enhancement, enhancement),
            )

    def test_enhancement_negative_points(self) -> None:
        with pytest.raises(ValueError):
            Enhancement(id="e1", name="X", points=-5)


class TestArmyList:
    def test_total_and_remaining_points(self) -> None:
        army_list = ArmyList(
            name="Test",
            faction=_faction(),
            detachment=_detachment(),
            ruleset=_ruleset(),
            points_limit=1000,
            selections=(
                UnitSelection(unit=melee_attacker(), quantity=2, points=180),
                UnitSelection(unit=light_infantry(), quantity=1, points=120),
            ),
        )
        assert army_list.total_points == 480
        assert army_list.remaining_points == 520
        assert army_list.selection_count == 2
        assert army_list.unit_count == 3

    def test_example_list_under_2000(self) -> None:
        army_list = example_army_list(points_limit=2000)
        assert army_list.total_points <= 2000
        assert army_list.remaining_points == 2000 - army_list.total_points
        result = validate_army_list(army_list)
        assert result.is_valid

    def test_multiple_selections(self) -> None:
        army_list = example_army_list()
        assert army_list.selection_count >= 2
        assert army_list.unit_count >= army_list.selection_count


class TestValidation:
    def test_detachment_faction_mismatch(self) -> None:
        army_list = ArmyList(
            name="Bad",
            faction=_faction(),
            detachment=Detachment(id="other", name="Other", faction_id="someone_else"),
            ruleset=_ruleset(),
            points_limit=2000,
            selections=(UnitSelection(unit=vehicle(), points=220),),
        )
        result = validate_army_list(army_list)
        assert not result.is_valid
        assert any(i.code == "DETACHMENT_FACTION_MISMATCH" for i in result.errors)

    def test_over_points(self) -> None:
        army_list = ArmyList(
            name="Over",
            faction=_faction(),
            detachment=_detachment(),
            ruleset=_ruleset(),
            points_limit=100,
            selections=(UnitSelection(unit=vehicle(), points=220),),
        )
        result = validate_army_list(army_list)
        assert not result.is_valid
        assert any(i.code == "OVER_POINTS" for i in result.errors)
        assert army_list.remaining_points < 0

    def test_empty_list(self) -> None:
        army_list = ArmyList(
            name="Empty",
            faction=_faction(),
            detachment=_detachment(),
            ruleset=_ruleset(),
            points_limit=2000,
            selections=(),
        )
        result = validate_army_list(army_list)
        assert not result.is_valid
        assert any(i.code == "EMPTY_ARMY_LIST" for i in result.errors)

    def test_validation_result_structure(self) -> None:
        result = ValidationResult(
            issues=(
                ValidationIssue(code="A", message="err"),
                ValidationIssue(code="B", message="warn", severity="warning"),
            )
        )
        assert not result.is_valid
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestArmyRuntime:
    def test_from_list_expands_quantity(self) -> None:
        army_list = ArmyList(
            name="Runtime",
            faction=_faction(),
            detachment=_detachment(),
            ruleset=_ruleset(),
            points_limit=2000,
            selections=(
                UnitSelection(unit=melee_attacker(), quantity=2, points=180),
                UnitSelection(unit=vehicle(), quantity=1, points=220),
            ),
        )
        army = Army.from_list(army_list)
        assert len(army.units) == 3
        assert army.source_list is army_list
        assert all(isinstance(u, UnitState) for u in army.units)

    def test_runtime_mutation_does_not_mutate_list(self) -> None:
        army_list = example_army_list()
        original_selections = army_list.selections
        army = Army.from_list(army_list)

        army.units[0].apply_models_lost(army.units[0].remaining_models)
        assert army.units[0].destroyed
        assert army.units[0].remaining_models == 0

        # Source list remains unchanged (frozen + same selection tuple).
        assert army.source_list.selections is original_selections
        assert army.source_list.selections[0].unit.profile.model_count == (
            original_selections[0].unit.profile.model_count
        )
        assert len(army.destroyed_units) == 1
        assert len(army.remaining_units) == len(army.units) - 1
