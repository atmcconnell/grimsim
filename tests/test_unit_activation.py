"""Tests for mixed-weapon unit activation against a shared target."""

from __future__ import annotations

import numpy as np
import pytest

from grimsim.models.activation import AttackPlan, WeaponAssignment
from grimsim.models.army import UnitState
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.simulation.activation import simulate_unit_activation


def _always_six(count: int, sides: int, rng: np.random.Generator) -> np.ndarray:
    return np.full(count, 6, dtype=np.int64)


def _patch_all_sixes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("grimsim.rules.hits.roll_dice", _always_six)
    monkeypatch.setattr("grimsim.rules.wounds.roll_dice", _always_six)
    monkeypatch.setattr("grimsim.rules.saves.roll_dice", _always_six)


def _chopper(*, attacks: int = 1, damage: int = 1) -> Weapon:
    return Weapon(
        profile=WeaponProfile(
            name="Chopper",
            attacks=attacks,
            skill=2,
            strength=8,
            ap=-4,
            damage=damage,
        )
    )


def _maul() -> Weapon:
    return Weapon(
        profile=WeaponProfile(
            name="Maul",
            attacks=1,
            skill=2,
            strength=8,
            ap=-4,
            damage=1,
        )
    )


def _attacker(weapons: tuple[Weapon, ...], models: int = 5) -> Unit:
    return Unit(
        profile=UnitProfile(
            name="Attackers",
            model_count=models,
            toughness=4,
            wounds_per_model=2,
            save=3,
        ),
        weapons=weapons,
        id="test-attackers",
    )


def _target(*, models: int = 5, wounds: int = 1, save: int = 7) -> Unit:
    return Unit(
        profile=UnitProfile(
            name="Targets",
            model_count=models,
            toughness=3,
            wounds_per_model=wounds,
            save=save,
        ),
        weapons=(),
        id="test-targets",
    )


class TestAttackPlanValidation:
    def test_rejects_more_models_than_alive(self) -> None:
        attacker = UnitState.from_unit(_attacker((_chopper(),)), remaining_models=3)
        plan = AttackPlan(assignments=(WeaponAssignment(_chopper(), models=4),))
        with pytest.raises(ValueError, match="remain"):
            plan.validate(attacker)

    def test_rejects_disjoint_sum_over_alive(self) -> None:
        attacker = UnitState.from_unit(_attacker((_chopper(), _maul())), remaining_models=5)
        plan = AttackPlan(
            assignments=(
                WeaponAssignment(_chopper(), models=4),
                WeaponAssignment(_maul(), models=2),
            )
        )
        with pytest.raises(ValueError, match="Disjoint"):
            plan.validate(attacker)


