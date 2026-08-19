"""Ruleset-aware points catalog.

Points are looked up from ``(unit identity, ruleset, model count)``, not stored
as timeless properties of a unit profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from grimsim.models.ruleset import Ruleset
from grimsim.models.unit import Unit


class MissingPointsError(LookupError):
    """No points entry exists for the requested unit/ruleset/size."""


@dataclass(frozen=True)
class PointsEntry:
    """One published cost for a unit configuration under a ruleset."""

    unit_id: str
    ruleset_id: str
    model_count: int
    points: int
    effective_date: date | None = None

    def __post_init__(self) -> None:
        if not self.unit_id.strip():
            raise ValueError("unit_id must be non-empty")
        if not self.ruleset_id.strip():
            raise ValueError("ruleset_id must be non-empty")
        if self.model_count < 1:
            raise ValueError(f"model_count must be >= 1, got {self.model_count}")
        if self.points < 0:
            raise ValueError(f"points must be >= 0, got {self.points}")


@dataclass(frozen=True)
class PointsCatalog:
    """Immutable in-memory points table. Not a global and not loaded from the web."""

    entries: tuple[PointsEntry, ...] = ()

    def cost_for(
        self,
        unit: Unit | str,
        ruleset: Ruleset,
        model_count: int,
        *,
        as_of: date | None = None,
    ) -> int:
        """Return points for ``unit`` at ``model_count`` under ``ruleset``.

        ``as_of`` defaults to ``ruleset.effective_date`` for historical lookup
        among dated entries.
        """
        found = self.try_cost_for(unit, ruleset, model_count, as_of=as_of)
        if found is None:
            unit_id = unit.identity if isinstance(unit, Unit) else unit
            raise MissingPointsError(
                f"No points for unit={unit_id!r} ruleset={ruleset.slug!r} "
                f"models={model_count}"
            )
        return found

    def try_cost_for(
        self,
        unit: Unit | str,
        ruleset: Ruleset,
        model_count: int,
        *,
        as_of: date | None = None,
    ) -> int | None:
        """Like ``cost_for`` but returns ``None`` when missing."""
        unit_id = unit.identity if isinstance(unit, Unit) else unit
        when = as_of if as_of is not None else ruleset.effective_date
        matches = [
            entry
            for entry in self.entries
            if entry.unit_id == unit_id
            and entry.ruleset_id == ruleset.slug
            and entry.model_count == model_count
        ]
        if not matches:
            return None

        dated = [e for e in matches if e.effective_date is not None]
        undated = [e for e in matches if e.effective_date is None]
        eligible_dated = [
            e for e in dated if e.effective_date is not None and e.effective_date <= when
        ]
        if eligible_dated:
            latest = max(eligible_dated, key=lambda e: e.effective_date or date.min)
            return latest.points
        if undated:
            return undated[-1].points
        return None

    def available_sizes(self, unit: Unit | str, ruleset: Ruleset) -> tuple[int, ...]:
        """Model counts that have at least one entry under ``ruleset``."""
        unit_id = unit.identity if isinstance(unit, Unit) else unit
        sizes = sorted(
            {
                e.model_count
                for e in self.entries
                if e.unit_id == unit_id and e.ruleset_id == ruleset.slug
            }
        )
        return tuple(sizes)
