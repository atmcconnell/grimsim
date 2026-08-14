"""GrimSim: competitive Warhammer 40,000 combat simulation."""

from grimsim.models.army import Army, UnitState
from grimsim.models.army_list import ArmyList
from grimsim.models.combat import CombatContext, CombatResult
from grimsim.models.detachment import Detachment
from grimsim.models.enhancement import Enhancement
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.simulation.combat import simulate_combat
from grimsim.simulation.monte_carlo import MonteCarloResult, simulate_many
from grimsim.validation import validate_army_list

__all__ = [
    "Army",
    "ArmyList",
    "CombatContext",
    "CombatResult",
    "Detachment",
    "Enhancement",
    "Faction",
    "MonteCarloResult",
    "Ruleset",
    "Unit",
    "UnitProfile",
    "UnitSelection",
    "UnitState",
    "Weapon",
    "WeaponProfile",
    "simulate_combat",
    "simulate_many",
    "validate_army_list",
]

__version__ = "0.2.0"
