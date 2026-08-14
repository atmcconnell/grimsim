"""Tests for Ruleset, Faction, Detachment, and related value semantics."""

from __future__ import annotations

from datetime import date

import pytest

from grimsim.models.detachment import Detachment
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset


def test_ruleset_construction_and_equality() -> None:
    a = Ruleset(
        id="r1",
        edition="10th",
        rules_version="0.2.0",
        points_version="2025.01",
        effective_date=date(2025, 1, 1),
    )
    b = Ruleset(
        id="r1",
        edition="10th",
        rules_version="0.2.0",
        points_version="2025.01",
        effective_date=date(2025, 1, 1),
    )
    assert a == b
    assert a.slug == "r1"
    assert a.edition == "10th"
    assert a.points_version == "2025.01"


def test_ruleset_derived_slug() -> None:
    ruleset = Ruleset(
        edition="10th",
        rules_version="0.2.0",
        points_version="2025.01",
        effective_date=date(2025, 1, 1),
    )
    assert ruleset.slug == "10th:0.2.0:2025.01"


def test_ruleset_rejects_empty_fields() -> None:
    with pytest.raises(ValueError):
        Ruleset(
            edition="",
            rules_version="0.2.0",
            points_version="2025.01",
            effective_date=date(2025, 1, 1),
        )


def test_faction_and_detachment() -> None:
    faction = Faction(id="crimson_hosts", name="Crimson Hosts")
    detachment = Detachment(
        id="blood_tide",
        name="Blood Tide",
        faction_id=faction.id,
    )
    assert detachment.faction_id == faction.id


def test_faction_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        Faction(id="", name="X")
