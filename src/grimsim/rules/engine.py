"""Combat rule engine orchestrating attack sequence stages."""

from __future__ import annotations

import numpy as np

from grimsim.models.combat import CombatContext, CombatResult
from grimsim.models.dice import resolve_value
from grimsim.models.unit import Unit
from grimsim.models.weapon import Weapon
from grimsim.rules.damage import resolve_damage
from grimsim.rules.hits import resolve_hits
from grimsim.rules.saves import resolve_saves
from grimsim.rules.wounds import resolve_wounds


class RuleEngine:
    """Interprets unit/weapon data and resolves a full attack sequence.

    Units describe data. This engine interprets that data. Simulators call
    this engine repeatedly.
    """

    def resolve_attack_sequence(
        self,
        attacker: Unit,
        weapon: Weapon,
        target: Unit,
        context: CombatContext,
        rng: np.random.Generator,
        *,
        target_remaining_models: int | None = None,
        target_wounds_on_current: int | None = None,
    ) -> CombatResult:
        """Resolve attacks → hits → wounds → saves → damage → allocation.

        Optional target remaining/wounds let a unit activation share one
        evolving target without mutating immutable profiles.
        """
        remaining = (
            target.profile.model_count
            if target_remaining_models is None
            else target_remaining_models
        )
        if remaining < 0:
            raise ValueError(f"target_remaining_models must be >= 0, got {remaining}")
        if remaining == 0:
            return CombatResult(
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

        profile = weapon.profile

        # Combine weapon and attacker abilities for offensive stages.
        offensive_abilities: tuple[object, ...] = (
            *weapon.abilities,
            *attacker.abilities,
        )
        defensive_abilities: tuple[object, ...] = target.abilities

        attacks = resolve_value(profile.attacks, rng)
        if attacks < 0:
            raise ValueError(f"resolved attacks must be >= 0, got {attacks}")

        hit_result = resolve_hits(
            attacks=attacks,
            skill=profile.skill,
            hit_modifier=context.hit_modifier,
            abilities=offensive_abilities,
            rng=rng,
        )

        wound_result = resolve_wounds(
            hits_to_wound=hit_result.hits_to_wound,
            strength=profile.strength,
            toughness=target.profile.toughness,
            wound_modifier=context.wound_modifier,
            abilities=offensive_abilities,
            rng=rng,
        )

        total_wounds = wound_result.wounds + hit_result.auto_wounds

        save_result = resolve_saves(
            wounds=total_wounds,
            armor_save=target.profile.save,
            ap=profile.ap,
            invulnerable_save=target.profile.invulnerable_save,
            save_modifier=context.save_modifier,
            rng=rng,
        )

        allocation = resolve_damage(
            failed_saves=save_result.failed_saves,
            damage=profile.damage,
            model_count=remaining,
            wounds_per_model=target.profile.wounds_per_model,
            target_abilities=defensive_abilities,
            rng=rng,
            starting_wounds_on_current=target_wounds_on_current,
        )

        return CombatResult(
            attacks=hit_result.attacks,
            hits=hit_result.hits,
            critical_hits=hit_result.critical_hits,
            wounds=total_wounds,
            critical_wounds=wound_result.critical_wounds,
            failed_saves=save_result.failed_saves,
            total_damage=allocation.total_damage_applied,
            models_killed=allocation.models_killed,
            remaining_models=allocation.remaining_models,
            remaining_wounds_on_damaged_model=allocation.remaining_wounds_on_damaged_model,
            damage_mitigated=allocation.damage_mitigated,
            auto_wounds=hit_result.auto_wounds,
        )
