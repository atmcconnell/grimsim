"""Tests for unit-activation Monte Carlo."""

from __future__ import annotations

import pytest

from grimsim.examples import light_infantry, mixed_melee_unit
from grimsim.models.activation import AttackPlan, WeaponAssignment
from grimsim.models.army import UnitState
from grimsim.simulation.activation_monte_carlo import simulate_many_unit_activations


def test_reproducible() -> None:
    attacker = UnitState.from_unit(mixed_melee_unit())
    target = UnitState.from_unit(light_infantry())
    plan = AttackPlan(
        assignments=(
            WeaponAssignment(attacker.unit.weapons[0], models=4),
            WeaponAssignment(attacker.unit.weapons[1], models=1),
        )
    )
    a = simulate_many_unit_activations(attacker, target, plan, iterations=200, seed=7)
    b = simulate_many_unit_activations(attacker, target, plan, iterations=200, seed=7)
    assert a.mean_damage == b.mean_damage
    assert a.mean_models_killed == b.mean_models_killed
    assert a.probability_target_destroyed == b.probability_target_destroyed


def test_aggregation_and_dataframe() -> None:
    attacker = UnitState.from_unit(mixed_melee_unit())
    target = UnitState.from_unit(light_infantry())
    result = simulate_many_unit_activations(
        attacker, target, iterations=50, seed=1
    )
    assert result.iterations == 50
    assert result.min_models_killed <= result.max_models_killed
    assert 0.0 <= result.probability_target_destroyed <= 1.0
    df = result.to_dataframe()
    assert len(df) == 50
    assert "total_damage" in df.columns
    assert "target_destroyed" in df.columns
    assert result.probability_models_killed_at_least(0) == 1.0
    assert result.probability_damage_at_least(0) == 1.0


def test_invalid_iterations() -> None:
    attacker = UnitState.from_unit(mixed_melee_unit())
    target = UnitState.from_unit(light_infantry())
    with pytest.raises(ValueError):
        simulate_many_unit_activations(attacker, target, iterations=-1)
