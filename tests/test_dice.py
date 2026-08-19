"""Tests for dice primitives."""

from __future__ import annotations

import numpy as np
import pytest

from grimsim.models.dice import DiceExpression, resolve_value, roll_dice, roll_die


class TestRollDie:
    def test_valid_range(self) -> None:
        rng = np.random.default_rng(0)
        for _ in range(100):
            value = roll_die(6, rng)
            assert 1 <= value <= 6

    def test_deterministic_seed(self) -> None:
        a = roll_die(6, np.random.default_rng(42))
        b = roll_die(6, np.random.default_rng(42))
        assert a == b

    def test_invalid_sides(self) -> None:
        rng = np.random.default_rng(0)
        with pytest.raises(ValueError, match="sides"):
            roll_die(1, rng)


class TestRollDice:
    def test_correct_count(self) -> None:
        rolls = roll_dice(10, 6, np.random.default_rng(1))
        assert len(rolls) == 10
        assert rolls.min() >= 1
        assert rolls.max() <= 6

    def test_zero_count(self) -> None:
        rolls = roll_dice(0, 6, np.random.default_rng(1))
        assert len(rolls) == 0

    def test_deterministic(self) -> None:
        a = roll_dice(20, 6, np.random.default_rng(7))
        b = roll_dice(20, 6, np.random.default_rng(7))
        np.testing.assert_array_equal(a, b)

    def test_invalid_count(self) -> None:
        with pytest.raises(ValueError, match="count"):
            roll_dice(-1, 6, np.random.default_rng(0))

    def test_invalid_sides(self) -> None:
        with pytest.raises(ValueError, match="sides"):
            roll_dice(3, 0, np.random.default_rng(0))


class TestDiceExpression:
    def test_flat(self) -> None:
        expr = DiceExpression.flat(3)
        assert expr.roll(np.random.default_rng(0)) == 3
        assert str(expr) == "3"

    def test_d3(self) -> None:
        expr = DiceExpression.d3()
        rng = np.random.default_rng(0)
        for _ in range(50):
            assert 1 <= expr.roll(rng) <= 3

    def test_d6(self) -> None:
        expr = DiceExpression.d6()
        assert str(expr) == "D6"
        rng = np.random.default_rng(1)
        assert 1 <= expr.roll(rng) <= 6

    def test_2d6(self) -> None:
        expr = DiceExpression(count=2, sides=6, modifier=0)
        assert str(expr) == "2D6"
        rng = np.random.default_rng(2)
        for _ in range(50):
            assert 2 <= expr.roll(rng) <= 12

    def test_d6_plus_2(self) -> None:
        expr = DiceExpression(count=1, sides=6, modifier=2)
        assert str(expr) == "D6+2"
        rng = np.random.default_rng(3)
        for _ in range(50):
            assert 3 <= expr.roll(rng) <= 8

    def test_scaled(self) -> None:
        expr = DiceExpression(count=1, sides=6, modifier=2)
        scaled = expr.scaled(3)
        assert scaled.count == 3
        assert scaled.modifier == 6

    def test_deterministic(self) -> None:
        expr = DiceExpression(count=2, sides=6, modifier=1)
        a = expr.roll(np.random.default_rng(99))
        b = expr.roll(np.random.default_rng(99))
        assert a == b

    def test_roll_many(self) -> None:
        expr = DiceExpression.d6(modifier=1)
        values = expr.roll_many(100, np.random.default_rng(5))
        assert len(values) == 100
        assert values.min() >= 2
        assert values.max() <= 7

    def test_invalid_count(self) -> None:
        with pytest.raises(ValueError, match="count"):
            DiceExpression(count=-1, sides=6)

    def test_invalid_sides(self) -> None:
        with pytest.raises(ValueError, match="sides"):
            DiceExpression(count=1, sides=1)

    def test_resolve_value(self) -> None:
        rng = np.random.default_rng(0)
        assert resolve_value(5, rng) == 5
        assert 1 <= resolve_value(DiceExpression.d6(), rng) <= 6
