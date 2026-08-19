"""UnitSelection: a unit chosen as part of an army list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from grimsim.models.enhancement import Enhancement
from grimsim.models.unit import Unit

if TYPE_CHECKING:
    from grimsim.data.points import PointsCatalog
    from grimsim.models.ruleset import Ruleset


@dataclass(frozen=True)
class UnitSelection:
    """Roster choice wrapping an immutable combat ``Unit`` profile.

    ``points`` is an optional explicit override (v0.2 compatibility). Versioned
    costs should be looked up from a ``PointsCatalog`` via ``catalog_points``.
    ``model_count`` overrides the profile size for this selection when set.
    """

    unit: Unit
    quantity: int = 1
    points: int = 0
    enhancements: tuple[Enhancement, ...] = ()
    model_count: int | None = None

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError(f"quantity must be >= 1, got {self.quantity}")
        if self.points < 0:
            raise ValueError(f"points must be >= 0, got {self.points}")
        if self.model_count is not None and self.model_count < 1:
            raise ValueError(f"model_count must be >= 1, got {self.model_count}")
        seen: set[str] = set()
        for enhancement in self.enhancements:
            if enhancement.id in seen:
                raise ValueError(f"duplicate enhancement id: {enhancement.id}")
            seen.add(enhancement.id)

    @property
    def size(self) -> int:
        """Models in this selection (override or profile default)."""
        return self.model_count if self.model_count is not None else self.unit.profile.model_count

    @property
    def total_points(self) -> int:
        """Explicit points for all copies plus attached enhancements."""
        return self.points * self.quantity + sum(e.points for e in self.enhancements)

    def catalog_points(self, catalog: PointsCatalog, ruleset: Ruleset) -> int:
        """Points from the catalog under ``ruleset``, plus enhancements."""
        unit_cost = catalog.cost_for(self.unit, ruleset, model_count=self.size)
        return unit_cost * self.quantity + sum(e.points for e in self.enhancements)
