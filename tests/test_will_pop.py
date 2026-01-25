from __future__ import annotations

from nuiitivet.modifiers import will_pop
from nuiitivet.navigation import Navigator, PageRoute
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


def test_will_pop_modifier_chains_inner_to_outer() -> None:
    calls: list[str] = []

    def inner() -> bool:
        calls.append("inner")
        return True

    def outer() -> bool:
        calls.append("outer")
        return True

    w = _FlagWidget().modifier(will_pop(inner) | will_pop(outer))
    handler = getattr(w, "handle_back_event", None)
    assert callable(handler)
    assert bool(handler()) is True
    assert calls == ["inner", "outer"]


def test_navigator_pop_respects_will_pop_cancel() -> None:
    calls: list[str] = []
    outgoing = _FlagWidget(label="outgoing")

    def on_will_pop() -> bool:
        calls.append("called")
        return False

    nav = Navigator(
        routes=[
            PageRoute(builder=lambda: _FlagWidget(label="root")),
            PageRoute(builder=lambda: outgoing.modifier(will_pop(on_will_pop))),
        ]
    )

    nav.rebuild()
    assert nav.can_pop() is True

    nav.pop()

    assert nav.can_pop() is True
    assert outgoing.unmounted is False
    assert calls == ["called"]


def test_navigator_pop_respects_will_pop_allow() -> None:
    outgoing = _FlagWidget(label="outgoing")

    def on_will_pop() -> bool:
        return True

    nav = Navigator(
        routes=[
            PageRoute(builder=lambda: _FlagWidget(label="root")),
            PageRoute(builder=lambda: outgoing.modifier(will_pop(on_will_pop))),
        ]
    )

    nav.rebuild()
    assert nav.can_pop() is True

    nav.pop()

    assert nav.can_pop() is False


def test_navigator_pop_calls_will_pop_inside_build() -> None:
    calls: list[str] = []

    from nuiitivet.widgeting.widget import ComposableWidget

    class Outgoing(ComposableWidget):
        def __init__(self) -> None:
            super().__init__()
            self.unmounted = False

        def on_unmount(self) -> None:
            self.unmounted = True
            super().on_unmount()

        def build(self) -> Widget:
            def on_will_pop() -> bool:
                calls.append("called")
                return False

            return Widget().modifier(will_pop(on_will_pop))

    outgoing = Outgoing()
    nav = Navigator(
        routes=[
            PageRoute(builder=lambda: _FlagWidget(label="root")),
            PageRoute(builder=lambda: outgoing),
        ]
    )

    nav.mount("test_app")
    assert nav.can_pop() is True

    nav.pop()

    assert calls == ["called"]
    assert nav.can_pop() is True
    assert outgoing.unmounted is False
