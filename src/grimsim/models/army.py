"""Army / UnitState: mutable runtime representation of a roster."""

from __future__ import annotations

from dataclasses import dataclass, field

from grimsim.models.army_list import ArmyList
from grimsim.models.unit import Unit


@dataclass
class UnitState:
    """Mutable in-game state for one instantiated unit.

    Distinct from:
    - ``Unit`` — immutable profile/data
    - ``UnitSelection`` — roster choice / list metadata
    """

    unit: Unit
    starting_models: int
    remaining_models: int
    wounds_on_current_model: int | None = None
    destroyed: bool = False

    def __post_init__(self) -> None:
        if self.starting_models < 1:
            raise ValueError(f"starting_models must be >= 1, got {self.starting_models}")
        if self.remaining_models < 0:
            raise ValueError(f"remaining_models must be >= 0, got {self.remaining_models}")
        if self.remaining_models > self.starting_models:
            raise ValueError("remaining_models cannot exceed starting_models")
        if self.destroyed and self.remaining_models != 0:
            raise ValueError("destroyed units must have remaining_models == 0")

    def apply_models_lost(self, models_killed: int) -> None:
        """Reduce remaining models after an attack sequence.

        Excess kills beyond remaining models are ignored.
        """
        if models_killed < 0:
            raise ValueError(f"models_killed must be >= 0, got {models_killed}")
        if self.destroyed:
            return
        self.remaining_models = max(0, self.remaining_models - models_killed)
        if self.remaining_models == 0:
            self.destroyed = True
            self.wounds_on_current_model = None


@dataclass
class Army:
    """Runtime army instantiated from a static ``ArmyList``.

    Mutating ``units`` must not mutate ``source_list``.
    """

    source_list: ArmyList
    units: list[UnitState] = field(default_factory=list)

    @classmethod
    def from_list(cls, army_list: ArmyList) -> Army:
        """Expand selections into independent ``UnitState`` instances."""
        states: list[UnitState] = []
        for selection in army_list.selections:
            for _ in range(selection.quantity):
                model_count = selection.unit.profile.model_count
                states.append(
                    UnitState(
                        unit=selection.unit,
                        starting_models=model_count,
                        remaining_models=model_count,
                    )
                )
        return cls(source_list=army_list, units=states)

    @property
    def remaining_units(self) -> list[UnitState]:
        """Units that are not destroyed."""
        return [state for state in self.units if not state.destroyed]

    @property
    def destroyed_units(self) -> list[UnitState]:
        """Units with no models remaining."""
        return [state for state in self.units if state.destroyed]
