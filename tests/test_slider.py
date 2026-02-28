from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.slider import CenteredSlider, Orientation, RangeSlider, Slider
from nuiitivet.observable import Observable
from tests.helpers.pointer import send_pointer_event_for_test


def _make_obs(initial: float):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_slider_track_click_updates_value_and_callback() -> None:
    called: list[float] = []
    s = Slider(value=0.0, on_change=lambda v: called.append(v), min_value=0.0, max_value=100.0, length=200)
    s.set_layout_rect(0, 0, 200, 48)

    assert send_pointer_event_for_test(s, PointerEventType.PRESS, x=150.0, y=24.0) is True

    assert 70.0 <= s.value <= 80.0
    assert len(called) == 1


def test_slider_discrete_stops_snaps_value() -> None:
    s = Slider(value=0.0, min_value=0.0, max_value=100.0, stops=5, length=200)
    s.set_layout_rect(0, 0, 200, 48)

    assert send_pointer_event_for_test(s, PointerEventType.PRESS, x=140.0, y=24.0) is True

    assert s.value in (0.0, 25.0, 50.0, 75.0, 100.0)


def test_slider_observable_binding_updates_source() -> None:
    state = _make_obs(0.0)
    s = Slider(value=state, min_value=0.0, max_value=10.0, length=200)
    s.set_layout_rect(0, 0, 200, 48)

    assert send_pointer_event_for_test(s, PointerEventType.PRESS, x=100.0, y=24.0) is True

    assert abs(state.value - s.value) <= 1e-6


def test_centered_slider_active_range_changes_around_zero() -> None:
    c = CenteredSlider(value=-0.5, min_value=-1.0, max_value=1.0, length=200)

    c.handle_key_event("right")

    assert c.value > -0.5


def test_range_slider_drag_updates_nearest_handle() -> None:
    called: list[tuple[float, float]] = []
    r = RangeSlider(
        value_start=20.0,
        value_end=80.0,
        on_change=lambda v: called.append(v),
        min_value=0.0,
        max_value=100.0,
        length=200,
    )
    r.set_layout_rect(0, 0, 200, 48)

    assert send_pointer_event_for_test(r, PointerEventType.PRESS, x=40.0, y=24.0) is True
    assert send_pointer_event_for_test(r, PointerEventType.MOVE, x=80.0, y=24.0) is True
    assert send_pointer_event_for_test(r, PointerEventType.RELEASE, x=80.0, y=24.0) is True

    assert r.value_start >= 20.0
    assert r.value_start <= r.value_end
    assert len(called) >= 1


def test_slider_vertical_orientation_key_event() -> None:
    s = Slider(value=0.5, min_value=0.0, max_value=1.0, orientation=Orientation.VERTICAL, length=200)

    s.handle_key_event("up")

    assert s.value >= 0.5


def test_slider_space_plus_arrow_uses_larger_step() -> None:
    s = Slider(value=0.0, min_value=0.0, max_value=1.0)

    assert s.handle_key_event("space") is True
    assert s.handle_key_event("right") is True

    assert abs(s.value - 0.1) <= 1e-9


def test_slider_value_indicator_path_during_drag() -> None:
    s = Slider(value=0.5, show_value_indicator=True, min_value=0.0, max_value=1.0, length=200)
    s.set_layout_rect(0, 0, 200, 48)

    assert send_pointer_event_for_test(s, PointerEventType.PRESS, x=100.0, y=24.0) is True

    class _DummyCanvas:
        def drawTextBlob(self, *_args, **_kwargs):
            return None

    # Should not raise while indicator drawing path is active.
    s.paint(_DummyCanvas(), 0, 0, 200, 48)


# --- D1: Disabled state rejects interaction ---


def test_slider_disabled_rejects_track_press() -> None:
    called: list[float] = []
    s = Slider(
        value=0.0, on_change=lambda v: called.append(v), min_value=0.0, max_value=100.0, disabled=True, length=200
    )
    s.set_layout_rect(0, 0, 200, 48)

    send_pointer_event_for_test(s, PointerEventType.PRESS, x=150.0, y=24.0)

    assert s.value == 0.0
    assert len(called) == 0


def test_slider_disabled_rejects_key_event() -> None:
    s = Slider(value=0.5, min_value=0.0, max_value=1.0, disabled=True)

    result = s.handle_key_event("right")

    assert result is False
    assert s.value == 0.5


# --- D2: Observable external change syncs to internal state ---


def test_slider_observable_external_change_syncs() -> None:
    obs = _make_obs(0.0)
    s = Slider(value=obs, min_value=0.0, max_value=1.0, length=200)
    s.set_layout_rect(0, 0, 200, 48)

    obs.value = 0.75

    assert abs(s.value - 0.75) <= 1e-6


def test_range_slider_observable_external_change_syncs() -> None:
    start_obs = _make_obs(0.2)
    end_obs = _make_obs(0.8)
    r = RangeSlider(value_start=start_obs, value_end=end_obs, min_value=0.0, max_value=1.0, length=200)
    r.set_layout_rect(0, 0, 200, 48)

    start_obs.value = 0.1
    end_obs.value = 0.9

    assert abs(r.value_start - 0.1) <= 1e-6
    assert abs(r.value_end - 0.9) <= 1e-6


