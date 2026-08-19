"""Tests for ruleset-aware points and profile catalogs."""

from __future__ import annotations

from datetime import date

import pytest

from grimsim.data.points import MissingPointsError, PointsCatalog, PointsEntry
from grimsim.data.profiles import MissingProfileError, ProfileCatalog, ProfileEntry
from grimsim.examples import (
    example_points_catalog,
    example_ruleset,
    example_ruleset_alt,
    melee_attacker,
)
from grimsim.models.ruleset import Ruleset
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile


def test_same_unit_different_ruleset_costs() -> None:
    catalog = example_points_catalog()
    unit = melee_attacker()
    jan = example_ruleset()
    jun = example_ruleset_alt()
    cost_a = catalog.cost_for(unit, jan, model_count=10)
    cost_b = catalog.cost_for(unit, jun, model_count=10)
    assert cost_a == 180
    assert cost_b == 200
    assert cost_a != cost_b


def test_missing_points() -> None:
    catalog = example_points_catalog()
    with pytest.raises(MissingPointsError):
        catalog.cost_for(melee_attacker(), example_ruleset(), model_count=3)
    assert catalog.try_cost_for(melee_attacker(), example_ruleset(), 3) is None


def test_available_sizes() -> None:
    catalog = example_points_catalog()
    assert catalog.available_sizes(melee_attacker(), example_ruleset()) == (10,)


def test_historical_lookup() -> None:
    ruleset = Ruleset(
        id="hist",
        edition="10th",
        rules_version="0.3.0",
        points_version="x",
        effective_date=date(2025, 3, 1),
    )
    catalog = PointsCatalog(
        entries=(
            PointsEntry(
                "u", "hist", 5, 100, effective_date=date(2025, 1, 1)
            ),
            PointsEntry(
                "u", "hist", 5, 120, effective_date=date(2025, 6, 1)
            ),
        )
    )
    assert catalog.cost_for("u", ruleset, 5) == 100
    assert catalog.cost_for("u", ruleset, 5, as_of=date(2025, 6, 1)) == 120


def test_profile_lookup_by_ruleset() -> None:
    unit_a = melee_attacker()
    unit_b = Unit(
        profile=UnitProfile(
            name="Example Berserkers",
            model_count=10,
            toughness=5,
            wounds_per_model=2,
            save=3,
        ),
        weapons=(
            Weapon(
                profile=WeaponProfile(
                    name="Chain Axe",
                    attacks=4,
                    skill=3,
                    strength=6,
                    ap=-2,
                    damage=2,
                )
            ),
        ),
        id="example-berserkers",
    )
    jan = example_ruleset()
    jun = example_ruleset_alt()
    catalog = ProfileCatalog(
        entries=(
            ProfileEntry("example-berserkers", jan.slug, unit_a),
            ProfileEntry("example-berserkers", jun.slug, unit_b),
        )
    )
    assert catalog.unit_for("example-berserkers", jan).profile.toughness == 4
    assert catalog.unit_for("example-berserkers", jun).profile.toughness == 5
    assert catalog.unit_for("example-berserkers", jan) is not catalog.unit_for(
        "example-berserkers", jun
    )
    with pytest.raises(MissingProfileError):
        catalog.unit_for("missing", jan)
