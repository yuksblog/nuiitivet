from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import FocusEvent, Widget


class DummyWidget(Widget):

    def build(self):  # pragma: no cover - builder host not exercised here
        return self

    def on_key_event(self, key: str, modifiers: int = 0) -> bool:
        self._key_events.append((key, modifiers))
        return False

    def on_focus_event(self, event: FocusEvent) -> bool:
        self._focus_events.append(event)
        return False

    def reset_logs(self) -> None:
        self._key_events: list[tuple[str, int]] = []
        self._focus_events: list[FocusEvent] = []


def test_scroll_hooks_run_before_pointer_hooks():
    widget = DummyWidget()
    widget.reset_logs()
    order = []

    def scroll_hook(event):
        order.append(("scroll", event.type))
        return False

    def pointer_hook(event):
        order.append(("pointer", event.type))
        return False

    widget.register_input_hook("scroll", scroll_hook)
    widget.register_input_hook("pointer", pointer_hook)

    event = PointerEvent.scroll_event(1, 0, 0, 0.0, -1.0)
    widget.dispatch_pointer_event(event)

    assert order[0][0] == "scroll"
    assert order[1][0] == "pointer"


def test_key_hook_short_circuits_default_handler():
    widget = DummyWidget()
    widget.reset_logs()
    events = []

    def key_hook(event):
        events.append((event.key, event.modifiers))
        return True

    widget.register_input_hook("key", key_hook)
    handled = widget.handle_key_event("space", modifiers=1)

    assert handled is True
    assert events == [("space", 1)]
    assert widget._key_events == []


def test_focus_hooks_chain_to_on_focus_event():
    widget = DummyWidget()
    widget.reset_logs()
    focus_event = FocusEvent(gained=True, reason="test")

    handled = widget.handle_focus_event(focus_event)

    assert handled is False
    assert widget._focus_events == [focus_event]
