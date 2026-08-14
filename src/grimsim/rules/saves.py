"""Save-stage resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from grimsim.models.dice import roll_dice


@dataclass(frozen=True)
class SaveChoice:
    """Resolved save to attempt (or None if saves automatically fail)."""

    target: int | None
    source: str  # "armor", "invulnerable", or "none"


def modified_armor_save(save: int, ap: int, save_modifier: int = 0) -> int:
    """Compute the modified armour save target.

    AP uses datasheet convention (0, -1, -2, …). A save of 3+ with AP -1
    becomes 4+. Positive ``save_modifier`` improves the save (lowers the target).
    """
    # AP is negative or zero: save - ap increases the target when ap is negative.
    return save - ap - save_modifier


def choose_save(
    armor_save: int,
    ap: int,
    invulnerable_save: int | None,
    save_modifier: int = 0,
) -> SaveChoice:
    """Choose the better legal save between armour and invulnerable.

    ``save_modifier`` applies to armour saves only (benefit-of-cover style).
    Invulnerable saves ignore both AP and ``save_modifier``.

    An armour save worse than 6+ (target > 6) is impossible and discarded.
    Lower target numbers are better (2+ beats 5+). Effective armour targets
    better than 2+ are treated as 2+.
    """
    mod_armor = modified_armor_save(armor_save, ap, save_modifier)
    armor_legal = mod_armor <= 6

    candidates: list[tuple[int, str]] = []
    if armor_legal:
        candidates.append((max(2, mod_armor), "armor"))
    if invulnerable_save is not None:
        # Invulnerable saves ignore AP and armour-only save modifiers.
        candidates.append((invulnerable_save, "invulnerable"))

    if not candidates:
        return SaveChoice(target=None, source="none")

    # Prefer the lower (better) target; break ties favoring invulnerable.
    best_target = min(t for t, _ in candidates)
    for target, source in candidates:
        if target == best_target and source == "invulnerable":
            return SaveChoice(target=target, source=source)
    return SaveChoice(target=best_target, source="armor")


@dataclass(frozen=True)
class SaveStageResult:
    """Outcome of the save stage."""

    wounds_to_save: int
    failed_saves: int
    successful_saves: int
    save_target: int | None
    save_source: str


def resolve_saves(
    wounds: int,
    armor_save: int,
    ap: int,
    invulnerable_save: int | None,
    save_modifier: int,
    rng: np.random.Generator,
) -> SaveStageResult:
    """Resolve armour / invulnerable saves against successful wounds."""
    if wounds < 0:
        raise ValueError(f"wounds must be >= 0, got {wounds}")
    if wounds == 0:
        choice = choose_save(armor_save, ap, invulnerable_save, save_modifier)
        return SaveStageResult(
            wounds_to_save=0,
            failed_saves=0,
            successful_saves=0,
            save_target=choice.target,
            save_source=choice.source,
        )

    choice = choose_save(armor_save, ap, invulnerable_save, save_modifier)
    if choice.target is None:
        return SaveStageResult(
            wounds_to_save=wounds,
            failed_saves=wounds,
            successful_saves=0,
            save_target=None,
            save_source="none",
        )

    rolls = roll_dice(wounds, 6, rng)
    successes = int((rolls >= choice.target).sum())
    failures = wounds - successes
    return SaveStageResult(
        wounds_to_save=wounds,
        failed_saves=failures,
        successful_saves=successes,
        save_target=choice.target,
        save_source=choice.source,
    )
