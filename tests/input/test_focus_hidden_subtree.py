"""Hidden subtrees are out of the Tab sequence (Collapsible, visible(), side sheet)."""

from __future__ import annotations

import pytest

from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.material.sheet import StandardSideSheet
from nuiitivet.modifiers.visible import visible
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.app import App
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.interaction import FocusNode, FocusSource, FocusTraversalBlocker

SHIFT = 1


def _focus_node(widget: Clickable) -> FocusNode:
    node = widget.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    return node


def _mounted_app(root) -> App:
    app = App(root)
    root.mount(app)
    return app


# --- Collapsible ---------------------------------------------------------------


def test_closed_collapsible_is_skipped_by_tab() -> None:
    """The whole subtree of a closed Collapsible drops out of the Tab sequence."""
    before = Clickable()
    inside_a = Clickable()
    inside_b = Clickable()
    after = Clickable()
    root = Column([before, Collapsible(Column([inside_a, inside_b]), opened=False), after])
    app = _mounted_app(root)

    assert app._collect_focus_nodes() == [_focus_node(before), _focus_node(after)]


def test_open_collapsible_keeps_its_children_in_the_tab_sequence() -> None:
    """Regression guard: an open Collapsible must not hide anything."""
    before = Clickable()
    inside = Clickable()
    after = Clickable()
    root = Column([before, Collapsible(Column([inside]), opened=True), after])
    app = _mounted_app(root)

    assert app._collect_focus_nodes() == [
        _focus_node(before),
        _focus_node(inside),
        _focus_node(after),
    ]


def test_tab_moves_across_a_closed_collapsible() -> None:
    """Tab / Shift+Tab step straight over the hidden content."""
    before = Clickable()
    inside = Clickable()
    after = Clickable()
    root = Column([before, Collapsible(Column([inside]), opened=False), after])
    app = _mounted_app(root)

    app._dispatch_key_press("tab")
    assert before.state.focused is True

    app._dispatch_key_press("tab")
    assert after.state.focused is True
    assert inside.state.focused is False

    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert before.state.focused is True


def test_closing_a_collapsible_releases_focus_held_inside() -> None:
    """Focus may not stay on a widget the user can no longer see."""
    inside = Clickable()
    opened = _ObservableValue(True)
    root = Column([Collapsible(Column([inside]), opened=opened)])
    app = _mounted_app(root)

    app.request_focus(_focus_node(inside), FocusSource.KEYBOARD)
    assert inside.state.focused is True

    opened.value = False
    app._release_focus_if_blocked()

    assert app._focused_node is None
    assert inside.state.focused is False


def test_collapsible_traversal_follows_opened_not_the_size_animation() -> None:
    """Traversal flips with ``opened``, without waiting for the size animation."""
    inside = Clickable()
    opened = _ObservableValue(False)
    content = Box(Column([inside]), width=Sizing.fixed(100), height=Sizing.fixed(50))
    collapsible = Collapsible(content, opened=opened)
    app = _mounted_app(Column([collapsible]))

    collapsible.preferred_size()
    assert app._collect_focus_nodes() == []

    # Opening: reachable right away, while the collapsible is still expanding.
    opened.value = True
    collapsible.preferred_size()
    assert collapsible.preferred_size()[0] < 100  # still animating open
    assert app._collect_focus_nodes() == [_focus_node(inside)]

    # Closing: unreachable right away, before the collapse animation finishes.
    opened.value = False
    collapsible.preferred_size()
    assert app._collect_focus_nodes() == []


# --- visible() -----------------------------------------------------------------


def test_hidden_visible_subtree_is_skipped_by_tab() -> None:
    """visible(False) keeps its layout space but not its Tab stops."""
    before = Clickable()
    inside = Clickable()
    hidden = Column([inside]).modifier(visible(False))
    root = Column([before, hidden])
    app = _mounted_app(root)

    assert app._collect_focus_nodes() == [_focus_node(before)]


def test_visible_observable_restores_tab_stops_when_shown() -> None:
    shown = _ObservableValue(False)
    inside = Clickable()
    root = Column([Column([inside]).modifier(visible(shown))])
    app = _mounted_app(root)

    assert app._collect_focus_nodes() == []

    shown.value = True
    assert app._collect_focus_nodes() == [_focus_node(inside)]


# --- Standard side sheet -------------------------------------------------------


def test_closed_standard_side_sheet_does_not_expose_its_content_to_tab() -> None:
    """The sheet collapses via Collapsible, so its content must go with it."""
    outside = Clickable()
    inside = Clickable()
    sheet = StandardSideSheet(Column([inside]), opened=False)
    app = _mounted_app(Column([outside, sheet]))

    assert _focus_node(inside) not in app._collect_focus_nodes()
    assert _focus_node(outside) in app._collect_focus_nodes()


# --- FocusTraversalBlocker contract --------------------------------------------


def test_focus_traversal_blocker_subclass_must_implement_the_property() -> None:
    """Inheriting the mixin means committing to an answer — no silent default."""

    class Forgetful(FocusTraversalBlocker, Box):
        pass

    with pytest.raises(TypeError):
        Forgetful()  # type: ignore[abstract]  # mypy rejects it too — that is the point
