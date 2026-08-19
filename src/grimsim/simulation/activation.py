"""Full-unit combat activation against a shared evolving target."""

from __future__ import annotations

import numpy as np

from grimsim.models.activation import (
    ActivationResult,
    AttackPlan,
    WeaponActivationResult,
    scale_weapon_for_models,
)
from grimsim.models.army import UnitState
from grimsim.models.combat import CombatContext, CombatResult
from grimsim.rules.engine import RuleEngine


def simulate_unit_activation(
    attacker: UnitState,
    target: UnitState,
    attack_plan: AttackPlan | None = None,
    *,
    context: CombatContext | None = None,
    seed: int | None = None,
    rng: np.random.Generator | None = None,
    engine: RuleEngine | None = None,
    apply_to_target: bool = False,
) -> ActivationResult:
    """Resolve every assignment in ``attack_plan`` into one evolving target.

    Surviving attacker models only are used. Weapons later in the plan see
    the target after earlier weapons have allocated damage. Immutable unit
    profiles are not mutated.

    If ``attack_plan`` is omitted, every remaining model fires every weapon
    on the attacker profile (overlapping assignments).

    Args:
        apply_to_target: If True, copy the final remaining models/wounds onto
            the provided ``target`` ``UnitState``.
    """
    if rng is not None and seed is not None:
        raise ValueError("provide seed or rng, not both")
    if rng is None:
        rng = np.random.default_rng(seed)

    plan = (
        attack_plan
        if attack_plan is not None
        else AttackPlan.all_remaining_fire_all_weapons(attacker)
    )
    plan.validate(attacker)

    active_engine = engine if engine is not None else RuleEngine()
    active_context = context if context is not None else CombatContext()

    working_target = target.copy()
    weapon_results: list[WeaponActivationResult] = []

    for assignment in plan.assignments:
        if working_target.remaining_models <= 0:
            combat = CombatResult(
                attacks=0,
                hits=0,
                critical_hits=0,
                wounds=0,
                critical_wounds=0,
                failed_saves=0,
                total_damage=0,
                models_killed=0,
                remaining_models=0,
                remaining_wounds_on_damaged_model=None,
                damage_mitigated=0,
                auto_wounds=0,
            )
        else:
            scaled = scale_weapon_for_models(assignment.weapon, assignment.models)
            combat = active_engine.resolve_attack_sequence(
                attacker=attacker.unit,
                weapon=scaled,
                target=working_target.unit,
                context=active_context,
                rng=rng,
                target_remaining_models=working_target.remaining_models,
                target_wounds_on_current=working_target.wounds_on_current_model,
            )
            working_target.apply_combat_result(
                combat.remaining_models,
                combat.remaining_wounds_on_damaged_model,
            )

        weapon_results.append(
            WeaponActivationResult(
                weapon_name=assignment.weapon.profile.name,
                models_assigned=assignment.models,
                combat=combat,
            )
        )

    if apply_to_target:
        target.apply_combat_result(
            working_target.remaining_models,
            working_target.wounds_on_current_model,
        )

    return ActivationResult(
        attacks=sum(r.combat.attacks for r in weapon_results),
        hits=sum(r.combat.hits for r in weapon_results),
        critical_hits=sum(r.combat.critical_hits for r in weapon_results),
        wounds=sum(r.combat.wounds for r in weapon_results),
        critical_wounds=sum(r.combat.critical_wounds for r in weapon_results),
        failed_saves=sum(r.combat.failed_saves for r in weapon_results),
        total_damage=sum(r.combat.total_damage for r in weapon_results),
        models_killed=sum(r.combat.models_killed for r in weapon_results),
        damage_mitigated=sum(r.combat.damage_mitigated for r in weapon_results),
        auto_wounds=sum(r.combat.auto_wounds for r in weapon_results),
        target_destroyed=working_target.destroyed,
        remaining_models=working_target.remaining_models,
        remaining_wounds_on_damaged_model=working_target.wounds_on_current_model,
        weapon_results=tuple(weapon_results),
        final_target=working_target,
    )
