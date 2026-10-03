"""Tests for what a Text reuses from one paint to the next."""

from typing import Any, Iterator
from unittest.mock import MagicMock, patch

import pytest

from nuiitivet.observable import Observable
from nuiitivet.rendering.skia.font import set_default_font_family
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.testing import mount
from nuiitivet.theme.plain_theme import PlainTheme
from nuiitivet.widgets import text as text_module
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.text_style import TextStyle

pytestmark = pytest.mark.skipif(get_skia(raise_if_missing=False) is None, reason="skia backend not available")

_BUILDERS = (
    "get_typeface",
    "make_font",
    "make_paint",
    "make_text_blob",
    "measure_text_width",
    "measure_text_ink_bounds",
)


@pytest.fixture
def builders() -> Iterator[dict[str, MagicMock]]:
    """The font helpers a paint may call, wrapped so their calls are counted."""
    mocks = {name: MagicMock(wraps=getattr(text_module, name)) for name in _BUILDERS}
    with patch.multiple(text_module, **mocks):
        yield mocks


def _calls(builders: dict[str, MagicMock]) -> dict[str, int]:
    return {name: mock.call_count for name, mock in builders.items()}


def _paint(widget: Text, width: int = 200, height: int = 40) -> Any:
    """Paint into a mock canvas and return the blobs it was asked to draw."""
    canvas = MagicMock()
    widget.paint(canvas, 0, 0, width, height)
    return [call.args[0] for call in canvas.drawTextBlob.call_args_list]


def _skia_paint(widget: Text) -> Any:
    """Paint into a mock canvas and return the paint the text was drawn with."""
    canvas = MagicMock()
    widget.paint(canvas, 0, 0, 200, 40)
    return canvas.drawTextBlob.call_args.args[3]


def test_repaint_builds_nothing(nuiitivet_mount, builders) -> None:
    widget = Text("Hello")
    nuiitivet_mount(widget)

    first = _paint(widget)
    after_first = _calls(builders)
    second = _paint(widget)

    assert len(first) == 1
    assert second[0] is first[0]
    assert _calls(builders) == after_first


def test_multi_line_repaint_builds_nothing(nuiitivet_mount, builders) -> None:
    widget = Text("one\ntwo\nthree")
    nuiitivet_mount(widget)

    first = _paint(widget, height=80)
    after_first = _calls(builders)
    second = _paint(widget, height=80)

    assert len(first) == 3
    assert all(a is b for a, b in zip(first, second))
    assert _calls(builders) == after_first


def test_moved_text_reuses_its_blob(nuiitivet_mount, builders) -> None:
    widget = Text("Hello")
    nuiitivet_mount(widget)
    first = _paint(widget)
    after_first = _calls(builders)

    canvas = MagicMock()
    widget.paint(canvas, 30, 50, 200, 40)

    assert canvas.drawTextBlob.call_args.args[0] is first[0]
    assert _calls(builders) == after_first


def test_label_change_rebuilds(nuiitivet_mount, builders) -> None:
    class _Model:
        label = Observable("Hello")

    model = _Model()
    widget = Text(model.label)
    nuiitivet_mount(widget)
    first = _paint(widget)
    built = builders["make_text_blob"].call_count

    model.label.value = "World"
    second = _paint(widget)

    assert second[0] is not first[0]
    assert builders["make_text_blob"].call_count == built + 1
    assert builders["make_text_blob"].call_args.args[0] == "World"


def test_box_change_rebuilds(nuiitivet_mount, builders) -> None:
    widget = Text("The quick brown fox jumps over the lazy dog")
    nuiitivet_mount(widget)

    assert len(_paint(widget, width=400)) == 1
    assert len(_paint(widget, width=80, height=200)) > 1


def test_font_default_change_rebuilds(nuiitivet_mount, builders) -> None:
    widget = Text("Hello")
    nuiitivet_mount(widget)
    first = _paint(widget)
    resolved = builders["get_typeface"].call_count
    built = builders["make_text_blob"].call_count

    set_default_font_family("Courier New")
    try:
        second = _paint(widget)
    finally:
        set_default_font_family(None)

    assert builders["get_typeface"].call_count == resolved + 1
    assert builders["get_typeface"].call_args.kwargs["family_candidates"][0] == "Courier New"
    # The machine may lack the family; the blob follows the typeface that resolved.
    rebuilt = builders["make_text_blob"].call_count > built
    assert rebuilt == (second[0] is not first[0])


def test_theme_change_rebuilds_the_paint(builders) -> None:
    widget = Text("Hello")
    with mount(widget, theme=PlainTheme.light()) as host:
        host.layout(200, 40)
        first = _skia_paint(widget)
        assert _skia_paint(widget) is first

        host.push_theme(PlainTheme.dark())

        assert _skia_paint(widget) is not first


def test_replaced_style_rebuilds_the_paint(nuiitivet_mount, builders) -> None:
    widget = Text("Hello", style=TextStyle(color="#112233"))
    nuiitivet_mount(widget)
    first = _skia_paint(widget)
    assert _skia_paint(widget) is first

    # How a button recolours its label.
    widget._style = TextStyle(color="#445566")
    second = _skia_paint(widget)

    assert second is not first
    assert second.getColor() != first.getColor()


def test_detached_text_keeps_no_paint(builders) -> None:
    widget = Text("Hello")
    with mount(widget, scope=False) as host:
        host.layout(200, 40)
        first = _skia_paint(widget)

        assert _skia_paint(widget) is not first
