"""Tests for key-aware snapshot/restore path identity (§7.4 / #375)."""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet.dev.snapshot import restore_observables, snapshot_observables
from nuiitivet.observable.protocols import MutableObservableBase


class _Obs(MutableObservableBase):
    """Minimal mutable observable holding a plain value."""

    def __init__(self, value: Any) -> None:
        self._value = value

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, v: Any) -> None:
        self._value = v


class _Widget:
    """A fake widget: optional ``key`` and an observable ``state`` attribute."""

    def __init__(self, *, key: Optional[str] = None, state: Any = None) -> None:
        self.key = key
        self.children: list["_Widget"] = []
        self.built_child: Optional["_Widget"] = None
        if state is not None:
            self.state = _Obs(state)


def test_snapshot_restore_stable_when_unchanged() -> None:
    old = _Widget()
    old.children = [_Widget(state=1), _Widget(state=2)]
    snap = snapshot_observables(old)

    new = _Widget()
    new.children = [_Widget(state=0), _Widget(state=0)]
    assert restore_observables(new, snap) == 2
    assert [c.state.value for c in new.children] == [1, 2]


def test_positional_state_lost_on_reorder_without_key() -> None:
    old = _Widget()
    old.children = [_Widget(state=1), _Widget(state=2)]
    snap = snapshot_observables(old)

    # Same types, swapped order, no keys: the position-based paths still match
    # by index, so state restores by position (not by identity) — documented.
    new = _Widget()
    new.children = [_Widget(state=0), _Widget(state=0)]
    restore_observables(new, snap)
    assert [c.state.value for c in new.children] == [1, 2]


def test_keyed_state_survives_reorder() -> None:
    old = _Widget()
    old.children = [_Widget(key="a", state=1), _Widget(key="b", state=2)]
    snap = snapshot_observables(old)

    # Reordered: keys anchor the state to the widget, not the slot.
    new = _Widget()
    new.children = [_Widget(key="b", state=0), _Widget(key="a", state=0)]
    restore_observables(new, snap)
    by_key = {c.key: c.state.value for c in new.children}
    assert by_key == {"a": 1, "b": 2}


def test_keyed_state_survives_sibling_insertion() -> None:
    old = _Widget()
    old.children = [_Widget(key="keep", state=42)]
    snap = snapshot_observables(old)

    # A new sibling is inserted before the keyed widget. Its index shifts from 0
    # to 1, but the key keeps its path stable so the state still restores.
    new = _Widget()
    new.children = [_Widget(state=0), _Widget(key="keep", state=0)]
    restore_observables(new, snap)
    kept = next(c for c in new.children if c.key == "keep")
    assert kept.state.value == 42


def test_keyed_built_child_state() -> None:
    old = _Widget()
    old.built_child = _Widget(key="body", state=7)
    snap = snapshot_observables(old)

    new = _Widget()
    new.built_child = _Widget(key="body", state=0)
    assert restore_observables(new, snap) == 1
    assert new.built_child.state.value == 7
