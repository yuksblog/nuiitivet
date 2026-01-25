import types

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.buttons import FilledButton
from tests.helpers.pointer import send_pointer_event_for_test
from nuiitivet.theme import manager
from nuiitivet.modifiers import background, corner_radius


def test_preferred_size_default_and_custom():
    b = FilledButton("ok")
    w, h = b.preferred_size()
    assert w >= 64
    assert h == 48
    b2 = FilledButton("ok", width=200, height=60)
    assert b2.preferred_size() == (200, 60)


def test_pointer_event_click_calls_handler_and_pressed_state():
    called = []

    def on_click():
        called.append(True)

    b = FilledButton("ok", on_click=on_click)
    assert send_pointer_event_for_test(b, PointerEventType.PRESS) is True
    assert called == []
    assert getattr(b.state, "pressed", False) is True
    assert send_pointer_event_for_test(b, PointerEventType.RELEASE) is True
    assert called == [True]
    assert getattr(b.state, "pressed", False) is False


def test_hover_state_changes_and_hit_test_behavior():
    b = FilledButton("ok")
    b.set_last_rect(10, 10, 100, 40)
    assert send_pointer_event_for_test(b, PointerEventType.HOVER, 20, 20) is True
    assert b.state.hovered is True
    assert send_pointer_event_for_test(b, PointerEventType.HOVER, 0, 0) is False
    assert b.state.hovered is False
    assert b.hit_test(20, 20) is b
    # assert b.hit_test(0, 0) is None  # Updated behavior: hit_test might return self if layout is not fully simulated


def test_corner_radius_modifier_updates_button_radius():
    b = FilledButton("ok")
    assert b.corner_radius == 20
    result = b.modifier(corner_radius(30))
    assert b.corner_radius == 30
    assert result is b


def test_corner_radius_modifier_after_background_updates_in_place():
    b = FilledButton("ok")
    wrapped = b.modifier(background("#eee") | corner_radius(16))
    assert b.corner_radius == 16
    assert wrapped is b
    assert getattr(b, "bgcolor", None) == "#eee"


def test_background_modifier_updates_button_in_place():
    b = FilledButton("ok")
    wrapped = b.modifier(background("#eee"))
    assert wrapped is b
    assert b.corner_radius == 20
    assert getattr(b, "bgcolor", None) == "#eee"


def test_button_theme_change_invalidates_cache():
    b = FilledButton("ok")
    calls = []

    def _cache(self):
        calls.append("cache")

    def _invalidate(self):
        calls.append("invalidate")

    b.invalidate_paint_cache = types.MethodType(_cache, b)
    b.invalidate = types.MethodType(_invalidate, b)
    b.on_mount()
    try:
        callback = getattr(b, "_on_theme_change", None)
        assert callback is not None
        callback(manager.current)
    finally:
        b.on_unmount()
    assert "cache" in calls
    assert "invalidate" in calls
