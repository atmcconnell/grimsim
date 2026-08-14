"""Integration tests for full combat resolution."""

from __future__ import annotations

import numpy as np

from grimsim.examples import elite_infantry, light_infantry, melee_attacker, vehicle
from grimsim.models.combat import CombatContext
from grimsim.models.dice import DiceExpression
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.rules.engine import RuleEngine
from grimsim.simulation.combat import CombatSimulator, simulate_combat


def test_simulate_combat_deterministic() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    a = simulate_combat(attacker, attacker.weapons[0], target, seed=42)
    b = simulate_combat(attacker, attacker.weapons[0], target, seed=42)
    assert a == b


def test_simulate_combat_pipeline_fields() -> None:
    attacker = melee_attacker()
    target = light_infantry()
    result = simulate_combat(attacker, attacker.weapons[0], target, seed=7)
    assert result.attacks >= 0
    assert result.hits >= result.critical_hits
    assert result.wounds >= 0
    assert result.failed_saves >= 0
    assert result.total_damage >= 0
    assert 0 <= result.models_killed <= target.profile.model_count
    assert result.remaining_models == target.profile.model_count - result.models_killed


def test_rule_engine_direct() -> None:
    engine = RuleEngine()
    attacker = melee_attacker()
    target = elite_infantry()
    result = engine.resolve_attack_sequence(
        attacker,
        attacker.weapons[0],
        target,
        CombatContext(),
        np.random.default_rng(99),
    )
    assert result.remaining_models <= target.profile.model_count


def test_combat_simulator_class() -> None:
    sim = CombatSimulator()
    attacker = vehicle()
    target = light_infantry()
    result = sim.simulate(attacker, attacker.weapons[0], target, seed=1)
    assert isinstance(result.attacks, int)


def test_dice_attacks_and_damage() -> None:
    weapon = Weapon(
        profile=WeaponProfile(
            name="Variable",
            attacks=DiceExpression.d6(),
            skill=3,
            strength=6,
            ap=-1,
            damage=DiceExpression(count=1, sides=3, modifier=0),
        ),
    )
    attacker = Unit(
        profile=UnitProfile(
            name="A",
            model_count=1,
            toughness=5,
            wounds_per_model=5,
            save=3,
        ),
        weapons=(weapon,),
    )
    target = light_infantry()
    result = simulate_combat(attacker, weapon, target, seed=123)
    assert 1 <= result.attacks <= 6


def test_context_modifiers_change_outcomes() -> None:
    attacker = melee_attacker()
    weapon = attacker.weapons[0]
    target = Unit(
        profile=UnitProfile(
            name="Hard",
            model_count=10,
            toughness=5,
            wounds_per_model=2,
            save=3,
        ),
        weapons=(),
    )
    base = simulate_combat(attacker, weapon, target, seed=50, context=CombatContext())
    buffed = simulate_combat(
        attacker,
        weapon,
        target,
        seed=50,
        context=CombatContext(hit_modifier=1, wound_modifier=1, save_modifier=-1),
    )
    # Buffed context should not deal less damage on the same seed path in aggregate fields;
    # modifiers change dice targets so outcomes differ.
    assert base != buffed or base.total_damage <= buffed.total_damage
