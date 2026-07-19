"""Tests for the dev navigation snapshot/restore glue (#378).

These cover the thin adapter over ``Navigator.root()``: a round-trip through the
process-global navigator, and the safe no-op behavior when no root is set.
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.dev.navigation_snapshot import restore_navigation, snapshot_navigation
from nuiitivet.navigation import Navigator
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def build(self) -> Widget:
        return self


@dataclass(frozen=True)
class _GoIntent:
    name: str


def test_snapshot_with_no_root_returns_empty() -> None:
    Navigator._root = None  # type: ignore[attr-defined]
    assert snapshot_navigation() == []


def test_restore_with_no_root_returns_zero() -> None:
    Navigator._root = None  # type: ignore[attr-defined]

    # A non-empty snapshot with no navigator root restores nothing, safely.
    fake = [object()]
    assert restore_navigation(fake) == 0  # type: ignore[arg-type]


def test_round_trip_replays_stack_onto_new_root() -> None:
    old_nav = Navigator.intents(
        initial_route=_GoIntent("home"),
        routes={_GoIntent: lambda _i: _FlagWidget()},
    )
    Navigator.set_root(old_nav)
    old_nav.push(_GoIntent("a"))
    old_nav.push(_GoIntent("b"))

    snap = snapshot_navigation()
    assert len(snap) == 2

    # A reload swaps in a fresh navigator as the root; restore replays onto it.
    new_nav = Navigator.intents(
        initial_route=_GoIntent("home"),
        routes={_GoIntent: lambda _i: _FlagWidget()},
    )
    Navigator.set_root(new_nav)

    restored = restore_navigation(snap)
    assert restored == 2
    assert new_nav.can_pop() is True
