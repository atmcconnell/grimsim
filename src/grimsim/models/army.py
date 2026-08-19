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
        if self.remaining_models == 0:
            self.wounds_on_current_model = None
            self.destroyed = True
        elif self.wounds_on_current_model is not None:
            max_wounds = self.unit.profile.wounds_per_model
            if not 1 <= self.wounds_on_current_model <= max_wounds:
                raise ValueError(
                    f"wounds_on_current_model must be 1..{max_wounds} or None, "
                    f"got {self.wounds_on_current_model}"
                )
            if self.wounds_on_current_model == max_wounds:
                self.wounds_on_current_model = None

    def apply_models_lost(self, models_killed: int) -> None:
        """Reduce remaining models after an attack sequence.

        Excess kills beyond remaining models are ignored. Killing models
        always removes the currently wounded model first, so partial wounds
        are cleared whenever at least one model dies.
        """
        if models_killed < 0:
            raise ValueError(f"models_killed must be >= 0, got {models_killed}")
        if self.destroyed:
            return
        self.remaining_models = max(0, self.remaining_models - models_killed)
        if self.remaining_models == 0:
            self.destroyed = True
            self.wounds_on_current_model = None
        elif models_killed > 0:
            self.wounds_on_current_model = None

    @classmethod
    def from_unit(
        cls,
        unit: Unit,
        *,
        remaining_models: int | None = None,
        wounds_on_current_model: int | None = None,
    ) -> UnitState:
        """Wrap an immutable ``Unit`` as fresh (or partially depleted) runtime state."""
        starting = unit.profile.model_count
        remaining = starting if remaining_models is None else remaining_models
        return cls(
            unit=unit,
            starting_models=starting,
            remaining_models=remaining,
            wounds_on_current_model=wounds_on_current_model,
            destroyed=remaining == 0,
        )

    def apply_combat_result(self, remaining_models: int, remaining_wounds: int | None) -> None:
        """Update this state to match an allocation result."""
        if remaining_models < 0:
            raise ValueError(f"remaining_models must be >= 0, got {remaining_models}")
        self.remaining_models = min(remaining_models, self.starting_models)
        self.wounds_on_current_model = remaining_wounds if self.remaining_models > 0 else None
        self.destroyed = self.remaining_models == 0

    def copy(self) -> UnitState:
        """Return an independent copy sharing the immutable ``unit`` profile."""
        return UnitState(
            unit=self.unit,
            starting_models=self.starting_models,
            remaining_models=self.remaining_models,
            wounds_on_current_model=self.wounds_on_current_model,
            destroyed=self.destroyed,
        )


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
                model_count = selection.size
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
