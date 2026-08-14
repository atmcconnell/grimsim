"""Tests for reusable combat abilities."""

from __future__ import annotations

import numpy as np
import pytest

from grimsim.models.ability import (
    FeelNoPain,
    LethalHits,
    RerollHitOnes,
    RerollWoundOnes,
    SustainedHits,
)
from grimsim.models.combat import CombatContext
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.rules.hits import resolve_hits
from grimsim.rules.wounds import resolve_wounds
from grimsim.simulation.combat import simulate_combat


def _target(*, toughness: int = 4, models: int = 10, wounds: int = 1, save: int = 7) -> Unit:
    """Helpless target that auto-fails saves (save 7+)."""
    return Unit(
        profile=UnitProfile(
            name="Target",
            model_count=models,
            toughness=toughness,
            wounds_per_model=wounds,
            save=save,
        ),
        weapons=(),
    )


class TestRerollHitOnes:
    def test_rerolls_ones(self) -> None:
        # Without rerolls, seeded run has a known failed-hit count;
        # with rerolls, failed hits should not increase and typically decrease.
        base = resolve_hits(
            100,
            skill=2,
            hit_modifier=0,
            abilities=(),
            rng=np.random.default_rng(1),
        )
        reroll = resolve_hits(
            100,
            skill=2,
            hit_modifier=0,
            abilities=(RerollHitOnes(),),
            rng=np.random.default_rng(1),
        )
        # Same seed means same initial rolls; rerolling ones can only help or stay equal.
        assert reroll.hits >= base.hits
        assert reroll.failed_hits <= base.failed_hits


class TestRerollWoundOnes:
    def test_rerolls_ones(self) -> None:
        base = resolve_wounds(
            100,
            strength=4,
            toughness=4,
            wound_modifier=0,
            abilities=(),
            rng=np.random.default_rng(2),
        )
        reroll = resolve_wounds(
            100,
            strength=4,
            toughness=4,
            wound_modifier=0,
            abilities=(RerollWoundOnes(),),
            rng=np.random.default_rng(2),
        )
        assert reroll.wounds >= base.wounds


class TestSustainedHits:
    def test_adds_extra_hits(self) -> None:
        result = resolve_hits(
            60,
            skill=3,
            hit_modifier=0,
            abilities=(SustainedHits(1),),
            rng=np.random.default_rng(3),
        )
        # hits == successful dice + critical_hits * bonus
        assert result.hits == (result.attacks - result.failed_hits) + result.critical_hits

    def test_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            SustainedHits(0)


class TestLethalHits:
    def test_auto_wounds(self) -> None:
        result = resolve_hits(
            60,
            skill=3,
            hit_modifier=0,
            abilities=(LethalHits(),),
            rng=np.random.default_rng(4),
        )
        assert result.auto_wounds == result.critical_hits
        assert result.hits_to_wound == result.hits - result.critical_hits


class TestFeelNoPainAbility:
    def test_reduces_damage_in_combat(self) -> None:
        weapon = Weapon(
            profile=WeaponProfile(
                name="Gun",
                attacks=20,
                skill=2,
                strength=8,
                ap=-4,
                damage=1,
            ),
        )
        attacker = Unit(
            profile=UnitProfile(
                name="Shooter",
                model_count=1,
                toughness=4,
                wounds_per_model=1,
                save=3,
            ),
            weapons=(weapon,),
        )
        plain = _target(models=20, wounds=1, save=7)
        with_fnp = Unit(
            profile=plain.profile,
            weapons=(),
            abilities=(FeelNoPain(5),),
        )

        plain_result = simulate_combat(attacker, weapon, plain, seed=10)
        fnp_result = simulate_combat(attacker, weapon, with_fnp, seed=10)
        assert fnp_result.total_damage <= plain_result.total_damage
        assert fnp_result.damage_mitigated >= 0

    def test_invalid_threshold(self) -> None:
        with pytest.raises(ValueError):
            FeelNoPain(1)


class TestAbilityComposition:
    def test_weapon_and_unit_abilities_combine(self) -> None:
        weapon = Weapon(
            profile=WeaponProfile(
                name="Axe",
                attacks=10,
                skill=3,
                strength=5,
                ap=-1,
                damage=1,
            ),
            abilities=(SustainedHits(1), LethalHits()),
        )
        attacker = Unit(
            profile=UnitProfile(
                name="Attacker",
                model_count=1,
                toughness=4,
                wounds_per_model=2,
                save=3,
            ),
            weapons=(weapon,),
            abilities=(RerollHitOnes(),),
        )
        result = simulate_combat(
            attacker,
            weapon,
            _target(toughness=4, models=20, wounds=1, save=7),
            seed=42,
            context=CombatContext(),
        )
        assert result.attacks == 10
        assert result.hits >= result.critical_hits
        assert result.models_killed >= 0
