"""A build result must be reachable from the tree as soon as it exists.

``X.of(context)`` resolves by walking ``_parent`` upward, and measuring is a
legitimate thing to do before mounting (App auto window sizing does it). A
composable that parents its built child only at mount therefore hands the
measurement a subtree with a broken ancestor chain: every lookup inside it
fails, and ``Theme.of`` blames the widget for a call the framework made. See
issue #476.
"""

from __future__ import annotations

import logging

import pytest

from nuiitivet.common.logging_once import set_log_once_enabled
from nuiitivet.layout.measure import preferred_size
from nuiitivet.material.card import Card
from nuiitivet.material.text import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget

_THEME_LOGGER = "nuiitivet.theme.theme"


class _Leaf(Widget):
    def build(self) -> Widget:  # pragma: no cover - never composed
        return self


class _Composes(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.leaf = _Leaf()

    def build(self) -> Widget:
        return self.leaf


@pytest.fixture
def no_log_dedup():
    """Disable once-per-process de-dup so a warning cannot be masked."""
    set_log_once_enabled(False)
    yield
    set_log_once_enabled(True)


def test_built_child_is_parented_while_the_host_is_unmounted() -> None:
    host = _Composes()
    host.rebuild()

    assert host.built_child is host.leaf
    assert host.leaf._parent is host


def test_unmounted_measurement_parents_the_build_result() -> None:
    """The App auto-sizing path: measure a composable that never mounted."""
    host = _Composes()
    preferred_size(host)

    assert host.leaf._parent is host


def test_unmounting_releases_the_built_childs_parent_link() -> None:
    host = _Composes()
    host.mount(None)
    leaf = host.built_child
    assert leaf is not None and leaf._parent is host

    host.unmount()

    assert leaf._parent is None


def test_releasing_does_not_steal_a_newer_parent() -> None:
    host = _Composes()
    host.rebuild()
    leaf = host.leaf
    adopter = _Leaf()
    adopter.add_child(leaf)
    assert leaf._parent is adopter

    host._unmount_built()

    assert leaf._parent is adopter


def test_clearing_children_keeps_a_reparented_childs_link() -> None:
    """A store may only drop the link it owns.

    ``Card`` re-parents its child into a scoped fragment and *then* clears its
    own child list; an unconditional clear would orphan a live widget.
    """
    old_parent = _Leaf()
    new_parent = _Leaf()
    child = _Leaf()

    old_parent.add_child(child)
    new_parent.add_child(child)
    assert child._parent is new_parent

    old_parent.clear_children()

    assert child._parent is new_parent


def test_measuring_an_unmounted_card_does_not_report_a_premature_lookup(
    caplog: pytest.LogCaptureFixture, no_log_dedup
) -> None:
    """The symptom from #476: the warning named ``Text``, which was blameless."""
    card = Card(width=200, height=100, child=Text("Fixed Size Box"), padding=16)

    with caplog.at_level(logging.WARNING, logger=_THEME_LOGGER):
        preferred_size(card)

    premature = [r for r in caplog.records if r.name == _THEME_LOGGER and "before it was mounted" in r.getMessage()]
    assert premature == []


class _SelfBuilder(ComposableWidget):
    """Decorates itself and returns itself, the way ``Card`` does."""

    def build(self) -> Widget:
        return self


def test_a_host_that_builds_itself_is_not_made_its_own_parent() -> None:
    """``find_ancestor`` would otherwise walk a one-node cycle forever."""
    host = _SelfBuilder()

    host.rebuild()

    assert host._parent is not host


def test_a_host_that_builds_itself_does_not_hold_itself_as_built_child() -> None:
    """``layout``/``paint``/``hit_test`` delegate to ``_built``, so storing
    ``self`` there recurses until the stack runs out."""
    host = _SelfBuilder()

    host.rebuild()

    assert host.built_child is not host


def test_rebuilding_a_self_building_host_can_still_lay_out() -> None:
    host = _SelfBuilder()
    host.rebuild()

    host.layout(100, 50)  # would raise RecursionError if _built were self
