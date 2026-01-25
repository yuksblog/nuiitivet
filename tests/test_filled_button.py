from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.buttons import FilledButton
from tests.helpers.pointer import send_pointer_event_for_test


def test_filled_preferred_size_and_click():
    called = []

    def on_click():
        called.append(True)

    b = FilledButton("ok", on_click=on_click)
    w, h = b.preferred_size()
    assert w >= 64
    assert h == 48
    assert send_pointer_event_for_test(b, PointerEventType.PRESS) is True
    assert called == []
    assert getattr(b.state, "pressed", False) is True
    assert send_pointer_event_for_test(b, PointerEventType.RELEASE) is True
    assert called == [True]
    assert getattr(b.state, "pressed", False) is False


def test_filled_hover_and_hit_test():
    b = FilledButton("ok")
    b.set_last_rect(10, 10, 100, 40)
    assert send_pointer_event_for_test(b, PointerEventType.HOVER, 20, 20) is True
    assert b.state.hovered is True
    assert send_pointer_event_for_test(b, PointerEventType.HOVER, 0, 0) is False
    assert b.state.hovered is False
    assert b.hit_test(20, 20) is b
    # assert b.hit_test(0, 0) is None
