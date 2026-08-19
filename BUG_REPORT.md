# Bug report (v0.3 scan)

Scan date: 2026-08-18  
Scope: GrimSim v0.3 codebase (`src/grimsim`, `tests`)  
Method: adversarial tests in `tests/test_bug_scan.py`, plus review of activation, catalogs, validation, and persistence.

All items below are **fixed** unless marked as remaining limitation.

---

## Fixed

### BUG-001 — `Army.from_list` ignored roster size

**Severity:** High  
**Where:** `src/grimsim/models/army.py`

Runtime `UnitState` used `selection.unit.profile.model_count` instead of `selection.size`. A 5-model selection of a 10-model profile instantiated 10 models in game state.

**Fix:** Instantiate from `selection.size`.

---

### BUG-002 — Killing models left stale partial wounds

**Severity:** High  
**Where:** `UnitState.apply_models_lost`

After `apply_models_lost(1)` on a unit with a wounded current model, `wounds_on_current_model` stayed set. The next model would inherit the previous model's remaining wounds.

**Fix:** Clear partial wounds whenever at least one model is removed and the unit still has models left.

---

### BUG-003 — Destroyed units could still carry wounds

**Severity:** Medium  
**Where:** `UnitState.__post_init__` / `from_unit`

`UnitState.from_unit(..., remaining_models=0, wounds_on_current_model=1)` produced `destroyed=True` with wounds still set, which is inconsistent and could crash damage allocation (`starting_wounds` must be `1..W`).

**Fix:** Remaining 0 forces `destroyed=True` and `wounds_on_current_model=None`. Invalid wound values now raise.

---

### BUG-004 — Invalid partial wounds were accepted

**Severity:** Medium  
**Where:** `UnitState`

`wounds_on_current_model=99` on a 2-wound model was allowed, then failed later inside `allocate_damage`.

**Fix:** Validate `1 <= wounds <= wounds_per_model`. Full wounds are normalized to `None` (undamaged).

---

### BUG-005 — Persistence dropped unit identity and size

**Severity:** High  
**Where:** `save_army_list` / `load_army_list`

Selections stored profile name and profile `model_count` only. After reload, `unit.identity` became the display name (`Example Berserkers` instead of `example-berserkers`) and size overrides were lost, breaking catalog lookups.

**Fix:** Persist `unit_id` and `selection.size`. Row primary keys use SHA-256 instead of Python `hash()` (which is process-randomized).

---

### BUG-006 — Over-points skipped when any selection lacked catalog cost

**Severity:** Medium  
**Where:** `PointsLimitRule`

`army_list.points_cost(catalog)` raised `MissingPointsError` on the first missing entry. The rule swallowed that and returned no `OVER_POINTS` issue, even when other selections already exceeded the limit.

**Fix:** Sum known catalog costs and still emit `OVER_POINTS` if that partial total exceeds the limit. `MISSING_POINTS` continues to fire separately.

---

### BUG-007 — Profile catalog used the first duplicate entry

**Severity:** Low  
**Where:** `ProfileCatalog.try_unit_for`

Duplicate `(unit_id, ruleset)` entries returned the first snapshot. Points undated lookups used last-write. Inconsistent and surprising if a catalog is built incrementally.

**Fix:** Last matching entry wins.

---

## Remaining limitations (not treated as defects)

| ID | Note |
| --- | --- |
| L-001 | Reloaded army lists still have empty `weapons` / `abilities` (combat requires the original unit objects). |
| L-002 | `ActivationResult.final_target` is a mutable `UnitState`; mutating it does not update the aggregate fields on the frozen result. |
| L-003 | Default attack plan fires every remaining model with every weapon (`disjoint=False`). Mixed loadouts need an explicit `AttackPlan`. |
| L-004 | Enhancements and detachment effects are list metadata only; they do not modify combat. |
| L-005 | No movement, charge, terrain, overwatch, or battle-round sequencing. |

---

## Tests added

`tests/test_bug_scan.py` covers BUG-001 through BUG-007.

Full suite after fixes: **217 passed**.
