"""GrimSim: competitive Warhammer 40,000 combat simulation."""

from grimsim.models.combat import CombatContext, CombatResult
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.simulation.combat import simulate_combat
from grimsim.simulation.monte_carlo import MonteCarloResult, simulate_many

__all__ = [
    "CombatContext",
    "CombatResult",
    "MonteCarloResult",
    "Unit",
    "UnitProfile",
    "Weapon",
    "WeaponProfile",
    "simulate_combat",
    "simulate_many",
]

__version__ = "0.1.0"
