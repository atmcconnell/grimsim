"""Enhancement: list-composition metadata (no combat logic in v0.2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Enhancement:
    """An enhancement attached to a unit selection.

    Points and identity only — enhancement combat rules are out of scope.
    """

    id: str
    name: str
    points: int

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("enhancement id must be non-empty")
        if not self.name.strip():
            raise ValueError("enhancement name must be non-empty")
        if self.points < 0:
            raise ValueError(f"enhancement points must be >= 0, got {self.points}")
