"""Combat simulation demo: mixed-loadout unit activation + Monte Carlo.

Run from the repository root:

    uv run python scripts/demo_combat.py
"""

from __future__ import annotations

from grimsim import (
    AttackPlan,
    UnitState,
    WeaponAssignment,
    simulate_many_unit_activations,
    simulate_unit_activation,
)
from grimsim.examples import elite_infantry, mixed_melee_unit

SEED = 42
ITERATIONS = 100_000


def _require_mixed_loadout() -> tuple[UnitState, UnitState, AttackPlan]:
    """Build attacker/target states and a 4+1 mixed melee plan."""
    attacker_unit = mixed_melee_unit()
    target_unit = elite_infantry()
    if len(attacker_unit.weapons) < 2:
        raise RuntimeError(
            "Demo data missing: mixed_melee_unit() must provide two weapon profiles."
        )

    attacker = UnitState.from_unit(attacker_unit)
    target = UnitState.from_unit(target_unit)
    chain, maul = attacker_unit.weapons[0], attacker_unit.weapons[1]
    plan = AttackPlan(
        assignments=(
            WeaponAssignment(chain, models=4),
            WeaponAssignment(maul, models=1),
        )
    )
    plan.validate(attacker)
    return attacker, target, plan


def _print_activation_plan(plan: AttackPlan) -> None:
    print("Attack Plan:")
    for assignment in plan.assignments:
        label = "model" if assignment.models == 1 else "models"
        print(f"  {assignment.models} {label} -> {assignment.weapon.profile.name}")


def main() -> None:
    attacker, target, plan = _require_mixed_loadout()

    print("=== GrimSim Combat Demo ===")
    print()
    print(f"Attacker: {attacker.unit.profile.name}")
    print(
        f"          {attacker.remaining_models} models, "
        f"T{attacker.unit.profile.toughness}, "
        f"{attacker.unit.profile.wounds_per_model}W, "
        f"{attacker.unit.profile.save}+ save"
    )
    print(f"Target:   {target.unit.profile.name}")
    print(
        f"          {target.remaining_models} models, "
        f"T{target.unit.profile.toughness}, "
        f"{target.unit.profile.wounds_per_model}W, "
        f"{target.unit.profile.save}+ save"
        + (
            f" / {target.unit.profile.invulnerable_save}++"
            if target.unit.profile.invulnerable_save is not None
            else ""
        )
    )
    print()
    _print_activation_plan(plan)

    # Single seeded activation: all weapons share one evolving target.
    result = simulate_unit_activation(attacker, target, plan, seed=SEED)

    print()
    print("--- Single Activation ---")
    print(f"Attacks:            {result.attacks:>6}")
    print(f"Hits:               {result.hits:>6}")
    print(f"Wounds:             {result.wounds:>6}")
    print(f"Failed Saves:       {result.failed_saves:>6}")
    print(f"Damage:             {result.total_damage:>6}")
    print(f"Models Killed:      {result.models_killed:>6}")
    print(f"Target Remaining:   {result.remaining_models:>6}")
    print(f"Target Destroyed:   {str(result.target_destroyed):>6}")
    print()
    print("Per-weapon results (shared evolving target):")
    for weapon_result in result.weapon_results:
        combat = weapon_result.combat
        print(
            f"  {weapon_result.models_assigned}x {weapon_result.weapon_name}: "
            f"{combat.attacks} attacks, {combat.models_killed} killed, "
            f"{combat.remaining_models} remaining"
        )

    # Monte Carlo of the same plan. Original states are not mutated.
    mc = simulate_many_unit_activations(
        attacker,
        target,
        plan,
        iterations=ITERATIONS,
        seed=SEED,
    )

    print()
    print(f"--- Monte Carlo: {mc.iterations:,} iterations (seed={SEED}) ---")
    print(f"Mean Damage:         {mc.mean_damage:>7.2f}")
    print(f"Median Damage:       {mc.median_damage:>7.2f}")
    print(f"Damage Std Dev:      {mc.std_damage:>7.2f}")
    print()
    print(f"Mean Models Killed:  {mc.mean_models_killed:>7.2f}")
    print(f"Median Models Killed: {mc.median_models_killed:>6.2f}")
    print(f"Min / Max Killed:    {mc.min_models_killed:>3} / {mc.max_models_killed}")
    print(f"P(Kill >= 2):        {mc.probability_models_killed_at_least(2):>6.1%}")
    print(f"P(Kill >= 3):        {mc.probability_models_killed_at_least(3):>6.1%}")
    print(f"P(Target Destroyed): {mc.probability_target_destroyed:>6.1%}")

    sample = mc.to_dataframe().head(5)
    print()
    print("--- to_dataframe() sample (first 5 iterations) ---")
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
