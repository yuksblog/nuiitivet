from unittest.mock import MagicMock
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.animation import Animatable
from nuiitivet.observable import runtime


class _FakeClock:
    def __init__(self):
        self.scheduled = []

    def schedule_interval(self, callback, interval):
        self.scheduled.append(callback)

    def unschedule(self, callback):
        if callback in self.scheduled:
            self.scheduled.remove(callback)


def test_text_field_uses_animatable_label_progress():
    tf = TextField(value="")
    assert isinstance(tf._label_progress, Animatable)
    assert tf._label_progress.value == 0.0
    assert tf._label_progress.target == 0.0

    tf = TextField(value="Hello")
    assert isinstance(tf._label_progress, Animatable)
    assert tf._label_progress.value == 1.0
    assert tf._label_progress.target == 1.0


def test_text_field_animates_label_on_focus():
    # Setup fake clock to test Animatable ticking without waiting
    fake_clock = _FakeClock()
    original_clock = runtime.clock
    runtime.clock = fake_clock

    try:
        tf = TextField(value="")
        # Simulate mount to allow invalidate (though Animatable doesn't check mount)
        tf._app = MagicMock()

        # Focus
        tf._editable.state.focused = True
        tf._on_editable_focus_change(True)

        assert tf._label_progress.target == 1.0
        # Start should be 0.0
        assert tf._label_progress.value == 0.0

        # Verify ticker was scheduled
        assert len(fake_clock.scheduled) > 0
        ticker = fake_clock.scheduled[0]

        # Step animation
        ticker(0.1)
        assert tf._label_progress.value > 0.0
        assert tf._label_progress.value < 1.0

        # Complete animation
        ticker(0.2)
        assert tf._label_progress.value == 1.0

    finally:
        runtime.clock = original_clock


def test_text_field_animates_indicator_width_on_focus():
    fake_clock = _FakeClock()
    original_clock = runtime.clock
    runtime.clock = fake_clock

    try:
        tf = TextField(
            value="", style=TextFieldStyle.filled().copy_with(indicator_width=1.0, focused_indicator_width=2.0)
        )
        # Initial state
        assert tf._anim_indicator_width.target == 1.0
        assert tf._anim_indicator_width.value == 1.0

        # Focus
        tf._editable.state.focused = True
        tf._on_editable_focus_change(True)

        assert tf._anim_indicator_width.target == 2.0

        # Verify ticker scheduled
        assert len(fake_clock.scheduled) > 0
        ticker = fake_clock.scheduled[-1]

        # Step animation
        ticker(0.1)
        assert tf._anim_indicator_width.value > 1.0
        assert tf._anim_indicator_width.value < 2.0

    finally:
        runtime.clock = original_clock
