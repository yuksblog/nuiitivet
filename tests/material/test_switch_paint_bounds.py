"""A switch paints its outline inside the track and declares all its overflow."""

from typing import Tuple

import pytest

from nuiitivet.material.selection_controls import Switch

skia = pytest.importorskip("skia", reason="rasterizing the switch needs skia-python")

_PAD = 40

FORM_FACTORS = ["desktop", "mobile"]


@pytest.fixture(params=FORM_FACTORS)
def form_factor(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> str:
    from nuiitivet.material.theme import form_factor

    monkeypatch.setattr(form_factor, "DEFAULT_FORM_FACTOR", request.param)
    return str(request.param)


def _painted_bounds(switch: Switch) -> Tuple[int, int, int, int]:
    """Return the painted pixels' bounds relative to the switch's rect, as (left, top, right, bottom)."""
    width, height = switch.preferred_size()
    surface = skia.Surface(width + _PAD * 2, height + _PAD * 2)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    switch.paint(canvas, _PAD, _PAD, width, height)
    alpha = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, 3]
    rows = [y for y in range(alpha.shape[0]) if alpha[y].any()]
    cols = [x for x in range(alpha.shape[1]) if alpha[:, x].any()]
    return (cols[0] - _PAD, rows[0] - _PAD, cols[-1] + 1 - _PAD, rows[-1] + 1 - _PAD)


def test_unchecked_switch_paints_inside_its_track(form_factor: str) -> None:
    switch = Switch(checked=False)
    width, height = switch.preferred_size()

    left = (width - 52) // 2
    top = (height - 32) // 2
    assert _painted_bounds(switch) == (left, top, left + 52, top + 32)


@pytest.mark.parametrize("checked, disabled", [(False, False), (True, False), (False, True)])
def test_paint_outsets_cover_everything_painted_outside(
    form_factor: str, checked: bool, disabled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    switch = Switch(checked=checked, disabled=disabled)
    if not disabled:
        monkeypatch.setattr(Switch, "_get_active_state_layer_opacity", lambda self: 0.12)
        monkeypatch.setattr(Switch, "should_show_focus_ring", property(lambda self: True))
    width, height = switch.preferred_size()

    left, top, right, bottom = _painted_bounds(switch)
    out_left, out_top, out_right, out_bottom = switch.paint_outsets()

    assert left >= -out_left
    assert top >= -out_top
    assert right <= width + out_right
    assert bottom <= height + out_bottom
