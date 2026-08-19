# GrimSim

Python simulation engine for competitive Warhammer 40,000 analysis.

**v0.3** can:

1. Resolve the attack pipeline **attacks → hits → wounds → saves → damage → models killed**
2. Represent a full army roster under a **ruleset, faction, and detachment**
3. Simulate a **mixed-loadout unit activation** against one evolving target
4. Look up **points and profiles by ruleset**

There is no graphical UI. You use the Python API.

Guiding principle:

> Units describe data. Rules interpret that data. Simulators orchestrate those rules.

> Army lists describe roster intent. Armies represent runtime state. Rulesets define the environment in which both are valid.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

```bash
uv run pytest
uv run pytest --cov=grimsim
uv run ruff check .
uv run mypy src
```

## Architecture

```text
Ruleset + Versioned Data
          ↓
Faction + Detachment
          ↓
ArmyList
          ↓
Army / UnitState
          ↓
Unit Activation
          ↓
Rule Engine
          ↓
Monte Carlo
          ↓
Analysis / Persistence
```

| Concept | Role |
| --- | --- |
| `DiceExpression` | Structured dice (`D6`, `2D6+2`, flat values) with injectable RNG |
| `Unit` / `UnitProfile` | Immutable combat profile |
| `Weapon` / `WeaponProfile` | Immutable weapon profile + abilities |
| `UnitSelection` | Roster choice (quantity, size, enhancements, optional explicit points) |
| `ArmyList` | Static roster under faction / detachment / ruleset |
| `UnitState` | Mutable in-game models/wounds/destroyed |
| `Army` | Runtime roster via `Army.from_list(army_list)` |
| `Ruleset` | Edition, rules version, points version, effective date |
| `Faction` | Identity only — no combat behavior |
| `Detachment` | Faction-scoped package (`abilities` + `RuleEffect` placeholders) |
| `Enhancement` | List metadata (id, name, points) |
| `PointsCatalog` | `(unit identity, ruleset, model count) → points` |
| `ProfileCatalog` | `(unit identity, ruleset) → Unit` |
| `AttackPlan` / `WeaponAssignment` | Which surviving models fire which weapons |
| `CombatContext` | Hit/wound/armour-save modifiers |
| `CombatResult` / `ActivationResult` | Typed outcomes |

Combat never requires DuckDB. Pandas is used only in Monte Carlo `to_dataframe()`.

---

## 1. Dice

```python
from grimsim.models.dice import DiceExpression, roll_die, roll_dice
import numpy as np

rng = np.random.default_rng(42)
roll_die(6, rng)
roll_dice(10, 6, rng)
DiceExpression(count=1, sides=6, modifier=2).roll(rng)  # D6+2
DiceExpression.d6().scaled(3)  # 3D6
```

RNG is always injected (`numpy.random.Generator`). No global random state.

---

## 2. Units, weapons, abilities

```python
from grimsim import Unit, UnitProfile, Weapon, WeaponProfile
from grimsim.models.ability import SustainedHits, LethalHits, RerollHitOnes, FeelNoPain

weapon = Weapon(
    profile=WeaponProfile(
        name="Chain Axe",
        attacks=4,          # per model in unit activation; once in simulate_combat
        skill=3,
        strength=5,
        ap=-2,
        damage=2,
    ),
    abilities=(SustainedHits(1), LethalHits()),
)
unit = Unit(
    profile=UnitProfile(
        name="Example Berserkers",
        model_count=10,
        toughness=4,
        wounds_per_model=2,
        save=3,
        invulnerable_save=None,
        objective_control=1,
    ),
    weapons=(weapon,),
    abilities=(RerollHitOnes(),),
    id="example-berserkers",
)
```

**Abilities (combat):**

| Type | Effect |
| --- | --- |
| `RerollHitOnes` | Reroll hit rolls of 1 |
| `RerollWoundOnes` | Reroll wound rolls of 1 |
| `SustainedHits(X)` | Each critical hit adds `X` extra hits |
| `LethalHits` | Critical hits auto-wound (saves still happen) |
| `FeelNoPain(X)` | Ignore each damage point on `X+` |

The rule engine discovers abilities on the unit and weapon. It never branches on unit or faction names.

Bundled example builders: `melee_attacker()`, `light_infantry()`, `elite_infantry()`, `vehicle()`, `mixed_melee_unit()`.

---

## 3. Weapon-level combat (v0.1, unchanged)

