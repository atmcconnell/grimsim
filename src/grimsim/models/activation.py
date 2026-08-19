"""Attack plans and unit-activation result types."""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.army import UnitState
from grimsim.models.combat import CombatResult
from grimsim.models.dice import DiceExpression
from grimsim.models.weapon import Weapon, WeaponProfile


@dataclass(frozen=True)
class WeaponAssignment:
    """Assign surviving models to one weapon profile for an activation.

    ``models`` is the number of living models firing this profile.
    ``weapon.profile.attacks`` is treated as **per-model** and scaled by
    ``models`` during activation (the low-level ``simulate_combat`` API
    still fires the profile once, unscaled).
    """

    weapon: Weapon
    models: int

    def __post_init__(self) -> None:
        if self.models < 1:
            raise ValueError(f"models must be >= 1, got {self.models}")


@dataclass(frozen=True)
class AttackPlan:
    """How surviving models are assigned to weapon profiles.

    When ``disjoint`` is True (default), the sum of assigned models cannot
    exceed living models — mixed loadouts. When False, each assignment is
    independently capped at living models (every model may fire every weapon).
    """

    assignments: tuple[WeaponAssignment, ...]
    disjoint: bool = True

    def validate(self, attacker: UnitState) -> None:
        """Raise ``ValueError`` if this plan is invalid for ``attacker``."""
        alive = attacker.remaining_models
        for assignment in self.assignments:
            if assignment.models > alive:
                raise ValueError(
                    f"Cannot assign {assignment.models} models to "
                    f"{assignment.weapon.profile.name}; {alive} remain."
                )
        if self.disjoint:
            total = sum(a.models for a in self.assignments)
            if total > alive:
                raise ValueError(
                    f"Disjoint plan assigns {total} models but only {alive} remain."
                )

    def describe(self) -> str:
        """Stable, human-readable summary for persistence."""
        if not self.assignments:
            return ""
        parts = [f"{a.models}x {a.weapon.profile.name}" for a in self.assignments]
        mode = "disjoint" if self.disjoint else "overlap"
        return f"{mode}: " + "; ".join(parts)

    @classmethod
    def all_remaining_fire_all_weapons(cls, attacker: UnitState) -> AttackPlan:
        """Every remaining model fires every weapon on the unit profile."""
        remaining = attacker.remaining_models
        if remaining < 1 or not attacker.unit.weapons:
            return cls(assignments=())
        return cls(
            assignments=tuple(
                WeaponAssignment(weapon=weapon, models=remaining)
                for weapon in attacker.unit.weapons
            ),
            disjoint=False,
        )


def scale_weapon_for_models(weapon: Weapon, models: int) -> Weapon:
    """Return a new weapon whose attacks are multiplied by ``models``."""
    if models < 1:
        raise ValueError(f"models must be >= 1, got {models}")
    attacks = weapon.profile.attacks
    scaled: int | DiceExpression = (
        attacks.scaled(models) if isinstance(attacks, DiceExpression) else attacks * models
    )
    profile = WeaponProfile(
        name=weapon.profile.name,
        attacks=scaled,
        skill=weapon.profile.skill,
        strength=weapon.profile.strength,
        ap=weapon.profile.ap,
        damage=weapon.profile.damage,
    )
    return Weapon(profile=profile, abilities=weapon.abilities)


@dataclass(frozen=True)
class WeaponActivationResult:
    """One weapon profile's contribution to a unit activation."""

    weapon_name: str
    models_assigned: int
    combat: CombatResult


@dataclass(frozen=True)
class ActivationResult:
    """Aggregate outcome of a full-unit activation against one target."""

    attacks: int
    hits: int
    critical_hits: int
    wounds: int
    critical_wounds: int
    failed_saves: int
    total_damage: int
    models_killed: int
    damage_mitigated: int
    auto_wounds: int
    target_destroyed: bool
    remaining_models: int
    remaining_wounds_on_damaged_model: int | None
    weapon_results: tuple[WeaponActivationResult, ...]
    final_target: UnitState
