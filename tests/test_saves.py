"""Tests for save selection and resolution."""

from __future__ import annotations

import numpy as np

from grimsim.rules.saves import choose_save, modified_armor_save, resolve_saves


class TestModifiedArmorSave:
    def test_ap_worsens_save(self) -> None:
        # 3+ with AP -1 -> 4+
        assert modified_armor_save(3, -1) == 4

    def test_ap_zero(self) -> None:
        assert modified_armor_save(3, 0) == 3

    def test_save_modifier_improves(self) -> None:
        assert modified_armor_save(4, -1, save_modifier=1) == 4  # 4 - (-1) - 1 = 4


class TestChooseSave:
    def test_armor_only(self) -> None:
        choice = choose_save(3, 0, None)
        assert choice.target == 3
        assert choice.source == "armor"

    def test_invulnerable_better(self) -> None:
        # Armor 5+ with AP -2 -> 7+ (impossible); invuln 4+ wins
        choice = choose_save(5, -2, 4)
        assert choice.target == 4
        assert choice.source == "invulnerable"

    def test_armor_better_than_invuln(self) -> None:
        choice = choose_save(2, 0, 5)
        assert choice.target == 2
        assert choice.source == "armor"

    def test_impossible_armor_uses_invuln(self) -> None:
        choice = choose_save(3, -4, 5)  # 3 - (-4) = 7, impossible
        assert choice.target == 5
        assert choice.source == "invulnerable"

    def test_impossible_armor_no_invuln(self) -> None:
        choice = choose_save(3, -4, None)
        assert choice.target is None
        assert choice.source == "none"

    def test_tied_prefers_invulnerable(self) -> None:
        choice = choose_save(4, 0, 4)
        assert choice.target == 4
        assert choice.source == "invulnerable"

    def test_save_modifier_is_armour_only(self) -> None:
        # +1 armour modifier must not improve a 4++ invulnerable save.
        choice = choose_save(5, 0, 4, save_modifier=1)
        assert choice.target == 4


class TestResolveSaves:
    def test_auto_fail_when_no_save(self) -> None:
        result = resolve_saves(5, 3, -4, None, 0, np.random.default_rng(0))
        assert result.failed_saves == 5
        assert result.successful_saves == 0
        assert result.save_target is None

    def test_deterministic(self) -> None:
        a = resolve_saves(20, 3, -1, None, 0, np.random.default_rng(42))
        b = resolve_saves(20, 3, -1, None, 0, np.random.default_rng(42))
        assert a.failed_saves == b.failed_saves

    def test_zero_wounds(self) -> None:
        result = resolve_saves(0, 3, 0, None, 0, np.random.default_rng(0))
        assert result.failed_saves == 0
