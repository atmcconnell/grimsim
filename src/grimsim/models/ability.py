"""Reusable combat ability objects.

Abilities are small typed objects composed onto units and weapons.
The rule engine discovers them via composition — never by unit name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Ability(Protocol):
    """Marker protocol for all combat abilities."""

    @property
    def name(self) -> str:
        """Human-readable ability name."""
        ...


@runtime_checkable
class HitAbility(Protocol):
    """Ability that participates in the hit stage."""

    @property
    def name(self) -> str: ...

    def is_reroll_hit_ones(self) -> bool: ...

    def sustained_hits_bonus(self) -> int: ...

    def causes_lethal_hits(self) -> bool: ...


@runtime_checkable
class WoundAbility(Protocol):
    """Ability that participates in the wound stage."""

    @property
    def name(self) -> str: ...

    def is_reroll_wound_ones(self) -> bool: ...


@runtime_checkable
class DamageMitigationAbility(Protocol):
    """Ability that mitigates incoming damage (e.g. Feel No Pain)."""

    @property
    def name(self) -> str: ...

    def feel_no_pain_threshold(self) -> int | None:
        """Return the FNP threshold (e.g. 5 for 5+), or None if not FNP."""
        ...


@dataclass(frozen=True)
class RerollHitOnes:
    """Reroll hit rolls of 1 (once)."""

    @property
    def name(self) -> str:
        return "Reroll Hit Ones"

    def is_reroll_hit_ones(self) -> bool:
        return True

    def sustained_hits_bonus(self) -> int:
        return 0

    def causes_lethal_hits(self) -> bool:
        return False


@dataclass(frozen=True)
class RerollWoundOnes:
    """Reroll wound rolls of 1 (once)."""

    @property
    def name(self) -> str:
        return "Reroll Wound Ones"

    def is_reroll_wound_ones(self) -> bool:
        return True


@dataclass(frozen=True)
class SustainedHits:
    """Critical hits generate ``value`` additional hits."""

    value: int = 1

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError(f"Sustained Hits value must be >= 1, got {self.value}")

    @property
    def name(self) -> str:
        return f"Sustained Hits {self.value}"

    def is_reroll_hit_ones(self) -> bool:
        return False

    def sustained_hits_bonus(self) -> int:
        return self.value

    def causes_lethal_hits(self) -> bool:
        return False


@dataclass(frozen=True)
class LethalHits:
    """Critical hits automatically wound the target."""

    @property
    def name(self) -> str:
        return "Lethal Hits"

    def is_reroll_hit_ones(self) -> bool:
        return False

    def sustained_hits_bonus(self) -> int:
        return 0

    def causes_lethal_hits(self) -> bool:
        return True


@dataclass(frozen=True)
class FeelNoPain:
    """Ignore each point of damage on a roll of ``threshold`` or higher."""

    threshold: int

    def __post_init__(self) -> None:
        if not 2 <= self.threshold <= 6:
            raise ValueError(f"Feel No Pain threshold must be 2-6, got {self.threshold}")

    @property
    def name(self) -> str:
        return f"Feel No Pain {self.threshold}+"

    def feel_no_pain_threshold(self) -> int | None:
        return self.threshold
