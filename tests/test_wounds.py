"""Tests for the Strength vs Toughness wound table."""

from __future__ import annotations

import pytest

from grimsim.rules.wounds import wound_target


@pytest.mark.parametrize(
    ("strength", "toughness", "expected"),
    [
        (8, 4, 2),  # S >= 2T
        (10, 5, 2),
        (5, 4, 3),  # S > T
        (6, 5, 3),
        (4, 4, 4),  # S == T
        (5, 5, 4),
        (4, 5, 5),  # S < T (but not 2S <= T)
        (5, 6, 5),
        (3, 6, 6),  # 2S <= T
        (4, 8, 6),
        (5, 10, 6),
    ],
)
def test_wound_target_table(strength: int, toughness: int, expected: int) -> None:
    assert wound_target(strength, toughness) == expected


def test_wound_target_invalid() -> None:
    with pytest.raises(ValueError):
        wound_target(0, 4)
    with pytest.raises(ValueError):
        wound_target(4, 0)
