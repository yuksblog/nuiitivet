import pytest

from nuiitivet.animation import Animation
from nuiitivet.runtime.app import App
from nuiitivet.widgeting.widget import Widget


class DummyWidget(Widget):
    def build(self):
        return None

    def paint(self, canvas, x, y, width, height):
        return None


def test_animation_delay_emits_zero_once():
    calls: list[float] = []

    anim = Animation(duration=0.1, delay=0.2, on_update=lambda value: calls.append(value))
    assert calls == [0.0]

    anim.update(0.05)
    anim.update(0.05)
    assert calls == [0.0]

    anim.update(0.2)
    assert pytest.approx(1.0) == calls[-1]


def test_app_animate_runs_and_returns_handle():
    widget = DummyWidget()
    app = App(widget)
    widget.mount(app)

    values: list[float] = []
    handle = app.animate(duration=0.1, on_update=lambda p: values.append(p))

    manager = app.animation_manager
    assert manager is not None

    manager.step(0.05)
    assert any(value > 0 for value in values)

    handle.cancel()
    assert not handle.is_running


def test_widget_animate_value_updates_attribute():
    widget = DummyWidget()
    widget.opacity = 0.0

    app = App(widget)
    widget.mount(app)

    widget.animate_value(target=1.0, duration=0.2, start=0.0, attr="opacity")
    manager = app.animation_manager
    assert manager is not None

    manager.step(0.1)
    assert 0.0 < widget.opacity < 1.0

    manager.step(0.2)
    assert pytest.approx(1.0, rel=1e-3) == widget.opacity
