"""Placeholder for future matchup prediction models.

Future models will estimate something like:

    P(win | army, opponent, list composition, mission, terrain, player skill, rules version)

No model is trained in v0.1. scikit-learn is declared as a dependency so the
ML stack is ready when simulation datasets exist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchupFeatures:
    """Feature vector sketch for a future supervised matchup model.

    Fields are intentionally coarse placeholders — real feature engineering
    will follow once Monte Carlo outputs and game results are persisted.
    """

    attacker_army: str
    defender_army: str
    mission: str
    rules_version: str
    player_skill_delta: float = 0.0


@dataclass(frozen=True)
class MatchupModelPlaceholder:
    """Non-functional placeholder documenting the intended ML API.

    Do not call ``predict`` expecting real probabilities — it raises.
    """

    target: str = "P(win | army, opponent, list, mission, terrain, skill, rules)"

    def predict(self, features: MatchupFeatures) -> float:
        """Reserved for a future scikit-learn estimator.

        Raises:
            NotImplementedError: Always, until a real model is trained.
        """
        raise NotImplementedError(
            "Matchup prediction is not implemented in v0.1. "
            f"Future models will estimate {self.target}. "
            f"Received features for {features.attacker_army} vs {features.defender_army}."
        )
