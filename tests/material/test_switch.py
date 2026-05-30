from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.selection_controls import Switch
from nuiitivet.observable import Observable
from tests.helpers.pointer import send_pointer_event_for_test


def _make_obs(initial: bool):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_switch_toggle_calls_handler_and_updates_state() -> None:
    called: list[bool] = []

    s = Switch(on_change=lambda v: called.append(v))
    assert s.value is False

    assert send_pointer_event_for_test(s, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(s, PointerEventType.RELEASE) is True

    assert s.value is True
    assert called == [True]


def test_switch_state_backed_observable_updates() -> None:
    state = _make_obs(False)
    called: list[bool] = []

    s = Switch(checked=state, on_change=lambda v: called.append(v))

    assert send_pointer_event_for_test(s, PointerEventType.PRESS) is True
    assert send_pointer_event_for_test(s, PointerEventType.RELEASE) is True

    assert state.value is True
    assert called == [True]


def test_switch_disabled_prevents_toggle() -> None:
    called: list[bool] = []

    s = Switch(disabled=True, on_change=lambda v: called.append(v))
    assert s.value is False

    assert send_pointer_event_for_test(s, PointerEventType.PRESS) is False
    assert send_pointer_event_for_test(s, PointerEventType.RELEASE) is False
    assert s.value is False
    assert called == []


def test_switch_preferred_size_default_and_padding() -> None:
    s1 = Switch()
    assert s1.preferred_size() == (48, 48)

    s2 = Switch(size=56)
    assert s2.preferred_size() == (56, 56)

    s3 = Switch(size=48, padding=8)
    assert s3.preferred_size() == (64, 64)
