"""Future full-unit activation API (stub for v0.3).

v0.2 establishes ``UnitState`` so a later milestone can resolve all weapon
profiles on a unit against a target without requiring ArmyList for the
existing low-level ``simulate_combat`` API.
"""

from __future__ import annotations

from grimsim.models.army import UnitState
from grimsim.models.combat import CombatContext, CombatResult


def simulate_unit_activation(
    attacker: UnitState,
    target: UnitState,
    *,
    context: CombatContext | None = None,
    seed: int | None = None,
) -> list[CombatResult]:
    """Resolve all of an attacker's weapon profiles into a target (v0.3).

    Not implemented in v0.2 — this stub documents the intended next API.

    Raises:
        NotImplementedError: Always, until v0.3.
    """
    _ = (attacker, target, context, seed)
    raise NotImplementedError(
        "simulate_unit_activation is planned for v0.3 "
        "(full-unit activation with multiple weapon profiles)."
    )
