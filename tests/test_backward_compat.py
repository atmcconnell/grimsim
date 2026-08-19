"""Backward-compatibility tests for v0.1/v0.2 combat APIs."""

from __future__ import annotations

from grimsim import simulate_combat, simulate_many, simulate_unit_activation
from grimsim.examples import example_army_list, light_infantry, melee_attacker
from grimsim.models.army import Army


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


def test_simulate_combat_attack_count_unscaled() -> None:
    """Weapon-level API still fires the profile once, not per model."""
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_combat(attacker, attacker.weapons[0], target, seed=1)
    assert result.attacks == 4


def test_unit_activation_default_plan_works() -> None:
    runtime = Army.from_list(example_army_list())
    result = simulate_unit_activation(runtime.units[0], runtime.units[1], seed=1)
    assert result.attacks >= 0
    assert result.remaining_models <= runtime.units[1].starting_models
