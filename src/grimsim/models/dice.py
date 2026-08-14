"""Dice primitives with injectable, seedable RNG."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def roll_die(sides: int, rng: np.random.Generator) -> int:
    """Roll a single die with the given number of sides.

    Args:
        sides: Number of faces on the die (must be >= 2).
        rng: Injected NumPy random generator.

    Returns:
        An integer in ``[1, sides]``.
    """
    if sides < 2:
        raise ValueError(f"sides must be >= 2, got {sides}")
    return int(rng.integers(1, sides + 1))


def roll_dice(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
    """Roll ``count`` dice with the given number of sides.

    Args:
        count: Number of dice to roll (must be >= 0).
        sides: Number of faces on each die (must be >= 2).
        rng: Injected NumPy random generator.

    Returns:
        A 1-D NumPy array of length ``count`` with values in ``[1, sides]``.
    """
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")
    if sides < 2:
        raise ValueError(f"sides must be >= 2, got {sides}")
    if count == 0:
        return np.array([], dtype=np.int64)
    return rng.integers(1, sides + 1, size=count, dtype=np.int64)


@dataclass(frozen=True)
class DiceExpression:
    """Structured representation of a dice expression such as ``2D6+2``.

    Attributes:
        count: Number of dice to roll (0 for a flat value with no dice).
        sides: Faces per die (ignored when ``count == 0``).
        modifier: Flat bonus or penalty added after rolling.
    """

    count: int = 0
    sides: int = 6
    modifier: int = 0

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError(f"count must be >= 0, got {self.count}")
        if self.count > 0 and self.sides < 2:
            raise ValueError(f"sides must be >= 2 when rolling dice, got {self.sides}")

    @classmethod
    def flat(cls, value: int) -> DiceExpression:
        """Create a flat (non-random) expression equal to ``value``."""
        return cls(count=0, sides=6, modifier=value)

    @classmethod
    def d3(cls, count: int = 1, modifier: int = 0) -> DiceExpression:
        """Create a D3-based expression."""
        return cls(count=count, sides=3, modifier=modifier)

    @classmethod
    def d6(cls, count: int = 1, modifier: int = 0) -> DiceExpression:
        """Create a D6-based expression."""
        return cls(count=count, sides=6, modifier=modifier)

    def roll(self, rng: np.random.Generator) -> int:
        """Evaluate this expression once, returning a single integer total."""
        if self.count == 0:
            return self.modifier
        rolls = roll_dice(self.count, self.sides, rng)
        return int(rolls.sum()) + self.modifier

    def roll_many(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Evaluate this expression ``n`` times.

        Returns:
            A 1-D array of length ``n``.
        """
        if n < 0:
            raise ValueError(f"n must be >= 0, got {n}")
        if n == 0:
            return np.array([], dtype=np.int64)
        if self.count == 0:
            return np.full(n, self.modifier, dtype=np.int64)
        # Shape (n, count) then sum across dice.
        rolls = rng.integers(1, self.sides + 1, size=(n, self.count), dtype=np.int64)
        return rolls.sum(axis=1) + self.modifier

    def __str__(self) -> str:
        if self.count == 0:
            return str(self.modifier)
        base = f"D{self.sides}" if self.count == 1 else f"{self.count}D{self.sides}"
        if self.modifier > 0:
            return f"{base}+{self.modifier}"
        if self.modifier < 0:
            return f"{base}{self.modifier}"
        return base


def resolve_value(value: int | DiceExpression, rng: np.random.Generator) -> int:
    """Resolve a fixed integer or dice expression to a single integer."""
    if isinstance(value, DiceExpression):
        return value.roll(rng)
    return value
