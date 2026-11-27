"""A disabled TextField paints the MD3 disabled state, in both styles."""

from __future__ import annotations

from typing import Any, Optional, Tuple

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.widgeting.widget import Widget
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable.value import State
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.theme import Theme

skia = pytest.importorskip("skia", reason="reading painted pixels needs skia-python")

STYLES = {"filled": TextFieldStyle.filled, "outlined": TextFieldStyle.outlined}

# One 8-bit step of rounding either way, plus anti-aliasing inside a glyph.
_ALPHA_TOLERANCE = 3


def _alpha(opacity: float) -> int:
    return round(255 * opacity)


def _field(style: TextFieldStyle, **kwargs: Any) -> TextField:
    return TextField(
        "abc",
        label="Label",
        leading_icon="person",
        trailing_icon="close",
        supporting_text="Help",
        style=style,
        width=240,
        **kwargs,
    )


def _mount(nuiitivet_app, tf: TextField) -> Any:
    return nuiitivet_app(Column([tf], padding=10), size=(300, 140))


def _rect(widget: Optional[Widget]) -> Tuple[int, int, int, int]:
    """The widget's laid-out rect, relative to its parent."""
    assert widget is not None and widget.layout_rect is not None
    x, y, w, h = widget.layout_rect
    return (int(x), int(y), int(w), int(h))


def _render(tf: TextField) -> Any:
    """Paint ``tf`` alone on a transparent surface; return unpremultiplied RGBA pixels."""
    _, _, w, h = _rect(tf)
    surface = skia.Surface(w, h)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    tf.paint(canvas, 0, 0, w, h)
    return surface.makeImageSnapshot().toarray(
        colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType
    )


def _densest(px: Any, rect: Tuple[int, int, int, int]) -> Tuple[Tuple[int, int, int], int]:
    """The colour and alpha of the most opaque pixel inside ``rect``."""
    x, y, w, h = rect
    region = px[y : y + h, x : x + w]
    alpha = region[:, :, 3]
    row, col = divmod(int(alpha.argmax()), w)
    r, g, b = (int(c) for c in region[row, col, :3])
    return (r, g, b), int(alpha.max())


def _supporting_rect(tf: TextField) -> Tuple[int, int, int, int]:
    _, _, w, h = _rect(tf)
    return (0, h - tf._error_height, w, tf._error_height)


