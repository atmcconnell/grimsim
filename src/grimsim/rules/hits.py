"""Hit-stage resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from grimsim.models.ability import HitAbility
from grimsim.models.dice import roll_dice


@dataclass(frozen=True)
class HitStageResult:
    """Outcome of the hit stage before wound resolution."""

    attacks: int
    hits: int
    critical_hits: int
    failed_hits: int
    # Number of hits that still need a wound roll (excludes lethal auto-wounds).
    hits_to_wound: int
    # Number of auto-wounds from Lethal Hits (from critical hits).
    auto_wounds: int


def collect_hit_flags(abilities: tuple[object, ...]) -> tuple[bool, int, bool]:
    """Extract hit-stage flags from a collection of abilities.

    Returns:
        ``(reroll_ones, sustained_hits_bonus, lethal_hits)``
    """
    reroll_ones = False
    sustained = 0
    lethal = False
    for ability in abilities:
        if isinstance(ability, HitAbility):
            if ability.is_reroll_hit_ones():
                reroll_ones = True
            sustained = max(sustained, ability.sustained_hits_bonus())
            if ability.causes_lethal_hits():
                lethal = True
    return reroll_ones, sustained, lethal


def resolve_hits(
    attacks: int,
    skill: int,
    hit_modifier: int,
    abilities: tuple[object, ...],
    rng: np.random.Generator,
    *,
    critical_threshold: int = 6,
) -> HitStageResult:
    """Resolve hit rolls for ``attacks`` attack dice.

    Critical hits are unmodified rolls of ``critical_threshold`` (usually 6).
    Hit modifiers apply to the success threshold, not to critical detection.
    """
    if attacks < 0:
        raise ValueError(f"attacks must be >= 0, got {attacks}")
    if attacks == 0:
        return HitStageResult(
            attacks=0,
            hits=0,
            critical_hits=0,
            failed_hits=0,
            hits_to_wound=0,
            auto_wounds=0,
        )

    reroll_ones, sustained_bonus, lethal = collect_hit_flags(abilities)
    target = _clamp_target(skill - hit_modifier)

    rolls = roll_dice(attacks, 6, rng)
    if reroll_ones:
        ones_mask = rolls == 1
        if ones_mask.any():
            rerolls = roll_dice(int(ones_mask.sum()), 6, rng)
            rolls = rolls.copy()
            rolls[ones_mask] = rerolls

    critical_mask = rolls >= critical_threshold
    # Unmodified 1s always fail; otherwise compare against modified target.
    success_mask = (rolls > 1) & ((rolls >= target) | critical_mask)

    critical_hits = int(critical_mask.sum())
    base_hits = int(success_mask.sum())
    failed_hits = attacks - base_hits

    # Sustained Hits: each critical hit generates additional hits.
    extra_hits = critical_hits * sustained_bonus
    total_hits = base_hits + extra_hits

    if lethal:
        # Critical hits auto-wound; remaining hits (including sustained extras) wound normally.
        # Sustained extra hits are normal hits, not criticals.
        auto_wounds = critical_hits
        hits_to_wound = total_hits - critical_hits
    else:
        auto_wounds = 0
        hits_to_wound = total_hits

    return HitStageResult(
        attacks=attacks,
        hits=total_hits,
        critical_hits=critical_hits,
        failed_hits=failed_hits,
        hits_to_wound=hits_to_wound,
        auto_wounds=auto_wounds,
    )


def _clamp_target(target: int) -> int:
    """Clamp a success threshold to a legal D6 range."""
    return max(2, min(6, target))
