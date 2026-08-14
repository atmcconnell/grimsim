"""Backward-compatibility tests for v0.1 combat APIs. """

from __future__ import annotations

import pytest

from grimsim import simulate_combat, simulate_many
from grimsim.examples import example_army_list, light_infantry, melee_attacker
from grimsim.models.army import Army
from grimsim.simulation.activation import simulate_unit_activation


def test_simulate_combat_still_works_without_army_list() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_combat(attacker, attacker.weapons[0], target, seed=42)
    assert result.attacks >= 0
    assert result.models_killed >= 0


def test_simulate_many_still_works_without_army_list() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_many(
        attacker,
        attacker.weapons[0],
        target,
        iterations=100,
        seed=7,
    )
    assert result.iterations == 100
    assert result.mean_damage >= 0


def test_unit_activation_stub_is_explicit() -> None:
    runtime = Army.from_list(example_army_list())
    with pytest.raises(NotImplementedError, match="v0.3"):
        simulate_unit_activation(runtime.units[0], runtime.units[1], seed=1)
