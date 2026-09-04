"""Tests for the dev navigation snapshot/restore glue.

These cover the thin adapter over the App's navigator: a round-trip across a
rebuild, and the safe no-op behavior when the App has no navigator yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.dev.navigation_snapshot import restore_navigation, snapshot_navigation
from nuiitivet.navigation import Navigator
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def build(self) -> Widget:
        return self


@dataclass(frozen=True)
class _GoIntent:
    name: str


def _intent_navigator() -> Navigator:
    return Navigator.intents(
        initial_route=_GoIntent("home"),
        routes={_GoIntent: lambda _i: _FlagWidget()},
    )


class _NavigatorlessApp:
    """Stands in for an App caught before its content root exists."""

    _navigator = None


def test_snapshot_without_a_navigator_returns_empty() -> None:
    assert snapshot_navigation(_NavigatorlessApp()) == []  # type: ignore[arg-type]


def test_restore_without_a_navigator_returns_zero() -> None:
    # A non-empty snapshot with no navigator restores nothing, safely.
    fake = [object()]
    assert restore_navigation(_NavigatorlessApp(), fake) == 0  # type: ignore[arg-type]


def test_round_trip_replays_stack_onto_the_rebuilt_navigator() -> None:
    app = App(Window(content=_intent_navigator())).main_window
    app.navigator.push(_GoIntent("a"))
    app.navigator.push(_GoIntent("b"))

    snap = snapshot_navigation(app)
    assert len(snap) == 2

    # A reload swaps in a fresh navigator; restore replays onto whichever one the
    # App has adopted by then.
    app._root_factory = _intent_navigator
    app._commit_content_root(app._rebuild_content_root())
    new_nav = app.navigator

    restored = restore_navigation(app, snap)
    assert restored == 2
    assert new_nav.can_pop() is True
