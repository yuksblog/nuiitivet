"""Tests for Intent System (Phase 5).

The intent system resolves an intent object to a Route/Widget via a type map.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from nuiitivet.navigation import Navigator, PageRoute, Route
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay import Overlay
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def __init__(self, *, label: str = "") -> None:
        super().__init__()
        self.label = label
        self.unmounted = False

    def on_unmount(self) -> None:
        self.unmounted = True
        super().on_unmount()

    def build(self) -> Widget:
        return self


@dataclass(frozen=True, slots=True)
class _PushIntent:
    label: str


@dataclass(frozen=True, slots=True)
class _DialogIntent:
    label: str


def test_navigator_push_intent_resolves_to_route() -> None:
    nav = Navigator(
        routes=[PageRoute(builder=_FlagWidget)],
        intent_routes={
            _PushIntent: lambda i: PageRoute(builder=lambda: _FlagWidget(label=i.label)),
        },
    )

    nav.push(_PushIntent(label="next"))

    # Navigator keeps the pushed widget as a child.
    children = nav.children_snapshot()
    assert any(isinstance(child, _FlagWidget) and child.label == "next" for child in children)


def test_navigator_push_intent_raises_when_unregistered() -> None:
    nav = Navigator(routes=[PageRoute(builder=_FlagWidget)])

    with pytest.raises(RuntimeError, match=r"No route is registered for intent"):
        nav.push(_PushIntent(label="x"))


def test_overlay_dialog_intent_resolves_to_widget() -> None:
    dialog_widget = _FlagWidget(label="dialog")

    overlay = MaterialOverlay(
        intents={
            _DialogIntent: lambda _i: dialog_widget,
        },
    )

    overlay.dialog(_DialogIntent(label="ignored"))

    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()

    def contains(root: Widget, needle: Widget) -> bool:
        if root is needle:
            return True
        try:
            children = root.children_snapshot()
        except Exception:
            children = getattr(root, "children", [])
        for child in children:
            if contains(child, needle):
                return True
        return False

    assert contains(built, dialog_widget)


def test_overlay_dialog_intent_raises_when_unregistered() -> None:
    overlay = MaterialOverlay(intents={})

    with pytest.raises(RuntimeError, match=r"No overlay intent is registered"):
        overlay.dialog(_DialogIntent(label="x"))


def test_overlay_dialog_route_disposes_route_on_remove() -> None:
    overlay = Overlay()

    route: Route = PageRoute(builder=_FlagWidget)

    handle = overlay.show(route)

    # Route widget is created eagerly by Overlay.dialog().
    assert route._widget is not None  # type: ignore[attr-defined]

    handle.close()

    assert route._widget is None  # type: ignore[attr-defined]
