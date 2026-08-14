"""Tests for domain model validation."""

from __future__ import annotations

import pytest

from grimsim.models.unit import UnitProfile
from grimsim.models.weapon import WeaponProfile


def test_weapon_profile_validation() -> None:
    with pytest.raises(ValueError):
        WeaponProfile(name="", attacks=1, skill=3, strength=4, ap=0, damage=1)
    with pytest.raises(ValueError):
        WeaponProfile(name="X", attacks=-1, skill=3, strength=4, ap=0, damage=1)
    with pytest.raises(ValueError):
        WeaponProfile(name="X", attacks=1, skill=1, strength=4, ap=0, damage=1)


def test_unit_profile_validation() -> None:
    with pytest.raises(ValueError):
        UnitProfile(name="X", model_count=0, toughness=4, wounds_per_model=1, save=3)
    with pytest.raises(ValueError):
        UnitProfile(
            name="X",
            model_count=1,
            toughness=4,
            wounds_per_model=1,
            save=3,
            invulnerable_save=1,
        )
