"""ArmyList: static roster / configuration (not runtime state)."""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.detachment import Detachment
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection


@dataclass(frozen=True)
class ArmyList:
    """Static army roster under a faction, detachment, and ruleset.

    This is configuration/intent — not in-game state. Use ``Army.from_list``
    to instantiate a runtime representation.
    """

    name: str
    faction: Faction
    detachment: Detachment
    ruleset: Ruleset
    selections: tuple[UnitSelection, ...]
    points_limit: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("army list name must be non-empty")
        if self.points_limit < 0:
            raise ValueError(f"points_limit must be >= 0, got {self.points_limit}")

    @property
    def total_points(self) -> int:
        """Sum of all selection point costs."""
        return sum(selection.total_points for selection in self.selections)

    @property
    def remaining_points(self) -> int:
        """Points left under the configured limit (may be negative if over)."""
        return self.points_limit - self.total_points

    @property
    def selection_count(self) -> int:
        """Number of roster entries (not expanded by quantity)."""
        return len(self.selections)

    @property
    def unit_count(self) -> int:
        """Total units after expanding selection quantities."""
        return sum(selection.quantity for selection in self.selections)
