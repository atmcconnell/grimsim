"""ArmyList: static roster / configuration (not runtime state)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from grimsim.models.detachment import Detachment
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection

if TYPE_CHECKING:
    from grimsim.data.points import PointsCatalog


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
        """Sum of explicit selection point costs (v0.2 compatibility)."""
        return sum(selection.total_points for selection in self.selections)

    def points_cost(self, catalog: PointsCatalog) -> int:
        """Sum of catalog costs for this list's ruleset, plus enhancements."""
        return sum(
            selection.catalog_points(catalog, self.ruleset) for selection in self.selections
        )

    @property
    def remaining_points(self) -> int:
        """Points left under the configured limit using explicit selection points."""
        return self.points_limit - self.total_points

    def remaining_catalog_points(self, catalog: PointsCatalog) -> int:
        """Points remaining under the limit using catalog costs."""
        return self.points_limit - self.points_cost(catalog)

    @property
    def selection_count(self) -> int:
        """Number of roster entries (not expanded by quantity)."""
        return len(self.selections)

    @property
    def unit_count(self) -> int:
        """Total units after expanding selection quantities."""
        return sum(selection.quantity for selection in self.selections)
