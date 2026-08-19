"""Regression tests for bugs found in a v0.3 scan."""

from __future__ import annotations

from datetime import date

import pytest

from grimsim.data.database import connect, initialize_schema
from grimsim.data.points import PointsCatalog, PointsEntry
from grimsim.data.profiles import ProfileCatalog, ProfileEntry
from grimsim.data.repository import (
    _selection_row_id,
    load_army_list,
    save_army_list,
)
from grimsim.examples import melee_attacker
from grimsim.models.army import Army, UnitState
from grimsim.models.army_list import ArmyList
from grimsim.models.detachment import Detachment
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.validation import validate_army_list


def _ruleset() -> Ruleset:
    return Ruleset(
        id="scan",
        edition="10th",
        rules_version="0.3.0",
        points_version="x",
        effective_date=date(2025, 1, 1),
    )


def _list(*selections: UnitSelection, limit: int = 2000) -> ArmyList:
    return ArmyList(
        name="Scan",
        faction=Faction(id="crimson_hosts", name="Crimson Hosts"),
        detachment=Detachment(
            id="blood_tide", name="Blood Tide", faction_id="crimson_hosts"
        ),
        ruleset=_ruleset(),
        selections=selections,
        points_limit=limit,
    )


class TestRuntimeStateBugs:
    def test_army_from_list_uses_selection_size_not_profile_count(self) -> None:
        unit = melee_attacker()
        assert unit.profile.model_count == 10
        army_list = _list(UnitSelection(unit=unit, quantity=1, points=180, model_count=5))
        army = Army.from_list(army_list)
        assert army.units[0].starting_models == 5
        assert army.units[0].remaining_models == 5

    def test_apply_models_lost_clears_partial_wounds(self) -> None:
        state = UnitState.from_unit(
            melee_attacker(), remaining_models=5, wounds_on_current_model=1
        )
        state.apply_models_lost(1)
        assert state.remaining_models == 4
        assert state.wounds_on_current_model is None

    def test_from_unit_destroyed_has_no_wounds(self) -> None:
        state = UnitState.from_unit(
            melee_attacker(), remaining_models=0, wounds_on_current_model=1
        )
        assert state.destroyed
        assert state.wounds_on_current_model is None

    def test_from_unit_rejects_invalid_wounds(self) -> None:
        with pytest.raises(ValueError, match="wounds"):
            UnitState.from_unit(
                melee_attacker(), remaining_models=3, wounds_on_current_model=99
            )


class TestPersistenceBugs:
    def test_selection_row_id_is_stable(self) -> None:
        first = _selection_row_id("list-a", 0)
        second = _selection_row_id("list-a", 0)
        assert first == second
        assert _selection_row_id("list-a", 0) != _selection_row_id("list-a", 1)

    def test_save_load_preserves_unit_id_and_size(self) -> None:
        conn = connect()
        initialize_schema(conn)
        unit = melee_attacker()
        original = _list(UnitSelection(unit=unit, quantity=2, points=180, model_count=5))
        save_army_list(conn, original, list_id="scan-1")
        loaded = load_army_list(conn, "scan-1")
        assert loaded.selections[0].unit.identity == "example-berserkers"
        assert loaded.selections[0].size == 5
        conn.close()


class TestCatalogAndValidationBugs:
    def test_over_points_still_fires_when_another_selection_is_missing(self) -> None:
        catalog = PointsCatalog(
            entries=(PointsEntry("example-berserkers", "scan", 10, 2000),)
        )
        unknown = Unit(
            profile=UnitProfile(
                name="Unknown",
                model_count=5,
                toughness=4,
                wounds_per_model=1,
                save=5,
            ),
            weapons=(
                Weapon(
                    profile=WeaponProfile(
                        name="X", attacks=1, skill=4, strength=4, ap=0, damage=1
                    )
                ),
            ),
            id="unknown-unit",
        )
        army = _list(
            UnitSelection(unit=melee_attacker(), points=0),
            UnitSelection(unit=unknown, points=0),
            limit=1000,
        )
        result = validate_army_list(army, catalog=catalog)
        codes = {i.code for i in result.issues}
        assert "MISSING_POINTS" in codes
        assert "OVER_POINTS" in codes

    def test_profile_catalog_duplicate_key_last_wins(self) -> None:
        ruleset = _ruleset()
        first = melee_attacker()
        second = Unit(
            profile=UnitProfile(
                name="Example Berserkers",
                model_count=10,
                toughness=5,
                wounds_per_model=2,
                save=3,
            ),
            weapons=first.weapons,
            id="example-berserkers",
        )
        catalog = ProfileCatalog(
            entries=(
                ProfileEntry("example-berserkers", ruleset.slug, first),
                ProfileEntry("example-berserkers", ruleset.slug, second),
            )
        )
        assert catalog.unit_for("example-berserkers", ruleset).profile.toughness == 5
