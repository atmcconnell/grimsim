"""Detachment: faction-scoped strategic rules package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from grimsim.models.ability import Ability


@runtime_checkable
class RuleEffect(Protocol):
    """Broad placeholder for future non-combat / detachment rule effects.

    v0.2 does not interpret these during combat. The protocol exists so
    detachments can carry typed hooks without inventing a rules DSL.
    """

    @property
    def name(self) -> str:
        """Human-readable effect name."""
        ...


@dataclass(frozen=True)
class Detachment:
    """A detachment belonging to a single faction.

    ``abilities`` may include combat ``Ability`` objects when relevant.
    ``effects`` holds broader placeholders for future detachment rules.
    """

    id: str
    name: str
    faction_id: str
    abilities: tuple[Ability, ...] = ()
    effects: tuple[RuleEffect, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("detachment id must be non-empty")
        if not self.name.strip():
            raise ValueError("detachment name must be non-empty")
        if not self.faction_id.strip():
            raise ValueError("detachment faction_id must be non-empty")
