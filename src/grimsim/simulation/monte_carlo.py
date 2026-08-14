"""Monte Carlo combat simulation layer."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from grimsim.models.combat import CombatContext, CombatResult
from grimsim.models.unit import Unit
from grimsim.models.weapon import Weapon
from grimsim.rules.engine import RuleEngine
from grimsim.simulation.combat import simulate_combat


@dataclass(frozen=True)
class MonteCarloResult:
    """Aggregated statistics from many combat simulations."""

    iterations: int
    mean_damage: float
    median_damage: float
    std_damage: float
    mean_models_killed: float
    median_models_killed: float
    probability_target_destroyed: float
    min_models_killed: int
    max_models_killed: int
    _damage: np.ndarray
    _models_killed: np.ndarray
    _results: tuple[CombatResult, ...]

    def probability_models_killed_at_least(self, n: int) -> float:
        """P(models_killed >= n)."""
        if self.iterations == 0:
            return 0.0
        return float(np.mean(self._models_killed >= n))

    def probability_damage_at_least(self, n: int) -> float:
        """P(total_damage >= n)."""
        if self.iterations == 0:
            return 0.0
        return float(np.mean(self._damage >= n))

    def to_dataframe(self) -> pd.DataFrame:
        """Return one row per simulation iteration."""
        rows = [
            {
                "iteration": i,
                "attacks": r.attacks,
                "hits": r.hits,
                "critical_hits": r.critical_hits,
                "wounds": r.wounds,
                "critical_wounds": r.critical_wounds,
                "failed_saves": r.failed_saves,
                "total_damage": r.total_damage,
                "models_killed": r.models_killed,
                "remaining_models": r.remaining_models,
                "remaining_wounds_on_damaged_model": r.remaining_wounds_on_damaged_model,
                "damage_mitigated": r.damage_mitigated,
                "auto_wounds": r.auto_wounds,
            }
            for i, r in enumerate(self._results)
        ]
        return pd.DataFrame(rows)


def simulate_many(
    attacker: Unit,
    weapon: Weapon,
    target: Unit,
    iterations: int,
    *,
    seed: int | None = None,
    context: CombatContext | None = None,
    engine: RuleEngine | None = None,
) -> MonteCarloResult:
    """Run ``iterations`` independent combat simulations.

    Uses a single seeded parent generator; each iteration draws from it so
    the overall sequence is deterministic for a given seed.
    """
    if iterations < 0:
        raise ValueError(f"iterations must be >= 0, got {iterations}")

    rng = np.random.default_rng(seed)
    active_engine = engine if engine is not None else RuleEngine()
    active_context = context if context is not None else CombatContext()

    results: list[CombatResult] = []
    for _ in range(iterations):
        # Derive a child seed so each iteration is independent but reproducible.
        child_seed = int(rng.integers(0, 2**63 - 1))
        child_rng = np.random.default_rng(child_seed)
        results.append(
            simulate_combat(
                attacker=attacker,
                weapon=weapon,
                target=target,
                rng=child_rng,
                context=active_context,
                engine=active_engine,
            )
        )

    damage = np.array([r.total_damage for r in results], dtype=np.float64)
    killed = np.array([r.models_killed for r in results], dtype=np.float64)
    damage.flags.writeable = False
    killed.flags.writeable = False
    starting_models = target.profile.model_count

    if iterations == 0:
        return MonteCarloResult(
            iterations=0,
            mean_damage=0.0,
            median_damage=0.0,
            std_damage=0.0,
            mean_models_killed=0.0,
            median_models_killed=0.0,
            probability_target_destroyed=0.0,
            min_models_killed=0,
            max_models_killed=0,
            _damage=damage,
            _models_killed=killed,
            _results=tuple(results),
        )

    destroyed = float(np.mean(killed >= starting_models))

    return MonteCarloResult(
        iterations=iterations,
        mean_damage=float(np.mean(damage)),
        median_damage=float(np.median(damage)),
        std_damage=float(np.std(damage, ddof=0)),
        mean_models_killed=float(np.mean(killed)),
        median_models_killed=float(np.median(killed)),
        probability_target_destroyed=destroyed,
        min_models_killed=int(np.min(killed)),
        max_models_killed=int(np.max(killed)),
        _damage=damage,
        _models_killed=killed,
        _results=tuple(results),
    )
