"""UnitSelection: a unit chosen as part of an army list."""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.enhancement import Enhancement
from grimsim.models.unit import Unit


@dataclass(frozen=True)
class UnitSelection:
    """Roster choice wrapping an immutable combat ``Unit`` profile.

    ``points`` is the per-copy unit cost under the list's ruleset/points
    version (excluding enhancements). Enhancements are attached once to
    this selection and are not multiplied by ``quantity``.
    """

    unit: Unit
    quantity: int = 1
    points: int = 0
    enhancements: tuple[Enhancement, ...] = ()

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError(f"quantity must be >= 1, got {self.quantity}")
        if self.points < 0:
            raise ValueError(f"points must be >= 0, got {self.points}")
        seen: set[str] = set()
        for enhancement in self.enhancements:
            if enhancement.id in seen:
                raise ValueError(f"duplicate enhancement id: {enhancement.id}")
            seen.add(enhancement.id)

    @property
    def total_points(self) -> int:
        """Points for all copies plus attached enhancements."""
        return self.points * self.quantity + sum(e.points for e in self.enhancements)
