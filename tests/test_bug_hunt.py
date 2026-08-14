"""Adversarial / invariant tests to surface rules bugs."""

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
from grimsim.rules.damage import allocate_damage, resolve_damage
from grimsim.rules.engine import RuleEngine
from grimsim.rules.hits import resolve_hits
from grimsim.rules.saves import choose_save, resolve_saves
from grimsim.rules.wounds import resolve_wounds, wound_target
from grimsim.simulation.combat import simulate_combat
from grimsim.simulation.monte_carlo import simulate_many


def _unit(
    *,
    name: str = "U",
    models: int = 10,
    toughness: int = 4,
    wounds: int = 1,
    save: int = 7,
    invuln: int | None = None,
    abilities: tuple[object, ...] = (),
) -> Unit:
    return Unit(
        profile=UnitProfile(
            name=name,
            model_count=models,
            toughness=toughness,
            wounds_per_model=wounds,
            save=save,
            invulnerable_save=invuln,
        ),
        weapons=(),
        abilities=abilities,  # type: ignore[arg-type]
    )


def _weapon(
    *,
    attacks: int = 10,
    skill: int = 3,
    strength: int = 4,
    ap: int = 0,
    damage: int = 1,
    abilities: tuple[object, ...] = (),
) -> Weapon:
    return Weapon(
        profile=WeaponProfile(
            name="Test Weapon",
            attacks=attacks,
            skill=skill,
            strength=strength,
            ap=ap,
            damage=damage,
        ),
        abilities=abilities,  # type: ignore[arg-type]
    )


class TestSaveModifierSemantics:
    def test_save_modifier_does_not_improve_invulnerable(self) -> None:
        """Armour-only modifier (cover-style) must not improve invulns.

        Armour 5+ with +1 becomes 4+. Invulnerable 4+ stays 4+.
        """
        choice = choose_save(5, 0, 4, save_modifier=1)
        assert choice.target == 4
        assert choice.source in {"armor", "invulnerable"}

    def test_save_modifier_improves_armor_only(self) -> None:
        # Armour 4+ with +1 -> 3+; invuln 5+ unchanged -> prefer armour 3+.
        choice = choose_save(4, 0, 5, save_modifier=1)
        assert choice.target == 3
        assert choice.source == "armor"

    def test_negative_save_modifier_does_not_worsen_invulnerable(self) -> None:
        # Armour 3+ with -1 -> 4+; invuln 3+ stays 3+ -> prefer invuln.
        choice = choose_save(3, 0, 3, save_modifier=-1)
        assert choice.target == 3
        assert choice.source == "invulnerable"

    def test_cover_on_no_armour_grants_six_plus(self) -> None:
        # Datasheet save 7+ (none) with +1 armour modifier -> 6+.
        choice = choose_save(7, 0, None, save_modifier=1)
        assert choice.target == 6
        assert choice.source == "armor"


class TestNaturalOneAndSixRules:
    def test_ones_always_miss_even_with_huge_hit_bonus(self) -> None:
        import grimsim.rules.hits as hits_mod

        original = hits_mod.roll_dice
        hits_mod.roll_dice = lambda count, sides, rng: np.ones(count, dtype=np.int64)
        try:
            result = resolve_hits(
                20,
                skill=2,
                hit_modifier=10,
                abilities=(),
                rng=np.random.default_rng(0),
            )
        finally:
            hits_mod.roll_dice = original
        assert result.hits == 0
        assert result.failed_hits == 20

    def test_sixes_always_hit_even_with_huge_hit_penalty(self) -> None:
        import grimsim.rules.hits as hits_mod

        original = hits_mod.roll_dice
        hits_mod.roll_dice = lambda count, sides, rng: np.full(count, 6, dtype=np.int64)
        try:
            result = resolve_hits(
                20,
                skill=4,
                hit_modifier=-10,
                abilities=(),
                rng=np.random.default_rng(0),
            )
        finally:
            hits_mod.roll_dice = original
        assert result.hits == 20
        assert result.critical_hits == 20

    def test_ones_always_fail_wounds_even_with_huge_bonus(self) -> None:
        import grimsim.rules.wounds as wounds_mod

        original = wounds_mod.roll_dice
        wounds_mod.roll_dice = lambda count, sides, rng: np.ones(count, dtype=np.int64)
        try:
            result = resolve_wounds(
                20,
                strength=10,
                toughness=3,
                wound_modifier=10,
                abilities=(),
                rng=np.random.default_rng(0),
            )
        finally:
            wounds_mod.roll_dice = original
        assert result.wounds == 0

    def test_save_ones_always_fail_on_two_plus(self) -> None:
        import grimsim.rules.saves as saves_mod

        original = saves_mod.roll_dice
        saves_mod.roll_dice = lambda count, sides, rng: np.ones(count, dtype=np.int64)
        try:
            result = resolve_saves(
                15,
                armor_save=2,
                ap=0,
                invulnerable_save=None,
                save_modifier=0,
                rng=np.random.default_rng(0),
            )
        finally:
            saves_mod.roll_dice = original
        assert result.failed_saves == 15
        assert result.successful_saves == 0


