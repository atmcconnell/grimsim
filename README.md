# GrimSim

Python simulation engine for competitive Warhammer 40,000 analysis.

**v0.2** extends the v0.1 unit-vs-unit combat simulator with first-class army
roster concepts: rulesets, factions, detachments, army lists, and runtime armies.

Core pipeline:

```text
attacks → hits → wounds → saves → damage → models killed
```

Guiding principles:

> Units describe data. Rules interpret that data. Simulators execute those rules repeatedly.

> Army lists describe roster intent. Armies represent runtime state. Rulesets define the environment in which both are valid.

There is no graphical UI — you use the Python API.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Architecture (v0.2)

```text
Ruleset
   ↓
Faction + Detachment
   ↓
ArmyList
   ↓
Army / UnitState
   ↓
Rule Engine
   ↓
Simulator
   ↓
Analysis
```

### Layer distinctions

| Concept | Role |
| --- | --- |
| `Unit` | Immutable game profile / combat data |
| `UnitSelection` | That unit chosen for a roster (points, quantity, enhancements) |
| `ArmyList` | Static roster definition under a faction/detachment/ruleset |
| `UnitState` | Mutable in-game state (models remaining, wounds, destroyed) |
| `Army` | Runtime representation instantiated from an `ArmyList` |
| `Ruleset` | Edition / rules / points environment |
| `Detachment` | Faction-specific strategic rules package |
| `Faction` | Identity data only — no combat behavior |

Low-level combat (`simulate_combat` / `simulate_many`) still works **without**
building an army list.

| Layer | Package | Responsibility |
| --- | --- | --- |
| Domain data | `grimsim.models` | Units, weapons, dice, roster, runtime state |
| Validation | `grimsim.validation` | Extensible army-list legality checks |
| Rules | `grimsim.rules` | Stage-based combat resolution |
| Simulation | `grimsim.simulation` | Single combat + Monte Carlo (+ activation stub) |
| Analysis | `grimsim.analysis` | Matchup summary helpers |
| Persistence | `grimsim.data` | Optional DuckDB adapters (not required for combat) |
| ML | `grimsim.ml` | Future matchup prediction placeholder |

## What is implemented

### v0.1 (still supported)

- Dice engine with injectable NumPy RNG
- Immutable `Unit` / `Weapon` profiles
- Hit / wound / save / damage stages
- Abilities: reroll 1s, Sustained Hits, Lethal Hits, Feel No Pain
- `simulate_combat` / `simulate_many`

### v0.2 (new)

- `Ruleset`, `Faction`, `Detachment`, `Enhancement`
- `UnitSelection`, `ArmyList` with derived points helpers
- `ArmyListValidator` / `validate_army_list` → `ValidationResult`
- `Army` + `UnitState` runtime models (`Army.from_list`)
- DuckDB tables for rulesets, factions, detachments, army lists
- `simulate_unit_activation` stub (implemented in v0.3)

## Army list example

```python
from datetime import date

from grimsim import (
    Army,
    ArmyList,
    Detachment,
    Enhancement,
    Faction,
    Ruleset,
    UnitSelection,
    validate_army_list,
)
from grimsim.examples import melee_attacker, light_infantry, elite_infantry, vehicle

ruleset = Ruleset(
    id="10th-balanced-2025.01",
    edition="10th",
    rules_version="0.2.0",
    points_version="2025.01",
    effective_date=date(2025, 1, 1),
)
faction = Faction(id="crimson_hosts", name="Crimson Hosts")
detachment = Detachment(
    id="blood_tide",
    name="Blood Tide",
    faction_id=faction.id,
)

army_list = ArmyList(
    name="Example Army",
    faction=faction,
    detachment=detachment,
    ruleset=ruleset,
    points_limit=2000,
    selections=(
        UnitSelection(unit=melee_attacker(), quantity=2, points=180),
        UnitSelection(unit=light_infantry(), quantity=2, points=120),
        UnitSelection(
            unit=elite_infantry(),
            quantity=1,
            points=200,
            enhancements=(Enhancement(id="blade", name="Exemplar Blade", points=25),),
        ),
        UnitSelection(unit=vehicle(), quantity=2, points=220),
    ),
)

validation = validate_army_list(army_list)
print(army_list.total_points, army_list.remaining_points, validation.is_valid)

army = Army.from_list(army_list)  # runtime state, separate from the list
```

Or use the bundled demo:

```python
from grimsim.examples import example_army_list, example_validated_army
from grimsim import validate_army_list

army_list = example_army_list()
print(army_list.total_points, validate_army_list(army_list).is_valid)
army_list, army = example_validated_army()
```

### Validation behavior

`validate_army_list` returns a `ValidationResult` with structured issues:

| Code | Meaning |
| --- | --- |
| `DETACHMENT_FACTION_MISMATCH` | Detachment does not belong to the list faction |
| `OVER_POINTS` | `total_points` exceeds `points_limit` |
| `EMPTY_ARMY_LIST` | No selections |

Construction also rejects invalid quantity/points and duplicate enhancement IDs on a selection. The validator is intentionally small and easy to extend later.

## Combat APIs (unchanged)

```python
from grimsim import simulate_combat, simulate_many
from grimsim.examples import melee_attacker, light_infantry

attacker = melee_attacker()
target = light_infantry()

result = simulate_combat(attacker, attacker.weapons[0], target, seed=42)
mc = simulate_many(attacker, attacker.weapons[0], target, iterations=100_000, seed=42)
```

## Persistence

Optional DuckDB helpers (combat never requires a database):

```python
from grimsim.data import connect, initialize_schema, save_army_list, load_army_list

conn = connect()  # or connect("grimsim.duckdb")
initialize_schema(conn)
save_army_list(conn, army_list, list_id="my-list")
loaded = load_army_list(conn, "my-list")
```

Tables: `rulesets`, `rules_versions` (legacy), `factions`, `detachments`,
`army_lists`, `army_list_selections`, `simulation_runs`.

## Development commands

```bash
uv sync
uv run pytest
uv run pytest --cov=grimsim
uv run ruff check .
uv run mypy src
```

## Current limitations

- No full official army construction rules (max copies, transports, leaders, …)
- Enhancements are points/identity only — no combat effects yet
- Detachment `effects` are typed placeholders, not interpreted in combat
- `simulate_unit_activation` is a v0.3 stub
- Persisted units reload without full weapon/ability graphs
- No terrain, stratagems, battle rounds, or multi-unit games

## Roadmap

### v0.3
- Full-unit activation (`simulate_unit_activation`)
- Multiple weapon profiles per activation
- Points/version-aware unit data
- Richer army-list validation
- Simulation persistence

### v0.4
- Trade evaluation
- Matchup representation
- Tournament game data
- Matchup analytics

### v0.5
- Baseline statistical / ML matchup models

Genetic algorithms and list optimization are intentionally deferred.

## License

See [LICENSE](LICENSE).
