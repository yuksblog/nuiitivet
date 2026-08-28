"""Tests for the human-only dev action overlay (#398).

The overlay visualizes AI-driven ``click`` / ``scroll`` / ``type`` / ``key`` actions for a
human watching hot reload, without ever entering the assistant's perception. The
critical properties verified here: recording is gated on a live dev session +
window (no-op under headless / tests), markers live outside the widget tree so
``describe_tree`` stays clean, typed content is never captured, consecutive
actions accumulate (trail), captions are ordered and capped, and expired markers
are purged on paint.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import pytest

from nuiitivet.dev import action_overlay as ao
from nuiitivet.dev.session import DevSession, set_dev_session
from nuiitivet.input.codes import MOD_ACCEL, MOD_CTRL, MOD_SHIFT


class _FakeClock:
    """Records scheduled/unscheduled callbacks in place of the runtime clock."""

    def __init__(self) -> None:
        self.scheduled: list[Callable[[float], None]] = []
        self.unscheduled: list[Callable[[float], None]] = []

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        self.scheduled.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self.unscheduled.append(fn)


class _App:
    """Minimal app stub with a window and a focus target."""

    def __init__(self, *, window: bool = True, focus_rect: Optional[tuple] = None) -> None:
        self.width = 400
        self.height = 300
        self._window = object() if window else None
        self.invalidated = 0
        self._focused_target = _Focus(focus_rect) if focus_rect is not None else None

    def invalidate(self) -> None:
        self.invalidated += 1


class _Focus:
    def __init__(self, rect: tuple) -> None:
        self.last_rect = rect
        self.global_layout_rect = rect


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Isolate the module registry, clock, dev session and env for each test."""
    ao._registries.clear()
    clock = _FakeClock()
    monkeypatch.setattr(ao.runtime, "clock", clock)
    monkeypatch.delenv("NUIITIVET_DEV_ACTION_OVERLAY", raising=False)
    set_dev_session(DevSession())
    try:
        yield clock
    finally:
        set_dev_session(None)
        ao._registries.clear()


def _reg(app: _App) -> ao._Registry:
    return ao._registries[id(app)]


# --- Gating -----------------------------------------------------------------


def test_no_op_without_dev_session() -> None:
    set_dev_session(None)
    app = _App()
    ao.record_click(app, 10, 20, target="submit")
    assert id(app) not in ao._registries
    assert app.invalidated == 0


def test_no_op_without_window() -> None:
    app = _App(window=False)
    ao.record_click(app, 10, 20, target="submit")
    assert id(app) not in ao._registries


def test_env_var_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NUIITIVET_DEV_ACTION_OVERLAY", "0")
    app = _App()
    ao.record_key(app, "Enter", 0)
    assert id(app) not in ao._registries


# --- Recording --------------------------------------------------------------


def test_record_click_adds_marker_and_caption() -> None:
    app = _App()
    ao.record_click(app, 60, 40, target="increment")

    reg = _reg(app)
    assert len(reg.markers) == 1
    marker = reg.markers[0]
    assert marker.kind == "click" and (marker.x, marker.y) == (60, 40)
    assert marker.text == "increment"
    assert [c.text for c in reg.captions] == ["click increment"]
    assert app.invalidated == 1


def test_click_without_target_shows_bare_point() -> None:
    app = _App()
    ao.record_click(app, 5, 7, target=None)
    reg = _reg(app)
    assert reg.markers[0].text is None
    assert reg.captions[0].text == "click"


def test_type_records_marker_near_focus_but_never_content() -> None:
    app = _App(focus_rect=(10, 20, 100, 40))
    # Only a location is passed in; the overlay API has no parameter for content.
    ao.record_type(app, x=60, y=40)
    reg = _reg(app)
    assert len(reg.markers) == 1
    assert reg.markers[0].kind == "type"
    # Caption is a bare verb; the typed text is never present anywhere.
    assert reg.captions[0].text == "type"
    assert reg.markers[0].text is None


def test_type_without_focus_records_caption_only() -> None:
    app = _App()
    ao.record_type(app, x=None, y=None)
    reg = _reg(app)
    assert reg.markers == []
    assert reg.captions[0].text == "type"


def test_record_scroll_carries_its_direction() -> None:
    app = _App()
    ao.record_scroll(app, 60, 40, dx=0.0, dy=5.0, target="feed")

    reg = _reg(app)
    marker = reg.markers[0]
    assert marker.kind == "scroll" and (marker.dx, marker.dy) == (0.0, 5.0)
    assert reg.captions[0].text == "scroll down feed"


