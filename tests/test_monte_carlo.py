"""Tests for Monte Carlo simulation."""

from __future__ import annotations

import pytest

from grimsim.examples import light_infantry, melee_attacker
from grimsim.simulation.monte_carlo import simulate_many


def test_simulate_many_stats() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_many(
        attacker,
        attacker.weapons[0],
        target,
        iterations=1_000,
        seed=42,
    )
    assert result.iterations == 1_000
    assert result.mean_damage >= 0
    assert result.median_damage >= 0
    assert result.std_damage >= 0
    assert result.mean_models_killed >= 0
    assert result.min_models_killed <= result.max_models_killed
    assert 0.0 <= result.probability_target_destroyed <= 1.0


def test_simulate_many_deterministic() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    a = simulate_many(attacker, attacker.weapons[0], target, iterations=200, seed=7)
    b = simulate_many(attacker, attacker.weapons[0], target, iterations=200, seed=7)
    assert a.mean_damage == b.mean_damage
    assert a.mean_models_killed == b.mean_models_killed


def test_probability_helpers() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_many(attacker, attacker.weapons[0], target, iterations=500, seed=3)
    p_kill = result.probability_models_killed_at_least(1)
    p_dmg = result.probability_damage_at_least(1)
    assert 0.0 <= p_kill <= 1.0
    assert 0.0 <= p_dmg <= 1.0
    assert result.probability_models_killed_at_least(10_000) == 0.0


def test_to_dataframe() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_many(attacker, attacker.weapons[0], target, iterations=50, seed=1)
    df = result.to_dataframe()
    assert len(df) == 50
    assert "total_damage" in df.columns
    assert "models_killed" in df.columns


def test_mean_within_tolerance() -> None:
    """Statistical sanity: mean models killed should be in a plausible band."""
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_many(
        attacker,
        attacker.weapons[0],
        target,
        iterations=5_000,
        seed=42,
    )
    # Berserkers into troopers should kill a non-trivial number on average.
    assert 1.0 < result.mean_models_killed < 10.0


def test_invalid_iterations() -> None:
    attacker = melee_attacker()
    with pytest.raises(ValueError):
        simulate_many(attacker, attacker.weapons[0], light_infantry(), iterations=-1)
