"""Combat context and result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CombatContext:
    """Modifiers and future hooks for conditional rules.

    Terrain, stratagems, detachments, and battle-round logic are intentionally
    out of scope for v0.1 — this object exists so those concepts have a home.

    ``save_modifier`` applies to **armour** saves only (cover-style), never to
    invulnerable saves.
    """

    hit_modifier: int = 0
    wound_modifier: int = 0
    save_modifier: int = 0


@dataclass(frozen=True)
class CombatResult:
    """Typed outcome of a single attack sequence."""

    attacks: int
    hits: int
    critical_hits: int
    wounds: int
    critical_wounds: int
    failed_saves: int
    total_damage: int
    models_killed: int
    remaining_models: int
    remaining_wounds_on_damaged_model: int | None
    damage_mitigated: int = 0
    auto_wounds: int = 0
