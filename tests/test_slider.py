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
