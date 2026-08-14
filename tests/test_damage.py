"""Tests for damage allocation and Feel No Pain."""

from __future__ import annotations

import numpy as np

from grimsim.models.ability import FeelNoPain
from grimsim.models.dice import DiceExpression
from grimsim.rules.damage import (
    allocate_damage,
    apply_feel_no_pain,
    resolve_damage,
    roll_damage_instances,
)


class TestAllocateDamage:
    def test_exact_lethal(self) -> None:
        # 3 wounds/model, damage 3 -> exact kill
        result = allocate_damage(np.array([3]), model_count=5, wounds_per_model=3)
        assert result.models_killed == 1
        assert result.remaining_models == 4
        assert result.remaining_wounds_on_damaged_model is None

    def test_overkill_no_spill(self) -> None:
        # Spec example: 5 models, 3W each; damage 2, 2, 4
        # Attack1: model at 1W remaining
        # Attack2: kills that model (1 excess lost)
        # Attack3: kills next model (1 excess lost)
        result = allocate_damage(
            np.array([2, 2, 4]),
            model_count=5,
            wounds_per_model=3,
        )
        assert result.models_killed == 2
        assert result.remaining_models == 3
        assert result.remaining_wounds_on_damaged_model is None

    def test_partial_wound(self) -> None:
        result = allocate_damage(np.array([1]), model_count=5, wounds_per_model=3)
        assert result.models_killed == 0
        assert result.remaining_models == 5
        assert result.remaining_wounds_on_damaged_model == 2

    def test_multiple_attacks_full_destruction(self) -> None:
        # 3 models x 2W; six damage-2 attacks should wipe the unit
        result = allocate_damage(
            np.array([2, 2, 2, 2, 2, 2]),
            model_count=3,
            wounds_per_model=2,
        )
        assert result.models_killed == 3
        assert result.remaining_models == 0
        assert result.remaining_wounds_on_damaged_model is None

    def test_starting_partial_model(self) -> None:
        result = allocate_damage(
            np.array([1]),
            model_count=2,
            wounds_per_model=3,
            starting_wounds_on_current=1,
        )
        assert result.models_killed == 1
        assert result.remaining_models == 1

    def test_zero_damage_instances(self) -> None:
        result = allocate_damage(np.array([]), model_count=5, wounds_per_model=2)
        assert result.models_killed == 0
        assert result.remaining_models == 5


class TestFeelNoPain:
    def test_mitigates_damage(self) -> None:
        # With threshold 2+, almost everything is ignored on average;
        # with seed we just check it reduces some damage.
        instances = np.array([5, 5, 5])
        mitigated, ignored = apply_feel_no_pain(instances, 2, np.random.default_rng(0))
        assert ignored > 0
        assert mitigated.sum() + ignored == 15

    def test_no_fnp(self) -> None:
        instances = np.array([3, 4])
        mitigated, ignored = apply_feel_no_pain(instances, None, np.random.default_rng(0))
        np.testing.assert_array_equal(mitigated, instances)
        assert ignored == 0


class TestRollDamage:
    def test_fixed(self) -> None:
        values = roll_damage_instances(4, 2, np.random.default_rng(0))
        np.testing.assert_array_equal(values, [2, 2, 2, 2])

    def test_dice(self) -> None:
        values = roll_damage_instances(10, DiceExpression.d3(), np.random.default_rng(1))
        assert len(values) == 10
        assert values.min() >= 1
        assert values.max() <= 3

    def test_resolve_damage_with_fnp(self) -> None:
        result = resolve_damage(
            failed_saves=3,
            damage=2,
            model_count=5,
            wounds_per_model=2,
            target_abilities=(FeelNoPain(6),),
            rng=np.random.default_rng(42),
        )
        assert result.models_killed >= 0
        assert result.remaining_models <= 5
