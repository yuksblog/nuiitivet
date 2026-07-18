"""Tests for the ``keyed`` modifier: pure-metadata identity, never wraps."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.modifiers import clickable, keyed
from nuiitivet.modifiers.keyed import KeyedModifier
from nuiitivet.widgets.text import TextBase as Text


def test_keyed_sets_key_and_returns_same_widget() -> None:
    widget = Text("hello")
    result = widget.modifier(keyed("greeting"))
    # Pure metadata: the very same node is returned (no wrapper), with key set.
    assert result is widget
    assert widget.key == "greeting"


def test_keyed_coerces_to_str() -> None:
    widget = Text("x")
    widget.modifier(keyed(123))  # type: ignore[arg-type]
    assert widget.key == "123"


def test_keyed_default_key_is_none() -> None:
    assert Text("x").key is None


def test_keyed_does_not_add_a_tree_node() -> None:
    child = Text("child")
    col = Column([child])
    col.modifier(keyed("col"))
    # The column keeps its single original child; keying added no wrapper.
    assert col.key == "col"
    assert list(col.children) == [child]


def test_keyed_outermost_when_chained_with_wrapping_modifier() -> None:
    widget = Text("x")
    # clickable wraps into an interaction region; keyed applied last lands the
    # key on the outer node so the bridge targets what actually holds the rect.
    result = widget.modifier(clickable(on_click=lambda: None) | keyed("row"))
    assert result.key == "row"


def test_keyed_factory_returns_modifier() -> None:
    assert isinstance(keyed("x"), KeyedModifier)
