"""Tests for the optional ``on_action`` hook on the action verbs.

The verbs are silent unless a driver asks to be told what they did. The dev
bridge asks, and draws its on-screen markers from it (``tests/dev/`` covers that
end); a test harness does not, and pays nothing.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest

from nuiitivet._interaction.action import click, press_key, scroll, scroll_into_view, type_text


class _Node:
    def __init__(self, *, rect: tuple = (0, 0, 100, 40), **identity: Any) -> None:
        self.children: list[_Node] = []
        self.built_child: Optional[_Node] = None
        self.parent: Optional[_Node] = None
        self.global_layout_rect = rect
        for name, value in identity.items():
            setattr(self, name, value)

    def add(self, *children: "_Node") -> "_Node":
        for child in children:
            child.parent = self
            self.children.append(child)
        return self

    def layout(self, width: int, height: int) -> None:
        pass

    def clear_needs_layout(self) -> None:
        pass


class _Region(_Node):
    """A node a wheel event can move, and that can reveal a rect on demand."""

    def __init__(self, *, delta: float = 30.0, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._delta = delta

    def scroll_metrics(self) -> dict[str, Any]:
        return {"axis": "vertical", "offset": 0.0, "at_start": True, "at_end": False}

    def scroll_rect_into_view(self, rect: tuple, *, align: str = "nearest") -> float:
        return self._delta


class _App:
    def __init__(self, root: _Node, *, handler: Optional[_Node] = None) -> None:
        self.root = root
        self.width = 360
        self.height = 240
        self._handler = handler

    def _dispatch_mouse_press(self, x: int, y: int, *, button: Any = None) -> None:
        pass

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Any = None) -> None:
        pass

    def _dispatch_mouse_scroll(self, x: int, y: int, dx: float, dy: float) -> Optional[_Node]:
        return self._handler

    def _dispatch_text(self, text: str) -> bool:
        return True

    def _dispatch_key_press(self, key: str, modifiers: int) -> bool:
        return True

    def _dispatch_key_release(self, key: str, modifiers: int) -> bool:
        return False

    def invalidate(self) -> None:
        pass


class _Recorder:
    """An :class:`ActionObserver` that keeps what it was told, in order."""

    def __init__(self) -> None:
        self.events: list[tuple] = []

    def on_click(self, app: Any, x: float, y: float, *, target: Optional[str]) -> None:
        self.events.append(("click", x, y, target))

    def on_scroll(
        self,
        app: Any,
        x: float,
        y: float,
        *,
        dx: float,
        dy: float,
        target: Optional[str],
        verb: str,
    ) -> None:
        self.events.append(("scroll", x, y, dx, dy, target, verb))

    def on_type(self, app: Any) -> None:
        self.events.append(("type",))

    def on_key(self, app: Any, key: str, modifiers: int) -> None:
        self.events.append(("key", key, modifiers))


def test_click_reports_the_resolved_point_and_target() -> None:
    observer = _Recorder()
    app = _App(_Node().add(_Node(key="submit", rect=(10, 20, 100, 40))))

    click(app, key="submit", on_action=observer)

    assert observer.events == [("click", 60.0, 40.0, "submit")]


def test_click_by_raw_coordinates_reports_no_target() -> None:
    observer = _Recorder()
    app = _App(_Node())

    click(app, x=5, y=7, on_action=observer)

    assert observer.events == [("click", 5.0, 7.0, None)]


def test_scroll_reports_the_wheel_notches() -> None:
    observer = _Recorder()
    region = _Region(key="feed", rect=(0, 0, 200, 100))
    app = _App(_Node().add(region), handler=region)

    scroll(app, key="feed", dy=5, on_action=observer)

    assert observer.events == [("scroll", 100.0, 50.0, 0.0, 5.0, "feed", "scroll")]


def test_scroll_into_view_reports_the_direction_it_moved() -> None:
    """Not the notches it did not send: it moves the region directly.

    So the hook carries a unit step in the direction of travel -- enough for a
    marker to point the right way, which is what the human needs to see.
    """
    observer = _Recorder()
    row = _Node(key="row-42", rect=(0, 500, 200, 40))
    region = _Region(rect=(0, 0, 200, 100)).add(row)
    app = _App(_Node().add(region))

    scroll_into_view(app, key="row-42", on_action=observer)

    assert observer.events == [("scroll", 100.0, 520.0, 0.0, 1.0, "row-42", "scroll into view")]


def test_scroll_into_view_stays_quiet_when_nothing_moved() -> None:
    observer = _Recorder()
    row = _Node(key="row-1", rect=(0, 0, 200, 40))
    region = _Region(delta=0.0, rect=(0, 0, 200, 100)).add(row)
    app = _App(_Node().add(region))

    scroll_into_view(app, key="row-1", on_action=observer)

    assert observer.events == []


def test_type_reports_that_it_typed_but_never_what() -> None:
    observer = _Recorder()

    type_text(_App(_Node()), "hunter2", on_action=observer)

    assert observer.events == [("type",)]


def test_key_reports_the_keystroke_and_modifiers() -> None:
    observer = _Recorder()

    press_key(_App(_Node()), "enter", ["ctrl"], on_action=observer)

    assert observer.events[0][0] == "key"
    assert observer.events[0][1] == "enter"


def test_verbs_are_silent_without_an_observer() -> None:
    app = _App(_Node().add(_Node(key="submit", rect=(10, 20, 100, 40))))

    assert click(app, key="submit")["clicked"]["key"] == "submit"
    assert type_text(app, "hello")["handled"] is True
    assert press_key(app, "enter")["handled"] is True


def test_a_raising_observer_reaches_the_caller() -> None:
    """Containing a hook failure is the driver's call, not the core's.

    The bridge swallows its own overlay errors because a missing marker must not
    fail an action; a harness observer that raises is reporting a real problem.
    """

    class _Boom(_Recorder):
        def on_click(self, app: Any, x: float, y: float, *, target: Optional[str]) -> None:
            raise RuntimeError("observer failed")

    app = _App(_Node().add(_Node(key="submit", rect=(10, 20, 100, 40))))

    with pytest.raises(RuntimeError, match="observer failed"):
        click(app, key="submit", on_action=_Boom())
