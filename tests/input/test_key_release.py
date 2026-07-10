"""Tests for key-release delivery and the authoritative modifier-key mask.

Key release had no dispatch path at all before #310: the runner dropped every
symbol except ``escape`` and forwarded that one as a *press*. These tests cover
the release path end to end at the framework boundary — ``_dispatch_key_release``,
``FocusNode.handle_key_release_event``, ``focusable(on_key_up=...)`` — plus the
App-owned modifier-key mask that release maintenance and window deactivation feed.
"""

from __future__ import annotations

import asyncio

import pytest
from pyglet.window import key as pyglet_key

from nuiitivet.backends.pyglet.runner import _normalize_key
from nuiitivet.input.codes import MOD_CTRL, MOD_SHIFT
from nuiitivet.layout.container import Container
from nuiitivet.modifiers.focus import focusable
from nuiitivet.navigation import Navigator
from nuiitivet.overlay import Overlay
from nuiitivet.runtime.app import App
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import FocusNode
from nuiitivet.widgeting.widget import Widget


class _LeafWidget(Widget):
    def paint(self, canvas, x, y, w, h):  # pragma: no cover - never painted
        pass


def _mounted_app(root: Widget) -> App:
    app = App(root)
    app.root.mount(app)
    return app


# ---------------------------------------------------------------------------
# Letter key: press/release pair
# ---------------------------------------------------------------------------


def test_letter_press_and_release_reach_separate_callbacks() -> None:
    presses: list[tuple[str, int]] = []
    releases: list[tuple[str, int]] = []

    child = _LeafWidget().modifier(
        focusable(
            on_key=lambda k, m: presses.append((k, m)) or True,
            on_key_up=lambda k, m: releases.append((k, m)) or True,
        )
    )
    root = Box()
    root.add_child(child)
    app = _mounted_app(root)
    child.get_node(FocusNode).request_focus()

    assert app._dispatch_key_press("a") is True
    assert app._dispatch_key_release("a") is True

    assert presses == [("a", 0)]
    assert releases == [("a", 0)]

    app.root.unmount()


def test_release_does_not_synthesize_a_press() -> None:
    """A node with only on_key must never see its press callback fire on release."""
    presses: list[str] = []

    child = _LeafWidget().modifier(focusable(on_key=lambda k, m: presses.append(k) or True))
    root = Box()
    root.add_child(child)
    app = _mounted_app(root)
    child.get_node(FocusNode).request_focus()

    assert app._dispatch_key_release("a") is False  # nothing consumes it
    assert presses == []  # crucially: no phantom press

    app.root.unmount()


# ---------------------------------------------------------------------------
# Modifier key: press/release pair carries the mask
# ---------------------------------------------------------------------------


def test_modifier_key_release_carries_mask() -> None:
    releases: list[tuple[str, int]] = []

    child = _LeafWidget().modifier(
        focusable(on_key_up=lambda k, m: releases.append((k, m)) or True)
    )
    root = Box()
    root.add_child(child)
    app = _mounted_app(root)
    child.get_node(FocusNode).request_focus()

    assert app._dispatch_key_release("lctrl", MOD_CTRL) is True
    assert releases == [("lctrl", MOD_CTRL)]

    app.root.unmount()


# ---------------------------------------------------------------------------
# Bubbling to a parent FocusNode
# ---------------------------------------------------------------------------


def test_release_bubbles_to_parent_focus_node() -> None:
    child_releases: list[str] = []
    parent_releases: list[str] = []

    child = _LeafWidget().modifier(
        focusable(on_key_up=lambda k, m: child_releases.append(k) or False)  # bubble up
    )
    parent = Box().modifier(focusable(on_key_up=lambda k, m: parent_releases.append(k) or True))
    parent.add_child(child)
    app = _mounted_app(parent)

    child.get_node(FocusNode).request_focus()
    assert app._dispatch_key_release("b") is True

    assert child_releases == ["b"]
    assert parent_releases == ["b"]

    app.root.unmount()


def test_release_bubbling_stops_on_truthy_return() -> None:
    child_releases: list[str] = []
    parent_releases: list[str] = []

    child = _LeafWidget().modifier(
        focusable(on_key_up=lambda k, m: child_releases.append(k) or True)  # consume
    )
    parent = Box().modifier(focusable(on_key_up=lambda k, m: parent_releases.append(k) or True))
    parent.add_child(child)
    app = _mounted_app(parent)

    child.get_node(FocusNode).request_focus()
    assert app._dispatch_key_release("b") is True

    assert child_releases == ["b"]
    assert parent_releases == []  # child consumed it, no bubbling

    app.root.unmount()


# ---------------------------------------------------------------------------
# Escape: release drives back-navigation, no press is synthesized
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escape_release_triggers_back_navigation() -> None:
    app = App(content=Container())
    Overlay.root()
    navigator = Navigator.root()
    navigator.push(Container())

    assert navigator.can_pop() is True

    handled = app._dispatch_key_release("escape")
    assert handled is True
    await asyncio.sleep(0)  # allow back event task to run
    assert navigator.can_pop() is False


@pytest.mark.asyncio
async def test_escape_release_does_not_reach_focus_node() -> None:
    """Escape is consumed for back-navigation, mirroring the press path."""
    releases: list[str] = []

    child = _LeafWidget().modifier(focusable(on_key_up=lambda k, m: releases.append(k) or True))
    root = Box()
    root.add_child(child)
    app = _mounted_app(root)
    child.get_node(FocusNode).request_focus()

    app._dispatch_key_release("escape")
    await asyncio.sleep(0)
    assert releases == []

    app.root.unmount()


# ---------------------------------------------------------------------------
# Authoritative modifier-key mask
# ---------------------------------------------------------------------------


def test_modifier_key_mask_is_exposed_and_read_only_default() -> None:
    app = App(content=Container())
    assert app.modifier_keys == 0

    app._set_modifier_keys(MOD_CTRL | MOD_SHIFT)
    assert app.modifier_keys == MOD_CTRL | MOD_SHIFT


def test_modifier_key_mask_cleared_on_deactivate() -> None:
    """Mimics on_deactivate: a modifier held when focus is lost must not stick."""
    app = App(content=Container())
    app._set_modifier_keys(MOD_CTRL)
    assert app.modifier_keys == MOD_CTRL

    app._clear_modifier_keys()
    assert app.modifier_keys == 0


# ---------------------------------------------------------------------------
# _normalize_key is exercised on the release path, not only press
# ---------------------------------------------------------------------------


def test_normalize_key_resolves_modifier_release() -> None:
    """The release handler forwards whatever _normalize_key returns for a modifier."""
    name, modifier_keys = _normalize_key(pyglet_key.LCTRL, pyglet_key.MOD_CTRL)
    assert name == "lctrl"
    assert modifier_keys == MOD_CTRL