# --- D3: RangeSlider value_start > value_end constraint ---


def test_range_slider_init_swaps_inverted_range() -> None:
    r = RangeSlider(value_start=0.8, value_end=0.2, min_value=0.0, max_value=1.0)

    assert r.value_start <= r.value_end


def test_range_slider_value_start_clamped_to_value_end() -> None:
    r = RangeSlider(value_start=0.2, value_end=0.6, min_value=0.0, max_value=1.0)

    r.value_start = 0.9  # Exceeds value_end; should be clamped

    assert r.value_start <= r.value_end


def test_range_slider_value_end_clamped_to_value_start() -> None:
    r = RangeSlider(value_start=0.4, value_end=0.8, min_value=0.0, max_value=1.0)

    r.value_end = 0.1  # Below value_start; should be clamped

    assert r.value_start <= r.value_end


# --- D4: Discrete stops keyboard navigation ---


def test_slider_discrete_stops_keyboard_moves_by_one_stop() -> None:
    s = Slider(value=0.0, min_value=0.0, max_value=1.0, stops=5)

    s.handle_key_event("right")

    # With 5 stops (0, 0.25, 0.5, 0.75, 1.0), one step = 0.25
    assert abs(s.value - 0.25) <= 1e-9


def test_slider_discrete_stops_keyboard_clamps_at_max() -> None:
    s = Slider(value=1.0, min_value=0.0, max_value=1.0, stops=5)

    s.handle_key_event("right")

    assert s.value <= 1.0


def test_slider_discrete_stops_keyboard_decrements() -> None:
    s = Slider(value=0.5, min_value=0.0, max_value=1.0, stops=5)

    s.handle_key_event("left")

    assert abs(s.value - 0.25) <= 1e-9


# --- D5: Paint under disabled state ---


def test_slider_paint_disabled_does_not_raise() -> None:
    s = Slider(value=0.5, min_value=0.0, max_value=1.0, disabled=True, length=200)
    s.set_layout_rect(0, 0, 200, 48)

    class _DummyCanvas:
        def drawTextBlob(self, *_args, **_kwargs):
            return None

    # Should not raise under disabled state
    s.paint(_DummyCanvas(), 0, 0, 200, 48)


def test_range_slider_paint_disabled_does_not_raise() -> None:
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0, disabled=True, length=200)
    r.set_layout_rect(0, 0, 200, 48)

    class _DummyCanvas:
        def drawTextBlob(self, *_args, **_kwargs):
            return None

    r.paint(_DummyCanvas(), 0, 0, 200, 48)


# --- D6: RangeSlider Tab focus between handles ---


def test_range_slider_tab_switches_active_handle() -> None:
    """Tab should move active handle from 0 to 1."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)

    assert r._active_handle_index == 0

    result = r.on_key_event("tab", 0)

    assert result is True
    assert r._active_handle_index == 1


def test_range_slider_tab_at_last_handle_does_not_go_beyond() -> None:
    """Tab at last handle should stay at handle index 1."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    r._active_handle_index = 1

    result = r.on_key_event("tab", 0)

    assert result is True
    assert r._active_handle_index == 1


def test_range_slider_shift_tab_moves_back() -> None:
    """Shift+Tab should move active handle from 1 to 0."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    r._active_handle_index = 1

    result = r.on_key_event("tab", 1)  # modifiers=1 (MOD_SHIFT)

    assert result is True
    assert r._active_handle_index == 0


def test_range_slider_wants_tab_at_first_handle() -> None:
    """wants_tab should return True when at first handle (forward)."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    r._active_handle_index = 0

    assert r._wants_tab(0) is True


def test_range_slider_wants_tab_at_last_handle_returns_false() -> None:
    """wants_tab should return False when at last handle (forward)."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    r._active_handle_index = 1

    assert r._wants_tab(0) is False


def test_range_slider_wants_tab_shift_at_first_handle_returns_false() -> None:
    """Shift+Tab wants_tab should return False when at first handle."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    r._active_handle_index = 0

    assert r._wants_tab(1) is False


def test_range_slider_wants_tab_shift_at_last_handle() -> None:
    """Shift+Tab wants_tab should return True when at last handle."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    r._active_handle_index = 1

    assert r._wants_tab(1) is True


def test_slider_wants_tab_always_false() -> None:
    """Single-handle Slider should never consume Tab."""
    s = Slider(value=0.5, min_value=0.0, max_value=1.0)

    assert s._wants_tab(0) is False
    assert s._wants_tab(1) is False


def test_range_slider_arrow_key_moves_active_handle_value() -> None:
    """Arrow key should move the value of the active handle."""
    r = RangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)

    # Tab to second handle
    r.on_key_event("tab", 0)
    assert r._active_handle_index == 1

    old_end = r.value_end
    r.on_key_event("right", 0)

    assert r.value_end > old_end
