"""Weapon domain models."""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.ability import Ability
from grimsim.models.dice import DiceExpression


@dataclass(frozen=True)
class WeaponProfile:
    """Numeric profile for a single weapon mode.

    Attributes:
        name: Display name for this profile.
        attacks: Fixed attack count or a dice expression.
        skill: Ballistic/Weapon Skill threshold (e.g. 3 for 3+).
        strength: Weapon strength characteristic.
        ap: Armour Penetration (0, -1, -2, …) in datasheet convention.
        damage: Fixed damage or a dice expression per successful wound.
    """

    name: str
    attacks: int | DiceExpression
    skill: int
    strength: int
    ap: int
    damage: int | DiceExpression

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("weapon profile name must be non-empty")
        if isinstance(self.attacks, int) and self.attacks < 0:
            raise ValueError(f"attacks must be >= 0, got {self.attacks}")
        if not 2 <= self.skill <= 6:
            raise ValueError(f"skill must be 2-6, got {self.skill}")
        if self.strength < 1:
            raise ValueError(f"strength must be >= 1, got {self.strength}")
        if isinstance(self.damage, int) and self.damage < 1:
            raise ValueError(f"damage must be >= 1, got {self.damage}")


@dataclass(frozen=True)
class Weapon:
    """A weapon composed of a profile and optional abilities."""

    profile: WeaponProfile
    abilities: tuple[Ability, ...] = ()
