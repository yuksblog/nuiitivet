"""Tests for the line box a Text measures and paints with."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import skia

from nuiitivet.theme.type_scale import TypeScale, TypeScaleToken
from nuiitivet.widgets.text import TextBase

_GLYPH_SETS = ["xxxx", "gjpqy", "ÅÉ", "x-height and Descenders", "…", ""]


def _baselines(label: str, token: TypeScaleToken, height: float) -> list[float]:
    """Paint ``label`` into a box ``height`` tall and return the y of each line's baseline."""
    canvas = MagicMock()
    TextBase(label, type_scale=token).paint(canvas, 0, 0, 400, int(height))
    return [float(call.args[2]) for call in canvas.drawTextBlob.call_args_list]


@pytest.mark.parametrize(
    "token",
    [TypeScale.HEADLINE_SMALL, TypeScale.BODY_MEDIUM, TypeScale.LABEL_SMALL],
    ids=["headline_small", "body_medium", "label_small"],
)
def test_one_line_is_one_line_height_tall(token: TypeScaleToken) -> None:
    assert TextBase("Dialog title", type_scale=token).preferred_size()[1] == token.line_height


@pytest.mark.parametrize("label", _GLYPH_SETS)
def test_one_line_height_does_not_depend_on_its_glyphs(label: str) -> None:
    assert TextBase(label, type_scale=TypeScale.HEADLINE_SMALL).preferred_size()[1] == 32


def test_many_lines_are_one_line_height_each() -> None:
    token = TypeScale.HEADLINE_SMALL
    one = TextBase("one", type_scale=token).preferred_size()[1]
    three = TextBase("one\ntwo\nthree", type_scale=token).preferred_size()[1]

    assert three == 3 * one


def test_one_line_baseline_is_where_the_first_of_many_lines_has_it() -> None:
    token = TypeScale.HEADLINE_SMALL
    line_height = token.line_height

    one = _baselines("Hg", token, line_height)
    two = _baselines("Hg\nHg", token, 2 * line_height)

    assert one == [two[0]]
    assert two[1] - two[0] == pytest.approx(line_height)


def test_one_line_baseline_does_not_depend_on_its_glyphs() -> None:
    token = TypeScale.BODY_MEDIUM
    baselines = {label: _baselines(label, token, token.line_height) for label in _GLYPH_SETS if label}

    assert len({tuple(ys) for ys in baselines.values()}) == 1, baselines


@pytest.mark.parametrize(
    ("font_size", "lines", "height"),
    [(10, 1, 13), (14, 1, 18), (18, 1, 23), (14, 3, 53)],
    ids=["12.5", "17.5", "22.5", "3 x 17.5"],
)
def test_fractional_line_height_rounds_up_to_hold_its_lines(font_size: int, lines: int, height: int) -> None:
    token = TypeScaleToken.from_size(font_size)
    label = "\n".join(["x"] * lines)

    assert TextBase(label, type_scale=token).preferred_size()[1] == height


def test_soft_wrapped_lines_are_one_line_height_each() -> None:
    token = TypeScale.HEADLINE_SMALL
    text = TextBase("aaa bbb ccc ddd eee fff", type_scale=token)
    width, height = text.preferred_size(max_width=120)
    canvas = MagicMock()

    text.paint(canvas, 0, 0, width, height)

    baselines = [float(call.args[2]) for call in canvas.drawTextBlob.call_args_list]
    assert len(baselines) > 1
    assert height == len(baselines) * token.line_height
    steps = [below - above for above, below in zip(baselines, baselines[1:])]
    assert steps == pytest.approx([token.line_height] * len(steps))


_MARGIN = 80


def _render(text: TextBase, width: int, height: int) -> Any:
    """Paint ``text`` into a ``width`` x ``height`` box with a white margin around it and return the image."""
    surface_type: Any = skia.Surface  # the local stub declares no constructor
    surface = surface_type(width + 2 * _MARGIN, height + 2 * _MARGIN)
    canvas = surface.getCanvas()
    canvas.clear(0xFFFFFFFF)
    text.paint(canvas, _MARGIN, _MARGIN, width, height)
    return surface.makeImageSnapshot()


@pytest.mark.parametrize(
    "token",
    [TypeScale.DISPLAY_LARGE, TypeScale.DISPLAY_MEDIUM, TypeScale.BODY_MEDIUM],
    ids=["display_large", "display_medium", "body_medium"],
)
def test_clipped_line_that_fits_its_box_loses_no_ink(token: TypeScaleToken) -> None:
    """A font taller than the line height reaches past the line box; the clip leaves that ink."""
    label = "Ågjpqy(|)"
    width, height = TextBase(label, type_scale=token).preferred_size()

    visible = _render(TextBase(label, type_scale=token), width, height)
    clipped = _render(TextBase(label, type_scale=token, overflow="clip"), width, height)

    assert bytes(clipped.tobytes()) == bytes(visible.tobytes())


def test_clipped_lines_that_do_not_fit_their_box_are_cut_at_it() -> None:
    token = TypeScale.HEADLINE_SMALL
    line_height = int(token.line_height)
    text = TextBase("Hg\nHg\nHg", type_scale=token, overflow="clip")
    width, _ = text.preferred_size()

    pixels = _render(text, width, line_height).toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3]

    inked_rows = [row for row in range(pixels.shape[0]) if (pixels[row] != 255).any()]
    assert inked_rows
    assert _MARGIN <= inked_rows[0] and inked_rows[-1] < _MARGIN + line_height
