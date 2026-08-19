"""Versioned unit profiles: identity + ruleset → Unit.

Does not assume a unit ID maps to one permanent profile.
"""

from __future__ import annotations

from dataclasses import dataclass

from grimsim.models.ruleset import Ruleset
from grimsim.models.unit import Unit


class MissingProfileError(LookupError):
    """No profile exists for the requested unit identity under a ruleset."""


@dataclass(frozen=True)
class ProfileEntry:
    """A full unit (profile + weapons + abilities) published for a ruleset."""

    unit_id: str
    ruleset_id: str
    unit: Unit

    def __post_init__(self) -> None:
        if not self.unit_id.strip():
            raise ValueError("unit_id must be non-empty")
        if not self.ruleset_id.strip():
            raise ValueError("ruleset_id must be non-empty")


@dataclass(frozen=True)
class ProfileCatalog:
    """Immutable lookup of ``Unit`` snapshots keyed by identity and ruleset."""

    entries: tuple[ProfileEntry, ...] = ()

    def unit_for(self, unit_id: str, ruleset: Ruleset) -> Unit:
        """Return the unit snapshot for ``unit_id`` under ``ruleset``."""
        found = self.try_unit_for(unit_id, ruleset)
        if found is None:
            raise MissingProfileError(
                f"No profile for unit={unit_id!r} ruleset={ruleset.slug!r}"
            )
        return found

    def try_unit_for(self, unit_id: str, ruleset: Ruleset) -> Unit | None:
        found: Unit | None = None
        for entry in self.entries:
            if entry.unit_id == unit_id and entry.ruleset_id == ruleset.slug:
                found = entry.unit
        return found
