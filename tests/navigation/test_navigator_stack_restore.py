"""Tests for declarative navigation stack snapshot/restore across reload (#378).

A hot reload rebuilds the tree from the factory, so the freshly built navigator
starts at its initial route. These tests exercise the descriptor log that lets
declaratively pushed (intent) routes be replayed onto the rebuilt navigator,
while imperative instance pushes are recorded as opaque and stop the replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from nuiitivet.navigation import Navigator, Route
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def build(self) -> Widget:
        return self


def _make_go_intent_cls() -> type:
    """Build a fresh ``GoIntent`` class object with a stable qualified name.

    Each call returns a distinct class that nonetheless shares ``__module__`` and
    ``__qualname__``, simulating a hot reload redefining the same intent type.
    """

    @dataclass(frozen=True)
    class GoIntent:
        name: str

    return GoIntent


def _make_other_intent_cls() -> type:
    @dataclass(frozen=True)
    class OtherIntent:
        name: str

    return OtherIntent


def test_snapshot_logs_declarative_pushes() -> None:
    Intent = _make_go_intent_cls()
    nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )

    nav.push(Intent("a"))
    nav.push(Intent("b"))

    snap = nav.snapshot_stack()
    assert len(snap) == 2
    assert [d.intent.name for d in snap if d is not None] == ["a", "b"]


def test_snapshot_records_instance_push_as_opaque() -> None:
    Intent = _make_go_intent_cls()
    nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )

    nav.push(Intent("a"))
    nav.push(_FlagWidget())  # imperative instance push
    nav.push(Route(builder=_FlagWidget))  # imperative route push

    snap = nav.snapshot_stack()
    assert len(snap) == 3
    assert snap[0] is not None
    assert snap[1] is None
    assert snap[2] is None


@pytest.mark.asyncio
async def test_snapshot_reflects_pops() -> None:
    Intent = _make_go_intent_cls()
    nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )
    nav.push(Intent("a"))
    nav.push(Intent("b"))
    assert len(nav.snapshot_stack()) == 2

    await nav.request_back()

    snap = nav.snapshot_stack()
    assert len(snap) == 1
    assert snap[0] is not None
    assert snap[0].intent.name == "a"


def test_restore_replays_intents_across_class_swap() -> None:
    OldIntent = _make_go_intent_cls()
    old_nav = Navigator.intents(
        initial_route=OldIntent("home"),
        routes={OldIntent: lambda _i: _FlagWidget()},
    )
    old_nav.push(OldIntent("a"))
    old_nav.push(OldIntent("b"))
    snap = old_nav.snapshot_stack()

    # Simulate a reload: a brand-new class object with the same qualified name,
    # plus a route table keyed by it. Restore must bridge old value -> new builder.
    NewIntent = _make_go_intent_cls()
    assert NewIntent is not OldIntent
    seen: list[Any] = []

    def _record(intent: Any) -> _FlagWidget:
        seen.append(intent)
        return _FlagWidget()

    new_nav = Navigator.intents(
        initial_route=NewIntent("home"),
        routes={NewIntent: _record},
    )
    seen.clear()  # drop the initial-route resolution; keep only replayed pushes

    restored = new_nav.restore_stack(snap)

    assert restored == 2
    assert new_nav.can_pop() is True
    assert [i.name for i in seen] == ["a", "b"]
    assert len(new_nav.snapshot_stack()) == 2


def test_restore_stops_at_opaque_push() -> None:
    Intent = _make_go_intent_cls()
    old_nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )
    old_nav.push(Intent("a"))
    old_nav.push(_FlagWidget())  # opaque
    old_nav.push(Intent("c"))
    snap = old_nav.snapshot_stack()

    new_nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )

    restored = new_nav.restore_stack(snap)

    # Replay stops at the opaque entry; the route above it is left collapsed.
    assert restored == 1


def test_restore_stops_when_intent_not_registered() -> None:
    Intent = _make_go_intent_cls()
    old_nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )
    old_nav.push(Intent("a"))
    snap = old_nav.snapshot_stack()

    Other = _make_other_intent_cls()
    new_nav = Navigator.intents(
        initial_route=Other("home"),
        routes={Other: lambda _i: _FlagWidget()},
    )

    restored = new_nav.restore_stack(snap)

    assert restored == 0
    assert new_nav.can_pop() is False


def test_restore_empty_snapshot_is_noop() -> None:
    Intent = _make_go_intent_cls()
    nav = Navigator.intents(
        initial_route=Intent("home"),
        routes={Intent: lambda _i: _FlagWidget()},
    )

    assert nav.restore_stack([]) == 0
    assert nav.can_pop() is False