def test_scroll_captions_use_ascii_direction_words() -> None:
    """Never arrow glyphs: the caption face is resolved at paint time and may lack them."""
    app = _App()
    ao.record_scroll(app, 1, 1, dy=-1.0)
    ao.record_scroll(app, 1, 1, dx=1.0)
    ao.record_scroll(app, 1, 1, dx=-1.0, dy=1.0)

    texts = [c.text for c in _reg(app).captions]
    assert texts == ["scroll up", "scroll right", "scroll down left"]
    assert all(text.isascii() for text in texts)


def test_scroll_marker_outlives_the_click_ripple() -> None:
    """A scroll moves the whole view, so its marker must survive the detour.

    The human reads the new content first and looks for the cause second; a
    marker on the ripple's timeline is gone by then.
    """
    app = _App()
    ao.record_click(app, 1, 1, target="a")
    ao.record_scroll(app, 1, 1, dy=1.0)

    click_marker, scroll_marker = _reg(app).markers
    just_past_a_ripple = click_marker.born + ao._MARKER_LIFETIME + 0.1
    assert click_marker.expired(just_past_a_ripple)
    assert not scroll_marker.expired(just_past_a_ripple)


def test_scroll_marker_holds_opacity_before_fading() -> None:
    """Presence is the event; the fade is its tail, not the whole of it."""
    hold = ao._SCROLL_MARKER_HOLD
    assert ao._hold_then_fade(0.0, hold=hold) == 1.0
    assert ao._hold_then_fade(hold, hold=hold) == 1.0
    assert ao._hold_then_fade(1.0, hold=hold) == 0.0
    # Half-way along the tail is half opacity -- a linear fall, not a cubic dive.
    assert ao._hold_then_fade(hold + (1.0 - hold) / 2, hold=hold) == pytest.approx(0.5)


def test_scroll_into_view_reuses_the_scroll_marker() -> None:
    app = _App()
    ao.record_scroll(app, 5, 5, dy=-1.0, target="row-42", verb="scroll into view")

    reg = _reg(app)
    assert reg.markers[0].kind == "scroll"
    assert reg.captions[0].text == "scroll into view up row-42"


def test_key_caption_renders_combo() -> None:
    app = _App()
    ao.record_key(app, "Enter", MOD_CTRL | MOD_SHIFT)
    reg = _reg(app)
    assert reg.captions[0].text == "key Ctrl+Shift+Enter"
    # key has no spatial marker.
    assert reg.markers == []


def test_accel_modifier_resolves_to_physical() -> None:
    app = _App()
    ao.record_key(app, "s", MOD_ACCEL)
    combo = _reg(app).captions[0].text
    assert combo in ("key Ctrl+s", "key Cmd+s")


# --- Trail / captions -------------------------------------------------------


def test_consecutive_actions_accumulate_a_trail() -> None:
    app = _App()
    ao.record_click(app, 1, 1, target="a")
    ao.record_click(app, 2, 2, target="b")
    ao.record_click(app, 3, 3, target="c")
    # All three coexist; they do not replace one another.
    assert len(_reg(app).markers) == 3


def test_captions_are_ordered_and_capped() -> None:
    app = _App()
    for i in range(ao._MAX_CAPTIONS + 3):
        ao.record_key(app, str(i), 0)
    reg = _reg(app)
    assert len(reg.captions) == ao._MAX_CAPTIONS
    # Sequence numbers are monotonic and the oldest were dropped.
    seqs = [c.seq for c in reg.captions]
    assert seqs == sorted(seqs)
    assert seqs[-1] == ao._MAX_CAPTIONS + 3


# --- Clock pump -------------------------------------------------------------


def test_pump_scheduled_on_first_marker(_clean_state: _FakeClock) -> None:
    app = _App()
    ao.record_click(app, 1, 1, target="a")
    ao.record_click(app, 2, 2, target="b")
    # Exactly one pump is scheduled regardless of marker count.
    assert len(_clean_state.scheduled) == 1


