"""Monte Carlo for full-unit activations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from grimsim.models.activation import AttackPlan
from grimsim.models.army import UnitState
from grimsim.models.combat import CombatContext
from grimsim.rules.engine import RuleEngine
from grimsim.simulation.activation import simulate_unit_activation


@dataclass(frozen=True)
class MonteCarloActivationResult:
    """Aggregated statistics from many unit activations."""

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
    _destroyed: np.ndarray
    _attacks: np.ndarray
    _hits: np.ndarray
    _wounds: np.ndarray
    _failed_saves: np.ndarray

    def probability_models_killed_at_least(self, n: int) -> float:
        if self.iterations == 0:
            return 0.0
        return float(np.mean(self._models_killed >= n))

    def probability_damage_at_least(self, n: int) -> float:
        if self.iterations == 0:
            return 0.0
        return float(np.mean(self._damage >= n))

    def to_dataframe(self) -> pd.DataFrame:
        """One row per simulation iteration."""
        return pd.DataFrame(
            {
                "iteration": np.arange(self.iterations),
                "attacks": self._attacks,
                "hits": self._hits,
                "wounds": self._wounds,
                "failed_saves": self._failed_saves,
                "total_damage": self._damage,
                "models_killed": self._models_killed,
                "target_destroyed": self._destroyed.astype(bool),
            }
        )


def simulate_many_unit_activations(
    attacker: UnitState,
    target: UnitState,
    attack_plan: AttackPlan | None = None,
    iterations: int = 10_000,
    *,
    seed: int | None = None,
    context: CombatContext | None = None,
    engine: RuleEngine | None = None,
) -> MonteCarloActivationResult:
    """Run ``iterations`` independent unit activations.

    Each iteration copies attacker/target state so the originals are unchanged.
    """
    if iterations < 0:
        raise ValueError(f"iterations must be >= 0, got {iterations}")

    rng = np.random.default_rng(seed)
    active_engine = engine if engine is not None else RuleEngine()
    active_context = context if context is not None else CombatContext()
    plan = (
        attack_plan
        if attack_plan is not None
        else AttackPlan.all_remaining_fire_all_weapons(attacker)
    )
    plan.validate(attacker)

    damage_list: list[int] = []
    killed_list: list[int] = []
    destroyed_list: list[float] = []
    attacks_list: list[int] = []
    hits_list: list[int] = []
    wounds_list: list[int] = []
    failed_list: list[int] = []

    for _ in range(iterations):
        child_seed = int(rng.integers(0, 2**63 - 1))
        child_rng = np.random.default_rng(child_seed)
        result = simulate_unit_activation(
            attacker=attacker.copy(),
            target=target.copy(),
            attack_plan=plan,
            rng=child_rng,
            context=active_context,
            engine=active_engine,
        )
        damage_list.append(result.total_damage)
        killed_list.append(result.models_killed)
        destroyed_list.append(1.0 if result.target_destroyed else 0.0)
        attacks_list.append(result.attacks)
        hits_list.append(result.hits)
        wounds_list.append(result.wounds)
        failed_list.append(result.failed_saves)

    damage = np.array(damage_list, dtype=np.float64)
    killed = np.array(killed_list, dtype=np.float64)
    destroyed = np.array(destroyed_list, dtype=np.float64)
    attacks = np.array(attacks_list, dtype=np.float64)
    hits = np.array(hits_list, dtype=np.float64)
    wounds = np.array(wounds_list, dtype=np.float64)
    failed = np.array(failed_list, dtype=np.float64)
    for arr in (damage, killed, destroyed, attacks, hits, wounds, failed):
        arr.flags.writeable = False

    if iterations == 0:
        return MonteCarloActivationResult(
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
            _destroyed=destroyed,
            _attacks=attacks,
            _hits=hits,
            _wounds=wounds,
            _failed_saves=failed,
        )

    return MonteCarloActivationResult(
        iterations=iterations,
        mean_damage=float(np.mean(damage)),
        median_damage=float(np.median(damage)),
        std_damage=float(np.std(damage, ddof=0)),
        mean_models_killed=float(np.mean(killed)),
        median_models_killed=float(np.median(killed)),
        probability_target_destroyed=float(np.mean(destroyed)),
        min_models_killed=int(np.min(killed)),
        max_models_killed=int(np.max(killed)),
        _damage=damage,
        _models_killed=killed,
        _destroyed=destroyed,
        _attacks=attacks,
        _hits=hits,
        _wounds=wounds,
        _failed_saves=failed,
    )
