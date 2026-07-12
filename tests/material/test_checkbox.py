from typing import Optional
from nuiitivet.material.selection_controls import Checkbox
from nuiitivet.observable import Observable
from nuiitivet.input.pointer import PointerEventType
from tests.helpers.pointer import send_pointer_event_for_test


def _make_obs(initial):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_preferred_size_default_and_custom():
    """Test preferred_size with default (48dp M3) and style-driven sizes."""
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle

    c = Checkbox()
    assert c.preferred_size() == (48, 48)
    # Touch-target size is style-driven (MD3 fixes the axis -> style only).
    c2 = Checkbox(style=CheckboxStyle(default_touch_target=56))
    assert c2.preferred_size() == (56, 56)
    c3 = Checkbox(style=CheckboxStyle(default_touch_target=48), padding=8)
    assert c3.preferred_size() == (64, 64)
    c4 = Checkbox(style=CheckboxStyle(default_touch_target=40))
    assert c4.preferred_size() == (40, 40)


def test_pointer_event_toggle_calls_handler_and_updates_state():
    called = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(on_toggle=on_toggle)
    assert c.value is False
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    # Toggle occurs on release, not press
    assert c.value is False
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert c.value is True
    assert called == [True]
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert c.value is False
    assert called == [True, False]


def test_state_backed_checkbox_respects_external_state():
    s = _make_obs(True)
    called = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(checked=s, on_toggle=on_toggle)
    assert s.value is True
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert s.value is False
    assert called == [False]


def test_indeterminate_initial_and_toggle():
    called = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(indeterminate=True, on_toggle=on_toggle)
    assert c.value is None
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert c.value is True
    assert called == [True]


def test_state_backed_indeterminate_state():
    s = _make_obs(None)
    called = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(checked=s, on_toggle=on_toggle)
    assert s.value is None
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert s.value is True
    assert called == [True]


def test_hover_state_changes_and_hit_test_behavior():
    c = Checkbox()
    c.set_layout_rect(10, 10, 100, 40)
    assert send_pointer_event_for_test(c, PointerEventType.HOVER, 20, 20) is True
    assert c.state.hovered is True
    assert send_pointer_event_for_test(c, PointerEventType.HOVER, 0, 0) is False
    assert c.state.hovered is False
    assert c.hit_test(20, 20) is c
    # assert c.hit_test(0, 0) is None


def test_pressed_state_changes_and_release_clears():
    called = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(on_toggle=on_toggle)
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert c.state.pressed is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert c.state.pressed is False


def test_disabled_prevents_toggle_and_press():
    called = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(disabled=True, on_toggle=on_toggle)
    assert c.value is False
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is False
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is False
    assert c.value is False
    assert called == []
    assert c.state.pressed is False


def test_disabled_observable_updates_interaction_state():
    disabled = _make_obs(True)

    called: list[Optional[bool]] = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(disabled=disabled, on_toggle=on_toggle)
    assert c.disabled is True
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is False
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is False

    c.on_mount()
    disabled.value = False
    assert c.disabled is False
    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert called == [True]


def test_indeterminate_observable_separate_from_checked():
    checked = _make_obs(False)
    indeterminate = _make_obs(True)

    called: list[Optional[bool]] = []

    def on_toggle(v: Optional[bool]):
        called.append(v)

    c = Checkbox(checked=checked, indeterminate=indeterminate, on_toggle=on_toggle)
    assert c.value is None

    assert send_pointer_event_for_test(c, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(c, PointerEventType.RELEASE) is True
    assert indeterminate.value is False
    assert checked.value is True
    assert c.value is True
    assert called == [True]


def _light_theme():
    from nuiitivet.material.theme.material_theme import MaterialThemeFactory

    return MaterialThemeFactory.light("#6750A4")


def _rgba(spec, alpha: float = 1.0):
    from nuiitivet.theme.resolver import resolve_color_to_rgba

    return resolve_color_to_rgba((spec, alpha), theme=_light_theme())


def test_enabled_box_colors_come_from_style_tokens():
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle

    style = CheckboxStyle()
    c = Checkbox(style=style)
    outline, container, mark = c._resolve_box_colors(_light_theme())

    assert outline == _rgba(style.stroke_color, style.stroke_alpha)
    assert container == _rgba(style.checked_background)
    assert mark == _rgba(style.checked_foreground)


def test_disabled_box_colors_come_from_disabled_tokens():
    """A disabled checkbox is on-surface @ 38% (outline and container), mark in surface."""
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle

    style = CheckboxStyle()
    c = Checkbox(disabled=True, style=style)
    outline, container, mark = c._resolve_box_colors(_light_theme())

    disabled = _rgba(style.disabled_color, style.disabled_alpha)
    assert outline == disabled
    assert container == disabled
    assert mark == _rgba(style.disabled_mark)


def test_disabled_box_colors_are_visibly_distinct_from_enabled():
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle

    theme = _light_theme()
    style = CheckboxStyle()
    for value in (False, True, None):
        enabled = Checkbox(checked=bool(value), indeterminate=value is None, style=style)
        disabled = Checkbox(checked=bool(value), indeterminate=value is None, disabled=True, style=style)
        assert enabled.value is value
        assert disabled.value is value
        assert disabled._resolve_box_colors(theme) != enabled._resolve_box_colors(theme)


def test_disabled_box_colors_honor_custom_tokens():
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle

    style = CheckboxStyle().copy_with(disabled_color="#FF0000", disabled_mark="#00FF00", disabled_alpha=0.5)
    c = Checkbox(disabled=True, style=style)
    outline, container, mark = c._resolve_box_colors(_light_theme())

    assert outline == (255, 0, 0, 127)
    assert container == (255, 0, 0, 127)
    assert mark == (0, 255, 0, 255)


def test_checkbox_padding():
    """Test padding support for Checkbox (M3: space between UI elements)."""
    c1 = Checkbox()
    assert c1.padding == (0, 0, 0, 0)
    assert c1.preferred_size() == (48, 48)
    c2 = Checkbox(padding=10)
    assert c2.padding == (10, 10, 10, 10)
    assert c2.preferred_size() == (68, 68)
    c3 = Checkbox(padding=(8, 12))
    assert c3.padding == (8, 12, 8, 12)
    assert c3.preferred_size() == (64, 72)
    c4 = Checkbox(padding=(5, 10, 15, 20))
    assert c4.padding == (5, 10, 15, 20)
    assert c4.preferred_size() == (68, 78)


def test_checkbox_content_rect():
    """Test content_rect applies padding correctly."""
    c = Checkbox(padding=10)
    cx, cy, cw, ch = c.content_rect(0, 0, 100, 100)
    assert cx == 10
    assert cy == 10
    assert cw == 80
    assert ch == 80
