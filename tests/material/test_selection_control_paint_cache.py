"""Tests for what a Checkbox and a Switch reuse from one paint to the next."""

from typing import Any, Callable, Iterator
from unittest.mock import MagicMock, patch

import pytest

from nuiitivet.material.selection_controls import Checkbox, Switch
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.observable import Observable
from nuiitivet.rendering.skia import color as color_module
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.testing import mount

skia = get_skia(raise_if_missing=False)
pytestmark = pytest.mark.skipif(skia is None, reason="skia backend not available")

SIZE = 48
CONTROLS: list[Callable[..., Any]] = [Checkbox, Switch]


@pytest.fixture
def made() -> Iterator[MagicMock]:
    """Counts the skia.Paint objects that get built."""
    with patch.object(color_module, "make_paint", wraps=color_module.make_paint) as mock:
        yield mock


def _watch(widget: Any) -> MagicMock:
    """Count how often the widget resolves its colours and sizes."""
    watched = MagicMock(wraps=widget._resolve_look)
    widget._resolve_look = watched
    return watched


def _paint(widget: Any) -> list[int]:
    """Paint into a mock canvas and return the colours it drew with, in order."""
    canvas = MagicMock()
    widget.paint(canvas, 0, 0, SIZE, SIZE)
    paint_type = get_skia(raise_if_missing=True).Paint
    colours = []
    for call in canvas.mock_calls:
        for arg in call.args:
            if isinstance(arg, paint_type):
                colours.append(arg.getColor())
    return colours


def _pin(widget: Any, progress: float) -> None:
    widget._get_selection_progress = lambda: progress


@pytest.mark.parametrize("control", CONTROLS)
@pytest.mark.parametrize("checked", [False, True])
def test_repaint_resolves_and_builds_nothing(control, checked, made) -> None:
    widget = control(checked)
    resolved = _watch(widget)
    with mount(widget, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(SIZE, SIZE)
        first = _paint(widget)
        resolved_once, made_once = resolved.call_count, made.call_count
        second = _paint(widget)

    assert first and second == first
    assert resolved.call_count == resolved_once == 1
    assert made.call_count == made_once


@pytest.mark.parametrize("control", CONTROLS)
def test_theme_change_resolves_again(control) -> None:
    widget = control(True)
    resolved = _watch(widget)
    with mount(widget, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(SIZE, SIZE)
        light = _paint(widget)
        host.push_theme(MaterialThemeFactory.dark("#6750A4"))
        dark = _paint(widget)

    assert resolved.call_count == 2
    assert dark != light


@pytest.mark.parametrize("control", CONTROLS)
def test_disabling_resolves_again(control) -> None:
    class _Model:
        disabled = Observable(False)

    model = _Model()
    widget = control(True, disabled=model.disabled)
    resolved = _watch(widget)
    with mount(widget, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(SIZE, SIZE)
        enabled = _paint(widget)
        model.disabled.value = True
        host.settle()
        disabled = _paint(widget)

    assert resolved.call_count == 2
    assert disabled != enabled


def test_switch_value_change_resolves_again() -> None:
    class _Model:
        checked = Observable(False)

    model = _Model()
    widget = Switch(model.checked)
    resolved = _watch(widget)
    with mount(widget, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(SIZE, SIZE)
        off = _paint(widget)
        model.checked.value = True
        host.settle()
        on = _paint(widget)

    assert resolved.call_count == 2
    assert on != off


def test_checkbox_animation_frame_scales_the_alpha() -> None:
    widget = Checkbox(True)
    resolved = _watch(widget)
    with mount(widget, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(SIZE, SIZE)
        _pin(widget, 1.0)
        settled = _paint(widget)
        _pin(widget, 0.5)
        halfway = _paint(widget)
        _pin(widget, 1.0)
        back = _paint(widget)

    # Outline, fill, and the two strokes of the mark.
    assert len(settled) == len(halfway) == 4
    assert halfway[0] == settled[0]
    assert [colour >> 24 for colour in halfway[1:]] == [128, 128, 128]
    assert [colour >> 24 for colour in settled[1:]] == [255, 255, 255]
    assert back == settled
    assert resolved.call_count == 1


def test_switch_animation_frame_moves_the_thumb() -> None:
    widget = Switch(True)
    with mount(widget, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(SIZE, SIZE)

        def thumb_left(progress: float) -> float:
            _pin(widget, progress)
            canvas = MagicMock()
            widget.paint(canvas, 0, 0, SIZE, SIZE)
            return canvas.drawOval.call_args.args[0].left()

        assert thumb_left(0.0) < thumb_left(0.5) < thumb_left(1.0)
