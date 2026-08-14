"""Faction identity as data (not behavior)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Faction:
    """Faction identity.

    Do not encode faction-specific combat behavior here. Attach reusable
    rule/effect objects elsewhere when those systems exist.
    """

    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("faction id must be non-empty")
        if not self.name.strip():
            raise ValueError("faction name must be non-empty")
