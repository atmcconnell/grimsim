"""GrimSim: competitive Warhammer 40,000 combat simulation."""

from grimsim.models.activation import ActivationResult, AttackPlan, WeaponAssignment
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
from grimsim.simulation.activation import simulate_unit_activation
from grimsim.simulation.activation_monte_carlo import (
    MonteCarloActivationResult,
    simulate_many_unit_activations,
)
from grimsim.simulation.combat import simulate_combat
from grimsim.simulation.monte_carlo import MonteCarloResult, simulate_many
from grimsim.validation import validate_army_list

__all__ = [
    "ActivationResult",
    "Army",
    "ArmyList",
    "AttackPlan",
    "CombatContext",
    "CombatResult",
    "Detachment",
    "Enhancement",
    "Faction",
    "MonteCarloActivationResult",
    "MonteCarloResult",
    "Ruleset",
    "Unit",
    "UnitProfile",
    "UnitSelection",
    "UnitState",
    "Weapon",
    "WeaponAssignment",
    "WeaponProfile",
    "simulate_combat",
    "simulate_many",
    "simulate_many_unit_activations",
    "simulate_unit_activation",
    "validate_army_list",
]

__version__ = "0.3.0"