def test_expired_markers_purged_on_paint(monkeypatch: pytest.MonkeyPatch, _clean_state: _FakeClock) -> None:
    monkeypatch.setattr("nuiitivet.rendering.skia.skia_module.get_skia", lambda **_: None)
    app = _App()
    ao.record_click(app, 1, 1, target="a")
    reg = _reg(app)
    # Age everything well past its lifetime.
    for m in reg.markers:
        m.born -= ao._CAPTION_LIFETIME + ao._MARKER_LIFETIME + 1
    for c in reg.captions:
        c.born -= ao._CAPTION_LIFETIME + ao._MARKER_LIFETIME + 1

    ao.paint_markers(app, canvas=object(), width=app.width, height=app.height)

    assert reg.markers == [] and reg.captions == []
    # The pump self-unschedules once the registry drains.
    assert reg.ticker is None
    assert len(_clean_state.unscheduled) == 1


def test_reset_clears_registry(_clean_state: _FakeClock) -> None:
    app = _App()
    ao.record_click(app, 1, 1, target="a")
    ao.reset(app)
    assert id(app) not in ao._registries
    assert len(_clean_state.unscheduled) == 1


# --- Integration with the action verbs & perception -------------------------


class _Node:
    def __init__(self, *, rect: Optional[tuple] = (0, 0, 100, 40), **identity: Any) -> None:
        self.children: list[_Node] = []
        self.built_child: Optional[_Node] = None
        self.global_layout_rect = rect
        for name, value in identity.items():
            setattr(self, name, value)

    def layout(self, width: int, height: int) -> None:  # pragma: no cover - trivial
        pass

    def clear_needs_layout(self) -> None:  # pragma: no cover - trivial
        pass


class _ActionApp(_App):
    """App stub that also accepts the synthetic input the action verbs dispatch."""

    def __init__(self, root: _Node, **kw: Any) -> None:
        super().__init__(**kw)
        self.root = root

    def _dispatch_mouse_press(self, x: int, y: int, *, button: Any = None) -> None:
        pass

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Any = None) -> None:
        pass

    def _dispatch_text(self, text: str) -> bool:
        return True

    def _dispatch_key_press(self, key: str, modifiers: int) -> bool:
        return True

    def _dispatch_key_release(self, key: str, modifiers: int) -> bool:
        return False


def test_click_verb_records_marker() -> None:
    from nuiitivet.dev.action import click

    root = _Node()
    root.children = [_Node(key="increment", rect=(10, 20, 100, 40))]
    app = _ActionApp(root)

    click(app, key="increment")

    reg = _reg(app)
    assert len(reg.markers) == 1
    assert reg.markers[0].text == "increment"


def test_type_marker_anchors_just_left_of_text_origin() -> None:
    from nuiitivet.dev.action import type_text

    # The focus system reports the editable text region; its rect starts at the
    # text origin (x=100) with no left padding.
    app = _ActionApp(_Node(), focus_rect=(100, 200, 240, 40))
    type_text(app, "secret")

    reg = _reg(app)
    assert len(reg.markers) == 1
    marker = reg.markers[0]
    # Just *left* of the text origin (x - 6), so the caret never overlaps the
    # glyphs, and well left of the geometric centre (220).
    assert marker.x == pytest.approx(94.0)
    assert marker.y == pytest.approx(220.0)


def test_actions_never_appear_in_describe_tree() -> None:
    from nuiitivet.dev.action import click, press_key, type_text
    from nuiitivet.dev.perception import describe_tree

    root = _Node(key="root")
    root.children = [_Node(key="increment", rect=(10, 20, 100, 40))]
    app = _ActionApp(root)

    before = describe_tree(root)
    click(app, key="increment")
    type_text(app, "secret-password")
    press_key(app, "Enter", MOD_CTRL)

    # Markers were recorded for the human...
    assert len(_reg(app).markers) >= 1
    # ...but the tree the assistant perceives is byte-for-byte unchanged, and the
    # typed content never leaks into it.
    after = describe_tree(root)
    assert after == before
    assert "secret-password" not in str(after)


def test_render_snapshot_paints_overlay_only_for_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """The overlay is drawn on live frames (``for_display=True``) but excluded
    from the ``screenshot`` render (``for_display=False``)."""
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window
    from nuiitivet.widgeting.widget import Widget

    class _Dummy(Widget):
        def build(self) -> "Widget":
            return self

        def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
            return None

    calls: list[str] = []
    monkeypatch.setattr(
        ao, "paint_markers", lambda **kw: calls.append("painted")
    )

    app = App(Window(content=_Dummy(), background="#123456")).main_window

    # Screenshot path: overlay excluded.
    app._render_snapshot(scale=1.0)
    assert calls == []

    # Live display path: overlay painted.
    app._render_snapshot(scale=1.0, for_display=True)
    assert calls == ["painted"]