class TestUnitActivation:
    def test_single_weapon_assignment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_all_sixes(monkeypatch)
        weapon = _chopper(attacks=1)
        attacker = UnitState.from_unit(_attacker((weapon,), models=4))
        target = UnitState.from_unit(_target(models=10, wounds=1, save=7))
        plan = AttackPlan(assignments=(WeaponAssignment(weapon, models=4),))
        result = simulate_unit_activation(attacker, target, plan, seed=1)
        assert result.attacks == 4
        assert result.models_killed == 4
        assert result.remaining_models == 6
        assert len(result.weapon_results) == 1
        assert result.weapon_results[0].weapon_name == "Chopper"

    def test_mixed_weapons_share_evolving_target(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_all_sixes(monkeypatch)
        chopper = _chopper(attacks=1)
        maul = _maul()
        attacker = UnitState.from_unit(_attacker((chopper, maul), models=5))
        target = UnitState.from_unit(_target(models=5, wounds=1, save=7))
        plan = AttackPlan(
            assignments=(
                WeaponAssignment(chopper, models=2),
                WeaponAssignment(maul, models=3),
            )
        )
        result = simulate_unit_activation(attacker, target, plan, seed=1)
        first, second = result.weapon_results
        assert first.combat.models_killed == 2
        assert first.combat.remaining_models == 3
        assert second.combat.models_killed == 3
        assert second.combat.remaining_models == 0
        assert result.models_killed == 5
        assert result.target_destroyed
        assert target.remaining_models == 5  # input not mutated

    def test_independent_resolution_would_overcount(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If each weapon reset the target, both would kill 5; shared state caps at 5."""
        _patch_all_sixes(monkeypatch)
        a = _chopper(attacks=2)
        b = _maul()
        attacker = UnitState.from_unit(_attacker((a, b), models=5))
        target = UnitState.from_unit(_target(models=5, wounds=1, save=7))
        plan = AttackPlan(
            assignments=(WeaponAssignment(a, models=5), WeaponAssignment(b, models=5)),
            disjoint=False,
        )
        result = simulate_unit_activation(attacker, target, plan, seed=1)
        assert result.weapon_results[0].combat.models_killed == 5
        assert result.weapon_results[1].combat.models_killed == 0
        assert result.weapon_results[1].combat.attacks == 0
        assert result.models_killed == 5
        assert result.target_destroyed

    def test_partial_attacker_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_all_sixes(monkeypatch)
        weapon = _chopper(attacks=1)
        attacker = UnitState.from_unit(
            _attacker((weapon,), models=6), remaining_models=4
        )
        target = UnitState.from_unit(_target(models=10, save=7))
        plan = AttackPlan(assignments=(WeaponAssignment(weapon, models=4),))
        result = simulate_unit_activation(attacker, target, plan, seed=2)
        assert result.attacks == 4
        assert attacker.remaining_models == 4

    def test_partial_target_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_all_sixes(monkeypatch)
        weapon = _chopper(attacks=1, damage=1)
        attacker = UnitState.from_unit(_attacker((weapon,), models=1))
        target = UnitState.from_unit(
            _target(models=3, wounds=2, save=7),
            remaining_models=2,
            wounds_on_current_model=1,
        )
        plan = AttackPlan(assignments=(WeaponAssignment(weapon, models=1),))
        result = simulate_unit_activation(attacker, target, plan, seed=3)
        assert result.models_killed == 1
        assert result.remaining_models == 1
        assert result.remaining_wounds_on_damaged_model is None

    def test_target_destroyed_before_later_weapons(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_all_sixes(monkeypatch)
        first = _chopper(attacks=5)
        second = _maul()
        attacker = UnitState.from_unit(_attacker((first, second), models=5))
        target = UnitState.from_unit(_target(models=3, wounds=1, save=7))
        plan = AttackPlan(
            assignments=(
                WeaponAssignment(first, models=3),
                WeaponAssignment(second, models=2),
            )
        )
        result = simulate_unit_activation(attacker, target, plan, seed=4)
        assert result.weapon_results[0].combat.models_killed == 3
        assert result.weapon_results[1].combat.attacks == 0
        assert result.target_destroyed
        assert result.models_killed == 3

    def test_aggregates_match_per_weapon_sum(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_all_sixes(monkeypatch)
        chopper = _chopper(attacks=1)
        maul = _maul()
        attacker = UnitState.from_unit(_attacker((chopper, maul), models=5))
        target = UnitState.from_unit(_target(models=10, save=7))
        plan = AttackPlan(
            assignments=(
                WeaponAssignment(chopper, models=2),
                WeaponAssignment(maul, models=3),
            )
        )
        result = simulate_unit_activation(attacker, target, plan, seed=5)
        assert result.attacks == sum(w.combat.attacks for w in result.weapon_results)
        assert result.hits == sum(w.combat.hits for w in result.weapon_results)
        assert result.wounds == sum(w.combat.wounds for w in result.weapon_results)
        assert result.failed_saves == sum(w.combat.failed_saves for w in result.weapon_results)
        assert result.total_damage == sum(w.combat.total_damage for w in result.weapon_results)
        assert result.models_killed == sum(w.combat.models_killed for w in result.weapon_results)
        assert len(result.weapon_results) == 2

    def test_deterministic_seed(self) -> None:
        weapon = _chopper(attacks=2)
        attacker = UnitState.from_unit(_attacker((weapon,)))
        target = UnitState.from_unit(_target(models=10, save=5))
        plan = AttackPlan(assignments=(WeaponAssignment(weapon, models=5),))
        a = simulate_unit_activation(attacker, target, plan, seed=42)
        b = simulate_unit_activation(attacker, target, plan, seed=42)
        assert a.attacks == b.attacks
        assert a.total_damage == b.total_damage
        assert a.models_killed == b.models_killed

    def test_does_not_mutate_profiles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_all_sixes(monkeypatch)
        weapon = _chopper(attacks=1)
        unit = _attacker((weapon,), models=5)
        attacker = UnitState.from_unit(unit)
        target_unit = _target(models=5, save=7)
        target = UnitState.from_unit(target_unit)
        plan = AttackPlan(assignments=(WeaponAssignment(weapon, models=5),))
        simulate_unit_activation(attacker, target, plan, seed=1, apply_to_target=True)
        assert unit.profile.model_count == 5
        assert target_unit.profile.model_count == 5
        assert target.remaining_models == 0
