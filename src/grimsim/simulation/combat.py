"""Single-combat simulation API."""

from __future__ import annotations

import numpy as np

from grimsim.models.combat import CombatContext, CombatResult
from grimsim.models.unit import Unit
from grimsim.models.weapon import Weapon
from grimsim.rules.engine import RuleEngine


def simulate_combat(
    attacker: Unit,
    weapon: Weapon,
    target: Unit,
    *,
    seed: int | None = None,
    rng: np.random.Generator | None = None,
    context: CombatContext | None = None,
    engine: RuleEngine | None = None,
) -> CombatResult:
    """Run a single attack sequence and return a typed ``CombatResult``.

    Provide either ``seed`` (creates a fresh Generator) or an injected ``rng``.
    If both are omitted, a non-deterministic default generator is used.

    This is the primary public API for one-shot combat resolution.
    """
    if rng is not None and seed is not None:
        raise ValueError("provide seed or rng, not both")
    if rng is None:
        rng = np.random.default_rng(seed)

    active_engine = engine if engine is not None else RuleEngine()
    active_context = context if context is not None else CombatContext()
    return active_engine.resolve_attack_sequence(
        attacker=attacker,
        weapon=weapon,
        target=target,
        context=active_context,
        rng=rng,
    )


class CombatSimulator:
    """Optional object-oriented wrapper around ``simulate_combat``."""

    def __init__(self, engine: RuleEngine | None = None) -> None:
        self._engine = engine if engine is not None else RuleEngine()

    def simulate(
        self,
        attacker: Unit,
        weapon: Weapon,
        target: Unit,
        *,
        seed: int | None = None,
        rng: np.random.Generator | None = None,
        context: CombatContext | None = None,
    ) -> CombatResult:
        return simulate_combat(
            attacker=attacker,
            weapon=weapon,
            target=target,
            seed=seed,
            rng=rng,
            context=context,
            engine=self._engine,
        )
