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

    nav = Navigator.routes(
        [
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

    nav = Navigator.routes(
        [
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
    nav = Navigator.routes(
        [
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


# ---------------------------------------------------------------------------
# Re-entrancy guard (#53)
# ---------------------------------------------------------------------------


def test_reentrant_back_is_dropped_while_handler_is_active() -> None:
    """A second back request while on_will_pop is executing must be dropped."""
    calls: list[str] = []
    scope_ref: list[object] = []

    def on_will_pop() -> bool:
        calls.append("enter")
        # Simulate re-entrant call (e.g. rapid Esc).
        scope = scope_ref[0]
        handler = getattr(scope, "handle_back_event", None)
        assert callable(handler)
        result = handler()
        calls.append(f"reentrant={result}")
        return False

    w = _FlagWidget()
    scoped = w.modifier(will_pop(on_will_pop))
    scope_ref.append(scoped)

    handler = getattr(scoped, "handle_back_event", None)
    assert callable(handler)
    result = handler()

    assert result is False
    assert calls == ["enter", "reentrant=False"]


def test_handling_flag_is_released_after_normal_return() -> None:
    """_handling must be False after a successful callback invocation."""
    scope_ref: list[object] = []

    def on_will_pop() -> bool:
        return False

    w = _FlagWidget()
    scoped = w.modifier(will_pop(on_will_pop))
    scope_ref.append(scoped)

    handler = getattr(scoped, "handle_back_event", None)
    assert callable(handler)
    handler()

    assert getattr(scoped, "_handling", True) is False


def test_handling_flag_is_released_after_exception() -> None:
    """_handling must be False even when the callback raises."""

    def on_will_pop() -> bool:
        raise RuntimeError("boom")

    w = _FlagWidget()
    scoped = w.modifier(will_pop(on_will_pop))

    handler = getattr(scoped, "handle_back_event", None)
    assert callable(handler)
    result = handler()  # fail-open → True

    assert result is True
    assert getattr(scoped, "_handling", True) is False


def test_normal_pop_allowed_works_after_previous_cancel() -> None:
    """After a cancelled pop, a subsequent allow should still propagate."""
    call_count = 0

    def on_will_pop() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count >= 2  # first call cancels, second allows

    nav = Navigator.routes(
        [
            PageRoute(builder=lambda: _FlagWidget(label="root")),
            PageRoute(builder=lambda: _FlagWidget(label="outgoing").modifier(will_pop(on_will_pop))),
        ]
    )
    nav.rebuild()

    nav.pop()
    assert nav.can_pop() is True  # first pop was cancelled

    nav.pop()
    assert nav.can_pop() is False  # second pop was allowed
