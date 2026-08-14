"""Wound-stage resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from grimsim.models.ability import WoundAbility
from grimsim.models.dice import roll_dice


def wound_target(strength: int, toughness: int) -> int:
    """Return the wound roll target for Strength vs Toughness.

    Standard 40k table:

    - S >= 2T  -> 2+
    - S > T    -> 3+
    - S == T   -> 4+
    - S < T    -> 5+
    - 2S <= T  -> 6+
    """
    if strength < 1:
        raise ValueError(f"strength must be >= 1, got {strength}")
    if toughness < 1:
        raise ValueError(f"toughness must be >= 1, got {toughness}")

    if strength >= 2 * toughness:
        return 2
    if strength > toughness:
        return 3
    if strength == toughness:
        return 4
    if 2 * strength <= toughness:
        return 6
    return 5


@dataclass(frozen=True)
class WoundStageResult:
    """Outcome of the wound stage."""

    wounds: int
    critical_wounds: int
    failed_wounds: int


def collect_reroll_wound_ones(abilities: tuple[object, ...]) -> bool:
    """Return True if any ability grants reroll wound ones."""
    for ability in abilities:
        if isinstance(ability, WoundAbility) and ability.is_reroll_wound_ones():
            return True
    return False


def resolve_wounds(
    hits_to_wound: int,
    strength: int,
    toughness: int,
    wound_modifier: int,
    abilities: tuple[object, ...],
    rng: np.random.Generator,
    *,
    critical_threshold: int = 6,
) -> WoundStageResult:
    """Resolve wound rolls for hits that were not auto-wounded."""
    if hits_to_wound < 0:
        raise ValueError(f"hits_to_wound must be >= 0, got {hits_to_wound}")
    if hits_to_wound == 0:
        return WoundStageResult(wounds=0, critical_wounds=0, failed_wounds=0)

    base_target = wound_target(strength, toughness)
    target = _clamp_target(base_target - wound_modifier)
    reroll_ones = collect_reroll_wound_ones(abilities)

    rolls = roll_dice(hits_to_wound, 6, rng)
    if reroll_ones:
        ones_mask = rolls == 1
        if ones_mask.any():
            rerolls = roll_dice(int(ones_mask.sum()), 6, rng)
            rolls = rolls.copy()
            rolls[ones_mask] = rerolls

    critical_mask = rolls >= critical_threshold
    success_mask = (rolls > 1) & ((rolls >= target) | critical_mask)

    wounds = int(success_mask.sum())
    critical_wounds = int(critical_mask.sum())
    failed_wounds = hits_to_wound - wounds

    return WoundStageResult(
        wounds=wounds,
        critical_wounds=critical_wounds,
        failed_wounds=failed_wounds,
    )


def _clamp_target(target: int) -> int:
    return max(2, min(6, target))
