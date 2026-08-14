"""Unit domain models."""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.ability import Ability
from grimsim.models.weapon import Weapon


@dataclass(frozen=True)
class UnitProfile:
    """Numeric profile for a unit of models.

    Attributes:
        name: Display name.
        model_count: Number of models in the unit.
        toughness: Toughness characteristic.
        wounds_per_model: Wounds characteristic per model.
        save: Armour save threshold (e.g. 3 for 3+).
        invulnerable_save: Optional invulnerable save threshold.
        objective_control: OC characteristic (unused in v0.1 combat).
    """

    name: str
    model_count: int
    toughness: int
    wounds_per_model: int
    save: int
    invulnerable_save: int | None = None
    objective_control: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("unit profile name must be non-empty")
        if self.model_count < 1:
            raise ValueError(f"model_count must be >= 1, got {self.model_count}")
        if self.toughness < 1:
            raise ValueError(f"toughness must be >= 1, got {self.toughness}")
        if self.wounds_per_model < 1:
            raise ValueError(f"wounds_per_model must be >= 1, got {self.wounds_per_model}")
        if not 2 <= self.save <= 7:
            raise ValueError(f"save must be 2-7, got {self.save}")
        if self.invulnerable_save is not None and not 2 <= self.invulnerable_save <= 6:
            raise ValueError(
                f"invulnerable_save must be 2-6 when set, got {self.invulnerable_save}"
            )
        if self.objective_control < 0:
            raise ValueError(f"objective_control must be >= 0, got {self.objective_control}")


@dataclass(frozen=True)
class Unit:
    """A unit composed of a profile, weapons, and optional abilities."""

    profile: UnitProfile
    weapons: tuple[Weapon, ...]
    abilities: tuple[Ability, ...] = ()
