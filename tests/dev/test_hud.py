"""Tests for the badge the dev modes share: where it sits and how it wraps."""

from __future__ import annotations

from typing import Any

import pytest

from nuiitivet.dev import hud

_WINDOW = (600.0, 400.0)
_NARROW = (200.0, 44.0)
_WIDE = (400.0, 44.0)


def _home(box: tuple[float, float]) -> tuple[float, float]:
    return (hud.MARGIN, _WINDOW[1] - hud.MARGIN - box[1])


class _Canvas:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        def _record(*_args: Any, **_kwargs: Any) -> None:
            self.calls.append(name)

        return _record


# --- placement --------------------------------------------------------------


def test_the_badge_sits_at_the_bottom_left() -> None:
    assert hud.Placement().place(_NARROW, _WINDOW, None) == _home(_NARROW)


def test_a_pointer_far_away_leaves_it_at_home() -> None:
    assert hud.Placement().place(_NARROW, _WINDOW, (500.0, 50.0)) == _home(_NARROW)


def test_a_narrow_badge_steps_across_when_the_pointer_comes_near() -> None:
    """Narrower than half the window, so the other side is clear of the pointer."""
    placement = hud.Placement()
    x, y = _home(_NARROW)

    assert placement.place(_NARROW, _WINDOW, (x + _NARROW[0] + 30.0, y + 10.0)) == (
        _WINDOW[0] - hud.MARGIN - _NARROW[0],
        y,
    )


def test_a_wide_badge_goes_to_the_top_instead() -> None:
    """Wider than half the window, a horizontal flip would still be under the pointer."""
    placement = hud.Placement()
    x, y = _home(_WIDE)

    assert placement.place(_WIDE, _WINDOW, (x + 100.0, y - 30.0)) == (hud.MARGIN, hud.MARGIN)


def test_it_comes_back_only_once_the_pointer_is_well_clear() -> None:
    """Moving as soon as the pointer left the near zone would flicker at the edge."""
    placement = hud.Placement()
    x, y = _home(_NARROW)
    placement.place(_NARROW, _WINDOW, (x + 10.0, y + 10.0))
    assert placement.away

    still_close = (x + _NARROW[0] + 60.0, y + 10.0)
    assert placement.place(_NARROW, _WINDOW, still_close) != _home(_NARROW)

    far = (x + _NARROW[0] + 200.0, y - 200.0)
    assert placement.place(_NARROW, _WINDOW, far) == _home(_NARROW)


def test_a_pointer_move_says_whether_the_badge_would_move() -> None:
    """A mode repaints only when the hover changes, so it has to ask."""
    placement = hud.Placement()
    assert placement.crosses((0.0, 0.0)) is False, "nothing drawn yet"
    x, y = _home(_NARROW)
    placement.place(_NARROW, _WINDOW, (500.0, 50.0))

    assert placement.crosses((500.0, 60.0)) is False
    assert placement.crosses((x + 10.0, y + 10.0)) is True

    placement.place(_NARROW, _WINDOW, (x + 10.0, y + 10.0))
    assert placement.crosses((x + _NARROW[0] + 60.0, y)) is False, "still inside the return zone"
    assert placement.crosses((500.0, 50.0)) is True


def test_a_reset_brings_it_home_at_once() -> None:
    placement = hud.Placement()
    x, y = _home(_NARROW)
    placement.place(_NARROW, _WINDOW, (x + 10.0, y + 10.0))

    placement.reset()

    assert placement.place(_NARROW, _WINDOW, None) == _home(_NARROW)


# --- drawing ----------------------------------------------------------------


def _skia() -> Any:
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        pytest.skip("skia is not available")
    return skia


def test_the_lines_share_one_box() -> None:
    skia = _skia()
    font, typeface = hud.hud_font(skia)
    canvas = _Canvas()

    hud.paint_hud(
        skia,
        canvas,
        mode_line="SELECT",
        hints=("Esc leave",),
        notices=[None, "opening app.py:12"],
        placement=hud.Placement(),
        pointer=None,
        font=font,
        typeface=typeface,
        width=600,
        height=400,
    )

    assert canvas.calls.count("drawRoundRect") == 1
    assert canvas.calls.count("drawTextBlob") == 3, "the mode line, the hint line, and the one real notice"


def test_nothing_to_say_draws_nothing() -> None:
    skia = _skia()
    font, typeface = hud.hud_font(skia)
    canvas = _Canvas()

    hud.paint_hud(
        skia,
        canvas,
        mode_line=None,
        hints=(),
        notices=[None],
        placement=None,
        pointer=None,
        font=font,
        typeface=typeface,
        width=600,
        height=400,
    )

    assert canvas.calls == []


def test_hints_wrap_instead_of_running_off_a_narrow_window() -> None:
    """A dev app is often a few hundred pixels wide; a hint off the edge teaches nothing."""
    from nuiitivet.rendering.skia.font import measure_text_width

    _font, typeface = hud.hud_font(_skia())
    parts = ("drag a corner resize", "drag reorder / move / align", "click select", "Ctrl+Shift+Click source")
    limit = 200.0

    lines = hud.wrap_hints(parts, typeface, limit)

    assert len(lines) > 1
    for line in lines:
        assert measure_text_width(typeface, hud.FONT_SIZE, line) <= limit
