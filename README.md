# GrimSim

Python simulation engine for competitive Warhammer 40,000 analysis.

GrimSim models the core attack pipeline:

```text
attacks → hits → wounds → saves → damage → models killed
```

**Units describe data. Rules interpret that data. Simulators execute those rules repeatedly.**

This is a v0.1 foundation — not a full 40k ruleset. There is no graphical UI; you use the Python API.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## What is implemented (v0.1)

| Area | Status |
| --- | --- |
| Dice engine (`roll_die`, `roll_dice`, `DiceExpression`) | Done — injectable, seedable NumPy RNG |
| Domain models (`Unit`, `Weapon`, profiles) | Done — frozen dataclasses, composition |
| Hit / wound / save / damage stages | Done — independently testable |
| Strength vs Toughness wound table | Done — `wound_target(S, T)` |
| Damage allocation (no spill between models) | Done |
| Abilities: reroll 1s, Sustained Hits, Lethal Hits, FNP | Done |
| Single combat API | Done — `simulate_combat` |
| Monte Carlo API | Done — `simulate_many` + pandas export |
| Example profiles | Done — melee, light/elite infantry, vehicle |
| DuckDB schema foundation | Done — optional, not required for combat |
| scikit-learn matchup model | Placeholder only (not trained) |

## Architecture

```text
Unit Data  ↔  Rule Engine  ↔  Simulator
```

| Layer | Package | Responsibility |
| --- | --- | --- |
| Domain data | `grimsim.models` | Immutable units, weapons, dice, combat results |
| Abilities | `grimsim.models.ability` | Small reusable effect objects |
| Rules | `grimsim.rules` | Stage-based combat resolution |
| Simulation | `grimsim.simulation` | Single combat + Monte Carlo |
| Analysis | `grimsim.analysis` | Matchup summary helpers |
| Persistence | `grimsim.data` | Optional DuckDB schemas |
| ML | `grimsim.ml` | Future matchup prediction placeholder |
| Examples | `grimsim.examples` | Fictional numeric demo profiles |

Composition over inheritance: units are data containers with attached ability objects. The rule engine discovers abilities through composition — never via unit-name or faction conditionals.

## User interface (Python API)

GrimSim is a library. The primary entry points are imported from `grimsim`:

```python
from grimsim import (
    simulate_combat,      # one attack sequence
    simulate_many,        # Monte Carlo wrapper
    CombatContext,        # optional modifiers
    CombatResult,         # typed single-run result
    MonteCarloResult,     # aggregated stats + helpers
    Unit,
    UnitProfile,
    Weapon,
    WeaponProfile,
)
```

### 1. Build units (data only)

```python
from grimsim import Unit, UnitProfile, Weapon, WeaponProfile
from grimsim.models.ability import SustainedHits, LethalHits, RerollHitOnes
from grimsim.models.dice import DiceExpression

weapon = Weapon(
    profile=WeaponProfile(
        name="Chain Axe",
        attacks=4,              # or DiceExpression.d6()
        skill=3,                # 3+
        strength=5,
        ap=-2,                  # datasheet convention (0, -1, -2, …)
        damage=2,               # or DiceExpression(count=1, sides=3)
    ),
    abilities=(SustainedHits(1), LethalHits()),
)

attacker = Unit(
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
)
```

Units and weapons hold data. They do **not** expose `roll_hits()` / `resolve_saves()` methods — the rule engine owns sequencing.

### 2. Single combat — `simulate_combat`

```python
from grimsim import simulate_combat, CombatContext
from grimsim.examples import melee_attacker, light_infantry

attacker = melee_attacker()
target = light_infantry()

result = simulate_combat(
    attacker=attacker,
    weapon=attacker.weapons[0],
    target=target,
    seed=42,  # or pass rng=np.random.default_rng(42)
    context=CombatContext(hit_modifier=0, wound_modifier=0, save_modifier=0),
)
```

**`CombatResult` fields**

| Field | Meaning |
| --- | --- |
| `attacks` | Attack dice resolved |
| `hits` | Total hits (includes Sustained Hits extras) |
| `critical_hits` | Unmodified 6s on the hit roll |
| `wounds` | Successful wounds + Lethal Hits auto-wounds |
| `critical_wounds` | Unmodified 6s on the wound roll |
| `auto_wounds` | Wounds from Lethal Hits (skipped the wound roll) |
| `failed_saves` | Wounds that got past armour / invuln |
| `total_damage` | Wounds actually removed after allocation (excess discarded) |
| `damage_mitigated` | Damage points ignored by Feel No Pain |
| `models_killed` | Models removed |
| `remaining_models` | Models left |
| `remaining_wounds_on_damaged_model` | Wounds left on the current model, or `None` if undamaged / dead |