```python
from grimsim import simulate_combat, simulate_many, CombatContext
from grimsim.examples import melee_attacker, light_infantry

attacker = melee_attacker()
target = light_infantry()

result = simulate_combat(
    attacker, attacker.weapons[0], target,
    seed=42,
    context=CombatContext(hit_modifier=0, wound_modifier=0, save_modifier=0),
)
# result.attacks, hits, critical_hits, wounds, auto_wounds, failed_saves,
# total_damage, models_killed, remaining_models, remaining_wounds_on_damaged_model,
# damage_mitigated

mc = simulate_many(attacker, attacker.weapons[0], target, iterations=100_000, seed=42)
mc.mean_damage, mc.median_damage, mc.std_damage
mc.mean_models_killed, mc.min_models_killed, mc.max_models_killed
mc.probability_target_destroyed
mc.probability_models_killed_at_least(5)
mc.probability_damage_at_least(10)
df = mc.to_dataframe()
```

This fires **one** weapon profile **once** (unscaled). You do not need an `ArmyList`.

Wound table: `from grimsim.rules import wound_target` → standard S vs T (2+/3+/4+/5+/6+).  
Saves: armour modified by AP; invulnerable ignores AP and cover-style `save_modifier`; better legal save is used.  
Damage does **not** spill between models.

---

## 4. Army lists and runtime armies (v0.2)

```python
from datetime import date
from grimsim import (
    Army, ArmyList, Detachment, Enhancement, Faction, Ruleset,
    UnitSelection, validate_army_list,
)
from grimsim.examples import melee_attacker, example_army_list

ruleset = Ruleset(
    id="10th-balanced-2025.01",
    edition="10th",
    rules_version="0.3.0",
    points_version="2025.01",
    effective_date=date(2025, 1, 1),
)
faction = Faction(id="crimson_hosts", name="Crimson Hosts")
detachment = Detachment(id="blood_tide", name="Blood Tide", faction_id=faction.id)

army_list = ArmyList(
    name="Example Army",
    faction=faction,
    detachment=detachment,
    ruleset=ruleset,
    points_limit=2000,
    selections=(
        UnitSelection(unit=melee_attacker(), quantity=2, points=180, model_count=10),
        UnitSelection(
            unit=melee_attacker(),
            quantity=1,
            points=180,
            enhancements=(Enhancement(id="blade", name="Exemplar Blade", points=25),),
        ),
    ),
)

army_list.total_points          # explicit selection.points
army_list.remaining_points
army_list.selection_count
army_list.unit_count

validation = validate_army_list(army_list)
validation.is_valid, validation.errors, validation.warnings

army = Army.from_list(army_list)  # one UnitState per copy; uses selection.size
```

`example_army_list()` is a 1995/2000-point demo roster.

---

## 5. Unit activation (v0.3)

```python
from grimsim import AttackPlan, WeaponAssignment
from grimsim import simulate_unit_activation, simulate_many_unit_activations
from grimsim.models.army import UnitState
from grimsim.examples import mixed_melee_unit, light_infantry

attacker = UnitState.from_unit(mixed_melee_unit(), remaining_models=5)
target = UnitState.from_unit(light_infantry())

plan = AttackPlan(
    assignments=(
        WeaponAssignment(attacker.unit.weapons[0], models=4),
        WeaponAssignment(attacker.unit.weapons[1], models=1),
    )
)
plan.validate(attacker)

result = simulate_unit_activation(attacker, target, plan, seed=42)
# result.attacks/hits/wounds/failed_saves/total_damage/models_killed
# result.target_destroyed, remaining_models, weapon_results, final_target

mc = simulate_many_unit_activations(attacker, target, plan, iterations=100_000, seed=42)
df = mc.to_dataframe()
```

Rules:

- `WeaponProfile.attacks` is **per model** here (4 models × 3 attacks = 12 dice).
- All weapons share **one evolving target**. If A kills 2 of 5, B attacks 3.
- A destroyed target makes later weapons resolve as 0 attacks.
- Default plan (no `attack_plan`): every remaining model fires every weapon (`disjoint=False`). Mixed loadouts need an explicit disjoint plan.
- `apply_to_target=True` writes remaining models/wounds back onto the passed-in target state.
- Profiles are never mutated.

`UnitState.from_unit(unit, remaining_models=..., wounds_on_current_model=...)` builds depleted/wounded state. `state.copy()` is used internally for Monte Carlo.

---

## 6. Ruleset-aware points and profiles (v0.3)

```python
from grimsim.examples import (
    melee_attacker, example_ruleset, example_ruleset_alt, example_points_catalog,
)
from grimsim.data import PointsCatalog, PointsEntry, ProfileCatalog, ProfileEntry

catalog = example_points_catalog()
unit = melee_attacker()
catalog.cost_for(unit, example_ruleset(), model_count=10)      # 180
catalog.cost_for(unit, example_ruleset_alt(), model_count=10)  # 200
catalog.try_cost_for(unit, example_ruleset(), 3)               # None if missing
catalog.available_sizes(unit, example_ruleset())

army_list.points_cost(catalog)
army_list.remaining_catalog_points(catalog)
```

Dated `PointsEntry.effective_date` values support historical lookup (`as_of=` or `ruleset.effective_date`).

`ProfileCatalog.unit_for("example-berserkers", ruleset)` returns the unit snapshot for that ruleset (last duplicate entry wins).

