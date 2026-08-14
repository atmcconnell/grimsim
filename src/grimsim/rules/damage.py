"""Damage rolling, Feel No Pain mitigation, and model allocation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from grimsim.models.ability import DamageMitigationAbility
from grimsim.models.dice import DiceExpression, resolve_value, roll_dice


@dataclass(frozen=True)
class AllocationResult:
    """Result of allocating damage across models in a unit."""

    models_killed: int
    remaining_models: int
    remaining_wounds_on_damaged_model: int | None
    total_damage_applied: int
    damage_mitigated: int


def collect_feel_no_pain(abilities: tuple[object, ...]) -> int | None:
    """Return the best (lowest threshold) Feel No Pain value, if any."""
    best: int | None = None
    for ability in abilities:
        if isinstance(ability, DamageMitigationAbility):
            threshold = ability.feel_no_pain_threshold()
            if threshold is not None:
                best = threshold if best is None else min(best, threshold)
    return best


def roll_damage_instances(
    count: int,
    damage: int | DiceExpression,
    rng: np.random.Generator,
) -> np.ndarray:
    """Roll damage for ``count`` failed saves.

    Returns:
        Array of per-wound damage values (before FNP / allocation).
    """
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")
    if count == 0:
        return np.array([], dtype=np.int64)
    if isinstance(damage, DiceExpression):
        return damage.roll_many(count, rng)
    if damage < 1:
        raise ValueError(f"damage must be >= 1, got {damage}")
    return np.full(count, damage, dtype=np.int64)


def apply_feel_no_pain(
    damage_instances: np.ndarray,
    threshold: int | None,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    """Apply Feel No Pain to each point of damage independently.

    Returns:
        ``(mitigated_damage_instances, total_points_ignored)``
    """
    if threshold is None or len(damage_instances) == 0:
        return damage_instances.astype(np.int64, copy=False), 0

    mitigated: list[int] = []
    ignored = 0
    for dmg in damage_instances:
        dmg_int = int(dmg)
        if dmg_int <= 0:
            mitigated.append(0)
            continue
        rolls = roll_dice(dmg_int, 6, rng)
        saved = int((rolls >= threshold).sum())
        ignored += saved
        mitigated.append(dmg_int - saved)
    return np.array(mitigated, dtype=np.int64), ignored


def allocate_damage(
    damage_instances: np.ndarray,
    model_count: int,
    wounds_per_model: int,
    *,
    starting_wounds_on_current: int | None = None,
) -> AllocationResult:
    """Allocate damage model-by-model without spilling excess between models.

    Args:
        damage_instances: Per-attack damage values (after FNP).
        model_count: Starting number of models.
        wounds_per_model: Full wound characteristic.
        starting_wounds_on_current: Wounds remaining on the currently damaged
            model; defaults to a fresh model at full wounds.
    """
    if model_count < 0:
        raise ValueError(f"model_count must be >= 0, got {model_count}")
    if wounds_per_model < 1:
        raise ValueError(f"wounds_per_model must be >= 1, got {wounds_per_model}")

    if model_count == 0:
        return AllocationResult(
            models_killed=0,
            remaining_models=0,
            remaining_wounds_on_damaged_model=None,
            total_damage_applied=0,
            damage_mitigated=0,
        )

    remaining_models = model_count
    current_wounds = (
        wounds_per_model if starting_wounds_on_current is None else starting_wounds_on_current
    )
    if not 1 <= current_wounds <= wounds_per_model:
        raise ValueError(
            f"starting_wounds_on_current must be 1..{wounds_per_model}, got {current_wounds}"
        )

    models_killed = 0
    total_applied = 0
    damaged = (
        starting_wounds_on_current is not None
        and starting_wounds_on_current < wounds_per_model
    )

    for raw in damage_instances:
        if remaining_models <= 0:
            break
        dmg = int(raw)
        if dmg <= 0:
            continue

        applied = min(dmg, current_wounds)
        current_wounds -= applied
        total_applied += applied
        # Excess damage on this attack is lost (no spill to next model).

        if current_wounds <= 0:
            models_killed += 1
            remaining_models -= 1
            if remaining_models > 0:
                current_wounds = wounds_per_model
                damaged = False
            else:
                current_wounds = 0
                damaged = False
        else:
            damaged = current_wounds < wounds_per_model

    remaining_wounds: int | None
    if remaining_models <= 0:
        remaining_wounds = None
    elif damaged:
        remaining_wounds = current_wounds
    else:
        remaining_wounds = None

    return AllocationResult(
        models_killed=models_killed,
        remaining_models=remaining_models,
        remaining_wounds_on_damaged_model=remaining_wounds,
        total_damage_applied=total_applied,
        damage_mitigated=0,
    )


def resolve_damage(
    failed_saves: int,
    damage: int | DiceExpression,
    model_count: int,
    wounds_per_model: int,
    target_abilities: tuple[object, ...],
    rng: np.random.Generator,
) -> AllocationResult:
    """Roll damage, apply Feel No Pain, and allocate to models."""
    instances = roll_damage_instances(failed_saves, damage, rng)
    fnp = collect_feel_no_pain(target_abilities)
    mitigated_instances, ignored = apply_feel_no_pain(instances, fnp, rng)
    allocation = allocate_damage(mitigated_instances, model_count, wounds_per_model)
    return AllocationResult(
        models_killed=allocation.models_killed,
        remaining_models=allocation.remaining_models,
        remaining_wounds_on_damaged_model=allocation.remaining_wounds_on_damaged_model,
        total_damage_applied=allocation.total_damage_applied,
        damage_mitigated=ignored,
    )


# Re-export for callers that need a single resolve helper.
__all__ = [
    "AllocationResult",
    "allocate_damage",
    "apply_feel_no_pain",
    "collect_feel_no_pain",
    "resolve_damage",
    "resolve_value",
    "roll_damage_instances",
]