### 3. Monte Carlo — `simulate_many`

```python
from grimsim import simulate_many
from grimsim.examples import melee_attacker, light_infantry

attacker = melee_attacker()
target = light_infantry()

mc = simulate_many(
    attacker=attacker,
    weapon=attacker.weapons[0],
    target=target,
    iterations=100_000,
    seed=42,
)

print(mc.mean_damage, mc.median_damage, mc.std_damage)
print(mc.mean_models_killed, mc.min_models_killed, mc.max_models_killed)
print(mc.probability_target_destroyed)
print(mc.probability_models_killed_at_least(5))
print(mc.probability_damage_at_least(10))
df = mc.to_dataframe()  # pandas: one row per iteration
```

### 4. Optional helpers

| Function / type | Module | Purpose |
| --- | --- | --- |
| `RuleEngine.resolve_attack_sequence(...)` | `grimsim.rules` | Direct engine access |
| `wound_target(strength, toughness)` | `grimsim.rules` | Pure S/T table lookup |
| `CombatSimulator` | `grimsim.simulation` | Thin OO wrapper around `simulate_combat` |
| `summarize_matchup(...)` | `grimsim.analysis` | Convenience Monte Carlo helper |
| `connect` / `initialize_schema` | `grimsim.data` | Local DuckDB setup |
| `MatchupModelPlaceholder` | `grimsim.ml` | Documents future `P(win \| …)` API |

## How combat resolution works

```text
resolve attacks  →  hits  →  wounds  →  saves  →  damage + FNP  →  allocate
```

1. **Attacks** — fixed int or `DiceExpression` (e.g. `D6`, `2D6+2`).
2. **Hits** — roll vs weapon skill; unmodified 1s always fail, unmodified 6s always hit / crit. Hit abilities apply here.
3. **Wounds** — standard S vs T table; wound-stage abilities apply. Lethal Hits convert critical hits into auto-wounds (skip this roll only).
4. **Saves** — armour modified by AP; invulnerable ignores AP. The better legal save is used. Impossible armour (>6+) is discarded.
5. **Damage** — fixed or dice per failed save; Feel No Pain can ignore individual damage points.
6. **Allocate** — model-by-model; excess damage on a killing blow does **not** spill to the next model.

### Combat context modifiers

```python
CombatContext(
    hit_modifier=1,    # positive = easier hits (3+ becomes 2+)
    wound_modifier=1,  # positive = easier wounds
    save_modifier=1,   # armour-only (cover-style); does not affect invulns
)
```

## Supported abilities

| Ability | Effect |
| --- | --- |
| `RerollHitOnes()` | Reroll hit rolls of 1 (once) |
| `RerollWoundOnes()` | Reroll wound rolls of 1 (once) |
| `SustainedHits(X)` | Each critical hit adds `X` additional hits |
| `LethalHits()` | Critical hits auto-wound (still allow saves) |
| `FeelNoPain(X)` | Ignore each damage point on `X+` |

Attach abilities to `Weapon.abilities` and/or `Unit.abilities`. Offensive stages read attacker + weapon abilities; Feel No Pain is read from the target unit.

## Example profiles

`grimsim.examples` provides fictional numeric profiles (not datasheet text):

- `melee_attacker()` — Sustained Hits, Lethal Hits, reroll hit 1s
- `light_infantry()` — soft 1W target
- `elite_infantry()` — multi-wound, invuln, Feel No Pain
- `vehicle()` — high T, dice attacks/damage

## Development commands

```bash
uv sync
uv run pytest
uv run pytest --cov=grimsim
uv run ruff check .
uv run mypy src
```

## Current limitations

- No terrain, stratagems, detachments, or battle-round sequencing
- No Blast, Torrent, Hazardous, Devastating Wounds, or mortal wounds
- No multi-weapon / full-unit activation in one call
- Each simulation starts from a fresh undamaged target
- DuckDB is schema-only; combat works without a database
- Matchup ML model is a documented placeholder (not trained)

## Roadmap

1. Devastating Wounds, Blast, Torrent, and mortal-wound pipelines
2. Multi-weapon / full unit activation and overwatch
3. Persist Monte Carlo runs to DuckDB and build analysis notebooks
4. Train matchup models: `P(win | army, opponent, list, mission, terrain, skill, rules version)`
5. Points / rules versioning and datasheet import adapters (non-copyrighted numeric feeds)

## License

See [LICENSE](LICENSE).