class TestRerollOnesOnly:
    def test_reroll_hit_ones_does_not_reroll_other_failures(self) -> None:
        import grimsim.rules.hits as hits_mod

        original = hits_mod.roll_dice
        calls: list[int] = []

        def tracked(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
            calls.append(count)
            if len(calls) == 1:
                # All 2s: fail against 3+, but must NOT reroll.
                return np.full(count, 2, dtype=np.int64)
            return np.full(count, 6, dtype=np.int64)

        hits_mod.roll_dice = tracked
        try:
            result = resolve_hits(
                8,
                skill=3,
                hit_modifier=0,
                abilities=(RerollHitOnes(),),
                rng=np.random.default_rng(0),
            )
        finally:
            hits_mod.roll_dice = original

        assert calls == [8]
        assert result.hits == 0

    def test_reroll_hit_ones_rerolls_only_ones(self) -> None:
        import grimsim.rules.hits as hits_mod

        original = hits_mod.roll_dice
        calls: list[int] = []

        def tracked(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
            calls.append(count)
            if len(calls) == 1:
                return np.array([1, 1, 3, 4, 5, 6], dtype=np.int64)
            # Reroll the two ones into misses (2) against skill 3+.
            return np.array([2, 2], dtype=np.int64)

        hits_mod.roll_dice = tracked
        try:
            result = resolve_hits(
                6,
                skill=3,
                hit_modifier=0,
                abilities=(RerollHitOnes(),),
                rng=np.random.default_rng(0),
            )
        finally:
            hits_mod.roll_dice = original

        assert calls == [6, 2]
        # Final rolls: 2,2,3,4,5,6 -> 4 hits, 1 crit
        assert result.hits == 4
        assert result.critical_hits == 1
        assert result.failed_hits == 2


class TestLethalAndSustainedAccounting:
    def test_lethal_hits_skip_wound_rolls_but_not_saves(self) -> None:
        import grimsim.rules.hits as hits_mod
        import grimsim.rules.saves as saves_mod
        import grimsim.rules.wounds as wounds_mod

        weapon = _weapon(attacks=5, skill=2, strength=4, ap=0, damage=1, abilities=(LethalHits(),))
        attacker = Unit(
            profile=UnitProfile(name="A", model_count=1, toughness=4, wounds_per_model=1, save=3),
            weapons=(weapon,),
        )
        target = _unit(models=10, save=2)  # strong armour

        h_orig, w_orig, s_orig = hits_mod.roll_dice, wounds_mod.roll_dice, saves_mod.roll_dice
        wound_rolls = {"count": 0}

        def hit_sixes(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
            return np.full(count, 6, dtype=np.int64)

        def track_wounds(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
            wound_rolls["count"] += count
            return np.full(count, 6, dtype=np.int64)

        def save_fails(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
            return np.ones(count, dtype=np.int64)

        hits_mod.roll_dice = hit_sixes
        wounds_mod.roll_dice = track_wounds
        saves_mod.roll_dice = save_fails
        try:
            result = RuleEngine().resolve_attack_sequence(
                attacker,
                weapon,
                target,
                CombatContext(),
                np.random.default_rng(0),
            )
        finally:
            hits_mod.roll_dice = h_orig
            wounds_mod.roll_dice = w_orig
            saves_mod.roll_dice = s_orig

        assert wound_rolls["count"] == 0  # all auto-wounded
        assert result.wounds == 5
        assert result.auto_wounds == 5
        assert result.failed_saves == 5  # saves still rolled
        assert result.models_killed == 5

    def test_sustained_plus_lethal_math(self) -> None:
        import grimsim.rules.hits as hits_mod

        original = hits_mod.roll_dice
        # Two crits, one normal hit (4), one miss (1), one miss (2)
        hits_mod.roll_dice = lambda c, s, r: np.array([6, 6, 4, 1, 2], dtype=np.int64)
        try:
            result = resolve_hits(
                5,
                skill=3,
                hit_modifier=0,
                abilities=(SustainedHits(1), LethalHits()),
                rng=np.random.default_rng(0),
            )
        finally:
            hits_mod.roll_dice = original

        # base hits: 6,6,4 = 3; sustained +2; total hits 5
        assert result.critical_hits == 2
        assert result.hits == 5
        assert result.auto_wounds == 2
        assert result.hits_to_wound == 3  # 1 normal hit + 2 sustained extras


class TestDamageAllocationEdgeCases:
    def test_spec_example_no_spill(self) -> None:
        result = allocate_damage(np.array([2, 2, 4]), model_count=5, wounds_per_model=3)
        assert result.models_killed == 2
        assert result.remaining_models == 3
        assert result.remaining_wounds_on_damaged_model is None
        # Wounds actually removed: 2 + 1 + 3 = 6 (excess discarded)
        assert result.total_damage_applied == 6

    def test_overkill_does_not_spill_to_next_model(self) -> None:
        # One attack of 100 damage against 2W models should kill exactly one.
        result = allocate_damage(np.array([100]), model_count=5, wounds_per_model=2)
        assert result.models_killed == 1
        assert result.remaining_models == 4
        assert result.total_damage_applied == 2

    def test_fnp_can_fully_negate_damage(self) -> None:
        import grimsim.rules.damage as damage_mod

        original = damage_mod.roll_dice
        # FNP rolls all 6s against 5+ -> every point ignored
        damage_mod.roll_dice = lambda c, s, r: np.full(c, 6, dtype=np.int64)
        try:
            result = resolve_damage(
                failed_saves=5,
                damage=2,
                model_count=10,
                wounds_per_model=1,
                target_abilities=(FeelNoPain(5),),
                rng=np.random.default_rng(0),
            )
        finally:
            damage_mod.roll_dice = original

        assert result.models_killed == 0
        assert result.total_damage_applied == 0
        assert result.damage_mitigated == 10  # 5 saves * 2 damage

    def test_partial_fnp_then_allocate(self) -> None:
        import grimsim.rules.damage as damage_mod

        original = damage_mod.roll_dice
        # For each 3-damage instance, FNP results: fail, pass, fail -> 2 damage remains
        damage_mod.roll_dice = lambda c, s, r: np.array([1, 6, 1][:c], dtype=np.int64)
        try:
            result = resolve_damage(
                failed_saves=1,
                damage=3,
                model_count=2,
                wounds_per_model=2,
                target_abilities=(FeelNoPain(5),),
                rng=np.random.default_rng(0),
            )
        finally:
            damage_mod.roll_dice = original

        assert result.damage_mitigated == 1
        assert result.models_killed == 1
        assert result.total_damage_applied == 2


class TestCombatInvariants:
    @pytest.mark.parametrize("seed", range(50))
    def test_model_conservation_across_seeds(self, seed: int) -> None:
        weapon = _weapon(
            attacks=8,
            skill=3,
            strength=5,
            ap=-2,
            damage=2,
            abilities=(SustainedHits(1), LethalHits()),
        )
        attacker = Unit(
            profile=UnitProfile(name="A", model_count=1, toughness=4, wounds_per_model=2, save=3),
            weapons=(weapon,),
            abilities=(RerollHitOnes(), RerollWoundOnes()),
        )
        target = _unit(
            models=5,
            toughness=4,
            wounds=3,
            save=3,
            invuln=5,
            abilities=(FeelNoPain(6),),
        )
        result = simulate_combat(attacker, weapon, target, seed=seed)
        assert result.models_killed + result.remaining_models == target.profile.model_count
        assert result.hits >= result.critical_hits
        assert result.wounds >= result.critical_wounds
        assert result.wounds >= result.auto_wounds
        assert result.failed_saves <= result.wounds
        assert result.total_damage >= 0
        assert result.damage_mitigated >= 0
        if result.remaining_wounds_on_damaged_model is not None:
            assert result.remaining_models >= 1
            assert 1 <= result.remaining_wounds_on_damaged_model < target.profile.wounds_per_model

    def test_auto_wounds_field_populated_with_lethal(self) -> None:
        import grimsim.rules.hits as hits_mod

        weapon = _weapon(attacks=4, abilities=(LethalHits(),))
        attacker = Unit(
            profile=UnitProfile(name="A", model_count=1, toughness=4, wounds_per_model=1, save=3),
            weapons=(weapon,),
        )
        target = _unit(models=10, save=7)

        original = hits_mod.roll_dice
        hits_mod.roll_dice = lambda c, s, r: np.full(c, 6, dtype=np.int64)
        try:
            result = simulate_combat(attacker, weapon, target, seed=0)
        finally:
            hits_mod.roll_dice = original

        assert result.auto_wounds == 4
        assert result.wounds == 4


class TestWoundTableBoundaries:
    @pytest.mark.parametrize(
        ("s", "t", "expected"),
        [
            (6, 3, 2),
            (5, 3, 3),
            (4, 4, 4),
            (3, 4, 5),
            (3, 6, 6),
            (4, 8, 6),  # 2S <= T
            (4, 7, 5),  # S < T but 2S > T → still 5+
            (4, 5, 5),
            (2, 3, 5),
            (2, 4, 6),
        ],
    )
    def test_boundaries(self, s: int, t: int, expected: int) -> None:
        assert wound_target(s, t) == expected


class TestMonteCarloIntegrity:
    def test_damage_arrays_are_readonly(self) -> None:
        weapon = _weapon(attacks=4)
        attacker = Unit(
            profile=UnitProfile(name="A", model_count=1, toughness=4, wounds_per_model=1, save=3),
            weapons=(weapon,),
        )
        target = _unit(models=5, save=5)
        result = simulate_many(attacker, weapon, target, iterations=20, seed=1)
        with pytest.raises(ValueError):
            result._damage[0] = 999  # type: ignore[index]
