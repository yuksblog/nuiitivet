from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.buttons import (
    ElevatedButton,
    FilledTonalButton,
    FloatingActionButton,
    OutlinedButton,
    TextButton,
)
from tests.helpers.pointer import send_pointer_event_for_test


def _basic_button_behavior(btn_class):
    called = []

    def on_click():
        called.append(True)

    b = btn_class("ok", on_click=on_click)
    assert b.preferred_size()[0] > 0
    assert send_pointer_event_for_test(b, PointerEventType.PRESS) is True
    assert called == []
    assert b.state.pressed is True
    assert send_pointer_event_for_test(b, PointerEventType.RELEASE) is True
    assert called == [True]
    assert b.state.pressed is False
    b.set_last_rect(10, 10, 100, 40)
    assert send_pointer_event_for_test(b, PointerEventType.HOVER, 20, 20) is True
    assert b.state.hovered is True
    assert send_pointer_event_for_test(b, PointerEventType.HOVER, 0, 0) is False
    assert b.state.hovered is False
    assert b.hit_test(20, 20) is b


def test_outlined():
    _basic_button_behavior(OutlinedButton)


def test_text():
    _basic_button_behavior(TextButton)


def test_elevated():
    _basic_button_behavior(ElevatedButton)


def test_tonal():
    _basic_button_behavior(FilledTonalButton)


def test_fab():
    _basic_button_behavior(FloatingActionButton)
