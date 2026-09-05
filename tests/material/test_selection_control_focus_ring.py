"""Selection controls draw the standard focus ring around their state-layer circle."""

from nuiitivet.material.selection_controls import Checkbox, RadioButton, Switch
from nuiitivet.material.styles.checkbox_style import CheckboxStyle
from nuiitivet.material.styles.radio_button_style import RadioButtonStyle
from nuiitivet.material.styles.switch_style import SwitchStyle


def _record_focus_ring_calls(widget):
    calls = []

    def record(canvas, x, y, width, height, radii):
        calls.append((x, y, width, height, radii))

    widget.draw_focus_ring = record  # type: ignore[method-assign]
    return calls


def test_checkbox_focus_ring_hugs_state_layer_circle():
    c = Checkbox(style=CheckboxStyle())
    calls = _record_focus_ring_calls(c)

    c.draw_focus_indicator(None, 0, 0, 48, 48)

    assert len(calls) == 1
    x, y, width, height, radii = calls[0]
    assert width == height == 40.0  # state layer diameter at 48dp touch target
    assert (x, y) == (4.0, 4.0)  # centered in the touch target
    assert radii == [20.0] * 4  # circular ring


def test_radio_button_focus_ring_hugs_state_layer_circle():
    r = RadioButton("a", style=RadioButtonStyle())
    calls = _record_focus_ring_calls(r)

    r.draw_focus_indicator(None, 0, 0, 48, 48)

    assert len(calls) == 1
    x, y, width, height, radii = calls[0]
    assert width == height == 40.0
    assert (x, y) == (4.0, 4.0)
    assert radii == [20.0] * 4


def test_switch_focus_ring_hugs_the_track():
    """The switch ring is a pill around the track, not a circle over the thumb."""
    style = SwitchStyle()
    unchecked = Switch(checked=False, style=style)
    checked = Switch(checked=True, style=style)
    unchecked_calls = _record_focus_ring_calls(unchecked)
    checked_calls = _record_focus_ring_calls(checked)

    unchecked.draw_focus_indicator(None, 0, 0, 48, 48)
    checked.draw_focus_indicator(None, 0, 0, 48, 48)

    assert len(unchecked_calls) == 1 and len(checked_calls) == 1

    sizes = style.compute_sizes(48)
    track_w = float(sizes["track_width"])
    track_h = float(sizes["track_height"])
    expected = (
        (48.0 - track_w) / 2.0,
        (48.0 - track_h) / 2.0,
        track_w,
        track_h,
        [track_h / 2.0] * 4,
    )

    # The ring hugs the track outline and stays put as the thumb moves.
    assert unchecked_calls[0] == expected
    assert checked_calls[0] == expected
