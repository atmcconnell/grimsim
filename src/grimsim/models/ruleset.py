"""Ruleset: edition / rules / points environment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Ruleset:
    """Immutable rules and points environment for list construction and analysis.

    Domain logic must not load this from DuckDB during combat resolution.
    Persistence adapters may store/load ``Ruleset`` values separately.
    """

    edition: str
    rules_version: str
    points_version: str
    effective_date: date
    id: str | None = None

    def __post_init__(self) -> None:
        if not self.edition.strip():
            raise ValueError("edition must be non-empty")
        if not self.rules_version.strip():
            raise ValueError("rules_version must be non-empty")
        if not self.points_version.strip():
            raise ValueError("points_version must be non-empty")
        if self.id is not None and not self.id.strip():
            raise ValueError("id must be non-empty when provided")

    @property
    def slug(self) -> str:
        """Stable identifier: explicit ``id`` or a derived key."""
        if self.id is not None:
            return self.id
        return f"{self.edition}:{self.rules_version}:{self.points_version}"
