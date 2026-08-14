"""Combat analysis helpers built on Monte Carlo results."""

from __future__ import annotations

from grimsim.models.unit import Unit
from grimsim.models.weapon import Weapon
from grimsim.simulation.monte_carlo import MonteCarloResult, simulate_many


def summarize_matchup(
    attacker: Unit,
    weapon: Weapon,
    target: Unit,
    *,
    iterations: int = 10_000,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Run a Monte Carlo matchup and return aggregated statistics.

    This is a thin analysis convenience wrapper around ``simulate_many``.
    """
    return simulate_many(
        attacker=attacker,
        weapon=weapon,
        target=target,
        iterations=iterations,
        seed=seed,
    )
