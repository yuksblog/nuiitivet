"""Tests that every dev action verb still reaches the overlay (#524).

The verbs themselves live in :mod:`nuiitivet._interaction.action` and are silent:
what each one did is reported to an optional ``ActionObserver``, and
:mod:`nuiitivet.dev.action` is what binds the overlay one in. That binding is a
seam — drop ``on_action`` from a single wrapper and the marker for that verb
disappears with every existing test still green, because
``test_action_overlay.py`` reaches the overlay through ``record_*`` directly for
scroll and key.

So this file drives the **verbs** and asserts a marker came out the far end, for
all five. What each marker looks like is ``test_action_overlay.py``'s business.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import pytest

from nuiitivet.dev import action, action_overlay as ao
from nuiitivet.dev.session import DevSession, set_dev_session
from nuiitivet.input.codes import MOD_CTRL


class _Clock:
    """Stands in for the runtime clock so a marker's pump is never scheduled."""

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        pass

    def unschedule(self, fn: Callable[[float], None]) -> None:
        pass


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


class _Focus:
    def __init__(self, rect: tuple) -> None:
        self.last_rect = rect
        self.global_layout_rect = rect


class _App:
    def __init__(
        self,
        root: _Node,
        *,
        handler: Optional[_Node] = None,
        focus_rect: Optional[tuple] = None,
    ) -> None:
        self.root = root
        self.width = 400
        self.height = 300
        # The overlay no-ops without a window, so the fake needs one.
        self._window = object()
        self._handler = handler
        self._focused_target = _Focus(focus_rect) if focus_rect is not None else None

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


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Isolate the module registry, clock, dev session and env for each test."""
    ao._registries.clear()
    monkeypatch.setattr(ao.runtime, "clock", _Clock())
    monkeypatch.delenv("NUIITIVET_DEV_ACTION_OVERLAY", raising=False)
    set_dev_session(DevSession())
    try:
        yield
    finally:
        set_dev_session(None)
        ao._registries.clear()


def _markers(app: _App) -> list[Any]:
    reg = ao._registries.get(id(app))
    return list(reg.markers) if reg else []


def _captions(app: _App) -> list[Optional[str]]:
    reg = ao._registries.get(id(app))
    return [c.text for c in reg.captions] if reg else []


def test_click_verb_reaches_the_overlay() -> None:
    app = _App(_Node().add(_Node(key="submit", rect=(10, 20, 100, 40))))

    action.click(app, key="submit")

    assert [(m.kind, m.text) for m in _markers(app)] == [("click", "submit")]


def test_scroll_verb_reaches_the_overlay() -> None:
    region = _Region(key="feed", rect=(0, 0, 200, 100))
    app = _App(_Node().add(region), handler=region)

    action.scroll(app, key="feed", dy=5)

    (marker,) = _markers(app)
    assert marker.kind == "scroll" and (marker.dx, marker.dy) == (0.0, 5.0)


def test_scroll_into_view_verb_reaches_the_overlay() -> None:
    row = _Node(key="row-42", rect=(0, 500, 200, 40))
    region = _Region(rect=(0, 0, 200, 100)).add(row)
    app = _App(_Node().add(region))

    action.scroll_into_view(app, key="row-42")

    (marker,) = _markers(app)
    assert marker.kind == "scroll" and marker.text == "row-42"
    assert "scroll into view" in (_captions(app)[0] or "")


def test_type_verb_reaches_the_overlay_without_the_content() -> None:
    app = _App(_Node(), focus_rect=(100, 200, 240, 40))

    action.type_text(app, "hunter2")

    (marker,) = _markers(app)
    assert marker.kind == "type"
    assert "hunter2" not in str(_markers(app) + _captions(app))


def test_key_verb_reaches_the_overlay_as_a_caption() -> None:
    """``record_key`` passes no marker position, so a keystroke is caption-only."""
    app = _App(_Node())

    action.press_key(app, "enter", MOD_CTRL)

    assert _markers(app) == []
    assert _captions(app) == ["key Ctrl+enter"]