def _container_probe(tf: TextField) -> Tuple[int, int]:
    """A point inside the container, clear of the label, the text and the icons."""
    _, _, w, h = _rect(tf)
    return (w // 2, h - tf._error_height - 4)


def _near(rgb: Tuple[int, int, int], expected: Tuple[int, int, int]) -> bool:
    return all(abs(a - b) <= 2 for a, b in zip(rgb, expected))


def _rgb(spec: Any, tf: TextField) -> Tuple[int, int, int]:
    r, g, b, _ = resolve_color_to_rgba(spec, theme=Theme.of(tf))
    return (r, g, b)


def test_presets_carry_the_md3_disabled_colors() -> None:
    filled = TextFieldStyle.filled()
    assert filled.disabled_container_color == (ColorRole.ON_SURFACE, 0.04)
    assert filled.disabled_indicator_color == (ColorRole.ON_SURFACE, 0.38)

    outlined = TextFieldStyle.outlined()
    assert outlined.disabled_container_color == (0, 0, 0, 0)
    assert outlined.disabled_indicator_color == (ColorRole.ON_SURFACE, 0.12)

    for style in (filled, outlined):
        assert style.disabled_text_color == (ColorRole.ON_SURFACE, 0.38)
        assert style.disabled_label_color == (ColorRole.ON_SURFACE, 0.38)
        assert style.disabled_supporting_text_color == (ColorRole.ON_SURFACE, 0.38)
        assert style.disabled_icon_color == (ColorRole.ON_SURFACE, 0.38)


@pytest.mark.parametrize("mode", list(STYLES))
def test_disabled_field_paints_each_element_at_its_md3_value(nuiitivet_app, mode: str) -> None:
    style = STYLES[mode]()
    tf = _field(style, disabled=True)
    _mount(nuiitivet_app, tf)
    px = _render(tf)
    on_surface = _rgb(ColorRole.ON_SURFACE, tf)
    theme = Theme.of(tf)

    cx, cy = _container_probe(tf)
    container_alpha = _alpha(0.04) if mode == "filled" else 0
    assert abs(int(px[cy, cx, 3]) - container_alpha) <= 1

    assert tf._anim_indicator_color.value == resolve_color_to_rgba(style.disabled_indicator_color, theme=theme)
    assert tf._anim_label_color.value == resolve_color_to_rgba((ColorRole.ON_SURFACE, 0.38), theme=theme)

    # Inside the container a glyph lands on the filled container's 4%.
    inside = 0.38 + 0.04 * (1 - 0.38) if mode == "filled" else 0.38
    for rect in (_rect(tf.leading_icon), _rect(tf.trailing_icon)):
        rgb, alpha = _densest(px, rect)
        assert abs(alpha - _alpha(inside)) <= _ALPHA_TOLERANCE
        assert _near(rgb, on_surface)
    # Small text may cover no pixel whole on every platform, so its alpha only has a ceiling.
    for rect, opacity in ((_rect(tf._editable), inside), (_supporting_rect(tf), 0.38)):
        rgb, alpha = _densest(px, rect)
        assert _alpha(opacity) // 2 < alpha <= _alpha(opacity) + _ALPHA_TOLERANCE
        assert _near(rgb, on_surface)


def test_tappable_icon_is_tinted_once_not_dimmed_twice(nuiitivet_app) -> None:
    tf = _field(TextFieldStyle.outlined(), disabled=True, on_tap_trailing_icon=lambda: None)
    _mount(nuiitivet_app, tf)

    _, alpha = _densest(_render(tf), _rect(tf.trailing_icon))
    assert abs(alpha - _alpha(0.38)) <= _ALPHA_TOLERANCE


def test_toggling_a_disabled_state_repaints_the_same_field(nuiitivet_app) -> None:
    disabled = State(False)
    style = TextFieldStyle.outlined()
    tf = _field(style, disabled=disabled)
    app = _mount(nuiitivet_app, tf)
    editable = tf._editable
    theme = Theme.of(tf)

    _, enabled_alpha = _densest(_render(tf), _rect(tf.leading_icon))
    assert enabled_alpha == 255

    disabled.value = True
    app.settle()
    assert tf._editable is editable
    assert tf._editable.text_color == style.disabled_text_color
    assert tf._anim_label_color.target == resolve_color_to_rgba(style.disabled_label_color, theme=theme)
    assert tf._anim_indicator_color.target == resolve_color_to_rgba(style.disabled_indicator_color, theme=theme)
    _, alpha = _densest(_render(tf), _rect(tf.leading_icon))
    assert abs(alpha - _alpha(0.38)) <= _ALPHA_TOLERANCE

    disabled.value = False
    app.settle()
    assert tf._editable.text_color == style.text_color
    assert tf._anim_label_color.target == resolve_color_to_rgba(style.label_color, theme=theme)
    assert tf._anim_indicator_color.target == resolve_color_to_rgba(style.indicator_color, theme=theme)
    _, alpha = _densest(_render(tf), _rect(tf.leading_icon))
    assert alpha == 255


@pytest.mark.parametrize("mode", list(STYLES))
def test_disabled_wins_over_error(nuiitivet_app, mode: str) -> None:
    style = STYLES[mode]()
    tf = _field(style, disabled=True, is_error=True)
    _mount(nuiitivet_app, tf)
    theme = Theme.of(tf)

    assert tf._anim_label_color.value == resolve_color_to_rgba(style.disabled_label_color, theme=theme)
    assert tf._anim_indicator_color.value == resolve_color_to_rgba(style.disabled_indicator_color, theme=theme)
    rgb, alpha = _densest(_render(tf), _supporting_rect(tf))
    assert _near(rgb, _rgb(ColorRole.ON_SURFACE, tf))
    assert alpha <= _alpha(0.38) + _ALPHA_TOLERANCE


def test_a_custom_style_overrides_the_disabled_colors(nuiitivet_app) -> None:
    style = TextFieldStyle.outlined().copy_with(
        disabled_container_color="#0000ff",
        disabled_indicator_color="#ff00ff",
        disabled_text_color="#ff0000",
        disabled_label_color="#00ffff",
        disabled_supporting_text_color="#ffff00",
        disabled_icon_color="#00ff00",
    )
    tf = _field(style, disabled=True)
    _mount(nuiitivet_app, tf)
    px = _render(tf)

    cx, cy = _container_probe(tf)
    assert tuple(int(c) for c in px[cy, cx]) == (0, 0, 255, 255)
    assert tf._editable.text_color == "#ff0000"
    assert tf._anim_label_color.value == (0, 255, 255, 255)
    assert tf._anim_indicator_color.value == (255, 0, 255, 255)
    assert _holds(px, _rect(tf.leading_icon), (0, 255, 0, 255))
    assert _holds(px, _rect(tf.trailing_icon), (0, 255, 0, 255))
    assert _near(_densest(px, _supporting_rect(tf))[0], (255, 255, 0))


def _holds(px: Any, rect: Tuple[int, int, int, int], rgba: Tuple[int, int, int, int]) -> bool:
    """Whether some pixel inside ``rect`` is exactly ``rgba``."""
    x, y, w, h = rect
    region = px[y : y + h, x : x + w]
    return bool((region == rgba).all(axis=2).any())
