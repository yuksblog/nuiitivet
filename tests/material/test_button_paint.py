"""Tests for the work a Button repeats, or does not, within one paint."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from nuiitivet.material.buttons import Button
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.testing import mount

skia = get_skia(raise_if_missing=False)
pytestmark = pytest.mark.skipif(skia is None, reason="skia backend not available")

WIDTH, HEIGHT = 160, 60


def _canvas() -> Any:
    return get_skia(raise_if_missing=True).Surface(WIDTH, HEIGHT).getCanvas()


def _watch_container(button: Button) -> MagicMock:
    watched = MagicMock(wraps=button._container_height_pixels)
    button._container_height_pixels = watched  # type: ignore[method-assign]
    return watched


@pytest.mark.parametrize("style", ["filled", "tonal", "outlined", "elevated", "text"])
def test_a_paint_computes_the_container_once(style) -> None:
    button = Button("Apply", style=getattr(ButtonStyle, style)())
    with mount(button, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(WIDTH, HEIGHT)
        canvas = _canvas()
        button.paint(canvas, 0, 0, WIDTH, HEIGHT)
        computed = _watch_container(button)

        button.paint(canvas, 0, 0, WIDTH, HEIGHT)

    assert computed.call_count == 1


def test_a_hovered_paint_still_computes_the_container_once() -> None:
    button = Button("Apply", style=ButtonStyle.filled())
    with mount(button, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(WIDTH, HEIGHT)
        canvas = _canvas()
        button._get_active_state_layer_opacity = lambda: 0.08  # type: ignore[method-assign]
        button.paint(canvas, 0, 0, WIDTH, HEIGHT)
        computed = _watch_container(button)

        button.paint(canvas, 0, 0, WIDTH, HEIGHT)

    assert computed.call_count == 1


def test_the_container_is_not_remembered_between_paints() -> None:
    button = Button("Apply", style=ButtonStyle.filled())
    with mount(button, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(WIDTH, HEIGHT)
        button.paint(_canvas(), 0, 0, WIDTH, HEIGHT)
        computed = _watch_container(button)

        assert button._container_memo is None
        first = button._container_in(0, 0, WIDTH, HEIGHT)
        second = button._container_in(0, 0, WIDTH, HEIGHT)

    assert first == second
    assert computed.call_count == 2


def test_a_repaint_replays_the_background() -> None:
    button = Button("Apply", style=ButtonStyle.filled())
    with mount(button, theme=MaterialThemeFactory.light("#6750A4")) as host:
        host.layout(WIDTH, HEIGHT)
        canvas = _canvas()
        button.paint(canvas, 0, 0, WIDTH, HEIGHT)
        recorded = MagicMock(wraps=button._begin_paint_cache)
        button._begin_paint_cache = recorded  # type: ignore[method-assign]

        button.paint(canvas, 0, 0, WIDTH, HEIGHT)

    assert recorded.call_count == 0