---

## 7. Validation

```python
from grimsim.validation import RosterConstraints, validate_army_list

constraints = RosterConstraints(
    max_copies=(("example-berserkers", 3),),
    allowed_sizes=(("example-berserkers", (5, 10)),),
    unique_unit_ids=("example-warlord",),
    unique_enhancements=True,
)
result = validate_army_list(army_list, catalog=catalog, constraints=constraints)
```

| Code | Meaning |
| --- | --- |
| `DETACHMENT_FACTION_MISMATCH` | Detachment does not belong to the list faction |
| `OVER_POINTS` | Cost exceeds limit (explicit points, or catalog costs including partial sums) |
| `EMPTY_ARMY_LIST` | No selections |
| `MISSING_POINTS` | No catalog cost for that identity/size/ruleset |
| `INVALID_UNIT_SIZE` | Size not in `allowed_sizes` |
| `MAX_COPIES` | Too many copies of an identity |
| `UNIQUE_UNIT` | Unique identity appears more than once |
| `DUPLICATE_ENHANCEMENT` | Same enhancement on multiple selections |

Rules are data-driven. There are no `if faction.name == ...` checks.

Construction also rejects non-positive quantity, negative points, and duplicate enhancements on a single selection.

---

## 8. Persistence

```python
from grimsim.data import (
    connect, initialize_schema, save_army_list, load_army_list,
    save_ruleset, save_simulation_summary, insert_rules_version,
)

conn = connect()  # or connect("grimsim.duckdb")
initialize_schema(conn)
save_army_list(conn, army_list, list_id="my-list")
loaded = load_army_list(conn, "my-list")  # identity + size preserved; weapons not serialized

save_simulation_summary(
    conn,
    simulation_type="unit_activation",
    attacker_name="Assault Squad",
    target_name="Troopers",
    attack_plan=plan.describe(),
    iterations=mc.iterations,
    seed=42,
    mean_damage=mc.mean_damage,
    median_damage=mc.median_damage,
    std_damage=mc.std_damage,
    mean_models_killed=mc.mean_models_killed,
    median_models_killed=mc.median_models_killed,
    min_models_killed=mc.min_models_killed,
    max_models_killed=mc.max_models_killed,
    probability_target_destroyed=mc.probability_target_destroyed,
    ruleset_id=army_list.ruleset.slug,
)
```

Tables: `rulesets`, `rules_versions` (legacy), `factions`, `detachments`, `army_lists`, `army_list_selections`, `simulation_runs`, `simulation_summaries`.

Simulation summary ids are SHA-256 of the inputs. Raw iterations are not stored.

---

## 9. Analysis / ML placeholder

`grimsim.analysis.summarize_matchup(...)` wraps `simulate_many`.

`MatchupModelPlaceholder.predict(...)` always raises `NotImplementedError`. Future models are intended to estimate `P(win | army, opponent, list, mission, terrain, skill, rules version)`.

---

## Public package imports

```python
from grimsim import (
    ActivationResult, Army, ArmyList, AttackPlan,
    CombatContext, CombatResult,
    Detachment, Enhancement, Faction,
    MonteCarloActivationResult, MonteCarloResult,
    Ruleset, Unit, UnitProfile, UnitSelection, UnitState,
    Weapon, WeaponAssignment, WeaponProfile,
    simulate_combat, simulate_many,
    simulate_unit_activation, simulate_many_unit_activations,
    validate_army_list,
)
```

---

## Examples / Demo Scripts

From the repository root:

```bash
uv run python scripts/demo_combat.py
uv run python scripts/demo_army.py
```

- `scripts/demo_combat.py` — mixed-loadout unit activation: a single seeded run, then a Monte Carlo of the same attack plan, including evolving per-weapon target state and `to_dataframe()` sample output.
- `scripts/demo_army.py` — rulesets, version-aware points, army-list validation (including an invalid list), runtime `Army` / `UnitState`, and an in-memory DuckDB round-trip.

Both scripts use the fictional example profiles in `grimsim.examples`.

---

## Current limitations

- No movement, charge, terrain, overwatch, or battle rounds
- No full official army-construction rules
- Enhancements and detachment effects do not modify combat
- Reloaded lists restore identity/size/points but not weapons or abilities
- Profile catalog is in-memory, not a full historical archive
- Default activation plan is “every model fires every weapon”; mixed loadouts need an explicit plan

See [BUG_REPORT.md](BUG_REPORT.md) for defects found in the v0.3 scan and how they were fixed.

## Roadmap

### v0.4
- Trade evaluator
- Attacker/counterattack exchanges
- Point-efficiency analysis
- Matchup representation

### v0.5
- Tournament-game data
- Descriptive matchup statistics
- Statistical baselines

### v0.6
- Calibrated matchup prediction models

## License

See [LICENSE](LICENSE).
