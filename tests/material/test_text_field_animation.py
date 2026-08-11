from unittest.mock import MagicMock
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.animation import Animatable
from nuiitivet.widgets.interaction import FocusSource


def test_text_field_uses_animatable_label_progress():
    tf = TextField(value="")
    assert isinstance(tf._label_progress, Animatable)
    assert tf._label_progress.value == 0.0
    assert tf._label_progress.target == 0.0

    tf = TextField(value="Hello")
    assert isinstance(tf._label_progress, Animatable)
    assert tf._label_progress.value == 1.0
    assert tf._label_progress.target == 1.0


def test_text_field_animates_label_on_focus(nuiitivet_clock):
    # The harness clock holds the Animatable ticker without firing it, so the
    # test steps the animation by hand instead of waiting.
    tf = TextField(value="")
    # Simulate mount to allow invalidate (though Animatable doesn't check mount)
    tf._app = MagicMock()

    # Focus
    tf._editable.state.focused = True
    tf._on_editable_focus_change(True, FocusSource.KEYBOARD)

    assert tf._label_progress.target == 1.0
    # Start should be 0.0
    assert tf._label_progress.value == 0.0

    # Verify ticker was scheduled
    tickers = [p.fn for p in nuiitivet_clock.pending() if p.is_interval]
    assert len(tickers) > 0
    ticker = tickers[0]

    # Step animation
    ticker(0.1)
    assert tf._label_progress.value > 0.0
    assert tf._label_progress.value < 1.0

    # Complete animation
    ticker(0.2)
    assert tf._label_progress.value == 1.0


def test_text_field_animates_indicator_width_on_focus(nuiitivet_clock):
    tf = TextField(
        value="", style=TextFieldStyle.filled().copy_with(indicator_width=1.0, focused_indicator_width=2.0)
    )
    # Initial state
    assert tf._anim_indicator_width.target == 1.0
    assert tf._anim_indicator_width.value == 1.0

    # Focus
    tf._editable.state.focused = True
    tf._on_editable_focus_change(True, FocusSource.KEYBOARD)

    assert tf._anim_indicator_width.target == 2.0

    # Verify ticker scheduled
    tickers = [p.fn for p in nuiitivet_clock.pending() if p.is_interval]
    assert len(tickers) > 0
    ticker = tickers[-1]

    # Step animation
    ticker(0.1)
    assert tf._anim_indicator_width.value > 1.0
    assert tf._anim_indicator_width.value < 2.0
