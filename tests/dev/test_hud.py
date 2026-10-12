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


# --- the splash and the sheet -----------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.armed: list[tuple[Any, float]] = []

    def schedule_once(self, fn: Any, delay: float) -> None:
        self.armed.append((fn, delay))


class _App:
    def __init__(self) -> None:
        self.frames = 0

    def invalidate(self, immediate: bool = False, content: bool = True) -> None:
        assert content is False, "the glass, not the tree"
        self.frames += 1


def _still(monkeypatch: pytest.MonkeyPatch, since: float) -> None:
    import time

    monkeypatch.setattr(hud, "_now", lambda: time.monotonic() + since)


def test_the_splash_shows_for_a_moment_after_entering_and_its_end_is_a_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _Clock()
    monkeypatch.setattr(hud.runtime, "get_clock", lambda: clock)
    app = _App()
    splash = hud.Splash()
    assert splash.text is None

    splash.show(app, "COMMENT MODE")

    assert splash.text == "COMMENT MODE"
    ((hide, delay),) = clock.armed
    assert delay == hud.SPLASH

    hide(0.0)

    assert splash.text is None, "the frame ends it, whatever the clock says"
    assert app.frames == 1, "the frame that takes the splash away"


def test_an_older_frame_does_not_end_a_newer_splash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Leaving within the entry splash's time arms a second frame; the first must not cut the second short."""
    clock = _Clock()
    monkeypatch.setattr(hud.runtime, "get_clock", lambda: clock)
    app = _App()
    splash = hud.Splash()
    splash.show(app, "COMMENT MODE")
    splash.show(app, "COMMENT MODE off")
    first, second = (fn for fn, _delay in clock.armed)

    first(0.0)
    assert splash.text == "COMMENT MODE off"

    second(0.0)
    assert splash.text is None


def test_the_splash_is_drawn_at_the_windows_centre(monkeypatch: pytest.MonkeyPatch) -> None:
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia()
    font, typeface = hud.hud_font(skia)
    placed: list[tuple[float, float]] = []
    monkeypatch.setattr(hud, "paint_caption", lambda _s, _c, _t, _f, _tf, x, y, *a: placed.append((x, y)))

    hud.paint_splash(skia, _Canvas(), "COMMENT MODE", font, typeface, 600.0, 400.0)

    ((x, y),) = placed
    w, h = hud.caption_size("COMMENT MODE", typeface)
    assert x == pytest.approx((600.0 - w) / 2.0) and y == pytest.approx((400.0 - h) / 2.0)


def test_the_help_sheet_lists_every_row_in_one_box() -> None:
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia()
    font, typeface = hud.hud_font(skia)
    canvas = _Canvas()
    rows = (("W / S", "parent / child"), ("Esc", "leave"))

    hud.paint_sheet(skia, canvas, "COMMENT MODE", rows, font, typeface, 600.0, 400.0)

    assert canvas.calls.count("drawRoundRect") == 1
    assert canvas.calls.count("drawTextBlob") == 1 + 2 * len(rows), "the title, then a key and a what per row"


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


def test_the_notices_share_one_box() -> None:
    skia = _skia()
    font, typeface = hud.hud_font(skia)
    canvas = _Canvas()

    hud.paint_hud(
        skia,
        canvas,
        notices=[None, "width is bound to a name", "opening app.py:12"],
        placement=hud.Placement(),
        pointer=None,
        font=font,
        typeface=typeface,
        width=600,
        height=400,
    )

    assert canvas.calls.count("drawRoundRect") == 1
    assert canvas.calls.count("drawTextBlob") == 2, "the two real notices"


def test_nothing_to_say_draws_nothing() -> None:
    skia = _skia()
    font, typeface = hud.hud_font(skia)
    canvas = _Canvas()

    hud.paint_hud(
        skia,
        canvas,
        notices=[None],
        placement=None,
        pointer=None,
        font=font,
        typeface=typeface,
        width=600,
        height=400,
    )

    assert canvas.calls == []


# --- captions inside the window -----------------------------------------------


def test_fit_inside_moves_a_box_the_least_distance_into_the_margins() -> None:
    assert hud.fit_inside((590.0, -22.0), (100.0, 20.0), _WINDOW) == (600.0 - hud.MARGIN - 100.0, hud.MARGIN)
    assert hud.fit_inside((100.0, 100.0), (100.0, 20.0), _WINDOW) == (100.0, 100.0)


def test_a_box_wider_than_the_window_sits_at_the_margin() -> None:
    assert hud.fit_inside((50.0, 50.0), (700.0, 20.0), _WINDOW) == (hud.MARGIN, 50.0)


def test_a_caption_given_the_window_is_drawn_inside_it() -> None:
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        pytest.skip("skia is needed to measure the caption")
    font, typeface = hud.hud_font(skia)
    boxes: list[tuple[float, float, float, float]] = []

    class _Recording(_Canvas):
        def drawRoundRect(self, rect: Any, *_args: Any) -> None:
            boxes.append((rect.left(), rect.top(), rect.width(), rect.height()))

    hud.paint_caption(skia, _Recording(), "Text  |  app.py:42", font, typeface, 590.0, -22.0, _WINDOW)

    ((x, y, w, h),) = boxes
    assert x >= hud.MARGIN and y == hud.MARGIN and x + w <= _WINDOW[0] - hud.MARGIN


def test_a_caption_with_line_breaks_is_as_wide_as_its_longest_line_and_a_row_per_line() -> None:
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        pytest.skip("skia is needed to measure the caption")
    _font, typeface = hud.hud_font(skia)

    one = hud.caption_size("a long first line", typeface)
    two = hud.caption_size("a long first line\nshort", typeface)

    assert two[0] == one[0] and two[1] == one[1] * 2
