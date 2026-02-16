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

    class _UnmountCountWidget(Widget):
        def __init__(self) -> None:
            super().__init__()
            self.unmount_count = 0

        def on_unmount(self) -> None:
            self.unmount_count += 1
            super().on_unmount()

        def build(self) -> Widget:
            return self

    route_widget = _UnmountCountWidget()
    route: Route = PageRoute(builder=lambda: route_widget)

    handle = overlay.show(route)

    # Route widget is created eagerly by Overlay.dialog().
    assert route._widget is not None  # type: ignore[attr-defined]

    handle.close()
    handle.close()

    assert route._widget is None  # type: ignore[attr-defined]
    assert route_widget.unmount_count == 1


def test_overlay_normalize_to_route_passes_route_through() -> None:
    overlay = Overlay()
    route = PageRoute(builder=_FlagWidget)

    normalized = overlay._normalize_to_route(route)

    assert normalized is route


def test_overlay_normalize_to_route_wraps_widget() -> None:
    overlay = Overlay()
    widget = _FlagWidget(label="overlay")

    normalized = overlay._normalize_to_route(widget)

    assert isinstance(normalized, Route)
    assert normalized is not widget
    assert normalized.build_widget() is widget


def test_material_overlay_dialog_normalize_to_route_resolves_intent() -> None:
    overlay = MaterialOverlay(intents={_DialogIntent: lambda i: _FlagWidget(label=i.label)})

    route = overlay._normalize_dialog_to_route(_DialogIntent(label="intent"), dismiss_on_outside_tap=True)

    assert isinstance(route, Route)
